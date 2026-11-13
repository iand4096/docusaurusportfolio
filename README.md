# Documentation engineering portfolio

A technical documentation portfolio built with Docusaurus, demonstrating docs-as-code workflows, automated documentation quality assurance, AI-assisted review, taxonomy governance and cloud-based retrieval-augmented search.

The repository contains the portfolio website, its documentation tooling, CI/CD workflows, a Python-based knowledge API and Terraform infrastructure for deployment to Azure Container Apps.

[Live portfolio](https://iand4096.github.io/docusaurusportfolio/)

The accompanying [case studies](docs/case-studies/) explain the engineering decisions, implementation approaches, validation methods and limitations of the projects, alongside selected technical-writing work in API documentation, payments, developer experience and software user documentation.

## Licence and permitted use

This repository is published solely for portfolio review by potential employers, recruiters and their evaluation teams. It is not open source. Original code and portfolio content may be inspected and run locally for that purpose; reuse, modification, redistribution and public deployment require prior written permission. Third-party material retains its own terms. See [`LICENSE.md`](LICENSE.md) for the full terms and [third-party notices](src/pages/third-party-notices.md) for Font Awesome attribution and licences.

## Architecture overview

Markdown and MDX content carry governed metadata validated against a canonical taxonomy. GitHub Actions validates metadata, builds the Docusaurus site, runs documentation QA and publishes the site together with its documentation QA reports to GitHub Pages.

The published AI search page calls a separate FastAPI backend on Azure Container Apps. The backend searches a prebuilt documentation index using BM25 and optional FAISS semantic retrieval, with optional DeepSeek answer generation grounded in retrieved passages. Terraform defines the Azure infrastructure; backend image packaging is separate from the website deployment workflow.

| Subsystem | Implementation and documentation |
| --- | --- |
| Portfolio website | [Documentation content](docs/), [pages and components](src/), and [Docusaurus configuration](docusaurus.config.ts). |
| Taxonomy governance | [Canonical vocabulary](taxonomy/taxonomy.yml), [validation and generation CLI](scripts/taxonomy.py), and [governance case study](docs/case-studies/TaxonomyGovernance.md). |
| Documentation QA | [AI-assisted review and deterministic checks](scripts/ai_docs_review.py), [review workflow](.github/workflows/docs-review.yml), and the detailed guide below. |
| CI/CD | [Site deployment and QA reports](.github/workflows/deploy.yml) and [pull-request metadata validation](.github/workflows/taxonomy-validation.yml). |
| Knowledge API and search | [API architecture, setup and security controls](knowledge-api/README.md), [search frontend](src/components/GovernedSearch/GovernedSearchPage.tsx), and [cloud search case study](docs/case-studies/RagSearchCloudArchitecture.md). |
| Azure infrastructure | [Terraform configuration](infra/azure/main.tf) and [backend image packaging script](scripts/build-azure-image.ps1). |

## Local development

```bash
npm install
npm run start
```

For the local search backend and frontend feature flags, follow the [Knowledge API setup guide](knowledge-api/README.md#local-setup).

### Generated See also links

The local Docusaurus plugin generates up to three related links after substantive documentation pages. It runs during `npm run start` and `npm run build`, and refreshes when documentation or the generated taxonomy navigation data changes. It does not call an AI service or the search API.

To generate and review the results separately:

```bash
npm run see-also:generate
npm run see-also:check
npm run test:see-also
```

Generation writes [the related-document index](src/generated/see-also.json) and [the review report](reports/see-also.md). Commit both artifacts with content changes. The check command is read-only and fails if either artifact is missing or stale; CI runs it before any build can refresh the files. Run `npm run taxonomy:generate` first if the canonical vocabulary or navigation metadata needs regeneration.

The broad topics `technical-writing` and `docs-as-code` are ignored throughout See also matching and scoring; they remain available for taxonomy navigation and filtering. Recommendations prioritise distinctive topics: topic overlap contributes up to `0.4`, weighted by squared inverse document frequency and normalised by the source page’s topic weights, so extra destination topics do not dilute the match. Technology overlap contributes up to `0.6` using squared inverse document frequency and coverage of the source page’s technologies, so extra technologies on a destination do not dilute the match. Candidates must share one of the source page’s least frequent topics (including ties), a specific technology, or its whole-page employer classification. A whole-page employer match adds `0.8`; audience overlap adds up to `0.04`. Neither establishes relevance alone: at least one shared topic or technology must occur on no more than 65% of eligible pages. The minimum score is `0.3`; fewer than three links are shown when insufficient candidates qualify. Scores explain ordering, not measured recommendation accuracy. Because technology coverage and distinctive topics are evaluated from the source page, recommendations need not be reciprocal.

Home and landing pages, drafts, unlisted pages, archived content and the current page are excluded. Historical samples remain eligible. A document already linked anywhere in the article body is excluded, including links to its sections, unless it shares the source page’s whole-page employer classification. Manual exclusions still apply to same-employer pages. Markdown references, relative file links, canonical routes, published-site URLs, configured redirect aliases and literal MDX `href`/`to` attributes resolve to the same document. Code samples, images and comments do not count as body links. Dynamic MDX links and unresolved document links appear as warnings in the review report and require inspection.

To exclude destinations, add their repository document IDs to the source page's frontmatter:

```yaml
see_also:
  exclude:
    - skills/DocumentationEngineering
    - case-studies/TaxonomyGovernance
```

IDs are paths under `docs/`, without the `.md` or `.mdx` extension; they are not URLs. Invalid IDs and unsupported options fail generation. Another qualifying candidate can fill an excluded destination's place. To hide the section on one page, use:

```yaml
see_also:
  enabled: false
```

This disables outgoing recommendations on that page; other pages can still recommend it. Do not edit the generated index or report to curate links.

### LLM-readable documentation

`npm run build` uses `docusaurus-plugin-llms` to generate `build/llms.txt`,
`build/llms-full.txt` and individual Markdown copies of the documentation.
The Markdown copies retain the governed taxonomy fields. These files are
generated during production builds, not by `npm run start`.

Documentation pages include **Copy page as Markdown** and **View Markdown**
controls. Copy uses the generated export and offers manual copying if clipboard
access is unavailable. Preview working exports locally with `npm run build`
followed by `npm run serve`.

After deployment, the index is available at
`https://iand4096.github.io/docusaurusportfolio/llms.txt`.

## Documentation QA

A QA report is generated for every change to the site and published at:

https://iand4096.github.io/docusaurusportfolio/qa/

I implemented the pipeline in [`scripts/ai_docs_review.py`](scripts/ai_docs_review.py). It combines AI-assisted editorial review with deterministic checks and established documentation tools, producing both HTML and JSON reports.

### Challenge feedback and saved reports

The report's **Challenge AI** button copies a CLI command for that exact saved
finding. Run it locally with `DEEPSEEK_API_KEY` configured. A challenge records
the rebuttal and adjudication in `qa/feedback.json`; it does not rerun the review.

Refresh the displayed report from the same saved JSON without running any checks
or making AI calls:

```bash
python3 scripts/ai_docs_review.py render \
  --report .qa/ai-doc-review.json \
  --report-dir .qa/feedback-view
```

`--report` also accepts the exact versioned GitHub Pages JSON URL copied by the
report. The output directory contains HTML, Markdown and JSON views, plus a
snapshot of the original report (`original-report.json`). The original review
date and finding IDs are preserved; a separate feedback timestamp identifies
when the view was refreshed.
Use a separate output directory for each original report. To publish a feedback
view, serve this output directory alongside the original versioned report; the
render command itself does not deploy or modify GitHub Pages.
For a view that will be published, use the versioned report URL as `--report`,
so copied challenge commands retain the public original-report reference.

The active list shows upheld, revised and pending findings. Withdrawn findings
remain in an expandable history section with human-dismissed findings. Revised
wording appears first, with the original criticism and challenge evidence retained.
An AI withdrawal alone does not change CI eligibility. Explicit human dismissal
removes an AI finding from CI counts:

```bash
python3 scripts/ai_docs_review.py resolve \
  --issue qa-REPLACE_WITH_FINDING_ID \
  --decision dismissed \
  --reason "The supplied source already answers this criticism."
```

Run `render` again after recording a resolution. Commit `qa/feedback.json` to
preserve decisions for other checkouts. Feedback is only applied when the saved
finding's source hash and proposed fix match the challenged version. Exact
recurring claims in changed documents keep the earlier discussion and are
marked **Needs revalidation**. See [QA finding identity and feedback continuity](qa/README.md)
for supported cases, revalidation commands and remaining limitations.

### What it checks

The **AI review** uses DeepSeek for conservative analysis of:

* Grammar and clarity.
* Structure and scannability.
* Portfolio quality.
* Repetition.
* Mermaid diagram opportunities.
* Site-wide consistency.

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

Issues are classified as **high**, **medium** or **low** severity, with confidence recorded separately.

Default CI thresholds are:

* 0 high-severity issues;
* 5 medium-severity issues;
* 0 API/check errors.

Because failure occurs when a count exceeds its threshold, one high issue, six medium issues, or one API/check error causes the QA gate to fail. Low-severity findings do not fail CI.

Thresholds can be configured with `--fail-high`, `--fail-medium`, and `--fail-api-errors`.

### GitHub Actions integration

The pull-request review and deployment workflows use the same [local composite action](.github/actions/setup-docs-qa/action.yml) to install Node.js, Python, Vale, LTeX+, Lychee and their configuration. The DeepSeek API key is injected only into the QA execution step.

The deployment workflow builds the Docusaurus site, installs the QA dependencies, runs the full review, and publishes the HTML and JSON reports.

The QA step is allowed to complete even when thresholds are exceeded, so the report can still be deployed under `/qa/`. A later QA gate then fails the workflow when required.
