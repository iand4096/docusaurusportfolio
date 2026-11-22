---
title: Governed documentation taxonomy
description: A case study describing the design and implementation of a governed documentation 
  taxonomy for a Docusaurus portfolio, including AI-assisted classification and deterministic 
  validation.
sidebar_position: 6
sidebar_custom_props:
  caseStudyCard:
    title: Governed Documentation Taxonomy
    tag: Metadata governance
    description: Built a shared set of metadata terms for documentation navigation and search.
    highlights:
      - Designed one metadata vocabulary for authoring, navigation and search
      - Built checks and reviewed change workflows for AI-suggested classifications
    ariaLabel: Read the documentation taxonomy case study
type:
  - case-study
audiences:
  - documentation-managers
  - technical-writers
topics:
  - documentation-governance
  - docs-as-code
  - documentation-engineering
  - taxonomy
technologies:
  - codex
  - agentic-ai
  - docusaurus
  - yaml
  - git
lifecycle:
  - current
tags:
  - agentic-ai
  - codex
  - docs-as-code
  - documentation-engineering
  - documentation-governance
  - docusaurus
  - git
  - taxonomy
  - yaml
---

import CaseStudySummary from '@site/src/components/CaseStudySummary';
import frontMatterActions from './img/FrontMatterActions.png';
import frontMatterMetadata from './img/FrontMatterMetaData.png';
import frontMatterTechnologies from './img/FrontMatterChooseFromTechList.png';
import taxonomyReview from './img/AI metadata suggestions.png';
import docusaurusExploreFilter from './img/DocusaurusExploreFilter.png';
import docusaurusFooterTags from './img/DocusaurusFooterTags.png';

<CaseStudySummary {...{
  "employer": "Independent project",
  "industry": "Documentation engineering",
  "projectType": "Metadata governance",
  "icon": "tags",
  "summary": "Built one controlled vocabulary connecting documentation metadata, navigation, authoring tools and search.",
  "role": "System design and development",
  "scope": "Metadata validation, authoring support and taxonomy change management",
  "decision": "Git-versioned vocabulary with deterministic checks and human-approved AI proposals",
  "deliverables": "YAML taxonomy, validation tools, generated views and migration workflows",
  "evidenceTitle": "What it enables",
  "evidence": [
    {
      "value": "Consistent classification",
      "label": "Shared terms across documents and authoring tools"
    },
    {
      "value": "Reliable discovery",
      "label": "The same metadata drives navigation, filters, links and search"
    },
    {
      "value": "Controlled evolution",
      "label": "Preview and validate taxonomy changes before applying them"
    }
  ]
}} />

## Context {/* #context */}

Structured metadata and taxonomy can improve navigation and search in a large documentation repository. They also support content ownership, documentation lifecycle management, publishing automation and a consistent vocabulary for better alignment across an organisation.

My work on a large doc-as-code portal at a financial institution showed me the need for a shared metadata vocabulary and a way to check that contributors used it consistently. I built the taxonomy for this Docusaurus portfolio to implement those controls on a smaller scale and explore how GenAI could help contributors apply metadata.

The taxonomy uses a *Git-versioned controlled vocabulary* rather than free-form tags. That vocabulary drives document metadata, Docusaurus tags, editor controls, and faceted navigation. Its definitions also appear as tooltips on the first eligible mention of a technology in the page text. [Explore the faceted navigation](/explore?view=browse)

## Challenge {/* #challenge */}

I wanted the repository to enforce the metadata model rather than rely on contributors to remember conventions. This required:

* Stable IDs for taxonomy terms, such as `api-documentation` for the topic labelled “API documentation”.
* One authoritative list of valid values. For example, `taxonomy.yml` lists `api-documentation` as an allowed value for `topics`.
* Authoring tools that use that list.
* Automatic detection of invalid metadata.
* Reproducible generation of Docusaurus tags and a shared source for technology definitions.
* Explicit handling of renames, corrections, replacements and deprecations.
* A way to see the effect of a taxonomy change before applying it.

This meant treating the taxonomy as a repository artefact rather than editorial guidance.

## Approach {/* #approach */}

One rule drives the implementation:

> *AI can propose changes to the central taxonomy and metadata applied to documents, but humans must approve them. Central tooling is used to change the canonical taxonomy instead of manual modification.*

AI can make a useful first pass at questions such as which existing terms apply to a document or whether the vocabulary lacks an important concept. However, I do not let the model determine whether the taxonomy is valid or whether a new term becomes canonical.

A central set of tools is used to validate IDs and cardinality, check migration preconditions, determine whether documents need rewriting, and control changes to the canonical taxonomy. AI produces proposals, a person reviews them, and the tools apply these approved changes.

The design uses these constraints:

* **One source of truth.** Docusaurus, the authoring environment, and navigation use views generated from the same taxonomy.
* **Dry runs before applying changes.** The tooling checks taxonomy changes against the documentation corpus before changing files.
* **Explicit migrations.** Vocabulary changes have their own reviewable records.
* **Deprecation rather than automatic deletion.** The taxonomy retains old IDs and replacement relationships.
* **Human review for semantic changes.** Automation can suggest a change but cannot silently redefine the vocabulary.
* **Controlled authoring.** Writers select governed values without needing to know how the taxonomy works internally.

## Implementation {/* #implementation */}

I used Codex as an agentic coding assistant while building the taxonomy tooling and its editor integration.

The system includes:

* A canonical taxonomy in YAML under Git version control.
* Controlled dimensions for content type, audience, topic, technology, and lifecycle.
* Tools for validating taxonomy and document metadata.
* Generation of Docusaurus tags, editor controls, and navigation data, with inline technology tooltips drawn directly from the taxonomy.
* Reviewed taxonomy migrations with preconditions and dry runs.
* Corpus-wide checks before applying a taxonomy change.

