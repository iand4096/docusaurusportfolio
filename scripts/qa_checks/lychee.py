"""Lychee external-link integration adapter."""
import json
import re
from pathlib import Path
import shutil
import subprocess

from qa_policy import make_issue

from .base import FileCheck
from .source import find_source_line, match_source_path


def lychee_preflight(root: Path) -> str:
    """Validate that the Lychee executable is available before checks run."""

    print("Lychee preflight:")

    executable = shutil.which("lychee")
    if executable is None:
        raise RuntimeError(
            "Lychee executable was not found in PATH. Install Lychee locally or "
            "in the GitHub Actions runner before running this script "
            "(and verify the install with `lychee --version`)."
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
            "Lychee is present but `lychee --version` failed"
            + (f": {detail}" if detail else ".")
        )

    version = version_result.stdout.strip() or version_result.stderr.strip()
    version = version.splitlines()[0] if version else "<unknown>"
    print(f"  Version: {version}")
    print()

    return executable

def lychee_status_text(status):
    """Return a readable status from Lychee's JSON status representation."""

    if isinstance(status, dict):
        text = str(status.get("text", "")).strip()
        code = status.get("code")

        if text and code is not None:
            return f"{text} (HTTP {code})"
        if text:
            return text
        if code is not None:
            return f"HTTP {code}"

        return json.dumps(status, ensure_ascii=False, sort_keys=True)
    if status is None:
        return "unknown failure"

    return str(status).strip() or "unknown failure"


def lychee_http_status(status):
    """Read an HTTP status without confusing transport errors with HTTP responses."""
    if isinstance(status, dict):
        code = status.get("code")
        if not isinstance(code, bool) and re.fullmatch(r"[1-5]\d{2}", str(code)):
            return int(code)
        text = str(status.get("text", ""))
    else:
        text = str(status or "")
    match = re.search(r"\b(?:HTTP\s+|status(?:\s+code)?\s*[:=]?\s*)([1-5]\d{2})\b", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_lychee_json(output, paths):
    """Convert Lychee JSON failures into the unified issue schema."""

    if not output.strip():
        return []

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Lychee returned invalid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("Lychee JSON output must be an object.")

    error_map = parsed.get("error_map", {})

    # Lychee used the name `fail_map` before 0.18. Supporting it here costs
    # almost nothing and makes local installations fail more gracefully.
    if not error_map and isinstance(parsed.get("fail_map"), dict):
        error_map = parsed["fail_map"]
    if not isinstance(error_map, dict):
        raise RuntimeError("Lychee JSON output contains an invalid error_map.")

    issues = []

    for raw_path, failures in error_map.items():
        path = match_source_path(raw_path, paths)

        if path is None or not isinstance(failures, list):
            continue

        content = path.read_text(encoding="utf-8")

        for failure in failures:
            if not isinstance(failure, dict):
                continue
            url = str(failure.get("url", "")).strip()
            if not url:
                continue

            # The HTTP/HTTPS scheme filters should already guarantee this, but keep
            # the parser defensive in case a future Lychee version changes filtering.
            if not re.match(r"^https?://", url, re.IGNORECASE):
                continue

            line = find_source_line(content, url) or 1
            raw_status = failure.get("status")
            status = lychee_status_text(raw_status)
            code = lychee_http_status(raw_status)
            severity, issue_type, category = "high", "defect", "external-link"
            message = f"External link failed Lychee validation: {status}"
            suggestion = (
                "Verify the destination, replace or remove the broken URL, "
                "or add a deliberate exception to .lycheeignore when the "
                "destination is known to reject automated checks."
            )
            # Lychee has already exhausted its configured retries. These statuses
            # establish a failed check, not that the destination has disappeared.
            if code == 429 or (code is not None and 500 <= code <= 599):
                severity, issue_type, category = "low", "improvement", "external-link-temporary"
                message = f"External link temporarily unavailable after Lychee retries: {status}"
                suggestion = (
                    "Recheck the URL later. The server returned a rate-limit or server-error "
                    "response; this does not establish that the link is broken. "
                    "If failures persist, review the destination and per-host request limits."
                )
            elif code in {401, 403}:
                severity, issue_type, category = "low", "improvement", "external-link-access"
                message = f"External link requires review: access restrictions prevented Lychee validation: {status}"
                suggestion = (
                    "Open the URL manually and check whether sign-in, permissions or automated-request "
                    "restrictions prevented validation. Correct the link if unsuitable for readers; "
                    "otherwise document a narrowly scoped exception after verification."
                )
            issues.append(
                make_issue(
                    file=path.as_posix(),
                    line=line,
                    severity=severity,
                    confidence="high",
                    issue_type=issue_type,
                    category=category,
                    original=url,
                    message=message,
                    suggestion=suggestion,
                    source="lychee",
                )
            )
    return issues


class LycheeCheck(FileCheck):
    """Run Lychee once across the selected Markdown/MDX files."""

    name = "LycheeCheck"
    source = "lychee"

    def preflight(self) -> str:
        return lychee_preflight(self.root)

    def run_files(self, paths, executable=None):
        executable = executable or shutil.which("lychee")

        if executable is None:
            raise RuntimeError(
                "Lychee executable was not found in PATH. Run the Lychee preflight "
                "before executing LycheeCheck."
            )
        # Use an absolute root directory. This is required by current Lychee
        # versions for root-relative links such as /docs/skills.
        root_dir = str(self.root.resolve())
        # Feed the exact file list over stdin instead of relying on shell globs.
        # This avoids Windows glob/path quoting differences and keeps Lychee's
        # scope identical to markdown_files(), including EXCLUDED_DIRS.
        command = [
            executable,
            "--root-dir",
            root_dir,
            "--scheme",
            "http",
            "--scheme",
            "https",
            "--format",
            "json",
            "--no-progress",
            "--files-from",
            "-",
        ]
        files_from = "\n".join(path.as_posix() for path in paths) + "\n"

        result = subprocess.run(
            command,
            cwd=self.root,
            input=files_from,
            capture_output=True,
            text=True,
            check=False,
        )
        # Lychee exit code 2 means link-check failures; that is expected input for
        # the report. Exit codes 1 and 3 indicate runtime/configuration failures.
        if result.returncode not in {0, 2}:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"Lychee exited with code {result.returncode}"
                + (f": {detail}" if detail else ".")
            )

        return parse_lychee_json(result.stdout, paths)
