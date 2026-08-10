import os
import json
import html
from pathlib import Path

import requests


API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"

ROOT = Path(".")
REPORT = Path("ai-doc-review.html")

EXCLUDED_DIRS = {
    "node_modules",
    "build",
    ".docusaurus",
    ".git",
    "static",
}

SEVERITIES = {
    "high",
    "medium",
    "low",
}

PER_PAGE_CATEGORIES = {
    "grammar",
    "clarity",
    "consistency",
    "repetition",
    "structure",
    "portfolio",
    "over-explanation",
    "scannability",
    "diagram",
    "unfinished",
    "punctuation",
    "other",
}

SITE_WIDE_CATEGORIES = {
    "repetition",
    "consistency",
    "structure",
    "portfolio",
    "diagram",
    "other",
}


PER_PAGE_SYSTEM_PROMPT = r"""
You are reviewing a technical-writing portfolio built with Docusaurus.

This is a PER-PAGE editorial and information-design review.

Use British English.

Focus on meaningful issues that affect publication quality, readability,
information design, or the effectiveness of the page as a professional
technical-writing portfolio.

Review only what is present in the supplied page.

1. LANGUAGE AND CLARITY

Identify meaningful problems involving:

- grammar
- clarity
- awkward or confusing wording
- incomplete sentences
- inconsistent terminology
- unexplained terminology where this materially affects comprehension
- unfinished or placeholder content
- obvious contradictions within the supplied page
- punctuation or hyphenation problems that materially affect correctness

Do NOT:

- perform general spelling checking; spelling is checked separately
- report correctly spelled words as spelling mistakes
- change valid British English to American English
- recommend Oxford -ize spelling
- rewrite text merely because you prefer another style
- flag product names, technologies or technical terms merely because they
  are unusual
- review programming code for style unless it creates a documentation problem
- claim technical information is wrong unless the supplied text itself
  demonstrates the inconsistency
- invent text that is not present in the supplied document

2. UNNECESSARY REPETITION

Identify ideas, explanations, qualifications or facts that are unnecessarily
repeated within the page.

Flag repetition when:

- two passages communicate substantially the same information
- a later sentence repeats something the reader has already understood
- several sentences could be consolidated without losing useful meaning
- terminology is repeatedly re-explained after it has already been established

Do NOT flag:

- intentional repetition needed for clarity
- repeated product names or terminology where pronouns would make the text
  less clear
- navigation, headings or standard Docusaurus UI text
- two passages merely because they discuss the same broad subject

3. INFORMATION STRUCTURE

Identify cases where:

- information appears in an awkward order
- a paragraph is doing several unrelated jobs
- important context arrives substantially later than the information it explains
- a dense paragraph would materially benefit from being divided
- closely related information is unnecessarily separated
- a heading does not accurately describe the content beneath it
- the page contains unnecessary explanatory detail for a portfolio case study

Do not recommend additional sections merely to create more headings.

Do not recommend changing a short, coherent paragraph into bullets unless
bullets would materially improve scanning.

4. PORTFOLIO EFFECTIVENESS

Treat this as a technical-writing portfolio rather than the original product
documentation.

Identify places where the page spends substantially more space explaining the
underlying technology than demonstrating the documentation work.

Consider whether the existing content clearly communicates, where relevant:

- what the documentation deliverable was
- who it was for
- what the author contributed
- why the documentation was useful or challenging
- the relationship between the portfolio description and the published work

Only report an issue when the supplied page provides enough evidence to justify
the observation.

Do NOT invent:

- project results
- metrics
- responsibilities
- audiences
- business impact
- design decisions
- technical facts

If useful information is genuinely absent, explain what KIND of information
might strengthen the page without inventing the information itself.

5. OVER-EXPLANATION

Identify background explanations that are disproportionately detailed relative
to their importance on a portfolio page.

Prefer concise context that helps a prospective employer or reviewer understand
the documentation challenge.

Do not remove technical context that is necessary to understand why the work
matters.

6. SCANNABILITY

Identify places where the reader must work unnecessarily hard to extract:

- the purpose of the document
- the author's contribution
- the important technical concept
- the relationship between technologies or actors

Do not flag a passage simply because it contains technical terminology.

7. MERMAID DIAGRAM OPPORTUNITIES

Very sparingly identify content that would be substantially easier to understand
as a small Mermaid diagram.

A diagram may be appropriate when the supplied text describes:

- a sequence of interactions
- a lifecycle
- a workflow
- a transformation from one state or artefact to another
- relationships between several systems or components
- a decision process
- a non-obvious hierarchy

Do NOT suggest a diagram:

- merely to make the page look more visual
- for a simple definition
- for a single fact
- for a list that is already easy to understand
- when the diagram would simply repeat one or two straightforward sentences
- when a paragraph is clearer and faster to read than the proposed diagram
- when the required relationships are not stated in the source
- when creating the diagram would require inventing technical details

Prefer ZERO diagram recommendations for most short pages.

Return no more than ONE diagram opportunity per file.

For a diagram finding:

- use category "diagram"
- use severity "low"
- "original" must contain the exact passage that motivates the diagram
- "message" must explain what relationship or process would benefit from
  visualisation
- "suggestion" must state the recommended Mermaid diagram type and briefly
  describe what it should show
- only include Mermaid source code when all nodes and relationships are directly
  supported by the supplied text

Suitable Mermaid types include:

- flowchart
- sequenceDiagram
- stateDiagram-v2

Prefer the simplest suitable diagram type.

8. REDUNDANCY BETWEEN TEXT AND VISUALS

If the supplied MDX already contains a Mermaid diagram, identify prose that
unnecessarily narrates every element of the diagram.

Do not recommend deleting prose that provides interpretation, context or
accessibility value.

GENERAL RULES

Only report meaningful issues.

Do not:

- manufacture problems to ensure every page receives findings
- recommend generic portfolio advice unrelated to the supplied source
- invent text that is not present
- invent technical relationships
- recommend decorative graphics
- recommend adding Mermaid to every page
- report the same underlying problem more than once

Be conservative.

A short, well-structured page may legitimately return no issues.

Every reported issue MUST include exact source text that caused the finding.

The "original" value must be copied exactly from the supplied documentation,
without the artificial line-number prefix.

Do not paraphrase "original".

Use the supplied line numbers to populate "line".

Return JSON only in this structure:

{
  "issues": [
    {
      "severity": "high|medium|low",
      "category": "grammar|clarity|consistency|repetition|structure|portfolio|over-explanation|scannability|diagram|unfinished|punctuation|other",
      "line": 12,
      "original": "exact text copied from the source",
      "message": "Concise explanation of the problem",
      "suggestion": "Specific suggested improvement"
    }
  ]
}

Return:

{
  "issues": []
}

when there are no meaningful issues.
"""


