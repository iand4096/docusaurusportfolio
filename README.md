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
| Documentation QA | [Documentation QA guides](docs/implementation-details/qa-overview.md), [CLI](scripts/ai_docs_review.py), and [review workflow](.github/workflows/docs-review.yml). |
| CI/CD | [Site deployment and QA reports](.github/workflows/deploy.yml) and [pull-request metadata validation](.github/workflows/taxonomy-validation.yml). |
| Knowledge API and search | [API architecture, setup and security controls](knowledge-api/README.md), [search frontend](src/components/GovernedSearch/GovernedSearchPage.tsx), and [cloud search case study](docs/case-studies/RagSearchCloudArchitecture.md). |
| Azure infrastructure | [Terraform configuration](infra/azure/main.tf) and [backend image packaging script](scripts/build-azure-image.ps1). |

## Local development

```bash
npm install
npm run start
```

For the local search backend and frontend feature flags, follow the [Knowledge API setup guide](knowledge-api/README.md#local-setup).

### Landing-page coverage

The full documentation QA review checks card metadata for pages under `tools/`,
`skills/`, `docs-samples/` and `case-studies/`. Missing or incomplete metadata
produces a high-severity static QA defect; it does not fail the Docusaurus build.
The section’s own `index` page and drafts are excluded. Tools, skills and samples
require `sidebar_custom_props.sampleCard`; case studies require
`sidebar_custom_props.caseStudyCard`. Each card needs a tag, description and a
non-empty list of highlights. Findings count towards the normal QA thresholds.

### Generated see also links

The local Docusaurus plugin generates up to three related links after substantive documentation pages. It runs during `npm run start` and `npm run build`, and refreshes when documentation or the generated taxonomy navigation data changes. It does not call an AI service or the search API.

To generate and review the results separately:

```bash
npm run see-also:generate
npm run see-also:check
npm run test:see-also
```

Generation writes [the related-document index](src/generated/see-also.json) and [the review report](reports/see-also.md). Commit both artefacts with content changes. The check command is read-only and fails if either artefact is missing or stale; CI runs it before any build can refresh the files. Run `npm run taxonomy:generate` first if the canonical vocabulary or navigation metadata needs regeneration.

**Excluded topics.** The broad topics `technical-writing` and `docs-as-code` are ignored throughout See also matching and scoring; they remain available for taxonomy navigation and filtering.

**Scoring.** Recommendations prioritise distinctive topics: topic overlap contributes up to `0.4`, weighted by squared inverse document frequency and normalised by the source page’s topic weights, so extra destination topics do not dilute the match. Technology overlap contributes up to `0.6` using squared inverse document frequency and coverage of the source page’s technologies, so extra technologies on a destination do not dilute the match. A whole-page employer match adds `0.8`; audience overlap adds up to `0.04`.

**Eligibility.** Candidates must share one of the source page’s least frequent topics (including ties), a specific technology, or its whole-page employer classification. Employer and audience matches cannot establish relevance alone: at least one shared topic or technology must occur on no more than 65% of eligible pages.

**Thresholds and caveats.** The minimum score is `0.3`; fewer than three links are shown when insufficient candidates qualify. Scores explain ordering, not measured recommendation accuracy. Because technology coverage and distinctive topics are evaluated from the source page, recommendations need not be reciprocal.

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

### Source code snippets

Mark the lines to show with named comments such as `# docs:start qa-response-validation` and `# docs:end qa-response-validation` in Python. Use `//` for JavaScript or TypeScript. Add an empty code fence with a language and a repository-relative source reference.

````markdown
```python source=scripts/qa_ai/validation.py#qa-response-validation
```
````

The site and Markdown exports copy the lines between the comments. The **View source** link shows the filename and opens the source snapshot included in that site build, with the excerpt marked.

## Documentation QA

The [Documentation QA guide](docs/implementation-details/qa-overview.md) covers local setup, report interpretation, the CLI and the architecture. To run a first check from a configured Python environment:

```bash
python3 scripts/ai_docs_review.py --mode per-page --filter accessibility
```

Open `.qa/ai-doc-review.html` for the local result or read the [latest published report](https://iand4096.github.io/docusaurusportfolio/qa/).
