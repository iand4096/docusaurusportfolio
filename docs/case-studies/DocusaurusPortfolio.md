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
      "label": "Markdown documentation set and versioned QA reports"
    }
  ]
}} />

## Context {/* #context */}

I built this portfolio to publish my documentation samples and demonstrate how I engineer and maintain a documentation site.

## Challenge {/* #challenge */}

The publishing workflow needed to catch routine defects and surface editorial issues, with enough evidence for me to assess individual findings and revisit earlier decisions.

## Approach {/* #approach */}

I used Docusaurus and MDX to publish the site. I built a Python QA pipeline that combines automated checks with AI editorial review and runs in GitHub Actions.

## Implementation {/* #implementation */}

### Documentation QA {/* #documentation-qa */}

The pipeline combines automated link, accessibility and Markdown checks with Vale style rules and DeepSeek editorial review. It validates AI findings against the source before reporting them. I can challenge, revise or dismiss a finding while preserving the original evidence and review history. When a finding recurs, the report links back to the earlier discussion. If the source has changed, the previous decision needs to be revalidated.

The workflow publishes the report before marking a run as failed when QA thresholds are exceeded. Each report is tied to the commit it checked, so someone investigating a failure can see the findings for that revision.

### Content discovery {/* #local-search-and-faceted-browsing */}

Readers can [browse by content type, topic and audience](/explore?view=browse) or [search source passages](/explore?view=ai-search) using keyword, semantic or hybrid retrieval. A Docusaurus plugin uses shared taxonomy terms to generate related-page links at build time. The [taxonomy governance case study](TaxonomyGovernance.md) explains how the metadata is managed, and the [cloud search case study](RagSearchCloudArchitecture.md) describes how the search service retrieves evidence.

### Machine-readable publishing {/* #machine-readable-publishing */}

Production builds publish individual pages and the full documentation set as Markdown, preserving governed taxonomy metadata. Readers can view or copy the Markdown for an individual page, and the site publishes `llms.txt` and `llms-full.txt` for tools that consume the documentation set.

### Reusable documentation components {/* #reusable-presentation */}

Reusable React components give authors a consistent way to summarise case studies, present capabilities and diagrams, highlight decisions and outcomes, and display API examples. Authors can use them directly in MDX.

To make the site easier to maintain, I apply the software engineering principle “Don’t Repeat Yourself” (DRY). Shared layouts live in reusable React components, so a layout change takes effect wherever the component is used. API operation links and request and response examples draw from a single OpenAPI specification. The [API component guide](../implementation-details/api-example.mdx) shows how this works.

## Impact {/* #impact */}

The [published QA report](pathname:///qa/) lets readers inspect findings and recorded review decisions. The [GitHub repository](https://github.com/iand4096/docusaurusportfolio) shows how GitHub Actions checks pull requests and publishes QA reports with each deployment.
