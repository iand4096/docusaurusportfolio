"""Render the interactive HTML report and its synthetic example."""
import html
import json
from pathlib import Path
import re
import shlex
from string import Template
from typing import Mapping
from urllib.parse import quote

from qa_feedback import DEFAULT_FEEDBACK
from qa_policy import evaluate_ci, make_issue

from .links import PORTFOLIO_URL, PROJECT_ROOT, github_file_url, recurrence_command
from .model import Report, ReportPaths, feedback_label, feedback_state, is_history_issue, report_counts

ASSETS = Path(__file__).resolve().parent


def html_file_link(file_path, line=None):
    """Render a report filename as a GitHub link when it represents a real file."""

    label = html.escape(str(file_path))
    url = github_file_url(file_path, line=line)

    if url is None:
        return label

    escaped_url = html.escape(url, quote=True)
    return f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{label}</a>'

def html_line_link(file_path, line):
    """Render a source line number as a GitHub line link when possible."""

    label = html.escape(str(line))
    url = github_file_url(file_path, line=line)

    if url is None:
        return label

    escaped_url = html.escape(url, quote=True)
    return f'<a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{label}</a>'

def ai_without_recurrence_concerns(issue):
    """Display-only classification; never changes feedback or CI eligibility."""
    return (issue.get('source') == 'ai' and not issue.get('feedback_link_confirmation')
            and not issue.get('recurrence_comparison_errors')
            and all((candidate.get('comparison') or {}).get('verdict') == 'different_complaint'
                    for candidate in issue.get('recurrence_candidates', [])))


