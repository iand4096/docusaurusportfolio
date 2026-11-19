import argparse
import json
import os
import re
import sys
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from qa_feedback import (decorate_issues, attach_feedback_status, save_findings, resolve as resolve_finding,
                         challenge as challenge_finding, load_report, DEFAULT_FEEDBACK, DEFAULT_FINDINGS)

from qa_ai import client
from qa_ai.cache import AI_REVIEW_POLICY_VERSION, AIReviewCache
from qa_ai.checks import (DiagramReview, GrammarReview, PortfolioReview, RepetitionReview,
                          SiteWideConsistencyReview, StructureReview)
from qa_checks.base import BaseCheck
from qa_checks.source import iter_lines_outside_code_fences
from qa_runner import CheckPlan, run_checks
from qa_checks.ltex import LtexCheck
from qa_checks.lychee import LycheeCheck
from qa_checks.remark import RemarkCheck
from qa_checks.vale import ValeCheck
from qa_policy import assert_ci_policy_invariants, evaluate_ci, make_issue
from qa_reporting import Report, ReportPaths, write_reports
from qa_reporting.links import PORTFOLIO_URL, github_repository, github_revision
from qa_reporting.model import report_counts

# Resolve the repository from the script location, never the invoking shell's CWD.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(".")  # Existing QA paths are relative to PROJECT_ROOT after main() starts.
REVIEW_FILES = ("README.md", "LICENSE.md")
REVIEW_DIRECTORIES = ("docs", "src/pages", "src/components", "knowledge-api")
SKIPPED_REVIEW_DIRECTORIES = {"node_modules", "build", "static", "reports", "FAPI"}
REVIEW_SUFFIXES = {".md", ".mdx"}

DEFAULT_FAIL_HIGH = 0
DEFAULT_FAIL_MEDIUM = 25
DEFAULT_FAIL_API_ERRORS = 0
FILTER_PRESETS = {
    "full": {
        "GrammarReview",
        "StructureReview",
        "AccessibilityCheck",
        "LinkCheck",
        "LandingPageCoverageCheck",
        "LycheeCheck",
        "RemarkCheck",
        "ValeCheck",
        "LtexCheck",
        "SiteWideConsistencyReview",
    },
    "editorial": {
        "GrammarReview",
        "StructureReview",
        "PortfolioReview",
        "RepetitionReview",
        "DiagramReview",
        "ValeCheck",
        "LtexCheck",
    },
    "portfolio": {
        "PortfolioReview",
    },
    "repetition": {
        "RepetitionReview",
    },
    "mermaid": {
        "DiagramReview",
    },
    "accessibility": {
        "AccessibilityCheck",
    },
    "site-wide-consistency": {
        "SiteWideConsistencyReview",
    },
    "vale": {
        "ValeCheck",
    },
    "ltex": {
        "LtexCheck",
    },
    "lychee": {
        "LycheeCheck",
    },
    "links": {
        "LinkCheck",
        "LycheeCheck",
    },
    "remark": {
        "RemarkCheck",
    },
}
FILTER_LABELS = {
    "full": "Full review — substantive AI defects",
    "editorial": "Optional editorial suggestions",
    "portfolio": "Portfolio only",
    "repetition": "Repetition only",
    "mermaid": "Mermaid opportunities only",
    "accessibility": "Accessibility only",
    "site-wide-consistency": "Site-wide consistency only",
    "vale": "Vale only",
    "ltex": "LTeX+ grammar/spelling only",
    "lychee": "Lychee external links only",
    "links": "Local and external links only",
    "remark": "Remark Markdown/MDX only",
}

def markdown_files(extra_paths=()) -> list[Path]:
    """Select portfolio documentation and explicitly requested repository files."""
    files = {ROOT / name for name in REVIEW_FILES
             if (ROOT / name).is_file() and not (ROOT / name).is_symlink()}
    for directory in REVIEW_DIRECTORIES:
        base = ROOT / directory
        if base.resolve() != ROOT.resolve() / directory:
            continue
        for current, dirs, names in os.walk(base):
            dirs[:] = [name for name in dirs if not name.startswith(".")
                       and name not in SKIPPED_REVIEW_DIRECTORIES]
            for name in names:
                path = Path(current) / name
                if (path.suffix.lower() in REVIEW_SUFFIXES and name != "ai-doc-review.md"
                        and path.is_file() and not path.is_symlink()):
                    files.add(path)

    for path in extra_paths:
        resolved = (ROOT / path).resolve()
        try:
            relative = resolved.relative_to(ROOT.resolve())
        except ValueError:
            raise ValueError(f"Review file must be inside the repository: {path}") from None
        if (not resolved.is_file() or resolved.suffix.lower() not in REVIEW_SUFFIXES
                or "FAPI" in relative.parts or resolved.name == "ai-doc-review.md"):
            raise ValueError(f"Expected a reviewable Markdown or MDX file: {path}")
        files.add(ROOT / relative)
    return sorted(files)