SITE_WIDE_SYSTEM_PROMPT = r"""
You are reviewing an entire Docusaurus technical-writing portfolio.

Use British English.

This is a SITE-WIDE review.

Do not perform a general grammar or spelling review. Individual pages can be
reviewed separately for those issues.

Instead, compare the supplied documentation files with one another and identify
meaningful portfolio-wide documentation issues.

1. REPETITION ACROSS PAGES

Identify information that is unnecessarily repeated across multiple pages,
including:

- substantially identical introductions
- repeated explanations of the same concept
- repeated descriptions of the author's role
- repeated publication or repository boilerplate
- repeated background information
- repeated definitions that could potentially be explained once elsewhere

Do not flag repetition merely because several case studies naturally use the
same product, technology or terminology.

Only report repetition when reducing it would improve the portfolio.

2. STRUCTURAL CONSISTENCY

Identify significant inconsistencies in how comparable pages are structured.

For example:

- one case study clearly establishes the author's contribution while another
  comparable case study does not
- similar pages introduce project context in substantially different ways
- equivalent information appears under inconsistent headings
- important information is easy to locate on some pages but buried on others

Do not demand identical templates for every case study.

Some variation is appropriate.

3. TERMINOLOGY

Identify terminology that is used inconsistently across the site where the
inconsistency could confuse a reader.

Do not report harmless stylistic variation.

4. PORTFOLIO EFFECTIVENESS

Identify patterns where the site repeatedly spends more space explaining the
technology than demonstrating the documentation work.

Consider whether comparable case studies communicate, where relevant:

- what was documented
- who the documentation was for
- what the author contributed
- what made the documentation challenging or useful
- where the resulting documentation can be viewed

Do not invent missing project information.

If useful information appears to be absent, describe the KIND of information
that could strengthen the portfolio rather than inventing it.

5. INFORMATION ARCHITECTURE

Identify information that may be better:

- consolidated
- moved to a shared introductory page
- explained once and linked from several pages
- reorganised to make case studies easier to compare

Only recommend this when there is clear evidence across several supplied files.

6. MERMAID DIAGRAM OPPORTUNITIES

Very sparingly identify places where a diagram would materially improve
comprehension.

A Mermaid diagram may be useful for:

- a sequence of interactions
- an API workflow
- a lifecycle
- a transformation
- a relationship between several systems
- a decision process
- a non-obvious hierarchy

Do NOT suggest diagrams:

- merely to make pages more visual
- for simple definitions
- for straightforward lists
- when prose is already clearer
- when creating the diagram would require inventing relationships
- on every case study

Prefer ZERO diagram recommendations unless there is a strong reason.

Do not recommend more than THREE Mermaid opportunities across the entire site.

For a diagram finding:

- category must be "diagram"
- severity must normally be "low"
- explain exactly what the diagram would clarify
- recommend the simplest suitable Mermaid type
- do not invent nodes or relationships

7. REDUNDANT PATTERNS

Look for repeated presentation patterns that add little value, such as:

- identical disclaimers
- repeated navigation instructions
- repeated descriptions of where content is published
- repetitive introductory sentences
- unnecessary repetition between a case-study summary and another page

Be conservative.

Do not manufacture issues merely because this is a site-wide review.

Every reported issue MUST:

- identify one specific file as the primary place where action should be taken
- contain exact source text copied from that file
- use the supplied line numbers
- refer to other files in the explanation when relevant

The "file" value must match one of the FILE values supplied to you.

The "original" value must be copied exactly from the source file, without the
artificial line-number prefix.

Do not paraphrase "original".

Return JSON only in this structure:

{
  "issues": [
    {
      "file": "docs/example.mdx",
      "severity": "high|medium|low",
      "category": "repetition|consistency|structure|portfolio|diagram|other",
      "line": 12,
      "original": "exact text copied from the specified file",
      "message": "Concise explanation of the site-wide problem",
      "suggestion": "Specific suggested improvement"
    }
  ]
}

Return:

{
  "issues": []
}

if there are no meaningful site-wide issues.
"""