def recurrence_html(issue, report_reference, feedback_path=DEFAULT_FEEDBACK):
    candidates = issue.get('recurrence_candidates', [])
    linked = issue.get('feedback_link_confirmation')
    if not candidates and not linked:
        return ''
    escape = lambda value: html.escape(str(value))

    def command_control(command, label):
        return ('<div class="recurrence-action"><details class="recurrence-command">'
                '<summary>Show command</summary><pre><code class="link-command" data-report-token="' +
                html.escape(shlex.quote(str(report_reference)), quote=True) + '">' + escape(command) +
                '</code></pre></details><button type="button" class="copy-link-command">' +
                escape(label) + '</button></div>')

    parts = ['<details class="feedback-details recurrence-details"><summary>Previous challenges and possible recurrence</summary>']
    if linked:
        parts.append('<p><strong>Human-confirmed link.</strong> The previous decision has not been applied automatically.</p>')
        history = issue.get('feedback_linked_history') or {}
        candidates = [{'record_id': linked['previous_record_id'],
                       'previous_finding': history.get('latest_finding') or {},
                       'previous_discussion': history.get('discussion') or [],
                       'previous_adjudications': history.get('adjudications') or []}]
    for candidate in candidates:
        old = candidate['previous_finding']
        comparison = candidate.get('comparison')
        precedent = candidate.get('precedent') or {}
        previous_decisions = candidate.get('previous_adjudications') or []
        previous_decision = previous_decisions[-1].get('decision', 'Not adjudicated') if previous_decisions else 'Not adjudicated'
        if precedent:
            previous_decision = ((precedent.get('resolution') or {}).get('decision') or
                                 (precedent.get('adjudication') or {}).get('decision') or 'Not adjudicated')
        old_sha = (old.get('document_revision') or {}).get('content_sha256')
        new_sha = (issue.get('document_revision') or {}).get('content_sha256')
        source_status = 'Unchanged' if old_sha and old_sha == new_sha else 'Changed — review context'
        verdict = (comparison['verdict'].replace('_', ' ') if comparison else
                   'Human-confirmed link' if linked else 'Not compared')
        parts.append('<section class="recurrence-candidate" aria-label="Challenge link comparison">'
                     '<dl class="recurrence-summary"><dt>AI assessment</dt><dd><strong>AI comparison: ' +
                     escape(verdict) + '</strong></dd><dt>Previous decision</dt><dd>' +
                     escape(previous_decision.replace('_', ' ').capitalize()) +
                     '</dd><dt>Source</dt><dd>' + escape(source_status) + '</dd></dl>')
        if not linked:
            parts.append('<div class="recurrence-actions">')
            from qa_recurrence import reusable
            if reusable(candidate):
                command = recurrence_command('reuse', report_reference, issue=issue['issue_id'],
                    previous=candidate['record_id'], proposal=candidate['proposal_id'],
                    reason='I verified that the prior decision still applies', feedback_file=feedback_path)
                parts.append(command_control(command, 'Copy revalidate and reuse command'))
            actions = [] if candidate.get('requires_revalidation') else [
                ('confirmed', 'Copy confirm link command'), ('rejected', 'Copy reject link command')]
            for decision, label in actions:
                command = recurrence_command('link', report_reference, issue=issue['issue_id'],
                    previous=candidate['record_id'], proposal=candidate['proposal_id'],
                    decision=decision, reason='Explain your link decision', feedback_file=feedback_path)
                parts.append(command_control(command, label))
            if not comparison:
                command = recurrence_command('compare', report_reference, feedback_file=feedback_path)
                parts.append(command_control(command, 'Copy compare command'))
            parts.append('</div><p class="recurrence-help">Copy a command, edit its reason and run locally. '
                         'Confirming a link does not dismiss the finding. Take no action to leave unresolved.</p>')
        parts.append('<details class="recurrence-evidence"><summary>Compare quotations and allegations</summary>')
        if old.get('original') == issue.get('original'):
            parts.append('<p><strong>Shared quotation</strong></p><blockquote>' + escape(issue.get('original', '')) + '</blockquote>')
        else:
            for label, finding in [('Previous', old), ('Current', issue)]:
                parts.append('<p><strong>' + label + ' quotation</strong></p><blockquote>' + escape(finding.get('original', '')) + '</blockquote>')
        for label, finding in [('Previous', old), ('Current', issue)]:
            parts.append('<p><strong>' + label + ' allegation</strong></p><p>' + escape(finding.get('message', '')) + '</p>')
        parts.append('</details>')
        if comparison:
            for label, field in [('Complaint relationship', 'complaint_relationship'),
                                 ('Prior decision applicability', 'prior_decision_applicability'),
                                 ('Document change impact', 'document_change_impact')]:
                if field in comparison:
                    parts.append('<p><strong>' + label + ':</strong> ' + escape(comparison[field]) + '</p>')
            parts.append('<details class="recurrence-reasoning"><summary>AI reasoning and evidence</summary><p>' + escape(comparison['reason']) + '</p>')
            for label, field in [('Previous finding evidence', 'old_evidence'), ('Current finding evidence', 'new_evidence')]:
                parts.append('<p><strong>' + label + '</strong></p>')
                for quote in comparison[field]:
                    parts.append('<blockquote>' + escape(quote) + '</blockquote>')
            parts.append('</details>')
        if precedent:
            parts.append('<details class="recurrence-precedent"><summary>Exact decision precedent</summary>'
                         '<p><code>' + escape(precedent.get('precedent_id', '')) + '</code></p>')
            if precedent.get('legacy'):
                parts.append('<p>Legacy binding: not eligible for decision reuse.</p>')
            for label, value in [('Rebuttal', precedent.get('rebuttal')),
                                 ('AI rationale', (precedent.get('adjudication') or {}).get('reason')),
                                 ('Human resolution reason', (precedent.get('resolution') or {}).get('reason'))]:
                if value:
                    parts.append('<p><strong>' + label + ':</strong> ' + escape(value) + '</p>')
            for quote in (precedent.get('adjudication') or {}).get('evidence', []):
                parts.append('<blockquote>' + escape(quote) + '</blockquote>')
            parts.append('</details>')
        parts.append('<details class="recurrence-history"><summary>Previous rebuttal and decision history</summary>')
        parts.append('<p>Previous finding: <code>' + escape(candidate['record_id']) + '</code></p>')
        if linked:
            parts.append('<p><strong>Link confirmation reason</strong></p><p>' + escape(linked['reason']) + '</p>')
        for entry in candidate.get('previous_discussion', []):
            if entry.get('role') == 'human':
                parts.append('<p><strong>Previous rebuttal</strong></p><p>' + escape(entry.get('text', '')) + '</p>')
        for entry in previous_decisions:
            parts.append('<p><strong>Previous AI decision: ' + escape(entry.get('decision', '')) + '</strong></p><p>' + escape(entry.get('reason', '')) + '</p>')
        parts.append('</details></section>')
    for error in issue.get('recurrence_comparison_errors', []):
        parts.append('<p role="status">Recurrence comparison failed: ' + escape(error['error']) + '</p>')
    parts.append('</details>')
    return ''.join(parts)


