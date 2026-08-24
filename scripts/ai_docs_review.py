import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests


API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"

# Hardcoded operational switch. Keep this False to disable all DeepSeek-backed
# checks without changing filter definitions or command-line invocations.
# Set it back to True when AI review should be re-enabled.
DEEPSEEK_AI_CHECKS_ENABLED = True

ROOT = Path(".")
REPORT = Path("ai-doc-review.html")
JSON_REPORT = Path("ai-doc-review.json")

PORTFOLIO_URL = "https://iand4096.github.io/docusaurusportfolio"
GITHUB_REPOSITORY_FALLBACK = "iand4096/docusaurusportfolio"

EXCLUDED_DIRS = {
    "node_modules",
    "build",
    ".docusaurus",
    ".git",
    "static",
    "taxonomy",
}

SEVERITIES = {"high", "medium", "low"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
ISSUE_TYPES = {"defect", "improvement", "diagram"}

DEFAULT_FAIL_HIGH = 0
DEFAULT_FAIL_MEDIUM = 25
DEFAULT_FAIL_API_ERRORS = 0

FILTER_PRESETS = {
    "full": {
        "GrammarReview",
        "StructureReview",
        "PortfolioReview",
        "RepetitionReview",
        "DiagramReview",
        "AccessibilityCheck",
        "LinkCheck",
        "LycheeCheck",
        "RemarkCheck",
        "ValeCheck",
        "LtexCheck",
        "SiteWideConsistencyReview",
    },
    "editorial": {
        "GrammarReview",
        "StructureReview",
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
    "full": "Full review",
    "editorial": "Editorial only",
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


COMMON_AI_RULES = r"""
Use British English.

Be conservative. Report only meaningful issues. A good page may legitimately
return no issues.

Do not:
- invent facts, responsibilities, metrics, audiences, outcomes, technical
  relationships or source text
- manufacture findings merely because you were asked to review the page
- rewrite text only because another style is possible
- claim technical information is incorrect unless the supplied text itself
  demonstrates the inconsistency
- include the artificial line-number prefix in the quoted source text

Every issue must include exact source text copied verbatim from the supplied
file in "original". The quoted text must be sufficient to identify the issue.
Do not paraphrase "original".

Severity means impact:
- high: materially misleading, broken, contradictory or publication-blocking
- medium: meaningful comprehension, structure or portfolio-quality problem
- low: worthwhile but non-blocking improvement

Confidence means certainty that the issue is genuinely present:
- high: directly supported by the supplied text
- medium: well supported but involves some editorial judgement
- low: plausible but subjective

Use issue type:
- defect: something is objectively or substantively wrong
- improvement: a defensible editorial or information-design improvement
- diagram: an optional Mermaid visualisation opportunity

Return JSON only. Do not include Markdown fences or commentary.
"""

PAGE_JSON_CONTRACT = r"""
Return exactly this structure:

{
  "issues": [
    {
      "severity": "high|medium|low",
      "confidence": "high|medium|low",
      "type": "defect|improvement|diagram",
      "category": "CATEGORY_FROM_THIS_CHECK",
      "line": 12,
      "original": "exact source text",
      "message": "Concise explanation of the problem",
      "suggestion": "Specific suggested correction or improvement",
      "source": "ai"
    }
  ]
}

Return {"issues": []} when there are no meaningful findings.
"""

SITE_JSON_CONTRACT = r"""
Return exactly this structure:

{
  "issues": [
    {
      "file": "docs/example.mdx",
      "severity": "high|medium|low",
      "confidence": "high|medium|low",
      "type": "defect|improvement|diagram",
      "category": "CATEGORY_FROM_THIS_CHECK",
      "line": 12,
      "original": "exact source text copied from the named file",
      "message": "Concise explanation of the site-wide problem",
      "suggestion": "Specific suggested correction or improvement",
      "source": "ai"
    }
  ]
}

The "file" value must exactly match one of the FILE values supplied in the
user message.

Return {"issues": []} when there are no meaningful findings.
"""


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def markdown_files():
    """Yield Markdown and MDX files that should be reviewed."""

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".md", ".mdx"}:
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        yield path


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


def add_line_numbers(text):
    """Add artificial line numbers for the model."""

    return "\n".join(
        f"{number:5}: {line}"
        for number, line in enumerate(text.splitlines(), start=1)
    )


def parse_model_json(model_output):
    """Parse JSON, tolerating accidental Markdown fences."""

    text = model_output.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return json.loads(text)


def request_review(system_prompt, user_prompt, api_key):
    """Send a review request, retrying once if the model returns invalid JSON."""

    if not DEEPSEEK_AI_CHECKS_ENABLED:
        raise RuntimeError(
            "DeepSeek AI checks are disabled by DEEPSEEK_AI_CHECKS_ENABLED = False."
        )

    payload = {
        "model": MODEL,
        "thinking": {"type": "disabled"},
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    last_error = None

    for attempt in range(2):
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )

        response.raise_for_status()
        result = response.json()
        model_output = result["choices"][0]["message"]["content"]

        try:
            return parse_model_json(model_output)
        except json.JSONDecodeError as error:
            last_error = error

            if attempt == 0:
                payload["messages"] = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return the review again as strictly valid JSON only. "
                            "Ensure all strings are correctly escaped and all "
                            "commas, quotes, brackets and braces are valid."
                        ),
                    },
                ]

    raise last_error


