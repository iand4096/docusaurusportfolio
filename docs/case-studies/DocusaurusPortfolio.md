---
title: Docusaurus Portfolio
description: A case study of building a Docusaurus documentation platform with governed content,
  search, related-content recommendations, Markdown exports, automated QA, and CI/CD.
sidebar_position: 7
sidebar_custom_props:
  caseStudyCard:
    title: Building a Documentation Platform
    tag: Documentation engineering
    description: Built this portfolio’s content discovery, documentation checks and automated publishing.
    highlights:
      - Built a Python QA pipeline covering style, accessibility, links and AI editorial review
      - Added metadata-driven browsing, related-content links and machine-readable exports
    ariaLabel: Read the Docusaurus portfolio case study
type:
  - case-study
audiences:
  - developers
  - technical-writers
  - documentation-managers
topics:
  - docs-as-code
  - documentation-engineering
  - developer-experience
  - technical-validation
technologies:
  - docusaurus
  - react
  - mdx
  - markdown
  - github-actions
  - github-pages
  - python
  - vale
  - languagetool
  - deepseek-api
  - mermaid
  - jsx
  - javascript
  - git
  - github
  - typescript
lifecycle:
  - current
tags:
  - deepseek-api
  - developer-experience
  - docs-as-code
  - documentation-engineering
  - docusaurus
  - git
  - github
  - github-actions
  - github-pages
  - javascript
  - jsx
  - languagetool
  - markdown
  - mdx
  - mermaid
  - python
  - react
  - technical-validation
  - typescript
  - vale
---

import CaseStudySummary from '@site/src/components/CaseStudySummary';

<CaseStudySummary {...{
  "employer": "Independent project",
  "industry": "Documentation engineering",
  "projectType": "Publishing and QA platform",
  "icon": "window-maximize",
  "summary": "Built this portfolio as a working example of automated QA, metadata-driven discovery and machine-readable publishing.",
  "role": "Sole designer, developer and documentation author",
  "scope": "Portfolio publishing, discovery, quality assurance and CI/CD",
  "decision": "Combine deterministic checks with AI review and source-validated findings",
  "deliverables": "Docusaurus site, Python QA pipeline, faceted browsing, related links and LLM exports",
  "evidenceTitle": "Delivered Capabilities",
  "evidence": [
    {
      "value": "Automated QA",
      "label": "Style, accessibility, links and AI editorial review"
    },
    {
      "value": "Content discovery",
      "label": "Faceted browsing and related-page recommendations"
    },
    {
      "value": "LLM exports",
      "label": "Markdown corpus and versioned QA reports"
    }
  ]
}} />

## Context {/* #context */}

I built this portfolio with Docusaurus to publish my documentation samples and demonstrate the tooling behind them. It includes search, automated content recommendations and a Python documentation QA pipeline.

## Challenge {/* #challenge */}

* Build a portfolio site using Docusaurus, React/JSX, TypeScript and GitHub Actions.
* Integrate an LLM API into an automated QA workflow.
* Combine AI review with deterministic checks such as Markdown linting, accessibility, style and link checks.

## Approach {/* #approach */}

Docusaurus provides the documentation framework. I used Markdown and MDX for content, and wrote React components for landing-page cards, capability grids and document controls.

GitHub Actions automate deployment and documentation QA.

For quality assurance, I wrote a Python script that combines AI review with deterministic checks such as link checking. The script validates the AI findings against the source to guard against hallucination, and generates a report containing the identified issues and suggested improvements.

## Implementation {/* #implementation */}

### Local search and faceted browsing {/* #local-search-and-faceted-browsing */}

The [Explore page](/explore?view=browse) combines relevance-ranked local search with filters for content type, audience, topic, technology and lifecycle. Search supports prefix matching and conservative typo tolerance, while facet counts help readers refine their selection. It searches titles, descriptions and metadata in the generated catalogue; article-body search is provided separately by the cloud API.

A generated taxonomy catalogue supplies the custom React interface. The [taxonomy case study](TaxonomyGovernance.md) explains the AI-assisted taxonomy generation and governance.

### Cloud-backed search {/* #cloud-backed-search */}

The Search tab connects the static site to a FastAPI service on Azure Container Apps. Readers can use keyword, semantic or hybrid retrieval, inspect source passages, and optionally request AI answers with source links. Governed metadata filters constrain retrieval. The [cloud search case study](RagSearchCloudArchitecture.md) explains the indexing, infrastructure and request controls.

### Related-content recommendations {/* #related-content-recommendations */}

A custom Docusaurus plugin generates up to three **See also** links from governed metadata during development and builds, without calling an AI service. Relevance rules favour distinctive shared topics and technologies, and authors can exclude destinations or disable recommendations per page. A generated review report explains the selections; CI checks that committed recommendations remain current.

### Machine-readable publishing {/* #machine-readable-publishing */}

Production builds generate `llms.txt`, `llms-full.txt` and individual Markdown exports that retain governed taxonomy fields. Documentation pages expose **Copy page as Markdown** and **View Markdown** controls. Copying includes a manual fallback when clipboard access is unavailable.

### Reusable documentation components {/* #reusable-presentation */}

These guides combine authoring examples with live previews of the components used across this portfolio.

- [CapabilityGrid and CapabilityCard](../implementation-details/capability-grid.mdx) display responsive grids, checklists and expandable cards.
- [SemanticLabel and SemanticLabelGroup](../implementation-details/semantic-label.mdx) identify decisions, rationale, contributions and outcomes in the prose.
- [CaseStudySummary and SidebarCardGrid](../implementation-details/case-study-summary-and-sidebar-card-grid.mdx) present project overviews and build landing-page cards from sidebar and frontmatter metadata.
- [DiagramFigure](../implementation-details/diagram-figure.mdx) adds automatic numbering, full-screen viewing and shareable links to Mermaid subgraphs.
- [ApiEndpoint and ApiExample](../implementation-details/api-example.mdx) use the same OpenAPI spec to link to Scalar operations and display request, response and cURL examples.

### Documentation QA {/* #documentation-qa */}

I combined deterministic checks for links, accessibility and style with AI editorial review. The workflow checks AI findings against the source before reporting them. The [Documentation QA guide](../implementation-details/qa-overview.md) explains how to run the checks and follow a finding through review.

The [Documentation QA case study](DocumentationQa.md) explains the design choices behind evidence verification, feedback and the CI gate.

### QA feedback and adjudication {/* #qa-feedback-and-adjudication */}

AI findings can be challenged, revised or dismissed while preserving the original criticism, evidence and review history. When the same AI criticism appears in a later review, the report links it to the earlier discussion. If the document has changed, the previous decision requires revalidation. Saved reports can be refreshed without rerunning checks or making AI calls, and AI withdrawal alone does not remove a finding from CI counts.

### Reliable report publishing {/* #reliable-report-publishing */}

I designed the workflow to publish reports even when findings exceed the QA thresholds, so readers can inspect what failed. Each report is tied to the commit it reviewed.

The implementation includes the portfolio published on GitHub Pages, a [Documentation QA report](pathname:///qa/) for the current site, and the [GitHub repository](https://github.com/iand4096/docusaurusportfolio) containing the source, QA tooling, and deployment workflow.

## Impact {/* #impact */}

Readers can browse by metadata, search source passages and follow related-page links. Each deployment also publishes a QA report with findings and recorded review decisions.