def feedback_html(issue):
    if issue.get('source') != 'ai':
        return ''
    parts = []
    if issue.get('feedback_needs_revalidation'):
        parts.append('<p>Previous feedback is linked to this exact claim, but the source or proposed fix has changed. It does not dismiss or revise this occurrence.</p>')
    for entry in issue.get('feedback_discussion', []):
        parts.append('<p><strong>' + html.escape(str(entry.get('role', '')).title()) +
                     '</strong> ' + html.escape(str(entry.get('at', ''))) + '</p><p>' +
                     html.escape(str(entry.get('text', ''))) + '</p>')
    for entry in issue.get('feedback_adjudications', []):
        parts.append('<p><strong>AI decision: ' + html.escape(str(entry.get('decision', ''))) +
                     '</strong></p><p>' + html.escape(str(entry.get('reason', ''))) + '</p>')
        parts.extend('<blockquote>' + html.escape(str(quote)) + '</blockquote>'
                     for quote in entry.get('evidence', []))
    for entry in issue.get('feedback_resolution_history', []):
        parts.append('<p><strong>Human resolution: ' + html.escape(str(entry.get('decision', ''))) +
                     '</strong></p><p>' + html.escape(str(entry.get('reason', ''))) + '</p>')
    if issue.get('feedback_attempts') and issue['feedback_attempts'][-1].get('result') == 'failed':
        parts.append('<p>Last adjudication attempt failed. The challenge remains pending; retry from the CLI.</p>')
    if not parts:
        return ''
    return '<details class="feedback-details"><summary>Challenge discussion and evidence</summary>' + ''.join(parts) + '</details>'


def issue_table(rows, table_id):
    headers = ('File', 'Line', 'Severity', 'Confidence', 'Type', 'Category', 'Source',
               'Original', 'Issue', 'Suggestion')
    return '<div class="table-wrap"><table id="' + table_id + '"><thead><tr>' + ''.join(
        '<th>' + heading + '</th>' for heading in headers) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def source_filter_buttons(issues, errors, metadata, checks: Mapping[str, str]):
    """Include executed sources even when they returned no findings."""
    labels = {'ai': 'AI', 'static': 'Static', 'vale': 'Vale', 'ltex': 'LTeX+',
              'lychee': 'Lychee', 'remark': 'Remark', 'tooltip': 'Tooltip audit'}
    selected = metadata.get('checks') or []
    sources = {checks[name] for name in selected if name in checks}
    sources.update(issue.get('source') for issue in issues)
    sources.update(checks.get(error.get('check')) for error in errors)
    counts = {source: sum(issue.get('source') == source for issue in issues) for source in labels}

    def button(source, label):
        count = len(issues) if not source else counts[source]
        descriptions = {
            '': 'Show findings from all AI and deterministic checks.',
            'ai': 'DeepSeek reviews language, clarity, structure, repetition and portfolio presentation, and suggests useful diagrams.',
            'static': 'Repository checks validate local links and assets, accessibility basics and landing-page coverage.',
            'vale': 'Vale checks prose against the configured writing style, terminology and editorial rules.',
            'ltex': 'LTeX+ checks spelling and grammar using the configured language and dictionary.',
            'lychee': 'Lychee checks external links for unreachable URLs and HTTP errors.',
            'tooltip': 'Advisory review of tooltip mentions and canonical definitions.',
            'remark': 'Remark checks Markdown and MDX structure against the configured lint rules.',
        }
        if source == 'ai' and selected and not set(selected) & {
                'PortfolioReview', 'RepetitionReview', 'DiagramReview'}:
            descriptions['ai'] = ('DeepSeek reviews language, structure and consistency for substantive '
                                  'defects, then verifies each allegation against the source.')
        title = descriptions[source]
        return (f'<button type="button" class="source-button source-{source or "all"}" '
                f'data-source-filter="{source}" aria-pressed="{str(not source).lower()}" '
                f'title="{html.escape(title, quote=True)}">{label} '
                f'<span class="source-count">{count}</span></button>')

    parts = [button('', 'All sources')]
    if 'ai' in sources:
        parts.append('<span class="source-group-label">AI</span>')
        parts.append(button('ai', labels['ai']))
    deterministic = [source for source in ('static', 'vale', 'ltex', 'lychee', 'remark') if source in sources]
    if deterministic:
        if 'ai' in sources:
            parts.append('<span class="source-separator" aria-hidden="true"></span>')
        parts.append('<span class="source-group-label">Deterministic</span>')
        parts.extend(button(source, labels[source]) for source in deterministic)
    if 'tooltip' in sources:
        parts.append(button('tooltip', labels['tooltip']))
    return '<div class="source-filters" role="group" aria-label="Filter findings by source">' + ''.join(parts) + '</div>'