def find_source_line(content, original, preferred_line=None):
    """Return the source line on which an exact quoted fragment starts."""

    positions = []
    start = 0

    while True:
        index = content.find(original, start)

        if index == -1:
            break

        positions.append(content.count("\n", 0, index) + 1)
        start = index + 1

    if not positions:
        return None

    if isinstance(preferred_line, int) and preferred_line > 0:
        return min(positions, key=lambda line: abs(line - preferred_line))

    return positions[0]


def source_line_text(content, line_number):
    lines = content.splitlines()

    if 1 <= line_number <= len(lines):
        return lines[line_number - 1]

    return ""


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


def normalise_ai_issue(issue, content, file_path, allowed_categories):
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

    # Source is assigned by the implementation rather than trusted from AI.
    return make_issue(
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


def iter_lines_outside_code_fences(content):
    """Yield (line_number, text) while skipping fenced code blocks."""

    in_fence = False
    fence_marker = None

    for number, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        match = re.match(r"(```+|~~~+)", stripped)

        if match:
            marker = match.group(1)

            if not in_fence:
                in_fence = True
                fence_marker = marker[0]
            elif marker[0] == fence_marker:
                in_fence = False
                fence_marker = None

            continue

        if not in_fence:
            yield number, line


# ---------------------------------------------------------------------------
# Check architecture
# ---------------------------------------------------------------------------


class BaseCheck(ABC):
    name = "BaseCheck"
    supports_page = False
    supports_site = False
    source = "ai"

    def run_page(self, path, content, api_key):
        return []

    def run_site(self, paths, contents, api_key):
        return []


class AIPageCheck(BaseCheck):
    supports_page = True
    allowed_categories = set()
    prompt = ""

    def run_page(self, path, content, api_key):
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.prompt
            + "\n\n"
            + PAGE_JSON_CONTRACT
        )

        parsed = request_review(
            system_prompt,
            (
                f"FILE: {path.as_posix()}\n\n"
                f"{add_line_numbers(content)}"
            ),
            api_key,
        )

        issues = parsed.get("issues", [])

        if not isinstance(issues, list):
            return []

        validated = []

        for issue in issues:
            normalised = normalise_ai_issue(
                issue,
                content,
                path.as_posix(),
                self.allowed_categories,
            )

            if normalised is not None:
                validated.append(normalised)

        return validated


class GrammarReview(AIPageCheck):
    name = "GrammarReview"
    allowed_categories = {
        "grammar",
        "clarity",
        "consistency",
        "unfinished",
        "punctuation",
    }
    prompt = r"""
Review sentence-level editorial quality only.

Look for:
- grammar problems
- materially awkward or confusing wording
- incomplete sentences
- inconsistent terminology within the page
- unfinished or placeholder content
- punctuation or hyphenation problems that affect correctness

Do not perform general spelling checking. Spelling is checked separately.
Do not change valid British English to American English.
Do not recommend Oxford -ize spelling.
Do not flag correctly spelled technical or product terminology merely because it
is unusual.

Allowed categories:
grammar, clarity, consistency, unfinished, punctuation

Use type "defect" for genuine language/correctness problems and "improvement"
only when comprehension is materially improved.
"""


class StructureReview(AIPageCheck):
    name = "StructureReview"
    allowed_categories = {
        "structure",
        "scannability",
        "over-explanation",
    }
    prompt = r"""
Review information structure and scannability only.

Look for:
- information in an awkward order
- a paragraph doing several unrelated jobs
- important context arriving too late
- dense paragraphs that materially benefit from division
- closely related information being unnecessarily separated
- headings that do not accurately describe their content
- excessive background explanation for a portfolio case study
- important information that is unnecessarily difficult to scan

Do not add headings merely to create more sections.
Do not convert short coherent paragraphs to bullets without a clear benefit.
Do not report ordinary grammar or spelling issues.

Allowed categories:
structure, scannability, over-explanation

These findings will normally use type "improvement".
"""


class PortfolioReview(AIPageCheck):
    name = "PortfolioReview"
    allowed_categories = {"portfolio"}
    prompt = r"""
Review this specifically as a technical-writing portfolio case study.

Consider whether the supplied page effectively communicates, where relevant:
- what the documentation deliverable was
- who it was for
- what the author contributed
- what made the work useful or challenging
- the relationship between the portfolio description and the published work

Identify places where the page spends substantially more space explaining the
technology than demonstrating the documentation work.

Do not invent project results, metrics, responsibilities, audiences, business
impact, design decisions or technical facts.

If information is genuinely absent, describe only the KIND of information that
could strengthen the page. Do not fabricate the missing content.

Allowed category:
portfolio

Use type "improvement".
"""


class DiagramReview(AIPageCheck):
    name = "DiagramReview"
    allowed_categories = {"diagram"}
    prompt = r"""
Look very sparingly for Mermaid diagram opportunities.

A diagram is appropriate only when the supplied text describes something that
would be substantially easier to understand visually, such as:
- a sequence of interactions
- an API workflow
- a lifecycle
- a transformation
- relationships among several systems or components
- a decision process
- a non-obvious hierarchy

Do not suggest a diagram:
- merely to make the page more visual
- for a simple definition or fact
- for an already-clear list
- when the diagram would just repeat one or two straightforward sentences
- when the diagram would require invented technical relationships

Prefer ZERO findings for most short pages.
Return no more than ONE issue.

Allowed category:
diagram

Every finding must use severity "low" and type "diagram".
The suggestion should name the simplest appropriate Mermaid diagram type and
briefly describe what it should show. Include Mermaid source only when every
node and relationship is directly supported by the supplied text.
"""