### Metadata authoring in VS Code

The Front Matter CMS extension uses the generated editor configuration to present the allowed values and selection limits. In the metadata panel for this case study, the content type field is already at its limit of one, while the audience and topic fields still allow more selections.

<p>
  <a href={frontMatterMetadata}>
    <img src={frontMatterMetadata} width={500} alt="Front Matter CMS metadata editor showing selected content type, audience and topic values with a selection limit for each field." />
  </a>
</p>

Writers can classify a page manually using the same vocabulary. Here, the **Technologies** picker lists approved terms such as `deepseek-api` alongside the values already assigned to this case study. With free-form metadata, writers could label the same API `DeepSeek`, `deepseek-api`, or `DeepSeek LLM API`. Those variants can split related pages across separate filters. Readers can select one value and miss pages filed under the others. The picker gives writers one canonical ID for the API, so those pages appear together under a single filter.

<p>
  <a href={frontMatterTechnologies}>
    <img src={frontMatterTechnologies} width={500} alt="Front Matter CMS Technologies picker showing available terms and the selected values Docusaurus, Git and YAML." />
  </a>
</p>

In the same sidebar, **Review metadata with DeepSeek** suggests classifications for the active document and flags gaps in the vocabulary. The other two custom actions apply the saved metadata proposal or draft a change to the vocabulary. [Front Matter custom actions documentation](https://frontmatter.codes/docs/custom-actions/)

<p>
  <a href={frontMatterActions} style={{display: 'inline-block', position: 'relative', maxWidth: '100%'}}>
    <img src={frontMatterActions} width={500} style={{display: 'block'}} alt="Front Matter CMS Actions panel with the three custom taxonomy buttons outlined: review metadata with DeepSeek, apply reviewed taxonomy metadata and generate a draft taxonomy migration." />

    <span aria-hidden="true" style={{position: 'absolute', inset: '86.4% 4.3% 0.2% 2.3%', border: '2px solid #ffcf40', borderRadius: 4, pointerEvents: 'none'}} />
  </a>
</p>

The **Taxonomy review** panel separates suggested additions using existing terms from proposals for new terms. In this review of the case study itself, DeepSeek suggests adding VS Code and the DeepSeek LLM API, and proposes **Front Matter CMS** as a new vocabulary term. The writer can expand the proposal to review the supporting excerpts before deciding whether to draft a migration. If an approved migration adds the term to the vocabulary, the saved metadata proposal can then assign it to the page.

<p>
  <a href={taxonomyReview} style={{display: 'inline-block', position: 'relative', maxWidth: '100%'}}>
    <img src={taxonomyReview} width={640} style={{display: 'block'}} alt="Taxonomy review panel with a green outline around the VS Code and DeepSeek LLM API additions and a gold outline around the proposed Front Matter CMS term and its evidence." />

    <span aria-hidden="true" style={{position: 'absolute', inset: '35.7% 3.1% 60% 4.4%', border: '2px solid #59dc9d', borderRadius: 4, pointerEvents: 'none'}} />

    <span aria-hidden="true" style={{position: 'absolute', inset: '62.1% 2.2% 8% 3.5%', border: '2px solid #ffcf40', borderRadius: 4, pointerEvents: 'none'}} />
  </a>
</p>

Because this repository is small, I can show the implementation in [full](../implementation-details/taxonomy.md).

## Impact {/* #impact */}

The portfolio now has one canonical vocabulary and one supported path for changing it.

Canonical IDs and validation reduce vocabulary drift. The same source drives Docusaurus tags, inline definition tooltips, editor configuration, and navigation. Updating a technology definition in the taxonomy keeps the reader-facing explanation in sync. Taxonomy corrections use migrations with dry runs and preconditions, and the tooling identifies which documents need changes before applying a migration.

The **Docusaurus** technology selected in the editor also appears as a filter in Explore and as a tag at the bottom of this case study. Explore groups technology filters by kind. **Documentation platform (3)** is the group containing Docusaurus, MkDocs and Sphinx. The number beside each platform shows how many pages use that term. Readers can start with the filter to find matching pages or follow the footer tag from a page they’re already reading. Both use the same taxonomy ID, `docusaurus`.

<p style={{marginBottom: '1.75rem'}}>
  <a href={docusaurusExploreFilter} style={{display: 'inline-block', position: 'relative', maxWidth: '100%'}}>
    <img src={docusaurusExploreFilter} width={420} style={{display: 'block'}} alt="Docusaurus selected and outlined in the Explore documentation platform filter." />

    <span aria-hidden="true" style={{position: 'absolute', inset: '32% 48.5% 35% 0', border: '2px solid #c76000', borderRadius: 999, pointerEvents: 'none'}} />
  </a>
</p>

<p>
  <a href={docusaurusFooterTags} style={{display: 'inline-block', position: 'relative', maxWidth: '100%'}}>
    <img src={docusaurusFooterTags} width={640} style={{display: 'block'}} alt="Docusaurus outlined among the tags in the case study footer." />

    <span aria-hidden="true" style={{position: 'absolute', inset: '51% 83.2% 8% 2%', border: '2px solid #c76000', borderRadius: 6, pointerEvents: 'none'}} />
  </a>
</p>

AI-assisted classification is advisory only. It can suggest a classification or new term, but it cannot make either canonical.

During one taxonomy correction, I prepared updates to five technology terms and ran the migration against all 26 portfolio documents. The first dry run found stale derived state in a recently added document. I corrected that first, reran the checks, and then applied the migration.
