"""Persistent, human-controlled feedback and DeepSeek adjudication for documentation QA.

No API key or conversation is published to generated HTML/JSON reports by default.
The stable identity excludes line numbers and source revisions; stale source is
rejected before adjudication. Human resolution is never set by the AI.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_FEEDBACK = Path('qa/feedback.json')
DEFAULT_FINDINGS = Path('qa/findings.json')
DECISIONS = {'upheld', 'revised', 'withdrawn', 'needs_evidence'}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def normalise(value: Any) -> str:
    return re.sub(r'\s+', ' ', str(value or '')).strip().casefold()


def finding_id(issue: dict) -> str:
    """Order-independent identity for a particular criticism of a source passage.

    Ignore line, severity, confidence, suggested fix and revision. Include the
    criticism to distinguish separate claims citing identical text.
    """
    parts = [str(issue.get('file', '')).replace('\\', '/').removeprefix('./'),
             normalise(issue.get('source')), normalise(issue.get('category')),
             normalise(issue.get('original')), normalise(issue.get('message'))]
    fingerprint = hashlib.sha256('\0'.join(parts).encode('utf-8')).hexdigest()[:24]
    return 'qa-' + fingerprint


def git_document_revision(path: str) -> dict:
    """Record Git revision and actual on-disk bytes (including uncommitted edits)."""
    source = Path(path)
    result = {'git_commit': None, 'content_sha256': None}
    if source.is_file():
        result['content_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    try:
        completed = subprocess.run(['git', 'rev-parse', 'HEAD'], check=False,
                                   capture_output=True, text=True, timeout=8)
        if completed.returncode == 0:
            result['git_commit'] = completed.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def decorate_issues(issues: list[dict]) -> None:
    """Assign deterministic IDs; reject truly identical duplicate findings."""
    seen = set()
    revisions = {}
    for issue in issues:
        identity = finding_id(issue)
        if identity in seen:
            raise ValueError(f'Duplicate QA finding with identical identity: {identity}')
        seen.add(identity)
        issue['issue_id'] = identity
        path = str(issue['file'])
        if path not in revisions:
            revisions[path] = git_document_revision(path)
        issue['document_revision'] = dict(revisions[path])


def _json_read(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('schema_version') != SCHEMA_VERSION:
        raise ValueError(f'Unsupported or invalid QA schema in {path}')
    return payload


def write_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=path.parent, prefix='.' + path.name,
                                         suffix='.tmp', delete=False) as stream:
            tmp = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        tmp.replace(path)
    finally:
        if tmp is not None and tmp.exists():
            tmp.unlink()


def save_findings(issues: list[dict], path: Path = DEFAULT_FINDINGS) -> None:
    write_atomic(path, {'schema_version': SCHEMA_VERSION, 'generated_at': utc_now(),
                        'issues': issues})


def feedback_records(path: Path = DEFAULT_FEEDBACK) -> dict:
    return _json_read(path, {'schema_version': SCHEMA_VERSION, 'records': {}})


def attach_feedback_status(issues: list[dict], feedback_path: Path = DEFAULT_FEEDBACK) -> None:
    records = feedback_records(feedback_path)['records']
    for issue in issues:
        if issue.get('source') != 'ai':
            # These checks have no DeepSeek challenge or human feedback state.
            issue.pop('feedback_status', None)
            issue.pop('human_resolution', None)
            issue.pop('latest_ai_decision', None)
            continue
        record = records.get(issue['issue_id'], {})
        issue['feedback_status'] = record.get('status', 'unreviewed')
        issue['human_resolution'] = record.get('human_resolution')
        issue['latest_ai_decision'] = (record.get('adjudications') or [{}])[-1].get('decision') if record.get('adjudications') else None


def _source_excerpt(source: str, original: str, context: int = 15) -> tuple[int, str]:
    pos = source.find(original)
    if pos < 0:
        raise ValueError('Source excerpt no longer matches this finding. Rerun QA before challenging.')
    lines = source.splitlines()
    line = source[:pos].count('\n') + 1
    start = max(1, line - context)
    end = min(len(lines), line + original.count('\n') + context)
    return line, '\n'.join(f'{index}: {lines[index - 1]}' for index in range(start, end + 1))


def adjudicate(issue: dict, rebuttal: str, discussion: list, api_key: str,
               request_review, *, prior_decisions=None) -> dict:
    """Use the existing DeepSeek JSON client with an evidence-focused prompt."""
    system = '''You are an independent second-pass documentation QA adjudicator.
Use British English. You have the initial review finding and a human objection.
Neither the original AI nor the human is presumed correct. Do not be sycophantic.
Assess only supplied evidence, not invented project facts.
Return a JSON object with exactly: decision (upheld|revised|withdrawn|needs_evidence),
reason (string), evidence (array of exact verbatim quotations from SOURCE CONTEXT),
revised_message (string or null), revised_suggestion (string or null).
Decision meanings: upheld = criticism stands; revised = criticism is partially
valid but must be modified; withdrawn = original criticism is unsupported or false;
needs_evidence = supplied context cannot establish the answer.
Quotes must match the source context exactly, excluding artificial line prefixes.
A withdrawal is allowed and expected when source evidence disproves the criticism.
No decision constitutes a human resolution.'''
    user = json.dumps({'finding': {k: issue.get(k) for k in (
        'issue_id', 'file', 'line', 'source', 'category', 'original',
        'message', 'suggestion', 'severity', 'confidence')},
        'human_rebuttal': rebuttal, 'prior_discussion': discussion[-8:],
        'prior_adjudications': (prior_decisions or [])[-3:],
        'source_context': issue['_source_context']}, ensure_ascii=False)
    result = request_review(system, user, api_key)
    if not isinstance(result, dict) or result.get('decision') not in DECISIONS:
        raise ValueError('DeepSeek returned an invalid adjudication decision')
    if not isinstance(result.get('reason'), str) or not result['reason'].strip():
        raise ValueError('DeepSeek did not provide a reason')
    evidence = result.get('evidence')
    if not isinstance(evidence, list) or not all(isinstance(x, str) for x in evidence):
        raise ValueError('DeepSeek evidence must be an array of quotations')
    source = issue['_source_full']
    if any(not item.strip() or item not in source for item in evidence):
        raise ValueError('DeepSeek supplied evidence not found in the document')
    if result['decision'] in {'upheld', 'revised', 'withdrawn'} and not evidence:
        raise ValueError('A substantive decision requires quoted source evidence')
    for key in ('revised_message', 'revised_suggestion'):
        if result.get(key) is not None and not isinstance(result[key], str):
            raise ValueError(f'Invalid {key}')
    if result['decision'] == 'revised' and not all(result.get(k) for k in ('revised_message', 'revised_suggestion')):
        raise ValueError('Revised finding requires a message and suggestion')
    return {key: result.get(key) for key in (
        'decision', 'reason', 'evidence', 'revised_message', 'revised_suggestion')}


# Only reports published by this portfolio are accepted as remote evidence.
REPORT_HOST = 'iand4096.github.io'
REPORT_PREFIX = '/docusaurusportfolio/qa/'
GITHUB_RAW_PREFIX = 'https://raw.githubusercontent.com/iand4096/docusaurusportfolio/'


def load_report(report: str | Path) -> tuple[dict, str]:
    """Load an exact local report or a versioned, trusted GitHub Pages JSON report."""
    reference = str(report)
    url = urlsplit(reference)
    if url.scheme or url.netloc:
        if (url.scheme != 'https' or url.netloc != REPORT_HOST
                or not url.path.startswith(REPORT_PREFIX)
                or not re.fullmatch(r'report-[A-Fa-f0-9]{12,40}\.json', url.path.rsplit('/', 1)[-1])
                or url.username or url.password or url.query or url.fragment):
            raise ValueError('Only immutable JSON reports on the configured GitHub Pages QA origin are accepted')
        response = requests.get(reference, timeout=30, allow_redirects=False)
        response.raise_for_status()
        if len(response.content) > 12_000_000:
            raise ValueError('Remote report is too large')
        payload = response.json()
    else:
        location = Path(reference)
        if not location.is_file():
            raise ValueError(f'Report file not found: {location}')
        payload = json.loads(location.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or not isinstance(payload.get('issues'), list):
        raise ValueError('Report must contain an issues array')
    metadata = payload.get('metadata', {})
    if url.scheme and (not isinstance(metadata, dict)
                       or metadata.get('github_repository') != 'iand4096/docusaurusportfolio'):
        raise ValueError('Remote report repository identity is not valid')
    return payload, reference


def _source_for_report_finding(issue: dict, *, historical: bool) -> str:
    """Verify exact original source bytes; permit historical source for explicit reports."""
    file_name = issue.get('file')
    if (not isinstance(file_name, str) or not file_name or '\\' in file_name
            or Path(file_name).is_absolute() or '..' in Path(file_name).parts):
        raise ValueError('Invalid repository-relative source path in finding')
    sha = (issue.get('document_revision') or {}).get('content_sha256')
    if not isinstance(sha, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', sha):
        raise ValueError('Finding has no verifiable source SHA-256')
    local = Path(file_name)
    if local.is_file():
        raw = local.read_bytes()
        if hashlib.sha256(raw).hexdigest() == sha:
            return raw.decode('utf-8')
    if not historical:
        if not local.is_file():
            raise ValueError(f'Source file is unavailable: {local}')
        raise ValueError('Source has changed since QA; rerun QA before challenging')
    commit = (issue.get('document_revision') or {}).get('git_commit')
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-fA-F]{40}', commit):
        raise ValueError('Original source revision cannot be verified (missing full Git commit)')
    # Prefer the checked-out repository's original immutable Git object.
    try:
        result = subprocess.run(['git', 'show', f'{commit}:{file_name}'],
                                capture_output=True, check=False, timeout=15)
        raw = result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        raw = None
    if raw is None or hashlib.sha256(raw).hexdigest() != sha:
        # Retrieve the public source at the immutable commit, not a moving branch.
        from urllib.parse import quote
        url = GITHUB_RAW_PREFIX + commit + '/' + quote(file_name, safe='/')
        response = requests.get(url, timeout=30, allow_redirects=False)
        response.raise_for_status()
        raw = response.content
    if hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('Original Git source does not match the finding source SHA-256')
    return raw.decode('utf-8')


def challenge(issue_id: str, rebuttal: str | None = None, *, retry: bool = False, findings_path: Path = DEFAULT_FINDINGS,
              feedback_path: Path = DEFAULT_FEEDBACK, api_key: str,
              request_review, report: str | Path | None = None) -> dict:
    """Save the human challenge first; save adjudication only after validation.

    API errors leave the rebuttal as pending so it can be retried without loss.
    """
    if retry:
        if rebuttal is not None:
            raise ValueError('Retry cannot include a new rebuttal')
    elif not rebuttal or not rebuttal.strip():
        raise ValueError('Rebuttal must not be empty')
    if report is None:
        findings = _json_read(findings_path, {'schema_version': SCHEMA_VERSION, 'issues': []})
        provenance = str(findings_path)
    else:
        findings, provenance = load_report(report)
    matches = [item for item in findings.get('issues', []) if isinstance(item, dict)
               and item.get('issue_id') == issue_id]
    if len(matches) != 1:
        raise ValueError(f'Finding {issue_id!r} not uniquely present in report {provenance}')
    issue = dict(matches[0])
    if issue.get('source') != 'ai':
        raise ValueError('Only AI-origin findings can be challenged with DeepSeek')
    source = _source_for_report_finding(issue, historical=report is not None)
    line, context = _source_excerpt(source, issue['original'])
    issue['_source_full'] = source
    issue['_source_context'] = context
    store = feedback_records(feedback_path)
    records = store['records']
    record = records.setdefault(issue_id, {
        'issue_id': issue_id, 'status': 'unreviewed',
        'human_resolution': None, 'discussion': [], 'adjudications': []})
    record['report_source'] = provenance
    record['latest_finding'] = {k: issue.get(k) for k in (
        'file', 'category', 'source', 'original', 'message', 'suggestion', 'document_revision')}
    if retry:
        if record.get('status') != 'challenged':
            raise ValueError('Only a pending challenge may be retried')
        humans = [x for x in record.get('discussion', []) if x.get('role') == 'human']
        if not humans:
            raise ValueError('No previous human rebuttal to retry')
        rebuttal = humans[-1]['text']
    else:
        record['status'] = 'challenged'
        record['discussion'].append({'role': 'human', 'text': rebuttal.strip(), 'at': utc_now()})
    record.setdefault('attempts', []).append({'at': utc_now(), 'result': 'pending', 'retry': retry})
    write_atomic(feedback_path, store)
    try:
        decision = adjudicate(issue, rebuttal.strip(), record['discussion'], api_key,
                              request_review, prior_decisions=record.get('adjudications'))
    except Exception as error:
        record['attempts'][-1]['result'] = 'failed'
        record['attempts'][-1]['error'] = f'{type(error).__name__}: {error}'[:500]
        write_atomic(feedback_path, store)
        raise
    record['attempts'][-1]['result'] = 'succeeded'
    record['adjudications'].append({'at': utc_now(), **decision, 'document_revision': issue['document_revision']})
    record['discussion'].append({'role': 'ai', 'text': decision['reason'],
                                 'decision': decision['decision'], 'at': utc_now()})
    record['status'] = 'adjudicated'
    write_atomic(feedback_path, store)
    return decision


HUMAN_DECISIONS = {'accepted', 'dismissed', 'change_requested', 'pending'}


def resolve(issue_id: str, decision: str, reason: str, *,
            feedback_path: Path = DEFAULT_FEEDBACK) -> dict:
    """Record an explicit human decision without altering AI adjudication."""
    if decision not in HUMAN_DECISIONS:
        raise ValueError(f'Unknown human decision: {decision}')
    if not reason.strip():
        raise ValueError('Human resolution requires a reason')
    store = feedback_records(feedback_path)
    record = store['records'].get(issue_id)
    if record is None:
        raise ValueError(f'No feedback record found for {issue_id}; challenge it first')
    event = {'decision': decision, 'reason': reason.strip(), 'at': utc_now()}
    record['human_resolution'] = decision
    record.setdefault('resolution_history', []).append(event)
    write_atomic(feedback_path, store)
    return event