def _last_sunday(year, month):
    """Return the day number of the last Sunday in a month."""

    last_day = monthrange(year, month)[1]
    last_date = datetime(year, month, last_day)
    return last_day - ((last_date.weekday() + 1) % 7)


def london_now():
    """Return the current time in Europe/London without OS-specific commands.
    Python's ZoneInfo is used when IANA timezone data is available. Some Windows
    Python installations do not ship an IANA database, so a standard-library
    fallback applies the current UK GMT/BST rule: clocks advance at 01:00 UTC on
    the last Sunday in March and return at 01:00 UTC on the last Sunday in October.
    """

    now_utc = datetime.now(timezone.utc)
    try:
        return now_utc.astimezone(ZoneInfo("Europe/London"))
    except ZoneInfoNotFoundError:
        year = now_utc.year
        bst_start = datetime(
            year,
            3,
            _last_sunday(year, 3),
            1,
            tzinfo=timezone.utc,
        )
        bst_end = datetime(
            year,
            10,
            _last_sunday(year, 10),
            1,
            tzinfo=timezone.utc,
        )
        if bst_start <= now_utc < bst_end:
            london_tz = timezone(timedelta(hours=1), name="BST")
        else:
            london_tz = timezone(timedelta(0), name="GMT")

        return now_utc.astimezone(london_tz)


def report_run_metadata():
    """Return machine-readable and display London timestamps for a report run."""
    run_time = london_now()
    return {
        "report_run_at": run_time.isoformat(timespec="seconds"),
        "report_run_at_display": run_time.strftime("%d %B %Y, %H:%M:%S %Z"),
        "report_time_zone": "Europe/London",
    }


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------


class AccessibilityCheck(BaseCheck):
    name = "AccessibilityCheck"
    supports_page = True
    source = "static"
    MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
    HTML_IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    ALT_ATTR_RE = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
    VAGUE_LINK_TEXT = {
        "click here",
        "here",
        "read more",
        "more",
        "learn more",
        "this link",
    }

    def run_page(self, path, content, api_key=None):
        issues = []
        for line_number, line in iter_lines_outside_code_fences(content):
            # Markdown images with empty alt text.
            for match in self.MARKDOWN_IMAGE_RE.finditer(line):
                alt_text = match.group(1).strip()
                if not alt_text:
                    issues.append(
                        make_issue(
                            file=path.as_posix(),
                            line=line_number,
                            severity="medium",
                            confidence="high",
                            issue_type="defect",
                            category="accessibility",
                            original=match.group(0),
                            message="Image has empty alternative text.",
                            suggestion=(
                                "Add concise alt text that communicates the image's "
                                "purpose, or use an explicitly decorative image pattern "
                                "where appropriate."
                            ),
                            source="static",
                        )
                    )
            # HTML/MDX img elements with missing or empty alt attributes.
            for match in self.HTML_IMG_RE.finditer(line):
                element = match.group(0)
                alt_match = self.ALT_ATTR_RE.search(element)
                if alt_match is None or not alt_match.group(2).strip():
                    issues.append(
                        make_issue(
                            file=path.as_posix(),
                            line=line_number,
                            severity="medium",
                            confidence="high",
                            issue_type="defect",
                            category="accessibility",
                            original=element,
                            message="Image element is missing meaningful alternative text.",
                            suggestion=(
                                "Add an alt attribute describing the image's purpose, "
                                "or use alt=\"\" only when the image is genuinely decorative."
                            ),
                            source="static",
                        )
                    )
            # Vague Markdown link text.
            for match in self.MARKDOWN_LINK_RE.finditer(line):
                label = re.sub(r"[`*_]", "", match.group(1)).strip().lower()
                if label in self.VAGUE_LINK_TEXT:
                    issues.append(
                        make_issue(
                            file=path.as_posix(),
                            line=line_number,
                            severity="low",
                            confidence="high",
                            issue_type="improvement",
                            category="accessibility",
                            original=match.group(0),
                            message=(
                                "Link text is vague when read out of context by a screen "
                                "reader or when scanning links."
                            ),
                            suggestion="Use link text that describes the destination or action.",
                            source="static",
                        )
                    )
        # Heading-level jumps.
        previous_level = None

        for line_number, line in iter_lines_outside_code_fences(content):
            match = re.match(r"^(#{1,6})\s+\S", line)

            if not match:
                continue

            level = len(match.group(1))
            if previous_level is not None and level > previous_level + 1:
                issues.append(
                    make_issue(
                        file=path.as_posix(),
                        line=line_number,
                        severity="low",
                        confidence="high",
                        issue_type="defect",
                        category="accessibility",
                        original=line,
                        message=(
                            f"Heading level jumps from H{previous_level} to H{level}, "
                            "which weakens the document outline."
                        ),
                        suggestion=(
                            "Use sequential heading levels unless the hierarchy is "
                            "intentionally represented by another accessible structure."
                        ),
                        source="static",
                    )
                )
            previous_level = level

        return issues