def markdown_files():
    """
    Yield Markdown and MDX files that should be reviewed.
    """

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".md", ".mdx"}:
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        yield path


def add_line_numbers(text):
    """
    Add artificial line numbers for the model without changing the source.
    """

    return "\n".join(
        f"{number:5}: {line}"
        for number, line in enumerate(text.splitlines(), start=1)
    )


def choose_review_mode():
    """
    Ask the user whether to review each page separately or compare
    the entire site.
    """

    print()
    print("Review mode:")
    print("  1. Per page")
    print("  2. Site wide")
    print()

    while True:
        choice = input("Select review mode [1]: ").strip()

        # Pressing Enter uses the default: per-page review.
        if not choice or choice == "1":
            return "per-page"

        if choice == "2":
            return "site-wide"

        print("Please enter 1 or 2.")


def parse_model_json(model_output):
    """
    Parse JSON returned by the model.

    response_format should result in plain JSON, but this also tolerates
    accidental Markdown code fences.
    """

    text = model_output.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return json.loads(text)


def find_source_line(content, original, preferred_line=None):
    """
    Find the line where an exact quoted source fragment starts.

    If the same text occurs more than once, choose the occurrence closest
    to the line reported by the model.
    """

    positions = []
    start = 0

    while True:
        index = content.find(original, start)

        if index == -1:
            break

        line_number = content.count("\n", 0, index) + 1
        positions.append(line_number)

        # Move forward so another occurrence of the same text can be found.
        start = index + 1

    if not positions:
        return None

    if isinstance(preferred_line, int) and preferred_line > 0:
        return min(
            positions,
            key=lambda line: abs(line - preferred_line),
        )

    return positions[0]


