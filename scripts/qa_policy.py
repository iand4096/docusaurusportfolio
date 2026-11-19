"""Finding construction and CI gate policy shared by checks and reporting."""
from typing import TypedDict


class CIThresholds(TypedDict):
    high: int
    medium: int
    api_errors: int


class CIResult(TypedDict):
    passed: bool
    high_count: int
    medium_count: int
    threshold_eligible_issue_count: int
    advisory_ai_issue_count: int
    api_error_count: int
    failures: list[str]
    policy: str
    thresholds: CIThresholds


def apply_ai_severity_policy(issue):
    """Enforce the ceiling for new and saved AI findings, preserving audit data."""
    if issue.get('source') == 'ai' and issue.get('severity') == 'high':
        issue.setdefault('model_reported_severity', 'high')
        issue['severity'] = 'medium'
    return issue


def make_issue(
    *,
    file,
    line,
    severity,
    confidence,
    issue_type,
    category,
    original,
    message,
    suggestion,
    source,
):
    """Create one issue using the unified schema."""
    return {
        "file": str(file).replace("\\", "/"),
        "line": int(line),
        "severity": severity,
        "confidence": confidence,
        "type": issue_type,
        "category": category,
        "original": original,
        "message": message,
        "suggestion": suggestion,
        "source": source,
    }


def is_ci_threshold_eligible(issue):
    """Return True when an issue is allowed to contribute to CI thresholds.
    Deterministic checks retain their existing severity behaviour. AI findings
    are intentionally stricter: only high-confidence substantive defects can
    contribute to the high/medium CI thresholds. Editorial improvements, diagram
    suggestions and uncertain AI judgements remain report-only.
    """

    if issue.get("source") != "ai":
        return True
    if issue.get("human_resolution") == "dismissed":
        return False

    return (
        issue.get("type") == "defect"
        and issue.get("confidence") == "high"
    )

def evaluate_ci(issues, errors, fail_high: int, fail_medium: int, fail_api_errors: int) -> CIResult:
    for issue in issues:
        apply_ai_severity_policy(issue)
    threshold_eligible = [
        issue for issue in issues
        if is_ci_threshold_eligible(issue)
    ]
    high_count = sum(
        1 for issue in threshold_eligible
        if issue["severity"] == "high"
    )
    medium_count = sum(
        1 for issue in threshold_eligible
        if issue["severity"] == "medium"
    )
    advisory_ai_count = sum(
        1 for issue in issues
        if issue.get("source") == "ai" and issue.get("human_resolution") != "dismissed"
        and not is_ci_threshold_eligible(issue)
    )
    api_error_count = len(errors)

    failures = []
    if high_count > fail_high:
        failures.append(
            f"CI-eligible high issues {high_count} > allowed {fail_high}"
        )

    if medium_count > fail_medium:
        failures.append(
            f"CI-eligible medium issues {medium_count} > allowed {fail_medium}"
        )

    if api_error_count > fail_api_errors:
        failures.append(
            f"API/check errors {api_error_count} > allowed {fail_api_errors}"
        )
    return {
        "passed": not failures,
        "high_count": high_count,
        "medium_count": medium_count,
        "threshold_eligible_issue_count": len(threshold_eligible),
        "advisory_ai_issue_count": advisory_ai_count,
        "api_error_count": api_error_count,
        "failures": failures,
        "policy": (
            "Deterministic findings use their normal severity. "
            "AI findings count towards CI only when type=defect and confidence=high, "
            "unless explicitly dismissed by a human. AI severity is capped at medium. "
            "AI withdrawal alone does not change CI eligibility."
        ),
        "thresholds": {
            "high": fail_high,
            "medium": fail_medium,
            "api_errors": fail_api_errors,
        },
    }