class LandingPageCoverageCheck(BaseCheck):
    name = "LandingPageCoverageCheck"
    supports_page = True
    source = "static"
    sections = {"tools": "sampleCard", "skills": "sampleCard",
                "docs-samples": "sampleCard", "case-studies": "caseStudyCard"}

    def run_page(self, path, content, api_key=None):
        from ruamel.yaml import YAML

        path = Path(path)
        try:
            relative = path.resolve().relative_to((PROJECT_ROOT / "docs").resolve())
        except ValueError:
            return []
        if len(relative.parts) < 2 or relative.parts[0] not in self.sections:
            return []
        if len(relative.parts) == 2 and path.stem == "index":
            return []
        parts = content.split("---", 2)
        front = YAML(typ="safe").load(parts[1]) if content.startswith("---\n") and len(parts) == 3 else {}
        front = front or {}
        if front.get("draft") is True:
            return []
        key = self.sections[relative.parts[0]]
        props = front.get("sidebar_custom_props")
        card = props.get(key) if isinstance(props, dict) else None
        missing = []
        if not isinstance(card, dict):
            missing.append(f"sidebar_custom_props.{key}")
        else:
            for field in ("tag", "description"):
                if not isinstance(card.get(field), str) or not card[field].strip():
                    missing.append(f"{key}.{field}")
            highlights = card.get("highlights")
            if not isinstance(highlights, list) or not highlights or any(
                    not isinstance(value, str) or not value.strip() for value in highlights):
                missing.append(f"{key}.highlights")
        if not missing:
            return []
        return [make_issue(
            file=path.as_posix(), line=1, severity="high", confidence="high",
            issue_type="defect", category="navigation", original=content.splitlines()[0] if content else "",
            message="Landing-page card metadata is missing or incomplete: " + ", ".join(missing),
            suggestion=f"Add valid sidebar_custom_props.{key} metadata so this page appears correctly on the {relative.parts[0]} landing page.",
            source="static",
        )]