def normalise_issue(issue, content, allowed_categories):
    """
    Validate a finding and correct its line number using the exact
    quoted source text.

    A finding is rejected if its "original" text does not actually occur
    in the source document.
    """

    required_fields = {
        "severity",
        "category",
        "line",
        "original",
        "message",
        "suggestion",
    }

    if not isinstance(issue, dict):
        return None

    if not required_fields.issubset(issue):
        return None

    severity = issue.get("severity")
    category = issue.get("category")
    original = issue.get("original")
    message = issue.get("message")
    suggestion = issue.get("suggestion")
    reported_line = issue.get("line")

    if severity not in SEVERITIES:
        return None

    if category not in allowed_categories:
        return None

    if not isinstance(original, str) or not original.strip():
        return None

    # Critical hallucination check.
    if original not in content:
        return None

    if not isinstance(message, str) or not message.strip():
        return None

    if not isinstance(suggestion, str) or not suggestion.strip():
        return None

    if not isinstance(reported_line, int):
        reported_line = None

    # Recalculate the real line number rather than trusting the model.
    actual_line = find_source_line(
        content,
        original,
        preferred_line=reported_line,
    )

    if actual_line is None:
        return None

    return {
        "severity": severity,
        "category": category,
        "line": actual_line,
        "original": original,
        "message": message.strip(),
        "suggestion": suggestion.strip(),
    }


