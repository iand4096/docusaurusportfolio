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


SYSTEM_PROMPT = """
You are reviewing technical documentation before publication.

Use British English.

Focus on meaningful editorial and documentation-quality issues:

- grammar
- clarity
- awkward or confusing wording
- incomplete sentences
- duplicated or repetitive wording
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

Every reported issue MUST include the exact source text that caused the issue.

The "original" value must be copied exactly from the supplied documentation.
Do not paraphrase it.

Return JSON only in this structure:

{
  "issues": [
    {
      "severity": "high|medium|low",
      "category": "grammar|clarity|consistency|unfinished|punctuation|other",
      "line": 12,
      "original": "exact text copied from the source",
      "message": "Concise explanation of the problem",
      "suggestion": "Suggested correction"
    }
  ]
}

Return:

{
  "issues": []
}

if there are no meaningful issues.
"""


def markdown_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".md", ".mdx"}:
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        yield path


def add_line_numbers(text):
    return "\n".join(
        f"{number:5}: {line}"
        for number, line in enumerate(text.splitlines(), start=1)
    )


def validate_issue(issue, content):
    """
    Reject hallucinated findings where the quoted original text
    does not actually occur in the source document.
    """

    required_fields = {
        "severity",
        "category",
        "line",
        "original",
        "message",
        "suggestion",
    }

    if not required_fields.issubset(issue):
        return False

    original = issue.get("original", "").strip()

    if not original:
        return False

    # Most important hallucination check.
    if original not in content:
        return False

    if issue["severity"] not in {"high", "medium", "low"}:
        return False

    return True


def review_file(path, api_key):
    content = path.read_text(encoding="utf-8")

    if not content.strip():
        return []

    numbered_content = add_line_numbers(content)

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
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": (
                    f"Review this documentation file: {path}\n\n"
                    f"{numbered_content}"
                )
            }
        ]
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

    parsed = json.loads(model_output)

    issues = parsed.get("issues", [])

    # Discard hallucinated or malformed findings.
    validated_issues = [
        issue
        for issue in issues
        if validate_issue(issue, content)
    ]

    return validated_issues


def generate_report(results):
    total_files = len(results)

    total_issues = sum(
        len(result["issues"])
        for result in results
    )

    rows = []

    for result in results:
        path = result["path"]

        if result.get("error"):
            rows.append(f"""
                <tr class="error">
                    <td>{html.escape(path)}</td>
                    <td>API error</td>
                    <td>-</td>
                    <td></td>
                    <td>{html.escape(result["error"])}</td>
                    <td></td>
                </tr>
            """)
            continue

        for issue in result["issues"]:
            severity = issue.get("severity", "")
            category = issue.get("category", "")
            line = issue.get("line", "")
            original = issue.get("original", "")
            message = issue.get("message", "")
            suggestion = issue.get("suggestion", "")

            rows.append(f"""
                <tr class="{html.escape(severity)}">
                    <td>{html.escape(path)}</td>
                    <td>{html.escape(severity)}</td>
                    <td>{html.escape(str(line))}</td>
                    <td>
                        <code>{html.escape(original)}</code>
                    </td>
                    <td>
                        <strong>{html.escape(category)}</strong><br>
                        {html.escape(message)}
                    </td>
                    <td>{html.escape(suggestion)}</td>
                </tr>
            """)

    if not rows:
        rows.append("""
            <tr>
                <td colspan="6">
                    No publishing issues found.
                </td>
            </tr>
        """)

    document = f"""<!DOCTYPE html>
<html lang="en-GB">

<head>
<meta charset="utf-8">
<title>AI Documentation Review</title>

<style>
body {{
    font-family: system-ui, sans-serif;
    max-width: 1600px;
    margin: 40px auto;
    padding: 0 24px;
    line-height: 1.5;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th,
td {{
    border-bottom: 1px solid #ddd;
    padding: 12px;
    text-align: left;
    vertical-align: top;
}}

th {{
    background: #f3f3f3;
}}

.high {{
    background: #ffe8e8;
}}

.medium {{
    background: #fff5dc;
}}

.low {{
    background: #f4f8ff;
}}

.error {{
    background: #eee;
}}

.summary {{
    margin-bottom: 30px;
}}

code {{
    white-space: pre-wrap;
    font-family: Consolas, monospace;
}}
</style>
</head>

<body>

<h1>AI Documentation Review</h1>

<div class="summary">
    <strong>{total_files}</strong> files reviewed<br>
    <strong>{total_issues}</strong> potential issues identified
</div>

<table>

<thead>
<tr>
    <th>File</th>
    <th>Severity</th>
    <th>Line</th>
    <th>Original text</th>
    <th>Issue</th>
    <th>Suggested change</th>
</tr>
</thead>

<tbody>
{''.join(rows)}
</tbody>

</table>

</body>
</html>
"""

    REPORT.write_text(
        document,
        encoding="utf-8"
    )


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY")

    if not api_key:
        print("DEEPSEEK_API_KEY is not set.")
        return

    results = []

    files = list(markdown_files())

    print(f"Reviewing {len(files)} files...")

    for number, path in enumerate(files, start=1):
        print(f"[{number}/{len(files)}] {path}")

        try:
            issues = review_file(path, api_key)

            results.append({
                "path": str(path),
                "issues": issues,
            })

        except Exception as error:
            # Record failures in the report instead of stopping the run.
            results.append({
                "path": str(path),
                "issues": [],
                "error": str(error),
            })

    generate_report(results)

    print()
    print(f"Report created: {REPORT.resolve()}")


if __name__ == "__main__":
    main()