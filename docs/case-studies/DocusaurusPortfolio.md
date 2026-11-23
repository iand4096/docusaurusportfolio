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
  - codex
  - agentic-ai
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
  - agentic-ai
  - codex
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

I built this portfolio to publish my writing samples and demonstrate the engineering that keeps a documentation site usable as it grows. I designed, implemented and documented the platform, using Codex as a coding assistant.

## Challenge {/* #challenge */}

Readers needed to find relevant material across case studies, writing samples and technical guides. As the sole maintainer, I needed to keep metadata consistent, catch editorial and technical defects during review, and keep examples and reference material in sync with their sources. Core browsing and reference pages also had to remain usable during a search service outage.

## Approach and design decisions {/* #approach */}

- **Keep core discovery static.** I used governed frontmatter as a shared input for browsing and recommendations. Full-text and semantic retrieval run through a separate cloud API.
- **Publish from maintained sources.** Docusaurus pulls code excerpts from the repository and publishes a versioned OpenAPI snapshot. Readers can inspect the API contract even when the service is unavailable.
- **Make quality checks auditable.** I combined deterministic checks with AI editorial review, verified AI findings against the source and made report publication independent of the QA thresholds.

## Implementation overview {/* #implementation */}

<span id="local-search-and-faceted-browsing" />

<span id="cloud-backed-search" />

<span id="related-content-recommendations" />

**Content discovery.** The [Explore page](/explore?view=browse) searches catalogue metadata locally and lets readers refine results with governed filters. The same taxonomy drives related-page suggestions. A [cloud search service](RagSearchCloudArchitecture.md) provides keyword, semantic and hybrid retrieval with source passages and optional AI answers. The [taxonomy governance case study](TaxonomyGovernance.md) explains how the vocabulary is maintained.

<span id="documentation-features-to-support-the-search-api" />

<span id="search-api-reference" />

<span id="api-request-and-response-examples" />

<span id="portfolio-wide-documentation-features" />

<span id="code-sample-inserts" />

<span id="machine-readable-publishing" />

<span id="reusable-presentation" />

**Documentation publishing.** Repository-backed excerpts keep code examples tied to their source. The build publishes Markdown exports and the static [Search API reference](pathname:///search-api). Reusable React components support [inline API examples](../implementation-details/api-example.mdx), [project summaries](../implementation-details/case-study-summary-and-sidebar-card-grid.mdx) and [interactive diagrams](../implementation-details/diagram-figure.mdx).

<span id="documentation-qa" />

<span id="qa-feedback-and-adjudication" />

<span id="reliable-report-publishing" />

**Quality assurance.** GitHub Actions runs checks for links, accessibility and style alongside evidence-validated AI editorial review. The deployment workflow publishes the report before enforcing the QA thresholds. The [Documentation QA case study](DocumentationQa.md) covers evidence verification, feedback and gating.

## Impact {/* #impact */}

- Readers can [browse by topic or technology](/explore?view=browse), then [search for source passages](/explore?view=ai-search) when they need the text behind a result.
- Authors can reuse [excerpts from checked-in code](../implementation-details/qa-key-concepts.md#check-adapters-and-shared-results). API maintainers can detect contract drift through the [schema validation workflow](https://github.com/iand4096/docusaurusportfolio/blob/main/.github/workflows/search-openapi.yml).
- Reviewers can inspect findings, source evidence and recorded review decisions in the [published QA report](pathname:///qa/). Reports identify the revision they reviewed and remain available when findings exceed the QA thresholds.

## Technical implementation {/* #technical-implementation */}

The [Portfolio architecture and publishing pipeline](../implementation-details/portfolio-architecture-and-publishing-pipeline.md) traces the build from source files to GitHub Pages and documents how to update the generated outputs.