def request_review(system_prompt, user_prompt, api_key):
    """
    Send one review request to the DeepSeek chat-completions API.
    """

    payload = {
        "model": MODEL,
        "thinking": {
            "type": "disabled"
        },
        "temperature": 0.0,
        "response_format": {
            "type": "json_object"
        },
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

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

    return parse_model_json(model_output)


def review_file(path, api_key):
    """
    Review one Markdown or MDX file in isolation.
    """

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        return []

    numbered_content = add_line_numbers(content)

    parsed = request_review(
        PER_PAGE_SYSTEM_PROMPT,
        (
            f"Review this documentation file: {path.as_posix()}\n\n"
            f"{numbered_content}"
        ),
        api_key,
    )

    issues = parsed.get("issues", [])

    if not isinstance(issues, list):
        return []

    validated_issues = []

    for issue in issues:
        validated = normalise_issue(
            issue,
            content,
            PER_PAGE_CATEGORIES,
        )

        if validated is not None:
            validated_issues.append(validated)

    return validated_issues


def normalise_model_path(raw_path, known_paths):
    """
    Match a path returned by the model to one of the exact paths that
    were supplied during the site-wide review.
    """

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


def review_site(paths, api_key):
    """
    Send all documentation files together so the model can identify
    cross-page repetition, consistency problems, portfolio patterns,
    and selective diagram opportunities.
    """

    contents = {}
    sections = []

    for path in paths:
        content = path.read_text(encoding="utf-8")

        if not content.strip():
            continue

        path_string = path.as_posix()

        contents[path_string] = content

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

    combined_content = "\n\n".join(sections)

    parsed = request_review(
        SITE_WIDE_SYSTEM_PROMPT,
        (
            "Review these documentation files as one portfolio. "
            "Compare them with one another and report only meaningful "
            "site-wide findings.\n\n"
            f"{combined_content}"
        ),
        api_key,
    )

    issues = parsed.get("issues", [])

    if not isinstance(issues, list):
        return []

    known_paths = list(paths)
    validated_issues = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        canonical_path = normalise_model_path(
            issue.get("file"),
            known_paths,
        )

        # Reject findings that identify a file that was not supplied.
        if canonical_path is None:
            continue

        content = contents.get(canonical_path)

        if content is None:
            continue

        validated = normalise_issue(
            issue,
            content,
            SITE_WIDE_CATEGORIES,
        )

        if validated is None:
            continue

        validated["file"] = canonical_path

        validated_issues.append(validated)

    return validated_issues


def group_site_issues(paths, issues):
    """
    Convert the flat site-wide issue list into the same per-file structure
    used by the HTML report.
    """

    grouped = {
        path.as_posix(): []
        for path in paths
    }

    for issue in issues:
        path = issue["file"]

        # The report already displays the file path separately.
        report_issue = {
            key: value
            for key, value in issue.items()
            if key != "file"
        }

        grouped[path].append(report_issue)

    return [
        {
            "path": path.as_posix(),
            "issues": grouped[path.as_posix()],
        }
        for path in paths
    ]


def generate_report(results, mode):
    """
    Generate an HTML report for either review mode.
    """

    total_files = len(results)

    total_issues = sum(
        len(result.get("issues", []))
        for result in results
    )

    total_errors = sum(
        1
        for result in results
        if result.get("error")
    )

    severity_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    issue_rows = []

    for result in results:
        path = result["path"]

        if result.get("error"):
            issue_rows.append(
                (
                    -1,
                    path,
                    0,
                    f"""
                    <tr class="error">
                        <td>{html.escape(path)}</td>
                        <td>
                            <span class="badge error-badge">
                                API error
                            </span>
                        </td>
                        <td>-</td>
                        <td>-</td>
                        <td></td>
                        <td>{html.escape(result["error"])}</td>
                        <td></td>
                    </tr>
                    """,
                )
            )

            continue

        for issue in result.get("issues", []):
            severity = issue.get("severity", "")
            category = issue.get("category", "")
            line = issue.get("line", "")
            original = issue.get("original", "")
            message = issue.get("message", "")
            suggestion = issue.get("suggestion", "")

            issue_rows.append(
                (
                    severity_order.get(severity, 99),
                    path,
                    int(line) if isinstance(line, int) else 0,
                    f"""
                    <tr class="{html.escape(severity)}">
                        <td>{html.escape(path)}</td>

                        <td>
                            <span class="badge {html.escape(severity)}-badge">
                                {html.escape(severity)}
                            </span>
                        </td>

                        <td>
                            {html.escape(category)}
                        </td>

                        <td>
                            {html.escape(str(line))}
                        </td>

                        <td>
                            <code>{html.escape(original)}</code>
                        </td>

                        <td>
                            {html.escape(message)}
                        </td>

                        <td>
                            {html.escape(suggestion)}
                        </td>
                    </tr>
                    """,
                )
            )

    # Sort by severity, then path, then line.
    issue_rows.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2],
        )
    )

    rows = [
        row[3]
        for row in issue_rows
    ]

    if not rows:
        rows.append(
            """
            <tr>
                <td colspan="7" class="empty-state">
                    No meaningful publishing issues found.
                </td>
            </tr>
            """
        )

    if mode == "per-page":
        mode_label = "Per-page review"
    else:
        mode_label = "Site-wide review"

    document = f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >

    <title>AI documentation review</title>

    <style>
        :root {{
            color-scheme: light dark;
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }}

        body {{
            margin: 0;
            background: #f5f7fa;
            color: #1f2937;
        }}

        main {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 32px;
        }}

        h1 {{
            margin: 0 0 8px;
            font-size: 30px;
        }}

        .subtitle {{
            margin: 0 0 24px;
            color: #4b5563;
        }}

        .summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 24px;
        }}

        .summary-card {{
            min-width: 150px;
            padding: 16px 18px;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            background: #ffffff;
        }}

        .summary-card strong {{
            display: block;
            margin-bottom: 4px;
            font-size: 22px;
        }}

        .summary-card span {{
            color: #6b7280;
            font-size: 14px;
        }}

        .table-wrap {{
            overflow-x: auto;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            background: #ffffff;
        }}

        table {{
            width: 100%;
            min-width: 1200px;
            border-collapse: collapse;
        }}

        th,
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
            vertical-align: top;
        }}

        th {{
            position: sticky;
            top: 0;
            background: #f9fafb;
            color: #4b5563;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        td {{
            font-size: 14px;
            line-height: 1.5;
        }}

        code {{
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            font-family:
                "SFMono-Regular",
                Consolas,
                "Liberation Mono",
                monospace;
            font-size: 12px;
        }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .high-badge {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .medium-badge {{
            background: #fef3c7;
            color: #92400e;
        }}

        .low-badge {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .error-badge {{
            background: #f3f4f6;
            color: #374151;
        }}

        tr.high td:first-child {{
            border-left: 4px solid #dc2626;
        }}

        tr.medium td:first-child {{
            border-left: 4px solid #d97706;
        }}

        tr.low td:first-child {{
            border-left: 4px solid #2563eb;
        }}

        tr.error td:first-child {{
            border-left: 4px solid #6b7280;
        }}

        .empty-state {{
            padding: 32px;
            text-align: center;
            color: #4b5563;
        }}

        @media (prefers-color-scheme: dark) {{
            body {{
                background: #111827;
                color: #f3f4f6;
            }}

            .subtitle,
            .summary-card span {{
                color: #9ca3af;
            }}

            .summary-card,
            .table-wrap {{
                background: #1f2937;
                border-color: #374151;
            }}

            th {{
                background: #111827;
                color: #d1d5db;
            }}

            th,
            td {{
                border-bottom-color: #374151;
            }}
        }}
    </style>
</head>

<body>
    <main>
        <h1>AI documentation review</h1>

        <p class="subtitle">
            {html.escape(mode_label)}
        </p>

        <div class="summary">

            <div class="summary-card">
                <strong>{total_files}</strong>
                <span>files reviewed</span>
            </div>

            <div class="summary-card">
                <strong>{total_issues}</strong>
                <span>issues found</span>
            </div>

            <div class="summary-card">
                <strong>{total_errors}</strong>
                <span>API errors</span>
            </div>

        </div>

        <div class="table-wrap">

            <table>

                <thead>
                    <tr>
                        <th>File</th>
                        <th>Severity</th>
                        <th>Category</th>
                        <th>Line</th>
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

    </main>
</body>
</html>
"""

    REPORT.write_text(
        document,
        encoding="utf-8",
    )


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        print("DEEPSEEK_API_KEY is not set.")
        return

    files = list(markdown_files())

    print(f"Found {len(files)} documentation files.")

    if not files:
        print("No Markdown or MDX files found.")
        return

    mode = choose_review_mode()

    print()

    if mode == "per-page":
        print("Mode: Per page")
        print(f"Reviewing {len(files)} files...")

        results = []

        for number, path in enumerate(files, start=1):
            print(
                f"[{number}/{len(files)}] "
                f"{path.as_posix()}"
            )

            try:
                issues = review_file(
                    path,
                    api_key,
                )

                results.append({
                    "path": path.as_posix(),
                    "issues": issues,
                })

            except Exception as error:
                # Record failures instead of stopping the entire run.
                results.append({
                    "path": path.as_posix(),
                    "issues": [],
                    "error": str(error),
                })

    else:
        print("Mode: Site wide")
        print(
            f"Comparing {len(files)} files "
            "in one review..."
        )

        try:
            issues = review_site(
                files,
                api_key,
            )

            results = group_site_issues(
                files,
                issues,
            )

        except Exception as error:
            print(
                f"Site-wide review failed: "
                f"{error}"
            )

            results = [
                {
                    "path": path.as_posix(),
                    "issues": [],
                    "error": str(error),
                }
                for path in files
            ]

    generate_report(
        results,
        mode,
    )

    print()
    print(
        f"Report created: "
        f"{REPORT.resolve()}"
    )


if __name__ == "__main__":
    main()