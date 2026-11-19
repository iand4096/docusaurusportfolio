"""Render the JavaScript-free Markdown report."""
from qa_feedback import DEFAULT_FEEDBACK
from qa_recurrence import reusable

from .links import github_file_url, recurrence_command
from .model import Report, ReportPaths, feedback_label, is_history_issue, report_counts


def generate_markdown_report(report: Report, paths: ReportPaths) -> None:
    """Write the complete report as Markdown for readers and crawlers."""
    issues = report.sorted_issues()
    errors, metadata, ci_result = report.errors, report.metadata, report.ci
    active = [issue for issue in issues if not is_history_issue(issue)]
    history = [issue for issue in issues if is_history_issue(issue)]
    ordered = active + history
    counts = report_counts(issues)

    def value(text):
        # Preserve content while preventing unintended Markdown headings in values.
        return str(text).replace("\r\n", "\n").replace("\r", "\n").strip()

    def quote_block(text):
        return "\n".join("> " + line for line in value(text).split("\n"))

    lines = [
        "# Documentation QA report", "",
        f"Report run: {metadata['report_run_at_display']} ({metadata['report_time_zone']})", "",
        f"Mode: {metadata['mode']}",
        f"Checks: {metadata['filter_label']}",
        f"Model: {metadata['model']}",
        f"AI policy: {metadata['ai_review_policy_version']}", "",
        "## Summary", "",
        f"- Files reviewed: {metadata['files_reviewed']}",
        f"- Total issues: {len(ordered)}",
        f"- Active findings: {counts['active']}",
        f"- Pending challenges: {counts['pending']}",
        f"- Needs revalidation: {counts['needs_revalidation']}",
        f"- Withdrawn / dismissed: {counts['history']}",
        *[f"- Active {level} severity: {counts[level]}" for level in ("high", "medium", "low")],
        f"- CI-eligible high: {ci_result['high_count']}",
        f"- CI-eligible medium: {ci_result['medium_count']}",
        f"- Advisory AI: {ci_result['advisory_ai_issue_count']}",
        f"- API/check errors: {len(errors)}",
        f"- CI result: {'PASS' if ci_result['passed'] else 'FAIL'}", "",
        "CI policy: " + value(ci_result['policy']),
        "Failures: " + ("; ".join(ci_result['failures']) if ci_result['failures'] else "None"),
        "", "## Issues", "",
    ]
    if metadata.get('feedback_updated_at'):
        lines.insert(4, 'Feedback updated: ' + value(metadata['feedback_updated_at']))
    if not active:
        lines += ['No active findings.', '']
    if not ordered:
        lines += ["No issues found by the selected checks.", ""]
    for number, issue in enumerate(ordered, 1):
        if history and number == len(active) + 1:
            lines += ['## Withdrawn / dismissed', '']
        lines += [f"### Issue {number}", ""]
        if issue.get("source") == "ai":
            issue_id = issue.get("issue_id")
            if issue_id:
                lines.append(f"- ID: `{value(issue_id)}`")
            lines.append(f"- Feedback: {value(feedback_label(issue))}")
            lines.append(f"- Persistent issue: `{value(issue.get('persistent_issue_id') or 'not linked')}`")
            lines.append(f"- Occurrence: `{value(issue.get('occurrence_id') or 'unknown')}`")
        lines += [
            f"- Document revision: `{issue.get('document_revision', {}).get('content_sha256') or 'unknown'}`",
            f"- File: `{value(issue['file'])}`",
            f"- Line: {issue['line']}",
            f"- Severity: {issue['severity']}",
            f"- Related findings: {', '.join(issue.get('related_findings', [])) or 'None'}",
            f"- Confidence: {issue['confidence']}",
            f"- Type: {issue['type']}",
            f"- Category: {value(issue['category'])}",
            f"- Source: {issue['source']}",
            f"- Source link: {github_file_url(issue['file'], issue['line']) or 'Not available'}",
            "", "**Original:**", "", quote_block(issue['original']), "",
            "**Issue:**", "", value(issue.get('effective_message', issue['message'])), "",
            "**Suggestion:**", "", value(issue.get('effective_suggestion', issue['suggestion'])), "",
        ]
        if issue.get('reader_impact'):
            lines += ['**Reader impact:**', '', value(issue['reader_impact']), '',
                      '**Rule basis:**', '', value(issue.get('rule_basis', '')), '']
            for evidence in issue.get('evidence', []):
                lines += ['**Supporting evidence (' + value(evidence['file']) + '):**', '',
                          quote_block(evidence['quote']), '']
        if issue.get('effective_ai_decision') == 'revised':
            lines += ['**Original criticism:**', '', value(issue['message']), '',
                      '**Original suggestion:**', '', value(issue['suggestion']), '']
        if issue.get('feedback_link_confirmation'):
            lines += ['**Human-confirmed recurrence link:** ' + value(issue['feedback_link_confirmation']['previous_record_id']),
                      '', 'Previous decisions are not applied automatically.', '']
            linked_history = issue.get('feedback_linked_history') or {}
            old = linked_history.get('latest_finding') or {}
            lines += ['**Linked previous allegation:**', '', value(old.get('message', '')), '']
            for entry in linked_history.get('discussion') or []:
                if entry.get('role') == 'human':
                    lines += ['**Previous rebuttal:**', '', value(entry.get('text', '')), '']
            for entry in linked_history.get('adjudications') or []:
                lines += ['**Previous decision:** ' + value(entry.get('decision', '')), '', value(entry.get('reason', '')), '']
        for candidate in issue.get('recurrence_candidates', []):
            old = candidate['previous_finding']
            lines += ['**Possible recurrence:** ' + value(candidate['record_id']), '',
                      '**Previous quotation:**', '', quote_block(old['original']), '',
                      '**Previous allegation:**', '', value(old['message']), '',
                      '**Current allegation:**', '', value(issue['message']), '']
            precedent = candidate.get('precedent') or {}
            if precedent:
                lines += ['**Decision precedent:** ' + value(precedent['precedent_id']), '',
                          '**Precedent rebuttal:** ' + value(precedent.get('rebuttal') or ''), '',
                          '**Precedent AI rationale:** ' + value((precedent.get('adjudication') or {}).get('reason', '')), '',
                          '**Precedent human decision:** ' + value((precedent.get('resolution') or {}).get('decision', '')), '']
            for entry in candidate.get('previous_discussion', []):
                if entry.get('role') == 'human':
                    lines += ['**Previous rebuttal:**', '', value(entry['text']), '']
            for entry in candidate.get('previous_adjudications', []):
                lines += ['**Previous decision:** ' + value(entry['decision']), '', value(entry['reason']), '']
            comparison = candidate.get('comparison')
            if comparison:
                lines += ['**AI comparison:** ' + comparison['verdict'], '', value(comparison['reason']), '']
                for field in ('complaint_relationship', 'prior_decision_applicability', 'document_change_impact'):
                    if field in comparison:
                        lines += [f'**{field.replace("_", " ").title()}:** ' + value(comparison[field]), '']
                for field in ('old_evidence', 'new_evidence'):
                    for quote in comparison[field]:
                        lines += [quote_block(quote), '']
            else:
                lines += ['Not compared by AI.', '']
            if reusable(candidate):
                command = recurrence_command('reuse', metadata.get('review_report_reference') or str(paths.json),
                    issue=issue['issue_id'], previous=candidate['record_id'], proposal=candidate['proposal_id'],
                    reason='I verified that the prior decision still applies',
                    feedback_file=metadata.get('feedback_file', DEFAULT_FEEDBACK))
                lines += ['**Human revalidation and decision reuse:**', '', '```bash', command, '```', '']
            for decision in (() if candidate.get('requires_revalidation') else ('confirmed', 'rejected')):
                command = recurrence_command('link', metadata.get('review_report_reference') or str(paths.json),
                    issue=issue['issue_id'], previous=candidate['record_id'], proposal=candidate['proposal_id'], decision=decision,
                    reason='Explain your link decision', feedback_file=metadata.get('feedback_file', DEFAULT_FEEDBACK))
                lines += ['```bash', command, '```', '']
        for error in issue.get('recurrence_comparison_errors', []):
            lines += ['**Recurrence comparison failed:** ' + value(error['error']), '']
        for entry in issue.get('feedback_discussion', []):
            lines += ['**' + value(entry.get('role', '')).title() + ' discussion:**', '', value(entry.get('text', '')), '']
        for entry in issue.get('feedback_adjudications', []):
            lines += ['**AI decision: ' + value(entry.get('decision', '')) + '**', '', value(entry.get('reason', '')), '']
            for evidence in entry.get('evidence', []):
                lines += [quote_block(evidence), '']
        for entry in issue.get('feedback_resolution_history', []):
            lines += ['**Human resolution: ' + value(entry.get('decision', '')) + '**', '', value(entry.get('reason', '')), '']
    lines += ["## API/check errors", ""]
    if not errors:
        lines += ["No API or check errors.", ""]
    for number, error in enumerate(errors, 1):
        lines += [
            f"### Error {number}", "",
            f"- Check: {value(error['check'])}",
            f"- File: {value(error['file'])}",
            "", value(error['error']), "",
        ]
    paths.markdown.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