class RepetitionReview(BaseCheck):
    name = "RepetitionReview"
    supports_page = True
    supports_site = True
    allowed_categories = {"repetition"}

    PAGE_PROMPT = r"""
Review only for unnecessary repetition within this page.

Flag repetition when:
- two passages communicate substantially the same information
- a later sentence repeats something the reader has already understood
- several sentences could be consolidated without losing useful meaning
- terminology is repeatedly re-explained after it has been established

Do not flag intentional repetition needed for clarity, repeated product names,
or passages merely because they concern the same broad subject.

Allowed category:
repetition

Use type "improvement" unless repetition creates a substantive contradiction.
"""

    SITE_PROMPT = r"""
Compare the supplied files only for unnecessary repetition across pages.

Look for:
- substantially identical introductions
- repeated explanations of the same concept
- repeated descriptions of the author's role
- repeated publication or repository boilerplate
- repeated background information
- repeated definitions that could be explained once elsewhere

Do not flag repetition merely because several case studies use the same product,
technology or terminology.

Only report repetition when reducing or consolidating it would materially improve
the portfolio.

For every issue, choose one file as the primary place where action should be
taken and quote exact text from that file. Mention the relevant comparison with
other supplied files in the message.

Allowed category:
repetition

Use type "improvement".
"""

    def run_page(self, path, content, api_key):
        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.PAGE_PROMPT
            + "\n\n"
            + PAGE_JSON_CONTRACT
        )

        parsed = request_review(
            system_prompt,
            f"FILE: {path.as_posix()}\n\n{add_line_numbers(content)}",
            api_key,
        )

        issues = parsed.get("issues", [])
        validated = []

        if not isinstance(issues, list):
            return validated

        for issue in issues:
            normalised = normalise_ai_issue(
                issue,
                content,
                path.as_posix(),
                self.allowed_categories,
            )

            if normalised is not None:
                validated.append(normalised)

        return validated

    def run_site(self, paths, contents, api_key):
        sections = []

        for path in paths:
            path_string = path.as_posix()
            content = contents.get(path_string, "")

            if not content.strip():
                continue

            sections.append(
                "\n".join(
                    [
                        "=" * 72,
                        f"FILE: {path_string}",
                        "=" * 72,
                        add_line_numbers(content),
                    ]
                )
            )

        if not sections:
            return []

        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.SITE_PROMPT
            + "\n\n"
            + SITE_JSON_CONTRACT
        )

        parsed = request_review(
            system_prompt,
            "Compare these files:\n\n" + "\n\n".join(sections),
            api_key,
        )

        return validate_site_ai_issues(
            parsed.get("issues", []),
            paths,
            contents,
            self.allowed_categories,
        )


class SiteWideConsistencyReview(BaseCheck):
    name = "SiteWideConsistencyReview"
    supports_site = True
    allowed_categories = {"consistency", "structure", "portfolio"}

    PROMPT = r"""
Compare the supplied documentation as one technical-writing portfolio.
Do not perform grammar, spelling or sentence-level editing.
Do not report cross-page repetition; that is handled by another check.

Focus on meaningful site-wide inconsistencies involving:

1. Structural consistency
- comparable case studies present equivalent information in confusingly
  different locations
- one comparable page clearly establishes the author's contribution while
  another does not
- comparable information appears under materially inconsistent headings
- important information is easy to locate on some pages but buried on others

Do not demand identical templates. Some variation is appropriate.

2. Terminology consistency
- the same concept is named differently across pages in a way that could confuse
  readers

Do not report harmless stylistic variation.

3. Portfolio effectiveness
- recurring structural patterns make it difficult to compare case studies
- case studies systematically explain technology more strongly than they
  demonstrate the documentation work
- information architecture could be consolidated or reorganised across the site

Do not invent missing project information. If a useful field appears absent,
describe only the kind of information that could strengthen comparable pages.

For every finding, choose one specific file as the primary action location and
quote exact text from that file. Use the message to explain the comparison with
other supplied files.

Allowed categories:
consistency, structure, portfolio

Use type "improvement" unless the inconsistency is objectively defective.
"""

    def run_site(self, paths, contents, api_key):
        sections = []

        for path in paths:
            path_string = path.as_posix()
            content = contents.get(path_string, "")

            if not content.strip():
                continue

            sections.append(
                "\n".join(
                    [
                        "=" * 72,
                        f"FILE: {path_string}",
                        "=" * 72,
                        add_line_numbers(content),
                    ]
                )
            )

        if not sections:
            return []

        system_prompt = (
            COMMON_AI_RULES
            + "\n\n"
            + self.PROMPT
            + "\n\n"
            + SITE_JSON_CONTRACT
        )

        parsed = request_review(
            system_prompt,
            "Review these files as one portfolio:\n\n" + "\n\n".join(sections),
            api_key,
        )

        return validate_site_ai_issues(
            parsed.get("issues", []),
            paths,
            contents,
            self.allowed_categories,
        )


def validate_site_ai_issues(issues, paths, contents, allowed_categories):
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
        )

        if normalised is not None:
            validated.append(normalised)

    return validated


# ---------------------------------------------------------------------------
# Vale integration
# ---------------------------------------------------------------------------


VALE_SEVERITY_MAP = {
    "error": "high",
    "warning": "medium",
    "suggestion": "low",
}


def normalise_vale_path(raw_path, paths):
    """Match a Vale result path to one of the files supplied to Vale."""

    if not isinstance(raw_path, str) or not raw_path.strip():
        return None

    candidate = raw_path.strip().replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]

    aliases = {}

    for path in paths:
        relative = path.as_posix()
        aliases[relative] = path

        try:
            aliases[path.resolve().as_posix()] = path
        except OSError:
            pass

    if candidate in aliases:
        return aliases[candidate]

    try:
        resolved = Path(raw_path).resolve().as_posix()
    except OSError:
        return None

    return aliases.get(resolved)


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
        path = normalise_vale_path(raw_path, paths)

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