class LinkCheck(BaseCheck):
    name = "LinkCheck"
    supports_page = True
    source = "static"

    MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
    MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    HTML_HREF_RE = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
    HTML_SRC_RE = re.compile(r"\bsrc\s*=\s*([\"'])(.*?)\1", re.IGNORECASE)
    def run_page(self, path, content, api_key=None):
        issues = []
        seen = set()

        for line_number, line in iter_lines_outside_code_fences(content):
            targets = []

            for match in self.MARKDOWN_LINK_RE.finditer(line):
                targets.append((match.group(0), self._extract_markdown_target(match.group(2))))
            for match in self.MARKDOWN_IMAGE_RE.finditer(line):
                targets.append((match.group(0), self._extract_markdown_target(match.group(2))))

            for match in self.HTML_HREF_RE.finditer(line):
                targets.append((match.group(0), match.group(2).strip()))

            for match in self.HTML_SRC_RE.finditer(line):
                targets.append((match.group(0), match.group(2).strip()))
            for original, target in targets:
                if not target or self._skip_target(target):
                    continue

                key = (line_number, target)

                if key in seen:
                    continue

                seen.add(key)

                if self._local_target_exists(path, target):
                    continue
                issues.append(
                    make_issue(
                        file=path.as_posix(),
                        line=line_number,
                        severity="high",
                        confidence="high",
                        issue_type="defect",
                        category="link",
                        original=original,
                        message=f"Local link or asset target does not resolve: {target}",
                        suggestion=(
                            "Correct the path or restore the referenced local file. "
                            "External HTTP(S) links are intentionally not checked here."
                        ),
                        source="static",
                    )
                )
        return issues

    @staticmethod
    def _extract_markdown_target(raw_target):
        """Remove an optional Markdown title from a simple link destination."""

        target = raw_target.strip()

        if target.startswith("<") and ">" in target:
            return target[1:target.index(">")].strip()

        # Common Markdown form: path "title"
        match = re.match(r"^(\S+)(?:\s+[\"'].*[\"'])?$", target)
        return match.group(1) if match else target
    @staticmethod
    def _skip_target(target):
        """Return True when a target should not be checked as a local file."""

        target = target.strip()

        if not target:
            return True

        # Fragment-only links point to the current page, not to another file.
        if target.startswith("#"):
            return True

        parsed = urlsplit(target)
        # Any explicit URI scheme is outside the local filesystem check.
        # This covers HTTP(S), mailto, tel, data, ftp, javascript, and others.
        if parsed.scheme:
            return True

        # Protocol-relative URLs such as //example.com/path are also external.
        if parsed.netloc:
            return True

        return False

    @staticmethod
    def _candidate_paths(source_path, target):
        parsed = urlsplit(target)
        path_part = unquote(parsed.path)
        if not path_part:
            return []

        if path_part.startswith("/"):
            relative = path_part.lstrip("/")

            if relative.startswith("img/") or relative.startswith("assets/"):
                base = ROOT / "static" / relative
            else:
                base = ROOT / relative
        else:
            base = source_path.parent / path_part

        candidates = [base]
        if base.suffix == "":
            candidates.extend(
                [
                    base.with_suffix(".md"),
                    base.with_suffix(".mdx"),
                    base / "index.md",
                    base / "index.mdx",
                ]
            )

        # Docusaurus frequently serves files under static/ from the site root.
        if path_part.startswith("/"):
            static_base = ROOT / "static" / path_part.lstrip("/")
            candidates.append(static_base)
            # React and Markdown pages are real routes, not root-level files.
            # Test explicit page entrypoints rather than accepting directories:
            # /explore?view=browse resolves to src/pages/explore/index.tsx.
            page_base = ROOT / "src" / "pages" / path_part.strip("/")
            if not page_base.suffix:
                for extension in (".md", ".mdx", ".js", ".jsx", ".ts", ".tsx"):
                    candidates.extend([page_base.with_suffix(extension), page_base / ("index" + extension)])
        return candidates

    def _local_target_exists(self, source_path, target):
        # Repository READMEs can legitimately link to source directories. Keep
        # those distinct from site-root routes, which require a page entrypoint.
        path_part = unquote(urlsplit(target).path)
        if not path_part.startswith("/") and (source_path.parent / path_part).is_dir():
            return True
        return any(candidate.is_file() for candidate in self._candidate_paths(source_path, target))
# ---------------------------------------------------------------------------
# Check selection and execution
# ---------------------------------------------------------------------------


def build_checks():
    """Return all available checks in execution order."""
    return [
        GrammarReview(),
        StructureReview(),
        PortfolioReview(),
        RepetitionReview(),
        DiagramReview(),
        AccessibilityCheck(),
        LinkCheck(),
        LandingPageCoverageCheck(),
        LycheeCheck(ROOT),
        RemarkCheck(ROOT),
        ValeCheck(ROOT),
        LtexCheck(ROOT),
        SiteWideConsistencyReview(),
    ]


def choose_review_mode():
    print()
    print("Review mode:")
    print("  1. Per page")
    print("  2. Site wide")
    print("  3. All (page and site checks)")
    print()
    while True:
        try:
            choice = input("Select review mode [1]: ").strip()
        except EOFError:
            print("No interactive input available; using per-page mode.")
            return "per-page"

        if not choice or choice == "1":
            return "per-page"

        if choice == "2":
            return "site-wide"
        if choice == "3":
            return "all"

        print("Please enter 1, 2 or 3.")

