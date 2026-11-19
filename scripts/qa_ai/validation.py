"""Validate AI finding schemas and bind quoted evidence to the source."""
import re

from qa_checks.source import find_source_line
from qa_policy import apply_ai_severity_policy, make_issue

from .routing import PORTFOLIO_REVIEW_GENRES, document_genre

SEVERITIES = {"high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
ISSUE_TYPES = {"defect", "improvement", "diagram"}

def require_review_issues(response):
    """Require an explicit list of finding objects, including for clean reviews."""
    issues = response.get("issues") if isinstance(response, dict) else None
    if not isinstance(issues, list):
        raise ValueError("Invalid AI review response: expected an 'issues' array")
    if any(not isinstance(issue, dict) for issue in issues):
        raise ValueError("Invalid AI review response: 'issues' must contain only objects")
    return issues


def valid_review_evidence(issue, sources):
    """Check supporting passages, not just the text selected for correction."""
    if any(not isinstance(issue.get(k), str) or not issue[k].strip()
           for k in ('reader_impact', 'rule_basis')):
        return False
    evidence = issue.get('evidence')
    if not isinstance(evidence, list) or not evidence:
        return False
    passages = set()
    for item in evidence:
        if not isinstance(item, dict):
            return False
        path, quote = item.get('file'), item.get('quote')
        if not isinstance(path, str) or not isinstance(quote, str) or not quote.strip():
            return False
        if path not in sources or quote not in sources[path]:
            return False
        passages.add((path, quote))
    if issue.get('category') in {'repetition', 'consistency'} and len(passages) < 2:
        return False
    return True


def normalise_ai_issue(issue, content, file_path, allowed_categories, *, genre=None, evidence_sources=None):
    """Validate an AI finding and recalculate its source line."""
    required_fields = {
        "severity",
        "confidence",
        "type",
        "category",
        "line",
        "original",
        "message",
        "suggestion",
        "source",
    }

    if not isinstance(issue, dict):
        return None

    if not required_fields.issubset(issue):
        return None
    if evidence_sources is not None and not valid_review_evidence(issue, evidence_sources):
        return None
    severity = issue.get("severity")
    confidence = issue.get("confidence")
    issue_type = issue.get("type")
    category = issue.get("category")
    original = issue.get("original")
    message = issue.get("message")
    suggestion = issue.get("suggestion")
    reported_line = issue.get("line")

    if severity not in SEVERITIES:
        return None

    if confidence not in CONFIDENCE_LEVELS:
        return None

    if issue_type not in ISSUE_TYPES:
        return None
    if category not in allowed_categories:
        return None
    # Do not allow model-selected categories to bypass the genre routing.
    if category == 'portfolio' and (genre or document_genre(file_path, content)) not in PORTFOLIO_REVIEW_GENRES:
        return None

    if not isinstance(original, str) or not original.strip():
        return None

    if original not in content:
        return None

    if not isinstance(message, str) or not message.strip():
        return None

    if not isinstance(suggestion, str) or not suggestion.strip():
        return None

    if not isinstance(reported_line, int):
        reported_line = None
    actual_line = find_source_line(
        content,
        original,
        preferred_line=reported_line,
    )

    if actual_line is None:
        return None
    # Enforce semantic invariants in code instead of trusting model labels.
    # Optional/editorial AI findings remain visible in the report but cannot
    # masquerade as high- or medium-severity defects because a model became
    # more aggressive after a backend update.
    # Do not let an explicitly non-defect criticism become a CI-blocking defect.
    if re.search(r"\b(?:rather than a defect|not a defect|purely stylistic)\b", message, re.IGNORECASE):
        issue_type = 'improvement'
        if 'consistency' in allowed_categories:
            category = 'consistency'
    if issue_type in {"improvement", "diagram"}:
        severity = "low"

    if confidence == "low":
        severity = "low"
    # Source is assigned by the implementation rather than trusted from AI.
    normalised = make_issue(
        file=file_path,
        line=actual_line,
        severity=severity,
        confidence=confidence,
        issue_type=issue_type,
        category=category,
        original=original,
        message=message.strip(),
        suggestion=suggestion.strip(),
        source="ai",
    )
    for field in ('reader_impact', 'evidence', 'rule_basis'):
        if field in issue:
            normalised[field] = issue[field]
    normalised['model_reported_severity'] = issue['severity']
    return apply_ai_severity_policy(normalised)

def normalise_model_path(raw_path, known_paths):
    """Match a model-returned path to an exact supplied file path."""

    if not isinstance(raw_path, str):
        return None

    candidate = raw_path.strip().replace("\\", "/")

    while candidate.startswith("./"):
        candidate = candidate[2:]

    aliases = {}

    for path in known_paths:
        canonical = path.as_posix()
        aliases[canonical] = canonical
        if canonical.startswith("./"):
            aliases[canonical[2:]] = canonical

    return aliases.get(candidate)


def validate_site_ai_issues(issues, paths, contents, allowed_categories, *, genres=None):
    """Validate site-wide AI findings against the named source file."""

    if not isinstance(issues, list):
        return []

    validated = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        canonical_path = normalise_model_path(
            issue.get("file"),
            paths,
        )

        if canonical_path is None:
            continue
        content = contents.get(canonical_path)

        if content is None:
            continue

        normalised = normalise_ai_issue(
            issue,
            content,
            canonical_path,
            allowed_categories,
            genre=(genres or {}).get(canonical_path),
            evidence_sources=contents,
        )

        if normalised is not None:
            validated.append(normalised)

    return validated
