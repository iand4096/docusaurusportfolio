"""Typed inputs and shared finding presentation for all report formats."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qa_checks.base import CheckError
from qa_policy import CIResult, apply_ai_severity_policy


@dataclass(frozen=True)
class ReportPaths:
    html: Path
    json: Path
    markdown: Path

    @classmethod
    def in_directory(cls, directory: Path) -> "ReportPaths":
        return cls(directory / "ai-doc-review.html",
                   directory / "ai-doc-review.json",
                   directory / "ai-doc-review.md")


@dataclass(frozen=True)
class Report:
    issues: list[dict[str, Any]]
    errors: list[CheckError]
    metadata: dict[str, Any]
    ci: CIResult

    def sorted_issues(self) -> list[dict[str, Any]]:
        return sort_issues([apply_ai_severity_policy(dict(issue)) for issue in self.issues])

    def payload(self) -> dict[str, Any]:
        issues = self.sorted_issues()
        return {
            "metadata": self.metadata,
            "ci": self.ci,
            "summary": report_counts(issues),
            "issues": issues,
            "errors": self.errors,
        }


def sort_issues(issues):
    severity_order = {"high": 0, "medium": 1, "low": 2}
    confidence_order = {"high": 0, "medium": 1, "low": 2}

    return sorted(
        issues,
        key=lambda issue: (
            severity_order.get(issue["severity"], 99),
            confidence_order.get(issue["confidence"], 99),
            issue["file"],
            issue["line"],
            issue["category"],
        ),
    )

def feedback_state(issue):
    if issue.get('source') != 'ai':
        return 'unreviewed'
    if issue.get('feedback_needs_revalidation'):
        return 'needs_revalidation'
    if issue.get('human_resolution') == 'dismissed':
        return 'dismissed'
    if issue.get('feedback_status') == 'challenged':
        return 'challenged'
    if issue.get('human_resolution') in {'accepted', 'change_requested'}:
        return issue['human_resolution']
    return issue.get('effective_ai_decision') or 'unreviewed'


def is_history_issue(issue):
    return feedback_state(issue) in {'withdrawn', 'dismissed'}


def feedback_label(issue):
    if issue.get('feedback_match') == 'ambiguous':
        return 'Unreviewed — multiple previous issues match; link not applied'
    if issue.get('feedback_needs_revalidation'):
        return 'Needs revalidation — exact claim matched; source or proposed fix changed'
    if issue.get('feedback_link_confirmation') and feedback_state(issue) == 'unreviewed':
        return 'Linked — awaiting human resolution'
    return {
        'unreviewed': 'Unreviewed', 'challenged': 'Challenged — awaiting decision',
        'withdrawn': 'Withdrawn by AI — awaiting human resolution',
        'dismissed': 'Dismissed by human', 'upheld': 'Upheld',
        'revised': 'Revised', 'needs_evidence': 'Needs evidence',
        'accepted': 'Accepted by human', 'change_requested': 'Change requested by human',
    }.get(feedback_state(issue), 'Unreviewed')


def report_counts(issues):
    active = [issue for issue in issues if not is_history_issue(issue)]
    return {
        'active': len(active), 'history': len(issues) - len(active),
        'pending': sum(feedback_state(issue) == 'challenged' for issue in active),
        'needs_revalidation': sum(feedback_state(issue) == 'needs_revalidation' for issue in active),
        **{level: sum(issue['severity'] == level for issue in active)
           for level in ('high', 'medium', 'low')},
    }