def choose_filter():
    print()
    print("Review checks:")
    print("  1. Full review (substantive AI defects)")
    print("  2. Optional editorial suggestions")
    print("  3. Portfolio only")
    print("  4. Repetition only")
    print("  5. Mermaid opportunities only")
    print("  6. Accessibility only")
    print("  7. Site-wide consistency only")
    print("  8. Remark Markdown/MDX only")
    print("  9. Vale only")
    print(" 10. LTeX+ grammar/spelling only")
    print(" 11. Lychee external links only")
    print(" 12. Local and external links only")
    print()
    choices = {
        "1": "full",
        "2": "editorial",
        "3": "portfolio",
        "4": "repetition",
        "5": "mermaid",
        "6": "accessibility",
        "7": "site-wide-consistency",
        "8": "remark",
        "9": "vale",
        "10": "ltex",
        "11": "lychee",
        "12": "links",
    }
    while True:
        try:
            choice = input("Select checks [1]: ").strip()
        except EOFError:
            print("No interactive input available; using full review.")
            return "full"

        if not choice:
            return "full"

        if choice in choices:
            return choices[choice]

        print("Please enter a number from 1 to 12.")

def selected_checks(filter_name):
    allowed = FILTER_PRESETS[filter_name]
    checks = [check for check in build_checks() if check.name in allowed]

    if not client.DEEPSEEK_AI_CHECKS_ENABLED:
        checks = [check for check in checks if check.source != "ai"]

    for check in checks:
        check.defects_only = filter_name == 'full' and check.source == 'ai'
    return checks


def resolve_mode_for_filter(mode, filter_name):
    """Handle presets that only make sense in one review scope."""
    if filter_name == "site-wide-consistency" and mode == "per-page":
        print("Site-wide consistency requires site-wide mode; switching to site-wide.")
        return "site-wide"

    page_only_filters = {
        "editorial",
        "portfolio",
        "mermaid",
        "accessibility",
        "links",
    }

    if filter_name in page_only_filters and mode == "site-wide":
        print(f"{FILTER_LABELS[filter_name]} requires per-page mode; switching to per-page.")
        return "per-page"
    return mode


# ---------------------------------------------------------------------------
# Finding relationships and saved-report refresh
# ---------------------------------------------------------------------------


def attach_related_findings(issues):
    """Expose overlap without merging allegations or their feedback identities."""
    groups = {}
    for issue in issues:
        if issue.get('source') == 'ai':
            groups.setdefault((issue['file'], issue['line'], issue['original']), []).append(issue)
    for group in groups.values():
        for issue in group:
            issue['related_findings'] = [other['issue_id'] for other in group
                                        if other is not issue and other.get('issue_id')]