EXAMPLE_REPORT_THRESHOLD = 5


def example_report_notice(issues, metadata):
    if metadata.get('example_report'):
        return ('<aside class="example-report-notice" aria-label="Example report notice">'
                '<strong>Demonstration only — synthetic findings</strong>'
                '<p>These deliberately flawed examples illustrate the checks and report filters. '
                'They are not defects found in this portfolio. The CI failure and check error '
                'below are simulated. Feedback actions are disabled.</p></aside>')
    if report_counts(issues)['active'] <= EXAMPLE_REPORT_THRESHOLD:
        return ('<aside class="example-report-notice" aria-label="Example report">'
                '<p>This report has few active findings. Explore a separate example to see '
                'how the checks report documentation problems.</p>'
                '<a class="example-report-link" href="qa-example.html">'
                'See example QA report with errors</a></aside>')
    return ''


def generate_example_report(paths: ReportPaths, metadata, check_sources: Mapping[str, str]) -> None:
    """Render a deterministic demonstration, never run checks or touch feedback."""
    cases = [
        ('static', 'high', 'links', '[Setup guide](missing-guide.md)',
         'The local link points to a file that does not exist.', 'Correct the path or restore the missing guide.'),
        ('static', 'medium', 'accessibility', '![](architecture.png)',
         'The diagram has no alternative text.', 'Describe the architecture diagram in its alternative text.'),
        ('ai', 'medium', 'clarity', 'Delete the old index before verifying the replacement.',
         'The instruction removes the working index before the replacement is verified.',
         'Verify the replacement first, then retire the old index.'),
        ('ai', 'low', 'repetition', 'The API returns JSON. Responses from the API use JSON.',
         'Two adjacent sentences repeat the response format.', 'Keep one statement of the response format.'),
        ('vale', 'low', 'style', 'Simply leverage the endpoint to get your data.',
         'The wording uses unnecessary filler and vague terminology.', 'Use the endpoint to retrieve data.'),
        ('ltex', 'low', 'spelling', 'The documantation describes the endpoint.',
         'The word “documantation” is misspelled.', 'Use “documentation”.'),
        ('lychee', 'medium', 'links', '[API reference](https://example.invalid/reference)',
         'The external API reference cannot be reached.', 'Replace the URL with a working reference.'),
        ('remark', 'low', 'heading-increment', '# Setup\n\n### Configure the client',
         'The heading skips a level.', 'Use a level-two heading after the level-one heading.'),
    ]
    examples = [make_issue(file='Synthetic example document', line=index,
        severity=severity, confidence='high', issue_type='defect' if severity != 'low' else 'improvement',
        category=category, original=original, message=message, suggestion=suggestion, source=source)
        for index, (source, severity, category, original, message, suggestion) in enumerate(cases, 1)]
    example_metadata = {**metadata, 'example_report': True, 'files_reviewed': 1,
        'filter_label': 'Demonstration of all sources', 'model': 'Synthetic examples — no API calls',
        'checks': list(check_sources)}
    example_errors = [{'check': 'LycheeCheck', 'file': 'Synthetic example document',
                      'error': 'Simulated check failure: the external-link service timed out.'}]
    example_ci = evaluate_ci(examples, example_errors, 0, 0, 0)
    example_paths = ReportPaths(paths.html.with_name('qa-example.html'), paths.json, paths.markdown)
    generate_html_report(Report(examples, example_errors, example_metadata, example_ci),
                         example_paths, check_sources, actual_report_name=paths.html.name)