def vale_preflight():
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
        cwd=ROOT,
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

    config_path = ROOT / ".vale.ini"

    if not config_path.is_file():
        raise RuntimeError(
            f"Vale configuration file was not found: {config_path.resolve()}. "
            "Commit .vale.ini at the repository root before running Vale in CI."
        )

    print(f"  Config: {config_path.resolve()}")

    config_result = subprocess.run(
        [executable, "ls-config"],
        cwd=ROOT,
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


class ValeCheck(BaseCheck):
    """Run Vale once across the selected Markdown/MDX files."""

    name = "ValeCheck"
    source = "vale"

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
            cwd=ROOT,
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


# ---------------------------------------------------------------------------
# LTeX+ grammar/spelling integration
# ---------------------------------------------------------------------------


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


def ltex_preflight():
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
        cwd=ROOT,
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

    config_path = ROOT / ".ltex.json"

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

        path = normalise_vale_path(header.get("path"), paths)
        if path is None:
            # Some renderers use file:// URIs. Convert those to local paths.
            raw_path = str(header.get("path") or "").strip()
            if raw_path.lower().startswith("file://"):
                candidate = unquote(urlsplit(raw_path).path)
                if os.name == "nt" and re.match(r"^/[A-Za-z]:/", candidate):
                    candidate = candidate[1:]
                path = normalise_vale_path(candidate, paths)

        current_header = header
        current_path = path
        current_block = []

    flush()
    return issues


class LtexCheck(BaseCheck):
    """Run LTeX+ once across the selected Markdown/MDX files."""

    name = "LtexCheck"
    source = "ltex"

    def run_files(self, paths, executable=None):
        executable = executable or shutil.which("ltex-cli-plus")

        if executable is None:
            raise RuntimeError(
                "LTeX+ CLI was not found in PATH. Run the LTeX+ preflight before "
                "executing LtexCheck."
            )

        config_path = ROOT / ".ltex.json"
        if not config_path.is_file():
            raise RuntimeError(".ltex.json was not found at the repository root.")

        command = [
            executable,
            f"--client-configuration={config_path.as_posix()}",
            *[path.as_posix() for path in paths],
        ]

        result = subprocess.run(
            command,
            cwd=ROOT,
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


# ---------------------------------------------------------------------------
# Remark Markdown/MDX integration
# ---------------------------------------------------------------------------


def find_remark_executable():
    """Return the local Remark CLI executable, with a PATH fallback."""

    binary_name = "remark.cmd" if os.name == "nt" else "remark"
    local_binary = ROOT / "node_modules" / ".bin" / binary_name

    if local_binary.is_file():
        return str(local_binary.resolve())

    return shutil.which("remark")


def find_remark_config():
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
        path = ROOT / name
        if path.is_file():
            return str(path.resolve())

    package_path = ROOT / "package.json"
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package = None

        if isinstance(package, dict) and "remarkConfig" in package:
            return f"{package_path.resolve()} (remarkConfig)"

    return None


def remark_preflight():
    """Validate the Remark CLI and repository configuration before checks run."""

    print("Remark preflight:")

    executable = find_remark_executable()

    if executable is None:
        raise RuntimeError(
            "Remark CLI was not found. Install remark-cli in the repository with "
            "`npm install --save-dev remark-cli` (or run `npm ci` in CI)."
        )

    print(f"  Executable: {executable}")

    version_result = subprocess.run(
        [executable, "--version"],
        cwd=ROOT,
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

    config = find_remark_config()
    if config is None:
        raise RuntimeError(
            "No Remark configuration was found. Commit .remarkrc.mjs (recommended "
            "for this Docusaurus repository) or configure remarkConfig in package.json."
        )

    print(f"  Config: {config}")

    ignore_path = ROOT / ".remarkignore"
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
        path = normalise_vale_path(raw_path, paths)

        if path is None:
            continue

        messages = file_result.get("messages", [])
        if not isinstance(messages, list):
            continue

        content = path.read_text(encoding="utf-8")

        for message in messages:
            if not isinstance(message, dict):
                continue

            reason = str(message.get("reason", "")).strip()
            if not reason:
                continue

            rule_id = str(message.get("ruleId") or "remark").strip()
            message_source = str(message.get("source") or "remark").strip()

            line = message.get("line")
            if not isinstance(line, int) or line <= 0:
                line = 1

            fatal = message.get("fatal")
            if fatal is True:
                severity = "high"
            elif fatal is False:
                severity = "medium"
            else:
                severity = "low"

            actual = message.get("actual")
            if isinstance(actual, str) and actual.strip():
                original = actual.strip()
            else:
                original = source_line_text(content, line)

            if not original:
                original = "<file-level Remark finding>"

            expected = message.get("expected")
            note = message.get("note")

            if isinstance(note, str) and note.strip():
                suggestion = note.strip()
            elif isinstance(expected, list) and expected:
                expected_text = ", ".join(str(item) for item in expected)
                suggestion = f"Update the Markdown/MDX to use one of: {expected_text}."
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


class RemarkCheck(BaseCheck):
    """Run Remark once across the selected Markdown/MDX files."""

    name = "RemarkCheck"
    source = "remark"

    # A tiny reporter module keeps this integration self-contained and avoids
    # requiring vfile-reporter-json as an extra project dependency.
    REPORTER_SOURCE = r'''export default function reporter(files) {
  const list = Array.isArray(files) ? files : [files];

  return JSON.stringify(list.map((file) => ({
    path: file.path || '',
    cwd: file.cwd || '',
    history: file.history || [],
    messages: (file.messages || []).map((message) => ({
      reason: message.reason || String(message),
      line: message.line ?? null,
      column: message.column ?? null,
      fatal: message.fatal ?? null,
      ruleId: message.ruleId ?? null,
      source: message.source ?? null,
      actual: message.actual ?? null,
      expected: message.expected ?? null,
      note: message.note ?? null,
      url: message.url ?? null
    }))
  })));
}
'''

    def run_files(self, paths, executable=None):
        executable = executable or find_remark_executable()

        if executable is None:
            raise RuntimeError(
                "Remark CLI was not found. Run the Remark preflight before "
                "executing RemarkCheck."
            )

        reporter_path = ROOT / f".remark-python-reporter-{os.getpid()}.mjs"

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
                cwd=ROOT,
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


# ---------------------------------------------------------------------------
# Lychee external-link integration
# ---------------------------------------------------------------------------


def lychee_preflight():
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
        cwd=ROOT,
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
        path = normalise_vale_path(raw_path, paths)

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
            status = lychee_status_text(failure.get("status"))

            issues.append(
                make_issue(
                    file=path.as_posix(),
                    line=line,
                    severity="high",
                    confidence="high",
                    issue_type="defect",
                    category="external-link",
                    original=url,
                    message=f"External link failed Lychee validation: {status}",
                    suggestion=(
                        "Verify the destination, replace or remove the broken URL, "
                        "or add a deliberate exception to .lycheeignore when the "
                        "destination is known to reject automated checks."
                    ),
                    source="lychee",
                )
            )

    return issues


class LycheeCheck(BaseCheck):
    """Run Lychee once across the selected Markdown/MDX files."""

    name = "LycheeCheck"
    source = "lychee"

    def run_files(self, paths, executable=None):
        executable = executable or shutil.which("lychee")

        if executable is None:
            raise RuntimeError(
                "Lychee executable was not found in PATH. Run the Lychee preflight "
                "before executing LycheeCheck."
            )

        # Use an absolute root directory. This is required by current Lychee
        # versions for root-relative links such as /docs/skills.
        root_dir = str(ROOT.resolve())

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
            cwd=ROOT,
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

        return candidates

    def _local_target_exists(self, source_path, target):
        return any(candidate.exists() for candidate in self._candidate_paths(source_path, target))


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
        LycheeCheck(),
        RemarkCheck(),
        ValeCheck(),
        LtexCheck(),
        SiteWideConsistencyReview(),
    ]


def choose_review_mode():
    print()
    print("Review mode:")
    print("  1. Per page")
    print("  2. Site wide")
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

        print("Please enter 1 or 2.")


def choose_filter():
    print()
    print("Review checks:")
    print("  1. Full review")
    print("  2. Editorial only")
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

    if not DEEPSEEK_AI_CHECKS_ENABLED:
        checks = [check for check in checks if check.source != "ai"]

    return checks


def resolve_mode_for_filter(mode, filter_name):
    """Handle presets that only make sense in one review scope."""

    if filter_name == "site-wide-consistency" and mode != "site-wide":
        print("Site-wide consistency requires site-wide mode; switching to site-wide.")
        return "site-wide"

    page_only_filters = {
        "editorial",
        "portfolio",
        "mermaid",
        "accessibility",
        "links",
    }

    if filter_name in page_only_filters and mode != "per-page":
        print(f"{FILTER_LABELS[filter_name]} requires per-page mode; switching to per-page.")
        return "per-page"

    return mode


def run_per_page_checks(paths, checks, api_key):
    issues = []
    errors = []
    runnable_checks = [check for check in checks if check.supports_page]

    if not runnable_checks:
        return issues, errors

    for file_number, path in enumerate(paths, start=1):
        content = path.read_text(encoding="utf-8")

        if not content.strip():
            continue

        print(f"[{file_number}/{len(paths)}] {path.as_posix()}")

        for check in runnable_checks:
            print(f"    {check.name}")

            try:
                issues.extend(
                    check.run_page(
                        path,
                        content,
                        api_key,
                    )
                )
            except Exception as error:
                errors.append(
                    {
                        "check": check.name,
                        "file": path.as_posix(),
                        "error": str(error),
                    }
                )

    return issues, errors


def run_site_checks(paths, checks, api_key):
    issues = []
    errors = []
    runnable_checks = [check for check in checks if check.supports_site]

    contents = {
        path.as_posix(): path.read_text(encoding="utf-8")
        for path in paths
    }

    for check in runnable_checks:
        print(f"[site] {check.name}")

        try:
            issues.extend(
                check.run_site(
                    paths,
                    contents,
                    api_key,
                )
            )
        except Exception as error:
            errors.append(
                {
                    "check": check.name,
                    "file": "<site-wide>",
                    "error": str(error),
                }
            )

    return issues, errors


# ---------------------------------------------------------------------------
# CI thresholds
# ---------------------------------------------------------------------------


def evaluate_ci(issues, errors, fail_high, fail_medium, fail_api_errors):
    high_count = sum(1 for issue in issues if issue["severity"] == "high")
    medium_count = sum(1 for issue in issues if issue["severity"] == "medium")
    api_error_count = len(errors)

    failures = []

    if high_count > fail_high:
        failures.append(
            f"high issues {high_count} > allowed {fail_high}"
        )

    if medium_count > fail_medium:
        failures.append(
            f"medium issues {medium_count} > allowed {fail_medium}"
        )

    if api_error_count > fail_api_errors:
        failures.append(
            f"API/check errors {api_error_count} > allowed {fail_api_errors}"
        )

    return {
        "passed": not failures,
        "high_count": high_count,
        "medium_count": medium_count,
        "api_error_count": api_error_count,
        "failures": failures,
        "thresholds": {
            "high": fail_high,
            "medium": fail_medium,
            "api_errors": fail_api_errors,
        },
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _run_git(*args):
    """Return stripped Git command output, or None when Git metadata is unavailable."""

    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def github_repository():
    """Return the GitHub owner/repository used for report source links."""

    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repository:
        return repository

    remote = _run_git("remote", "get-url", "origin")
    if remote:
        match = re.search(
            r"(?:github\.com[/:])(?P<repository>[^/\s]+/[^/\s]+?)(?:\.git)?$",
            remote,
            re.IGNORECASE,
        )
        if match:
            return match.group("repository")

    return GITHUB_REPOSITORY_FALLBACK


def github_revision():
    """Return the editable GitHub branch used by report source links."""

    return "main"


def github_file_url(file_path, line=None):
    """Build a GitHub blob URL for a repository-relative file and optional line."""

    if not isinstance(file_path, str):
        return None

    normalised = file_path.strip().replace("\\", "/")
    while normalised.startswith("./"):
        normalised = normalised[2:]

    if not normalised or normalised.startswith("<"):
        return None

    repository = github_repository().strip("/")
    revision = github_revision()

    repository_url = quote(repository, safe="/")
    revision_url = quote(revision, safe="")
    file_url = quote(normalised, safe="/")
    # `?plain=1` keeps GitHub in source-file view, and the fragment must come
    # after the query string so line anchors work as expected, e.g.
    # `...?plain=1#L22`.
    url = f"https://github.com/{repository_url}/blob/{revision_url}/{file_url}?plain=1"

    if isinstance(line, int) and line > 0:
        url += f"#L{line}"

    return url


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


def generate_json_report(issues, errors, metadata, ci_result):
    payload = {
        "metadata": metadata,
        "ci": ci_result,
        "issues": sort_issues(issues),
        "errors": errors,
    }

    JSON_REPORT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def generate_html_report(issues, errors, metadata, ci_result):
    issues = sort_issues(issues)

    high_count = sum(1 for issue in issues if issue["severity"] == "high")
    medium_count = sum(1 for issue in issues if issue["severity"] == "medium")
    low_count = sum(1 for issue in issues if issue["severity"] == "low")

    rows = []

    for issue in issues:
        file_link = html_file_link(issue["file"], line=issue["line"])
        line_link = html_line_link(issue["file"], issue["line"])

        rows.append(
            f"""
            <tr
                data-severity="{html.escape(issue['severity'])}"
                data-source="{html.escape(issue['source'])}"
                data-category="{html.escape(issue['category'])}"
            >
                <td>{file_link}</td>
                <td>{line_link}</td>
                <td><span class="badge severity-{html.escape(issue['severity'])}">{html.escape(issue['severity'])}</span></td>
                <td><span class="badge confidence-{html.escape(issue['confidence'])}">{html.escape(issue['confidence'])}</span></td>
                <td>{html.escape(issue['type'])}</td>
                <td>{html.escape(issue['category'])}</td>
                <td><span class="badge source-{html.escape(issue['source'])}">{html.escape(issue['source'])}</span></td>
                <td><code>{html.escape(issue['original'])}</code></td>
                <td>{html.escape(issue['message'])}</td>
                <td>{html.escape(issue['suggestion'])}</td>
            </tr>
            """
        )

    if not rows:
        rows.append(
            """
            <tr>
                <td colspan="10" class="empty-state">
                    No issues found by the selected checks.
                </td>
            </tr>
            """
        )

    error_rows = []

    for error in errors:
        error_file_link = html_file_link(error["file"])

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

    document = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Documentation QA report</title>
    <script>
        // GitHub Pages controls the response Cache-Control header, so this page
        // cache-busts its own URL once on each visit. A stale cached copy still
        // executes this code and requests a unique URL for the current report.
        (() => {{
            if (window.location.protocol !== 'http:' && window.location.protocol !== 'https:') {{
                return;
            }}

            const url = new URL(window.location.href);
            const refreshParameter = '_qa_refresh';

            if (!url.searchParams.has(refreshParameter)) {{
                url.searchParams.set(refreshParameter, Date.now().toString());
                window.location.replace(url.toString());
                return;
            }}

            // Keep the address bar clean after the cache-busted page has loaded.
            window.addEventListener('DOMContentLoaded', () => {{
                const cleanUrl = new URL(window.location.href);
                cleanUrl.searchParams.delete(refreshParameter);
                window.history.replaceState(
                    null,
                    '',
                    cleanUrl.pathname + cleanUrl.search + cleanUrl.hash,
                );
            }});
        }})();
    </script>
    <style>
        :root {{
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color-scheme: light dark;
        }}

        body {{
            margin: 0;
            background: #f5f7fa;
            color: #111827;
        }}

        main {{
            max-width: 1800px;
            margin: 0 auto;
            padding: 32px;
        }}

        h1 {{ margin-bottom: 6px; }}
        h2 {{ margin-top: 32px; }}

        a {{
            color: #2563eb;
            text-decoration: underline;
            text-underline-offset: 2px;
        }}

        a:hover {{
            text-decoration-thickness: 2px;
        }}

        .portfolio-link {{
            margin: 0 0 18px;
        }}

        .report-actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 0 0 18px;
        }}

        .report-actions a {{
            display: inline-block;
            padding: 7px 10px;
            border: 1px solid #d1d5db;
            border-radius: 7px;
            background: #fff;
            text-decoration: none;
        }}

        .report-actions a:hover {{
            text-decoration: underline;
        }}

        .subtitle {{
            margin-top: 0;
            color: #6b7280;
        }}

        .cards {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin: 24px 0;
        }}

        .card {{
            min-width: 135px;
            padding: 14px 16px;
            background: #fff;
            border: 1px solid #d1d5db;
            border-radius: 10px;
        }}

        .card strong {{
            display: block;
            font-size: 22px;
        }}

        .card span {{
            color: #6b7280;
            font-size: 13px;
        }}

        .ci-box {{
            padding: 14px 16px;
            border-radius: 10px;
            margin: 18px 0 24px;
            border: 1px solid;
        }}

        .ci-pass {{
            background: #ecfdf5;
            border-color: #10b981;
            color: #065f46;
        }}

        .ci-fail {{
            background: #fef2f2;
            border-color: #ef4444;
            color: #991b1b;
        }}

        .filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 14px;
        }}

        select {{
            padding: 7px 9px;
            border-radius: 7px;
            border: 1px solid #d1d5db;
        }}

        .table-wrap {{
            overflow-x: auto;
            background: #fff;
            border: 1px solid #d1d5db;
            border-radius: 10px;
        }}

        table {{
            width: 100%;
            min-width: 1500px;
            border-collapse: collapse;
        }}

        th, td {{
            padding: 11px 12px;
            text-align: left;
            vertical-align: top;
            border-bottom: 1px solid #e5e7eb;
            font-size: 13px;
            line-height: 1.45;
        }}

        th {{
            position: sticky;
            top: 0;
            background: #f9fafb;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        code {{
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-size: 12px;
        }}

        .badge {{
            display: inline-block;
            padding: 2px 7px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
        }}

        .severity-high {{ background: #fee2e2; color: #991b1b; }}
        .severity-medium {{ background: #fef3c7; color: #92400e; }}
        .severity-low {{ background: #dbeafe; color: #1e40af; }}
        .confidence-high {{ background: #dcfce7; color: #166534; }}
        .confidence-medium {{ background: #fef3c7; color: #92400e; }}
        .confidence-low {{ background: #f3f4f6; color: #4b5563; }}
        .source-static {{ background: #ede9fe; color: #5b21b6; }}
        .source-ai {{ background: #e0f2fe; color: #075985; }}
        .source-vale {{ background: #dcfce7; color: #166534; }}
        .source-ltex {{ background: #fae8ff; color: #86198f; }}
        .source-lychee {{ background: #fef3c7; color: #92400e; }}
        .source-remark {{ background: #e0e7ff; color: #3730a3; }}
        .empty-state {{ text-align: center; padding: 30px; color: #6b7280; }}

        @media (prefers-color-scheme: dark) {{
            body {{ background: #111827; color: #f3f4f6; }}
            .card, .table-wrap {{ background: #1f2937; border-color: #374151; }}
            .report-actions a {{ background: #1f2937; border-color: #374151; }}
            th {{ background: #111827; }}
            th, td {{ border-bottom-color: #374151; }}
            .subtitle, .card span {{ color: #9ca3af; }}
        }}
    </style>
</head>
<body>
<main>
    <h1>Documentation QA report</h1>
    <p class="portfolio-link">
        <a href="{html.escape(PORTFOLIO_URL, quote=True)}">← Back to Portfolio</a>
    </p>
    <div class="report-actions">
        <a id="latestReportLink" href="#">Load latest report</a>
    </div>
    <p class="subtitle">
        Report run: {html.escape(metadata['report_run_at_display'])}
        ({html.escape(metadata['report_time_zone'])})<br>
        Mode: {html.escape(metadata['mode'])} ·
        Checks: {html.escape(metadata['filter_label'])} ·
        Model: {html.escape(metadata['model'])}
    </p>

    <div class="cards">
        <div class="card"><strong>{metadata['files_reviewed']}</strong><span>files reviewed</span></div>
        <div class="card"><strong>{len(issues)}</strong><span>total issues</span></div>
        <div class="card"><strong>{high_count}</strong><span>high</span></div>
        <div class="card"><strong>{medium_count}</strong><span>medium</span></div>
        <div class="card"><strong>{low_count}</strong><span>low</span></div>
        <div class="card"><strong>{len(errors)}</strong><span>API/check errors</span></div>
    </div>

    <div class="ci-box {ci_class}">
        <strong>CI threshold result: {ci_label}</strong><br>
        {html.escape(failure_text)}<br>
        Thresholds: high &gt; {ci_result['thresholds']['high']},
        medium &gt; {ci_result['thresholds']['medium']},
        API/check errors &gt; {ci_result['thresholds']['api_errors']}.
    </div>

    <h2>Issues</h2>

    <div class="filters">
        <label>
            Severity
            <select id="severityFilter">
                <option value="">All</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
            </select>
        </label>

        <label>
            Source
            <select id="sourceFilter">
                <option value="">All</option>
                <option value="static">Static</option>
                <option value="ai">AI</option>
                <option value="vale">Vale</option>
                <option value="ltex">LTeX+</option>
                <option value="lychee">Lychee</option>
                <option value="remark">Remark</option>
            </select>
        </label>
    </div>

    <div class="table-wrap">
        <table id="issuesTable">
            <thead>
                <tr>
                    <th>File</th>
                    <th>Line</th>
                    <th>Severity</th>
                    <th>Confidence</th>
                    <th>Type</th>
                    <th>Category</th>
                    <th>Source</th>
                    <th>Original</th>
                    <th>Issue</th>
                    <th>Suggestion</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>

    <h2>API/check errors</h2>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Check</th>
                    <th>File</th>
                    <th>Error</th>
                </tr>
            </thead>
            <tbody>
                {''.join(error_rows)}
            </tbody>
        </table>
    </div>
</main>

<script>
    const severityFilter = document.getElementById('severityFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    const latestReportLink = document.getElementById('latestReportLink');

    if (latestReportLink) {{
        latestReportLink.addEventListener('click', (event) => {{
            event.preventDefault();
            const url = new URL(window.location.href);
            url.searchParams.set('_qa_refresh', Date.now().toString());
            window.location.assign(url.toString());
        }});
    }}

    function applyFilters() {{
        const severity = severityFilter.value;
        const source = sourceFilter.value;
        const rows = document.querySelectorAll('#issuesTable tbody tr[data-severity]');

        for (const row of rows) {{
            const severityMatch = !severity || row.dataset.severity === severity;
            const sourceMatch = !source || row.dataset.source === source;
            row.style.display = severityMatch && sourceMatch ? '' : 'none';
        }}
    }}

    severityFilter.addEventListener('change', applyFilters);
    sourceFilter.addEventListener('change', applyFilters);
</script>
</body>
</html>
"""

    REPORT.write_text(document, encoding="utf-8")


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run static and AI documentation QA checks for a Docusaurus site."
    )

    parser.add_argument(
        "--ci",
        action="store_true",
        help="Run non-interactively and return exit code 1 when thresholds fail.",
    )

    parser.add_argument(
        "--mode",
        choices=["per-page", "site-wide"],
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
    args = parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if DEEPSEEK_AI_CHECKS_ENABLED:
        print("DeepSeek AI checks: ENABLED")
    else:
        print("DeepSeek AI checks: DISABLED (hardcoded switch)")

    files = list(markdown_files())

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
    checks = selected_checks(filter_name)

    file_checks = [check for check in checks if hasattr(check, "run_files")]
    scoped_checks = [check for check in checks if check not in file_checks]

    # Only retain implementations that can actually run in the chosen scope.
    if mode == "per-page":
        scoped_checks = [check for check in scoped_checks if check.supports_page]
    else:
        scoped_checks = [check for check in scoped_checks if check.supports_site]

    checks = scoped_checks + file_checks

    if not checks:
        if not DEEPSEEK_AI_CHECKS_ENABLED:
            print(
                "No runnable checks remain for this preset because DeepSeek AI checks "
                "are disabled by the hardcoded switch."
            )
        else:
            print("No checks are available for the selected mode and filter.")
        return 2

    vale_executable = None
    ltex_executable = None
    lychee_executable = None
    remark_executable = None

    if any(check.source == "vale" for check in file_checks):
        try:
            vale_executable = vale_preflight()
        except RuntimeError as error:
            print(f"Vale preflight failed: {error}", file=sys.stderr)
            return 2

    if any(check.source == "ltex" for check in file_checks):
        try:
            ltex_executable = ltex_preflight()
        except RuntimeError as error:
            print(f"LTeX+ preflight failed: {error}", file=sys.stderr)
            return 2

    if any(check.source == "lychee" for check in file_checks):
        try:
            lychee_executable = lychee_preflight()
        except RuntimeError as error:
            print(f"Lychee preflight failed: {error}", file=sys.stderr)
            return 2

    if any(check.source == "remark" for check in file_checks):
        try:
            remark_executable = remark_preflight()
        except RuntimeError as error:
            print(f"Remark preflight failed: {error}", file=sys.stderr)
            return 2

    if DEEPSEEK_AI_CHECKS_ENABLED and not api_key and any(
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

    if mode == "per-page":
        issues, errors = run_per_page_checks(
            files,
            scoped_checks,
            api_key,
        )
    else:
        issues, errors = run_site_checks(
            files,
            scoped_checks,
            api_key,
        )

    for check in file_checks:
        print(f"[{check.source}] {check.name}")

        try:
            executable_by_source = {
                "vale": vale_executable,
                "ltex": ltex_executable,
                "lychee": lychee_executable,
                "remark": remark_executable,
            }
            executable = executable_by_source.get(check.source)
            issues.extend(check.run_files(files, executable=executable))
        except Exception as error:
            errors.append(
                {
                    "check": check.name,
                    "file": f"<{check.source}>",
                    "error": str(error),
                }
            )

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
        "filter": filter_name,
        "filter_label": FILTER_LABELS[filter_name],
        "model": MODEL if DEEPSEEK_AI_CHECKS_ENABLED else f"{MODEL} (disabled)",
        "ai_checks_enabled": DEEPSEEK_AI_CHECKS_ENABLED,
        "files_reviewed": len(files),
        "checks": [check.name for check in checks],
        "portfolio_url": PORTFOLIO_URL,
        "github_repository": github_repository(),
        "github_revision": github_revision(),
    }

    generate_html_report(
        issues,
        errors,
        metadata,
        ci_result,
    )

    generate_json_report(
        issues,
        errors,
        metadata,
        ci_result,
    )

    print()
    print(f"HTML report: {REPORT.resolve()}")
    print(f"JSON report: {JSON_REPORT.resolve()}")
    print()

    print(
        "CI thresholds: "
        f"high > {args.fail_high}, "
        f"medium > {args.fail_medium}, "
        f"API/check errors > {args.fail_api_errors}"
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