def render_saved_report(reference, feedback_path, output_dir, *, compare=False):
    """Render saved findings with current feedback; never execute review checks."""
    payload, reference = load_report(reference)
    source_path = Path(reference) if not urlsplit(reference).scheme else None
    raw_snapshot = source_path.read_bytes() if source_path else (
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    output_dir = Path(output_dir).resolve()
    paths = ReportPaths.in_directory(output_dir)
    snapshot_path = output_dir / 'original-report.json'
    if source_path and source_path.resolve() in {paths.html, paths.json, paths.markdown}:
        raise ValueError('Choose a different output directory; the original report must not be overwritten')
    if snapshot_path.exists() and snapshot_path.read_bytes() != raw_snapshot:
        raise ValueError('Output directory contains a different original report; choose a new directory')
    issues = payload['issues']
    metadata = dict(payload['metadata'])
    errors = payload.get('errors', [])
    thresholds = payload['ci']['thresholds']
    if not all(isinstance(thresholds.get(key), int) for key in ('high', 'medium', 'api_errors')):
        raise ValueError('Saved report must include its original CI thresholds')
    attach_feedback_status(issues, feedback_path)
    comparison_errors = []
    if compare:
        from qa_recurrence import compare_recurrences
        comparison_errors = compare_recurrences(issues, feedback_path=feedback_path,
            api_key=os.environ.get('DEEPSEEK_API_KEY'), request_review=client.request_review)
    ci_result = evaluate_ci(issues, errors, thresholds['high'], thresholds['medium'], thresholds['api_errors'])
    metadata['feedback_updated_at'] = london_now().isoformat(timespec='seconds')
    metadata['review_report_reference'] = str(source_path.resolve()) if source_path else reference
    metadata['original_report_snapshot'] = snapshot_path.name
    metadata['feedback_view'] = True
    metadata['feedback_file'] = str(feedback_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not snapshot_path.exists():
        snapshot_path.write_bytes(raw_snapshot)
    write_reports(Report(issues, errors, metadata, ci_result), paths,
                  {check.name: check.source for check in build_checks()})
    counts = report_counts(issues)
    print(f"Rendered saved report: {paths.html}")
    print(f"Active: {counts['active']}; pending: {counts['pending']}; withdrawn/dismissed: {counts['history']}")
    print(('Compared possible recurrences; no review checks were rerun.' if compare else
           'No checks or AI calls were run.') + ' Original snapshot: ' + str(snapshot_path))
    if comparison_errors:
        print(f'Recurrence comparison failures: {len(comparison_errors)}; findings remain unresolved.')
    print('CI result: ' + ('PASS' if ci_result['passed'] else 'FAIL'))
    return ci_result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run documentation QA, compare recurring findings, or record human feedback."
    )
    parser.add_argument("command", nargs="?", choices=["challenge", "resolve", "render", "compare", "link", "reuse"],
                        help="Challenge/resolve findings, compare recurrences, confirm/reject links, or render saved reports")
    parser.add_argument("--no-review-cache", action="store_true",
                        help="Bypass review cache reads and writes for a fresh AI review")
    parser.add_argument("--include-file", type=Path, action="append", default=[],
                        help="Also review a repository-relative Markdown or MDX file. Repeat as needed.")
    parser.add_argument("--proposal", help="Source-bound proposal token copied from the report")
    parser.add_argument("--previous", help="Previous feedback record ID for link confirmation/rejection")
    parser.add_argument("--issue", help="Stable QA issue ID for challenge mode")
    parser.add_argument("--report", help="Exact local report JSON path or versioned GitHub Pages JSON URL for challenge, resolve or render")
    parser.add_argument("--reason", help="Rebuttal or human resolution explanation")
    parser.add_argument("--retry", action="store_true", help="Retry pending challenge without adding a new rebuttal")
    parser.add_argument("--decision", choices=["accepted", "dismissed", "change_requested", "pending", "confirmed", "rejected"], help="Human resolution, or confirmed/rejected for the link command")
    parser.add_argument("--reason-file", type=Path, help="Read rebuttal from a UTF-8 text file")
    parser.add_argument("--findings-file", type=Path, default=DEFAULT_FINDINGS)
    parser.add_argument("--feedback-file", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--report-dir", type=Path, default=None,
                        help="Directory for HTML, JSON and Markdown reports, relative to project root. "
                             "Defaults to .qa locally and project root in GitHub Actions.")

    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run non-interactively and return exit code 1 when thresholds fail.",
    )
    parser.add_argument(
        "--mode",
        choices=["per-page", "site-wide", "all"],
        help="Review scope. Defaults to per-page in CI mode.",
    )

    parser.add_argument(
        "--filter",
        choices=list(FILTER_PRESETS),
        help="Check preset. Defaults to full in CI mode.",
    )

    parser.add_argument(
        "--fail-high",
        type=int,
        default=DEFAULT_FAIL_HIGH,
        help=f"Fail CI when high issues exceed this value (default: {DEFAULT_FAIL_HIGH}).",
    )
    parser.add_argument(
        "--fail-medium",
        type=int,
        default=DEFAULT_FAIL_MEDIUM,
        help=f"Fail CI when medium issues exceed this value (default: {DEFAULT_FAIL_MEDIUM}).",
    )

    parser.add_argument(
        "--fail-api-errors",
        type=int,
        default=DEFAULT_FAIL_API_ERRORS,
        help=(
            "Fail CI when API/check errors exceed this value "
            f"(default: {DEFAULT_FAIL_API_ERRORS})."
        ),
    )

    return parser.parse_args()

