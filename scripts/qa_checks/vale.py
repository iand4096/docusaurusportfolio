"""Vale integration adapter."""
import json
from pathlib import Path
import shutil
import subprocess

from qa_policy import make_issue

from .base import FileCheck
from .source import match_source_path, source_line_text


VALE_SEVERITY_MAP = {
    "error": "high",
    "warning": "medium",
    "suggestion": "low",
}


def vale_original_text(content, alert, line_number):
    """Extract the text Vale identified, falling back to the whole source line."""

    line_text = source_line_text(content, line_number)

    match = alert.get("Match")
    if isinstance(match, str) and match.strip():
        return match

    span = alert.get("Span")
    if (
        isinstance(span, list)
        and len(span) >= 2
        and isinstance(span[0], int)
        and isinstance(span[1], int)
        and span[0] > 0
        and span[1] >= span[0]
        and line_text
    ):
        start = span[0] - 1
        end = min(span[1], len(line_text))

        if start < len(line_text):
            return line_text[start:end]

    return line_text or "<source text unavailable>"

def normalise_vale_alert(alert, path, content):
    """Convert one Vale JSON alert into the unified report issue schema."""

    if not isinstance(alert, dict):
        return None

    raw_severity = str(alert.get("Severity", "")).strip().lower()
    severity = VALE_SEVERITY_MAP.get(raw_severity)

    if severity is None:
        return None

    line = alert.get("Line")
    if not isinstance(line, int) or line <= 0:
        return None
    check = str(alert.get("Check", "")).strip() or "vale"
    message = str(alert.get("Message", "")).strip()
    description = str(alert.get("Description", "")).strip()

    if not message:
        message = description or f"Vale rule {check} reported an issue."

    if description and description != message:
        suggestion = description
    else:
        suggestion = f"Resolve this text against the Vale rule {check}."
    return make_issue(
        file=path.as_posix(),
        line=line,
        severity=severity,
        confidence="high",
        issue_type="defect" if raw_severity == "error" else "improvement",
        category=check,
        original=vale_original_text(content, alert, line),
        message=message,
        suggestion=suggestion,
        source="vale",
    )


def parse_vale_json(output, paths):
    """Parse Vale --output=JSON output and return unified issues."""
    if not output.strip():
        return []

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Vale returned invalid JSON: {error}") from error

    if not isinstance(parsed, dict):
        raise RuntimeError("Vale JSON output must be an object keyed by file path.")

    issues = []

    for raw_path, alerts in parsed.items():
        path = match_source_path(raw_path, paths)

        if path is None:
            continue
        if not isinstance(alerts, list):
            continue

        content = path.read_text(encoding="utf-8")

        for alert in alerts:
            issue = normalise_vale_alert(alert, path, content)

            if issue is not None:
                issues.append(issue)

    return issues


def vale_preflight(root: Path) -> str:
    """Validate the Vale executable and repository configuration before checks run."""

    print("Vale preflight:")

    executable = shutil.which("vale")
    if executable is None:
        raise RuntimeError(
            "Vale executable was not found in PATH. "
            "Install Vale in the GitHub Actions runner before running this script "
            "(and verify the install with `vale --version`)."
        )

    print(f"  Executable: {executable}")

    version_result = subprocess.run(
        [executable, "--version"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if version_result.returncode != 0:
        detail = version_result.stderr.strip() or version_result.stdout.strip()
        raise RuntimeError(
            "Vale is present but `vale --version` failed"
            + (f": {detail}" if detail else ".")
        )

    version = version_result.stdout.strip() or version_result.stderr.strip()
    version = version.splitlines()[0] if version else "<unknown>"
    print(f"  Version: {version}")

    config_path = root / ".vale.ini"
    if not config_path.is_file():
        raise RuntimeError(
            f"Vale configuration file was not found: {config_path.resolve()}. "
            "Commit .vale.ini at the repository root before running Vale in CI."
        )

    print(f"  Config: {config_path.resolve()}")

    config_result = subprocess.run(
        [executable, "ls-config"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if config_result.returncode != 0:
        detail = config_result.stderr.strip() or config_result.stdout.strip()
        raise RuntimeError(
            "Vale found .vale.ini, but `vale ls-config` could not load the "
            "configuration"
            + (f": {detail}" if detail else ".")
        )

    print("  Configuration: OK")
    print()

    return executable


class ValeCheck(FileCheck):
    """Run Vale once across the selected Markdown/MDX files."""
    name = "ValeCheck"
    source = "vale"

    def preflight(self) -> str:
        return vale_preflight(self.root)

    def run_files(self, paths, executable=None):
        executable = executable or shutil.which("vale")

        if executable is None:
            raise RuntimeError(
                "Vale executable was not found in PATH. Run the Vale preflight "
                "before executing ValeCheck."
            )
        command = [
            executable,
            "--output=JSON",
            "--no-exit",
            *[path.as_posix() for path in paths],
        ]

        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            if detail:
                raise RuntimeError(
                    f"Vale exited with code {result.returncode}: {detail}"
                )

            raise RuntimeError(f"Vale exited with code {result.returncode}.")

        return parse_vale_json(result.stdout, paths)
