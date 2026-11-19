"""LTeX+ grammar/spelling integration adapter."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

from qa_policy import make_issue

from .base import FileCheck
from .source import match_source_path, source_line_text


LTEX_SEVERITY_MAP = {
    "error": "high",
    "warning": "medium",
    "information": "low",
    "info": "low",
    "hint": "low",
}

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
# lsp-cli-plus/LTeX+ uses a human-readable compiler-style diagnostic stream.
# Keep several compatible header patterns so minor formatting differences do not
# silently discard findings. The check is run once for the exact file list.
LTEX_DIAGNOSTIC_PATTERNS = [
    re.compile(
        r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+):\s*"
        r"(?:(?P<severity>error|warning|information|info|hint)\s*:\s*)?"
        r"(?P<message>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)\s+-\s+"
        r"(?:(?P<severity>error|warning|information|info|hint)\s+-\s+)?"
        r"(?P<message>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?P<path>.+?)\((?P<line>\d+),(?P<column>\d+)\):\s*"
        r"(?:(?P<severity>error|warning|information|info|hint)\s*:\s*)?"
        r"(?P<message>.+)$",
        re.IGNORECASE,
    ),
]

def strip_ansi(text):
    """Remove terminal colour/control sequences from CLI output."""

    return ANSI_ESCAPE_RE.sub("", text)


def ltex_preflight(root: Path) -> str:
    """Validate the LTeX+ CLI executable and repository configuration."""

    print("LTeX+ preflight:")

    executable = shutil.which("ltex-cli-plus")
    if executable is None:
        raise RuntimeError(
            "LTeX+ CLI was not found in PATH. Install ltex-ls-plus and expose "
            "its bin/ltex-cli-plus launcher before running this script."
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
            "LTeX+ is present but `ltex-cli-plus --version` failed"
            + (f": {detail}" if detail else ".")
        )

    version_text = version_result.stdout.strip() or version_result.stderr.strip()

    try:
        version_data = json.loads(version_text) if version_text else {}
    except json.JSONDecodeError:
        version_data = {}
    if isinstance(version_data, dict):
        ltex_version = version_data.get("ltex-ls-plus") or version_data.get("ltex-cli-plus")
        java_version = version_data.get("java")

        if ltex_version:
            print(f"  Version: {ltex_version}")
        elif version_text:
            print(f"  Version: {version_text.splitlines()[0]}")
        else:
            print("  Version: <unknown>")
        if java_version:
            print(f"  Java: {java_version}")
    else:
        print(f"  Version: {version_text.splitlines()[0] if version_text else '<unknown>'}")

    config_path = root / ".ltex.json"

    if not config_path.is_file():
        raise RuntimeError(
            f"LTeX+ configuration file was not found: {config_path.resolve()}. "
            "Commit .ltex.json at the repository root before running LTeX+ in CI."
        )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f".ltex.json is not valid JSON: {error}") from error

    if not isinstance(config, dict):
        raise RuntimeError(".ltex.json must contain a JSON object.")

    print(f"  Config: {config_path.resolve()}")
    # Surface the configured language in the preflight output when present.
    ltex_settings = config.get("ltex") if isinstance(config.get("ltex"), dict) else config
    language = ltex_settings.get("language") if isinstance(ltex_settings, dict) else None
    if isinstance(language, str) and language.strip():
        print(f"  Language: {language.strip()}")

    print("  Configuration: OK")
    print()

    return executable

def parse_ltex_diagnostic_header(line):
    """Parse one LTeX+/lsp-cli-plus diagnostic header line."""

    clean = strip_ansi(line).rstrip()

    for pattern in LTEX_DIAGNOSTIC_PATTERNS:
        match = pattern.match(clean)
        if match:
            data = match.groupdict()
            try:
                data["line"] = int(data["line"])
                data["column"] = int(data["column"])
            except (TypeError, ValueError):
                return None
            return data
    return None


def ltex_rule_and_message(message):
    """Extract a trailing LanguageTool rule id when the CLI includes one."""

    text = message.strip()

    # Common diagnostic renderers append the LSP diagnostic code in brackets.
    match = re.search(r"\s*\[([A-Za-z0-9_.-]+)\]\s*$", text)
    if match:
        return match.group(1), text[: match.start()].strip()
    # Be tolerant of variants such as "(RULE_ID)" at the end of a message.
    match = re.search(r"\s*\(([A-Z][A-Z0-9_.-]{2,})\)\s*$", text)
    if match:
        return match.group(1), text[: match.start()].strip()

    return "ltex", text


def ltex_suggestion(block_lines, rule):
    """Choose a useful quick-fix line from a rendered diagnostic block."""

    candidates = []

    for raw_line in block_lines:
        line = strip_ansi(raw_line).strip()
        if not line:
            continue
        # lsp-cli-plus can print code actions beneath diagnostics. Prefer an
        # explicit replacement action and ignore administrative actions such as
        # adding words to dictionaries or disabling rules.
        cleaned = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line).strip()
        lowered = cleaned.lower()

        if lowered.startswith("use ") or lowered.startswith("replace "):
            candidates.append(cleaned)

    if candidates:
        return candidates[0]
    if rule != "ltex":
        return f"Review and correct the text reported by LTeX+ rule {rule}."

    return "Review and correct the grammar or spelling issue reported by LTeX+."


def ltex_original_text(content, line_number, column_number):
    """Return source text for an LTeX+ finding."""

    line_text = source_line_text(content, line_number)
    if not line_text:
        return "<source text unavailable>"
    # The CLI location is 1-based. Without a structured end range, retaining the
    # full source line is safer than guessing the diagnostic span.
    return line_text


def is_ltex_non_prose_line(content, line_number):
    """Return True when an LTeX+ diagnostic points at source syntax, not prose.
    LTeX+ can interpret Docusaurus/MDX source constructs as English text when
    checking Markdown files. This filter is deliberately narrow: it ignores
    diagnostics on import/export statements, Docusaurus directive markers, and
    React/MDX component markup while leaving the surrounding reader-facing prose
    available to LTeX+.
    """

    lines = content.splitlines()

    if not 1 <= line_number <= len(lines):
        return False
    target_index = line_number - 1
    stripped = lines[target_index].strip()

    # Empty lines are never reader-facing prose.
    if not stripped:
        return True

    # ES module / MDX imports and exports.
    if re.match(r"^(?:import|export)\b", stripped):
        return True

    # Docusaurus directives/admonition markers. Only the marker line is ignored;
    # prose inside the admonition remains eligible for LTeX+ checking.
    if stripped.startswith(":::"):
        return True
    # Closing React/MDX component tags, for example </Tabs>.
    if re.match(r"^</[A-Z][A-Za-z0-9_.:-]*\s*>$", stripped):
        return True

    # Self-contained React/MDX component tags on one line.
    if re.match(r"^<[A-Z][A-Za-z0-9_.:-]*\b.*?/?>\s*$", stripped):
        return True
    # Determine whether the diagnostic line sits inside a multiline React/MDX
    # opening tag, for example:
    #
    # <SidebarCardGrid
    #   metadataKey="skillCard"
    #   linkLabel="Explore skills →"
    # />
    in_jsx_opening_tag = False

    for index, raw_line in enumerate(lines):
        if index > target_index:
            break

        current = raw_line.strip()
        if not in_jsx_opening_tag:
            if re.match(r"^<[A-Z][A-Za-z0-9_.:-]*\b", current):
                if index == target_index:
                    return True

                if ">" not in current:
                    in_jsx_opening_tag = True
        else:
            if index == target_index:
                return True

            if ">" in current:
                in_jsx_opening_tag = False

    return False

def normalise_ltex_diagnostic(header, block_lines, path, content):
    """Convert one LTeX+ diagnostic into the unified report issue schema."""

    line = header.get("line")
    column = header.get("column")

    if not isinstance(line, int) or line <= 0:
        return None

    if not isinstance(column, int) or column <= 0:
        column = 1
    # LTeX+ can report Docusaurus/MDX source syntax as English prose. Drop only
    # those diagnostics; reader-facing prose on surrounding lines is unchanged.
    if is_ltex_non_prose_line(content, line):
        return None
    raw_severity = str(header.get("severity") or "").strip().lower()
    # LTeX+ diagnostics are warning-level by default. If a renderer omits the
    # severity, keep the finding non-blocking rather than inventing a high level.
    severity = LTEX_SEVERITY_MAP.get(raw_severity, "low")

    rule, message = ltex_rule_and_message(str(header.get("message") or ""))
    if is_ltex_context_false_positive(content, line, column, rule, message):
        return None
    if not message:
        message = f"LTeX+ rule {rule} reported a grammar or spelling issue."
    return make_issue(
        file=path.as_posix(),
        line=line,
        severity=severity,
        confidence="high",
        issue_type="defect" if raw_severity == "error" else "improvement",
        category=rule,
        original=ltex_original_text(content, line, column),
        message=message,
        suggestion=ltex_suggestion(block_lines, rule),
        source="ltex",
    )


def is_ltex_context_false_positive(content, line, column, rule, message):
    """Ignore known syntax/proper-name artefacts, not other prose on the line.

    Keep these exceptions tied to both the rule and the diagnostic location.
    In particular, a table or inline code must not exempt surrounding prose.
    """
    text = source_line_text(content, line)
    offset = column - 1

    def at(pattern):
        return any(match.start() <= offset < match.end()
                   for match in re.finditer(pattern, text))

    if rule == "MORFOLOGIK_RULE_EN_GB" and "'Center'" in message:
        return at(r"\bDeveloper Center\b")
    if rule == "LICENCE_LICENSE_NOUN_SINGULAR":
        return at(r"\b(?:SIL Open Font License(?: 1\.1)?|MIT License)\b")
    if rule == "EN_A_VS_AN":
        # LTeX replaces code with a dummy token, changing the apparent initial
        # sound. 'an items array' is correct; do not rewrite it to 'a items'.
        return at(r"\ban\s+`items`\s+array\b")
    if rule == "UPPERCASE_SENTENCE_START":
        for match in re.finditer(r"\[`?(?P<command>npm|pip)\s+[^\]\n]+\]\(", text):
            if match.start("command") <= offset < match.end("command"):
                return True
        return False
    if rule in {"PHRASE_REPETITION", "OK_OK_COMMA"} and text.lstrip().startswith("|"):
        # A repeated Yes/No across cells is independent table data. Preserve
        # genuine repetition within a cell and all other grammar diagnostics.
        cells = text.strip().strip("|").split("|")
        if any(re.search(r"\b(Yes|No)\s+\1\b", cell, re.I) for cell in cells):
            return False
        boundaries = list(re.finditer(r"\|", text))
        cell_index = sum(boundary.start() < offset for boundary in boundaries) - 1
        if 0 <= cell_index < len(cells) - 1:
            left, right = (cells[cell_index].strip(), cells[cell_index + 1].strip())
            return left in {"Yes", "No"} and re.match(rf"{left}\b", right) is not None
    return False


def parse_ltex_output(output, paths):
    """Parse LTeX+ CLI output and return unified issues."""
    if not output.strip():
        return []

    rendered_lines = strip_ansi(output).splitlines()
    issues = []
    current_header = None
    current_path = None
    current_block = []

    def flush():
        nonlocal current_header, current_path, current_block
        if current_header is not None and current_path is not None:
            content = current_path.read_text(encoding="utf-8")
            issue = normalise_ltex_diagnostic(
                current_header,
                current_block,
                current_path,
                content,
            )
            if issue is not None:
                issues.append(issue)

        current_header = None
        current_path = None
        current_block = []
    for rendered_line in rendered_lines:
        header = parse_ltex_diagnostic_header(rendered_line)

        if header is None:
            if current_header is not None:
                current_block.append(rendered_line)
            continue

        flush()
        path = match_source_path(header.get("path"), paths)
        if path is None:
            # Some renderers use file:// URIs. Convert those to local paths.
            raw_path = str(header.get("path") or "").strip()
            if raw_path.lower().startswith("file://"):
                candidate = unquote(urlsplit(raw_path).path)
                if os.name == "nt" and re.match(r"^/[A-Za-z]:/", candidate):
                    candidate = candidate[1:]
                path = match_source_path(candidate, paths)
        current_header = header
        current_path = path
        current_block = []

    flush()
    return issues


def ltex_output_contains_only_ignored_syntax(output, paths):
    """Tell filtered MDX diagnostics from unparseable CLI output.

    Return True only if at least one LTeX+ diagnostic header was recognised,
    every header refers to a reviewed file, and every finding is on a line
    intentionally excluded as syntax or a known contextual false positive. Anything else stays
    an error instead of being mistakenly considered a clean LTeX+ run.
    """

    found_diagnostic = False

    for rendered_line in strip_ansi(output).splitlines():
        header = parse_ltex_diagnostic_header(rendered_line)
        if header is None:
            continue
        found_diagnostic = True

        path = match_source_path(header.get("path"), paths)
        if path is None:
            raw_path = str(header.get("path") or "").strip()
            if raw_path.lower().startswith("file://"):
                candidate = unquote(urlsplit(raw_path).path)
                if os.name == "nt" and re.match(r"^/[A-Za-z]:/", candidate):
                    candidate = candidate[1:]
                path = match_source_path(candidate, paths)

        # Do not silently discard findings with unknown/unresolvable paths.
        if path is None:
            return False

        # An invalid line must not be mistaken for filtered source syntax.
        line_number = header.get("line")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return False

        if not isinstance(line_number, int) or not 1 <= line_number <= len(content.splitlines()):
            return False
        if normalise_ltex_diagnostic(header, [], path, content) is not None:
            return False

    return found_diagnostic


class LtexCheck(FileCheck):
    """Run LTeX+ once across the selected Markdown/MDX files."""

    name = "LtexCheck"
    source = "ltex"

    def preflight(self) -> str:
        return ltex_preflight(self.root)

    def run_files(self, paths, executable=None):
        executable = executable or shutil.which("ltex-cli-plus")
        if executable is None:
            raise RuntimeError(
                "LTeX+ CLI was not found in PATH. Run the LTeX+ preflight before "
                "executing LtexCheck."
            )

        config_path = self.root / ".ltex.json"
        if not config_path.is_file():
            raise RuntimeError(".ltex.json was not found at the repository root.")
        command = [
            executable,
            f"--client-configuration={config_path.as_posix()}",
            *[path.as_posix() for path in paths],
        ]

        result = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        # Official LTeX+ CLI exit codes: 0 = no diagnostics, 3 = diagnostics;
        # 1 = runtime exception, 2 = invalid CLI arguments.
        if result.returncode not in {0, 3}:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"LTeX+ exited with code {result.returncode}"
                + (f": {detail}" if detail else ".")
            )

        if result.returncode == 0:
            return []
        issues = parse_ltex_output(result.stdout, paths)
        # Exit code 3 can legitimately produce zero reportable findings when
        # every diagnostic belongs to intentionally ignored MDX source syntax.
        # Only accept that case if every diagnostic is recognised and resolved.
        if not issues and ltex_output_contains_only_ignored_syntax(result.stdout, paths):
            return []
        # Do not silently report a clean run when LTeX+ explicitly told us that
        # diagnostics existed but its renderer changed in an incompatible way.
        if not issues:
            detail = result.stdout.strip() or result.stderr.strip()
            if len(detail) > 4000:
                detail = detail[:4000] + "\n...<truncated>"
            raise RuntimeError(
                "LTeX+ reported diagnostics (exit code 3), but the QA script could "
                "not parse the CLI output. Raw output follows:\n" + detail
            )
        return issues
