# Ian Drewett - technical writing portfolio

A Docusaurus portfolio presenting selected technical-writing work in API
documentation, payments, developer experience, and software user
documentation. See the site at https://iand4096.github.io/docusaurusportfolio/.

## Technology

- Docusaurus
- Markdown and MDX
- TypeScript
- GitHub Pages

## Local development

```bash
npm install
npm run start
```

## Documentation QA

A QA report is generated for every change to the site and published at:

https://iand4096.github.io/docusaurusportfolio/qa/

The pipeline is implemented in [`scripts/ai_docs_review.py`](scripts/ai_docs_review.py). It combines AI-assisted editorial review with deterministic checks and established documentation tools, producing both HTML and JSON reports.

### What it checks

The **AI review** uses DeepSeek for conservative analysis of:

* Grammar and clarity;
* structure and scannability;
* portfolio quality;
* repetition;
* Mermaid diagram opportunities;
* site-wide consistency.

AI findings must quote exact source text. The script validates each quotation against the source and recalculates its line number, discarding findings that cannot be verified.

The pipeline also runs:

* **AccessibilityCheck** — checks alt text, vague link text, and heading-level jumps.
* **LinkCheck** — validates local links and assets.
* **Remark** — checks Markdown/MDX syntax and structural conventions.
* **Vale** — checks mechanically enforceable prose and style-guide rules, such as terminology, wording, punctuation, and other configured conventions.
* **Lychee** — checks external HTTP/HTTPS links.

This keeps deterministic checks separate from the higher-level editorial judgement handled by the AI review.

### Review scopes and presets

The tool supports two review scopes:

* **Per-page** — reviews individual Markdown and MDX documents.
* **Site-wide** — compares documents for repetition and consistency.

Available presets include:

* Full review
* Editorial only
* Portfolio only
* Repetition only
* Mermaid opportunities only
* Accessibility only
* Site-wide consistency only
* Remark only
* Vale only
* Lychee only
* Link checks only

Checks that do not apply to the selected scope are automatically excluded.

### Modes

The script can run in two modes:

* **Local mode** — runs the selected checks and generates reports for inspection during development.
* **CI mode** (`--ci`) — runs the QA pipeline and returns exit code `1` when configured issue or check-error thresholds are exceeded.

### Reports

The script generates:

* `ai-doc-review.html` — human-readable report.
* `ai-doc-review.json` — structured output for automation and CI.

The report records file, line, severity, confidence, type, category, source, original text, issue, and suggestion. Findings can be filtered by severity and source, including AI, static checks, Remark, Vale, and Lychee.

### Severity and CI

Issues are classified as **High**, **Medium**, or **Low**, with confidence recorded separately.

Default CI thresholds are:

* 0 high-severity issues;
* 5 medium-severity issues;
* 0 API/check errors.

Because failure occurs when a count exceeds its threshold, one high issue, six medium issues, or one API/check error causes the QA gate to fail. Low-severity findings do not fail CI.

Thresholds can be configured with `--fail-high`, `--fail-medium`, and `--fail-api-errors`.

### GitHub Actions integration

The deployment workflow builds the Docusaurus site, installs the QA dependencies, runs the full review, and publishes the HTML and JSON reports.

The QA step is allowed to complete even when thresholds are exceeded, so the report can still be deployed under `/qa/`. A later QA gate then fails the workflow when required.