def main():
    # The script historically assumes project-relative paths throughout its checks,
    # source references, Git commands, and report generation. Set that base once.
    # This also makes `python /path/to/project/scripts/ai_docs_review.py` work from
    # any local directory, including the scripts directory itself.
    os.chdir(PROJECT_ROOT)
    args = parse_args()
    # Local reports belong under .qa; retain root outputs for the existing
    # GitHub Actions deployment workflow, which uploads these root filenames.
    # An explicit --report-dir overrides either default.
    report_dir = args.report_dir if args.report_dir is not None else (
        Path(".") if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" else Path(".qa")
    )
    if args.command in {'render', 'compare'} and args.report_dir is None:
        report_dir = Path('.qa') / 'feedback-view'
    if not report_dir.is_absolute():
        report_dir = PROJECT_ROOT / report_dir
    paths = ReportPaths.in_directory(report_dir)
    if args.command not in {"challenge", "resolve", "render", "compare", "link", "reuse"}:
        report_dir.mkdir(parents=True, exist_ok=True)
    assert_ci_policy_invariants()
    if args.command == 'reuse':
        if not all([args.report, args.issue, args.previous, args.proposal, args.reason]) or args.decision or args.retry or args.reason_file:
            print('Reuse requires --report, --issue, --previous, --proposal and --reason', file=sys.stderr)
            return 2
        from qa_recurrence import reuse_decision
        try:
            result = reuse_decision(args.issue, args.previous, args.reason, report=args.report,
                                    proposal=args.proposal, feedback_path=args.feedback_file)
        except (ValueError, OSError, requests.RequestException, KeyError) as error:
            print(f'Revalidation failed: {error}', file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print('Human-approved decision reuse recorded. Render the report again.')
        return 0
    if args.command == 'link':
        if not args.report or not args.issue or not args.previous or not args.reason or args.decision not in {'confirmed', 'rejected'} or args.retry or args.reason_file:
            print('Link requires --report, --issue, --previous, --decision confirmed/rejected and --reason', file=sys.stderr)
            return 2
        from qa_recurrence import decide_link
        try:
            result = decide_link(args.issue, args.previous, args.decision, args.reason,
                                 report=args.report, proposal=args.proposal, feedback_path=args.feedback_file)
        except (ValueError, OSError, requests.RequestException, KeyError) as error:
            print(f'Link failed: {error}', file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print('Link recorded. Confirmation does not dismiss or adjudicate the finding. Render the report again.')
        return 0
    if args.command in {'render', 'compare'}:
        if not args.report:
            print('Render requires --report with the saved report JSON path or versioned URL', file=sys.stderr)
            return 2
        try:
            if args.command == 'compare' and (not client.DEEPSEEK_AI_CHECKS_ENABLED or not os.environ.get('DEEPSEEK_API_KEY')):
                print('Compare requires enabled DeepSeek checks and DEEPSEEK_API_KEY', file=sys.stderr)
                return 2
            result = render_saved_report(args.report, args.feedback_file, report_dir,
                                         compare=args.command == 'compare')
        except (ValueError, OSError, requests.RequestException, KeyError, json.JSONDecodeError) as error:
            print(f'Render failed: {error}', file=sys.stderr)
            return 1
        return 1 if args.ci and not result['passed'] else 0
    if args.command == "resolve":
        if not args.issue or not args.decision or not args.reason or args.reason_file or args.retry:
            print("Resolve requires --issue, --decision and --reason", file=sys.stderr)
            return 2
        try:
            result = resolve_finding(args.issue, args.decision, args.reason,
                                     feedback_path=args.feedback_file, report=args.report)
        except (ValueError, OSError, requests.RequestException, KeyError, json.JSONDecodeError) as error:
            print(f"Resolve failed: {error}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "challenge":
        if not args.issue:
            print("Challenge requires --issue", file=sys.stderr)
            return 2
        if (args.retry and (args.reason is not None or args.reason_file is not None)) or (not args.retry and bool(args.reason) == bool(args.reason_file)):
            print("Provide exactly one of --reason or --reason-file", file=sys.stderr)
            return 2
        if not client.DEEPSEEK_AI_CHECKS_ENABLED:
            print("DeepSeek checks are disabled", file=sys.stderr)
            return 2
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            print("DEEPSEEK_API_KEY is required", file=sys.stderr)
            return 2
        try:
            rebuttal = None if args.retry else (args.reason if args.reason is not None else args.reason_file.read_text(encoding="utf-8"))
            decision = challenge_finding(args.issue, rebuttal, retry=args.retry,
                findings_path=args.findings_file, feedback_path=args.feedback_file,
                api_key=api_key, request_review=client.request_review, report=args.report)
        except (ValueError, OSError, requests.RequestException, KeyError, json.JSONDecodeError) as error:
            print(f"Challenge failed: {error}", file=sys.stderr)
            return 1
        print(json.dumps(decision, ensure_ascii=False, indent=2))
        print(f"Feedback saved to {args.feedback_file}")
        return 0

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if client.DEEPSEEK_AI_CHECKS_ENABLED:
        print("DeepSeek AI checks: ENABLED")
    else:
        print("DeepSeek AI checks: DISABLED (hardcoded switch)")

    try:
        files = markdown_files(args.include_file)
    except (ValueError, OSError) as error:
        print(f"Invalid review scope: {error}", file=sys.stderr)
        return 2

    print(f"Found {len(files)} documentation files.")

    if not files:
        print("No Markdown or MDX files found.")
        return 0
    # GitHub Actions and other CI runners do not provide interactive stdin.
    # Only display menus when we actually have a terminal and --ci was not used.
    interactive = sys.stdin.isatty() and not args.ci

    if args.mode:
        mode = args.mode
    elif interactive:
        mode = choose_review_mode()
    else:
        mode = "per-page"
        print("No interactive input available; defaulting --mode to per-page.")
    if args.filter:
        filter_name = args.filter
    elif interactive:
        filter_name = choose_filter()
    else:
        filter_name = "full"
        print("No interactive input available; defaulting --filter to full.")

    mode = resolve_mode_for_filter(mode, filter_name)
    plan = CheckPlan.for_mode(mode, selected_checks(filter_name))
    checks = plan.checks
    if not checks:
        if not client.DEEPSEEK_AI_CHECKS_ENABLED:
            print(
                "No runnable checks remain for this preset because DeepSeek AI checks "
                "are disabled by the hardcoded switch."
            )
        else:
            print("No checks are available for the selected mode and filter.")
        return 2

    if client.DEEPSEEK_AI_CHECKS_ENABLED and not api_key and any(
        check.source == "ai" for check in checks
    ):
        print("DEEPSEEK_API_KEY is not set, but the selected review includes AI checks.")
        return 2
    print()
    print(f"Mode: {mode}")
    print(f"Checks: {FILTER_LABELS[filter_name]}")
    print("Selected implementations:")

    for check in checks:
        print(f"  - {check.name} ({check.source})")

    print()

    cache = AIReviewCache(PROJECT_ROOT / '.qa/review-cache', enabled=not args.no_review_cache)
    result = run_checks(files, plan, api_key, cached_check=cache.run)
    issues, errors = result.issues, result.errors
    decorate_issues(issues)
    attach_related_findings(issues)
    attach_feedback_status(issues, args.feedback_file)
    if client.DEEPSEEK_AI_CHECKS_ENABLED and api_key:
        from qa_recurrence import compare_recurrences
        comparison_errors = compare_recurrences(issues, feedback_path=args.feedback_file,
            api_key=api_key, request_review=client.request_review)
        if comparison_errors:
            print(f'Recurrence comparison failures: {len(comparison_errors)}; findings remain unresolved.')
    save_findings(issues, args.findings_file)
    ci_result = evaluate_ci(
        issues,
        errors,
        fail_high=args.fail_high,
        fail_medium=args.fail_medium,
        fail_api_errors=args.fail_api_errors,
    )
    metadata = {
        **report_run_metadata(),
        "mode": mode,
        "feedback_file": str(args.feedback_file),
        "filter": filter_name,
        "filter_label": FILTER_LABELS[filter_name],
        "model": client.MODEL if client.DEEPSEEK_AI_CHECKS_ENABLED else f"{client.MODEL} (disabled)",
        "ai_review_policy_version": AI_REVIEW_POLICY_VERSION,
        "ai_checks_enabled": client.DEEPSEEK_AI_CHECKS_ENABLED,
        "ai_review_intent": "substantive-defects" if filter_name == "full" else "optional-editorial",
        "files_reviewed": len(files),
        "checks": [check.name for check in checks],
        "portfolio_url": PORTFOLIO_URL,
        "github_repository": github_repository(),
        "github_revision": github_revision(),
    }
    write_reports(Report(issues, errors, metadata, ci_result), paths,
                  {check.name: check.source for check in build_checks()})

    print()
    print(f"HTML report: {paths.html.as_posix()}")
    print(f"JSON report: {paths.json.as_posix()}")
    print(f"Markdown report: {paths.markdown.as_posix()}")
    print()
    print(
        "CI thresholds (deterministic findings + high-confidence AI defects only): "
        f"high > {args.fail_high}, "
        f"medium > {args.fail_medium}, "
        f"API/check errors > {args.fail_api_errors}"
    )
    print(
        "AI advisory findings excluded from CI thresholds: "
        f"{ci_result['advisory_ai_issue_count']}"
    )

    if ci_result["passed"]:
        print("CI result: PASS")
    else:
        print("CI result: FAIL")
        for failure in ci_result["failures"]:
            print(f"  - {failure}")

    if args.ci and not ci_result["passed"]:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
