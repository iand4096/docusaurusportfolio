"""Remark Markdown/MDX integration adapter."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from qa_policy import make_issue

from .base import FileCheck
from .source import match_source_path, source_line_text


def find_remark_executable(root: Path):
    """Return the local Remark CLI executable, with a PATH fallback."""

    binary_name = "remark.cmd" if os.name == "nt" else "remark"
    local_binary = root / "node_modules" / ".bin" / binary_name

    if local_binary.is_file():
        return str(local_binary.resolve())
    return shutil.which("remark")


def find_remark_config(root: Path):
    """Return the repository Remark config source, if configured."""

    config_names = [
        ".remarkrc",
        ".remarkrc.json",
        ".remarkrc.yaml",
        ".remarkrc.yml",
        ".remarkrc.js",
        ".remarkrc.cjs",
        ".remarkrc.mjs",
    ]

    for name in config_names:
        path = root / name
        if path.is_file():
            return str(path.resolve())
    package_path = root / "package.json"
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package = None

        if isinstance(package, dict) and "remarkConfig" in package:
            return f"{package_path.resolve()} (remarkConfig)"

    return None


def remark_preflight(root: Path) -> str:
    """Validate the Remark CLI and repository configuration before checks run."""
    print("Remark preflight:")

    executable = find_remark_executable(root)

    if executable is None:
        raise RuntimeError(
            "Remark CLI was not found. Install remark-cli in the repository with "
            "`npm install --save-dev remark-cli` (or run `npm ci` in CI)."
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
            "Remark is present but `remark --version` failed"
            + (f": {detail}" if detail else ".")
        )

    version = version_result.stdout.strip() or version_result.stderr.strip()
    version = version.splitlines()[0] if version else "<unknown>"
    print(f"  Version: {version}")
    config = find_remark_config(root)
    if config is None:
        raise RuntimeError(
            "No Remark configuration was found. Commit .remarkrc.mjs (recommended "
            "for this Docusaurus repository) or configure remarkConfig in package.json."
        )

    print(f"  Config: {config}")

    ignore_path = root / ".remarkignore"
    if ignore_path.is_file():
        print(f"  Ignore: {ignore_path.resolve()}")
    else:
        print("  Ignore: <none>")

    print()
    return executable

def parse_remark_json(output, paths):
    """Convert Remark/vfile JSON messages into the unified issue schema."""

    if not output.strip():
        return []

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Remark returned invalid JSON: {error}") from error

    if not isinstance(parsed, list):
        raise RuntimeError("Remark JSON output must be an array of files.")

    issues = []
    for file_result in parsed:
        if not isinstance(file_result, dict):
            continue

        raw_path = file_result.get("path")
        path = match_source_path(raw_path, paths)

        if path is None:
            continue

        messages = file_result.get("messages", [])
        if not isinstance(messages, list):
            continue

        content = path.read_text(encoding="utf-8")
        for message in messages:
            if not isinstance(message, dict):
                continue

            # unified-engine wraps parser errors in "Cannot process file".
            # Keep the wrapper's fatal status but report the nested cause's
            # useful location, parser name and diagnostic.
            diagnostic = message
            while isinstance(diagnostic.get("cause"), dict):
                diagnostic = diagnostic["cause"]
            reason = str(diagnostic.get("reason", "")).strip()
            outer_reason = str(message.get("reason", "")).strip()
            if outer_reason and outer_reason != reason:
                reason = f"{outer_reason}: {reason}" if reason else outer_reason
            if not reason:
                continue

            rule_id = str(diagnostic.get("ruleId") or message.get("ruleId") or "remark").strip()
            message_source = str(diagnostic.get("source") or message.get("source") or "remark").strip()

            line = diagnostic.get("line") or message.get("line")
            if not isinstance(line, int) or line <= 0:
                line = 1
            fatal = message.get("fatal")
            if fatal is None:
                fatal = diagnostic.get("fatal")
            if fatal is True:
                severity = "high"
            elif fatal is False:
                severity = "medium"
            else:
                severity = "low"

            actual = diagnostic.get("actual")
            if isinstance(actual, str) and actual.strip():
                original = actual.strip()
            else:
                original = source_line_text(content, line)
            if not original:
                original = "<file-level Remark finding>"

            expected = diagnostic.get("expected")
            note = diagnostic.get("note")
            if isinstance(note, str) and note.strip():
                suggestion = note.strip()
            elif isinstance(expected, list) and expected:
                expected_text = ", ".join(str(item) for item in expected)
                suggestion = f"Update the Markdown/MDX to use one of: {expected_text}."
            elif fatal is True and message_source != "remark":
                suggestion = "Correct the syntax at the reported location so the Markdown/MDX parser can process this file."
            elif fatal is True:
                suggestion = "Check file availability, access and checker configuration; this is a processing failure rather than a lint-rule violation."
            else:
                suggestion = (
                    f"Correct the Markdown/MDX structure to satisfy Remark rule "
                    f"`{rule_id}`."
                )
            issues.append(
                make_issue(
                    file=path.as_posix(),
                    line=line,
                    severity=severity,
                    confidence="high",
                    issue_type="defect",
                    category=rule_id,
                    original=original,
                    message=f"Remark ({message_source}): {reason}",
                    suggestion=suggestion,
                    source="remark",
                )
            )
    return issues


class RemarkCheck(FileCheck):
    """Run Remark once across the selected Markdown/MDX files."""

    name = "RemarkCheck"
    source = "remark"

    # A tiny reporter module keeps this integration self-contained and avoids
    # requiring vfile-reporter-json as an extra project dependency.
    REPORTER_SOURCE = r'''function diagnostic(message, depth = 0) {
  return {
    reason: message.reason || message.message || String(message),
    line: message.line ?? null,
    column: message.column ?? null,
    fatal: message.fatal ?? null,
    ruleId: message.ruleId ?? null,
    source: message.source ?? null,
    actual: message.actual ?? null,
    expected: message.expected ?? null,
    note: message.note ?? null,
    url: message.url ?? null,
    cause: message.cause && depth < 8 ? diagnostic(message.cause, depth + 1) : null
  };
}
export default function reporter(files) {
  const list = Array.isArray(files) ? files : [files];
  return JSON.stringify(list.map((file) => ({
    path: file.path || '',
    cwd: file.cwd || '',
    history: file.history || [],
    messages: (file.messages || []).map((message) => diagnostic(message))
  })));
}
'''
    def preflight(self) -> str:
        return remark_preflight(self.root)

    def run_files(self, paths, executable=None):
        executable = executable or find_remark_executable(self.root)

        if executable is None:
            raise RuntimeError(
                "Remark CLI was not found. Run the Remark preflight before "
                "executing RemarkCheck."
            )

        reporter_path = self.root / f".remark-python-reporter-{os.getpid()}.mjs"

        try:
            reporter_path.write_text(self.REPORTER_SOURCE, encoding="utf-8")
            command = [
                executable,
                "--no-color",
                "--no-stdout",
                "--quiet",
                "--silently-ignore",
                "--report",
                f"./{reporter_path.name}",
                "--",
                *[path.as_posix() for path in paths],
            ]
            result = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            try:
                reporter_path.unlink(missing_ok=True)
            except OSError:
                pass
        # unified-engine writes reporter output to stderr. Normal lint warnings
        # return 0 because this integration intentionally does not use --frail;
        # CI policy is applied by the unified severity thresholds below.
        report_text = result.stderr.strip()
        if report_text:
            try:
                issues = parse_remark_json(report_text, paths)
            except RuntimeError:
                if result.returncode != 0:
                    detail = result.stderr.strip() or result.stdout.strip()
                    raise RuntimeError(
                        f"Remark exited with code {result.returncode}: {detail}"
                    )
                raise

            if issues or result.returncode == 0:
                return issues
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"Remark exited with code {result.returncode}"
                + (f": {detail}" if detail else ".")
            )

        return []