def generate_html_report(report: Report, paths: ReportPaths, check_sources: Mapping[str, str],
                         *, actual_report_name: str = 'ai-doc-review.html') -> None:
    payload = report.payload()
    issues = payload["issues"]
    errors, metadata, ci_result = report.errors, report.metadata, report.ci
    counts = payload["summary"]
    if metadata.get('example_report'):
        return_url = './' + quote(actual_report_name)
        return_label = '← Back to actual QA report'
    else:
        return_url = PORTFOLIO_URL
        return_label = '← Back to Portfolio'
    high_count, medium_count, low_count = (counts[level] for level in ('high', 'medium', 'low'))
    pinned_report = metadata.get('review_report_reference')
    pinned_report_json = json.dumps(pinned_report).replace('<', '\\u003c')
    try:
        local_report = paths.json.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        local_report = paths.json.as_posix()
    local_report_json = json.dumps(local_report).replace('<', '\\u003c')
    rows = []
    history_rows = []
    recurrence_overview_rows = []
    possible_count = sum(bool(issue.get('recurrence_candidates')) for issue in issues)
    linked_count = sum(bool(issue.get('feedback_link_confirmation')) for issue in issues)
    ai_clear_count = sum(ai_without_recurrence_concerns(issue) for issue in issues)

    for number, issue in enumerate(issues, 1):
        file_link = (html.escape(issue['file']) if metadata.get('example_report') else
                     html_file_link(issue["file"], line=issue["line"]))
        line_link = (str(issue['line']) if metadata.get('example_report') else
                     html_line_link(issue["file"], issue["line"]))
        issue_id = str(issue.get("issue_id", ""))
        # Only DeepSeek-originated findings can be challenged by the AI
        # adjudication command. Keep the command in a data attribute so it is
        # available without embedding untrusted issue content in JavaScript.
        challenge_control = (
            '<button type="button" class="challenge-button" '
            'data-issue-id="' + html.escape(issue_id, quote=True) + '" '
            'aria-label="Copy challenge command for finding '
            + html.escape(issue_id, quote=True) + '">Challenge AI</button>'
            if issue.get("source") == "ai" and issue_id and not metadata.get("example_report") else ""
        )
        file_detail = file_link
        if issue.get("source") == "ai" and issue_id:
            file_detail = (
                '<small><strong>ID:</strong> <code>' + html.escape(issue_id) +
                '</code></small><br>' + file_link + '<br><small>Status: ' +
                html.escape(feedback_label(issue)) +
                '</small><br><small>Persistent issue: <code>' +
                html.escape(issue.get('persistent_issue_id') or 'not linked') +
                '</code><br>Occurrence: <code>' + html.escape(issue.get('occurrence_id') or 'unknown') +
                '</code></small><br>' + challenge_control
            )
        recurrence_state = ('possible' if issue.get('recurrence_candidates') else
                            'confirmed' if issue.get('feedback_link_confirmation') else '')
        if recurrence_state:
            candidates = issue.get('recurrence_candidates') or [{
                'previous_adjudications': (issue.get('feedback_linked_history') or {}).get('adjudications') or [],
                'comparison': None}]
            verdict_labels = {'same_complaint': 'Same complaint',
                              'different_complaint': 'Different complaint', 'uncertain': 'Uncertain'}
            assessments = []
            decisions = []
            for candidate in candidates:
                comparison = candidate.get('comparison')
                assessments.append(verdict_labels.get(comparison.get('verdict'), 'Not compared')
                                   if comparison else 'Human-confirmed link' if recurrence_state == 'confirmed' else 'Not compared')
                prior = candidate.get('previous_adjudications') or []
                decisions.append(str(prior[-1].get('decision', 'Not adjudicated')).replace('_', ' ').title()
                                 if prior else 'Not adjudicated')
            recurrence_overview_rows.append(
                '<tr><td>' + file_link + ' · line ' + str(issue['line']) + '</td><td>' +
                html.escape(', '.join(dict.fromkeys(decisions))) + '</td><td>' +
                html.escape(', '.join(dict.fromkeys(assessments))) + '</td><td>' +
                '<a class="review-recurrence" href="#finding-' + str(number) +
                '">Review comparison</a></td></tr>')
        message = html.escape(issue.get('effective_message', issue['message']))
        if issue.get('reader_impact'):
            message += '<details><summary>Reader impact and supporting evidence</summary><p>' + html.escape(issue['reader_impact']) + '</p><p>' + html.escape(issue.get('rule_basis', '')) + '</p>'
            for evidence in issue.get('evidence', []):
                message += '<p>' + html.escape(evidence['file']) + '</p><blockquote>' + html.escape(evidence['quote']) + '</blockquote>'
            message += '</details>'
        if issue.get('related_findings'):
            message += '<p><strong>Related findings:</strong> ' + html.escape(', '.join(issue['related_findings'])) + '</p>'
        suggestion = html.escape(issue.get('effective_suggestion', issue['suggestion']))
        if issue.get('effective_ai_decision') == 'revised':
            message += '<details><summary>Original criticism and suggestion</summary><p>' + html.escape(issue['message']) + '</p><p>' + html.escape(issue['suggestion']) + '</p></details>'
        message += feedback_html(issue)
        message += recurrence_html(issue, pinned_report or str(paths.json), metadata.get('feedback_file', DEFAULT_FEEDBACK))
        (history_rows if is_history_issue(issue) else rows).append(
            f"""
            <tr id="finding-{number}" data-recurrence="{recurrence_state}"
                data-ai-clear="{'true' if ai_without_recurrence_concerns(issue) else 'false'}"
                data-severity="{html.escape(issue['severity'])}"
                data-source="{html.escape(issue['source'])}"
                data-category="{html.escape(issue['category'])}"
            >
                <td>{file_detail}</td>
                <td>{line_link}<br><small>{html.escape((issue.get("document_revision", {}).get("content_sha256") or "")[:12] or "revision unavailable")}</small></td>
                <td><span class="badge severity-{html.escape(issue['severity'])}">{html.escape(issue['severity'])}</span></td>
                <td><span class="badge confidence-{html.escape(issue['confidence'])}">{html.escape(issue['confidence'])}</span></td>
                <td>{html.escape(issue['type'])}</td>
                <td>{html.escape(issue['category'])}</td>
                <td><span class="badge source-{html.escape(issue['source'])}">{html.escape(issue['source'])}</span></td>
                <td><code>{html.escape(issue['original'])}</code></td>
                <td>{message}</td>
                <td>{suggestion}</td>
            </tr>
            """
        )
    if not rows:
        rows.append(
            """
            <tr>
                <td colspan="10" class="empty-state">
                    No active findings.
                </td>
            </tr>
            """
        )

    history_markup = ('<details class="feedback-history"><summary>Withdrawn / dismissed (' + str(len(history_rows)) + ')</summary>' + issue_table(history_rows, 'historyTable') + '</details>') if history_rows else ''
    recurrence_overview = (
        '<section id="possibleLinks" aria-labelledby="possibleLinksTitle">'
        '<h2 id="possibleLinksTitle">Challenge links</h2><p>' + str(possible_count) +
        ' findings with possible links · ' + str(linked_count) + ' human-confirmed links.</p>'
        '<p><button type="button" id="showPossibleLinks">Show only possible links</button> '
        '<button type="button" id="showAllFindings">Show all findings</button></p>'
        '<div class="table-wrap recurrence-overview"><table><thead><tr><th>Location</th>'
        '<th>Previous AI decision</th><th>Assessment</th><th>Action</th></tr></thead><tbody>' +
        ''.join(recurrence_overview_rows) + '</tbody></table></div></section>'
    ) if recurrence_overview_rows else (
        '<section id="possibleLinks"><h2>Challenge links</h2><p>No possible or confirmed links in this report.</p></section>')
    feedback_timestamp = ('<p>Feedback updated: ' + html.escape(str(metadata['feedback_updated_at'])) + '</p>') if metadata.get('feedback_updated_at') else ''
    snapshot_link = ('<a href="original-report.json">Original review snapshot</a>'
                     if metadata.get('original_report_snapshot') == 'original-report.json' else '')
    error_rows = []

    for error in errors:
        error_file_link = (html.escape(error['file']) if metadata.get('example_report') else
                           html_file_link(error["file"]))
        error_rows.append(
            f"""
            <tr>
                <td>{html.escape(error['check'])}</td>
                <td>{error_file_link}</td>
                <td>{html.escape(error['error'])}</td>
            </tr>
            """
        )

    if not error_rows:
        error_rows.append(
            """
            <tr>
                <td colspan="3" class="empty-state">No API or check errors.</td>
            </tr>
            """
        )
    ci_class = "ci-pass" if ci_result["passed"] else "ci-fail"
    ci_label = "PASS" if ci_result["passed"] else "FAIL"

    failure_text = (
        "; ".join(ci_result["failures"])
        if ci_result["failures"]
        else "All configured thresholds are satisfied."
    )
    stylesheet = (ASSETS / 'report.css').read_text(encoding='utf-8')
    script = (ASSETS / 'report.js').read_text(encoding='utf-8')
    script = re.sub(r'__PINNED_REPORT_JSON__|__LOCAL_REPORT_JSON__',
                    lambda match: pinned_report_json if match[0] == '__PINNED_REPORT_JSON__'
                    else local_report_json, script)
    embedded_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    embedded_data = '<script id="qa-report-data" type="application/json">\n' + embedded_json + '\n</script>\n'
    template = Template((ASSETS / 'report.html').read_text(encoding='utf-8'))
    document = template.substitute(
        markdown_filename=html.escape(paths.markdown.name, quote=True),
        json_filename=html.escape(paths.json.name, quote=True),
        stylesheet=stylesheet,
        example_notice=example_report_notice(issues, metadata),
        return_url=html.escape(return_url, quote=True),
        return_label=return_label,
        possible_count=possible_count,
        linked_count=linked_count,
        snapshot_link=snapshot_link,
        report_run_at_display=html.escape(metadata['report_run_at_display']),
        report_time_zone=html.escape(metadata['report_time_zone']),
        mode=html.escape(metadata['mode']),
        filter_label=html.escape(metadata['filter_label']),
        model=html.escape(metadata['model']),
        ai_review_policy_version=html.escape(metadata['ai_review_policy_version']),
        feedback_timestamp=feedback_timestamp,
        files_reviewed=metadata['files_reviewed'],
        issue_count=len(issues),
        count_active=counts['active'],
        count_pending=counts['pending'],
        count_needs_revalidation=counts['needs_revalidation'],
        count_history=counts['history'],
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        ci_high_count=ci_result['high_count'],
        ci_medium_count=ci_result['medium_count'],
        ci_advisory_ai_issue_count=ci_result['advisory_ai_issue_count'],
        tooltip_issue_count=sum(issue.get('source') == 'tooltip' for issue in issues),
        error_count=len(errors),
        ci_class=ci_class,
        ci_label=ci_label,
        failure_text=html.escape(failure_text),
        ci_policy=html.escape(ci_result['policy']),
        ci_thresholds_high=ci_result['thresholds']['high'],
        ci_thresholds_medium=ci_result['thresholds']['medium'],
        ci_thresholds_api_errors=ci_result['thresholds']['api_errors'],
        recurrence_overview=recurrence_overview,
        ai_clear_count=ai_clear_count,
        source_filters=source_filter_buttons(issues, errors, metadata, check_sources),
        issue_rows=issue_table(rows, 'issuesTable'),
        history_markup=history_markup,
        error_rows=''.join(error_rows),
        script=script,
        embedded_data=embedded_data,
    )
    if metadata.get('example_report'):
        document = document.replace('<title>Documentation QA report</title>',
                                    '<title>Example QA report — synthetic findings</title>')
        document = document.replace('<h1>Documentation QA report</h1>',
                                    '<h1>Example QA report</h1>')
        # The example is standalone: never link its synthetic data to the real
        # report exports or expose actions that could write actual feedback.
        document = re.sub(r'    <div class="report-actions">.*?</div>', '', document, count=1, flags=re.S)
        document = re.sub(r'    <link rel="alternate"[^>]*>\n', '', document)
        document = document.replace('AI readers can also use the linked Markdown or JSON files when published alongside this page.',
                                    'The embedded JSON contains the same synthetic examples.')
        document = re.sub(r'    <p>For AI findings, select <strong>Challenge AI</strong>.*?</p>',
                          '', document, count=1, flags=re.S)
    destination = paths.html
    destination.write_text(document, encoding="utf-8")
    if not metadata.get('example_report') and counts['active'] <= EXAMPLE_REPORT_THRESHOLD:
        generate_example_report(paths, metadata, check_sources)
