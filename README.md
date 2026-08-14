# Ian Drewett — Technical Writing Portfolio

A Docusaurus portfolio presenting selected technical-writing work in API
documentation, payments, developer experience, and software user
documentation.

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

## QA Site Report

A QA Report is generated using [DeepSeek AI](scripts/ai_docs_review.py) for every change to the site. See output at https://iand4096.github.io/docusaurusportfolio/qa/

The report script **ai_docs_review.py** review a Docusaurus documentation/technical-writing portfolio and produce both human-readable and machine-readable QA results.

It provides a documentation QA pipeline for a technical-writing portfolio that combines conservative LLM editorial analysis with deterministic accessibility/link checks, validates AI findings against the source, produces HTML/JSON reports, and can block CI when serious documentation problems are found.

Further details are provided below.

### What it checks

The tool combines **AI-based editorial review** with **deterministic/static checks**.

The AI checks cover:

* **Grammar and clarity** — grammar, confusing wording, incomplete sentences, terminology consistency, unfinished content, and punctuation. It deliberately avoids general spelling corrections and preserves valid British English. 
* **Structure and scannability** — awkward ordering, overly dense paragraphs, misplaced context, misleading headings and over-explanation. 
* **Portfolio quality** — specifically asks whether a technical-writing case study clearly shows the deliverable, audience, author's contribution, challenges/usefulness, and relationship to the published work. It also flags cases where too much space is spent explaining technology rather than demonstrating documentation work. 
* **Repetition** — detects unnecessary duplication within a page or across pages. 
* **Mermaid diagram opportunities** — very conservatively suggests diagrams for workflows, lifecycles, system relationships, decisions or other information that would benefit from visualisation. 
* **Site-wide consistency** — compares portfolio pages for inconsistent structure, terminology and presentation of the author's contribution. 

There are also two static checks:

- **AccessibilityCheck** finds issues such as missing/empty image alt text, vague links such as “click here”, and heading-level jumps.
- **LinkCheck** tests local links and assets to make sure their targets exist; external HTTP links are deliberately excluded from that test. 

### How the AI part works

The script uses the Requests library to make REST API calls to the configured DeepSeek mode with documentation text and requires structured JSON findings. Each AI issue contains things such as:

`severity → confidence → type → category → file/line → original text → explanation → suggestion`

An important safeguard is that AI findings are **validated against the actual source**. The model has to quote exact source text, and the implementation recalculates the real line number. If the quoted text cannot be found, the finding is discarded. This reduces fabricated or mislocated findings. 

The prompts are also intentionally conservative: a good page is allowed to return **zero issues**, rather than forcing the model to manufacture criticism.

### Per-page vs site-wide review

The tool supports two scopes:

**Per-page mode** reviews each Markdown/MDX document individually. A full per-page review effectively runs grammar, structure, portfolio, repetition, Mermaid, accessibility and link checks.

**Site-wide mode** compares documents together. The relevant checks are primarily cross-page repetition and site-wide consistency.

The tool automatically removes checks that do not support the selected review scope. 

It also provides presets such as **Full review, Editorial only, Portfolio only, Repetition only, Mermaid opportunities only, Accessibility only, and Site-wide consistency only**.

### What the generated QA report looks like

The HTML report contains an issue table with these columns:

**File | Line | Severity | Confidence | Type | Category | Source | Original | Issue | Suggestion**

It also separately displays API/check errors. 

The HTML UI lets you filter findings by **severity** and whether the finding came from **static analysis or AI**. 

The script generates two files:

* `ai-doc-review.html` — visual report for a person to inspect.
* `ai-doc-review.json` — structured output suitable for automation/CI.

Both are generated after all selected checks run. 

### Severity and CI behaviour

Issues have three severities:

* **High** — materially misleading, broken, contradictory or publication-blocking.
* **Medium** — significant comprehension, structural or portfolio-quality problems.
* **Low** — worthwhile but non-blocking improvements.

There is also **high/medium/low confidence**, which is separate from severity.

The default CI thresholds are particularly useful: **0 high issues, 5 medium issues and 0 API/check errors are allowed before crossing the configured threshold**. Because the comparison is `count > threshold`, one high issue fails by default, six medium issues fail, and one API/check error fails. Low-severity issues do not affect CI failure. The CLI exposes these as `--fail-high`, `--fail-medium`, and `--fail-api-errors`. 

### Modes (local / ci)

The script can be run locally or as part of a Github Action with `--ci` where a failed threshold causes an exit code of `1`

