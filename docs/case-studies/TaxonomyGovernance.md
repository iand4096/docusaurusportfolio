---
title: Governed documentation taxonomy
description: A case study describing the design and implementation of a governed documentation 
  taxonomy for a Docusaurus portfolio, including AI-assisted classification and deterministic 
  validation.
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
  - docusaurus
  - yaml
  - git
lifecycle:
  - current
tags:
  - docs-as-code
  - documentation-engineering
  - documentation-governance
  - docusaurus
  - git
  - taxonomy
  - yaml
---

## Context

In a large documentation repository, structured metadata and taxonomy can improve navigation and search while also supporting content ownership, documentation lifecycle management, publishing automation, and consistent vocabulary.

I built the taxonomy for this Docusaurus portfolio after encountering these problems in a much larger docs-as-code portal at a financial institution. GenAI now makes it increasingly practical to automate the application and validation of structured metadata. I therefore wanted to build a smaller implementation of the metadata controls that would have been useful in that environment.

The taxonomy uses a **Git-versioned controlled vocabulary** rather than free-form tags. That vocabulary drives document metadata, Docusaurus tags, editor controls, and faceted navigation — see [the browse page](pathname:///browse/) for an example of the latter.

## Challenge

I wanted the repository to enforce the metadata model rather than rely on contributors to remember conventions. This required:

* Stable IDs for canonical taxonomy concepts.
* One authoritative list of valid values.
* Authoring tools that use that list.
* Automatic detection of invalid metadata.
* Reproducible generated files such as Docusaurus tags.
* Explicit handling of renames, corrections, replacements, and deprecations.
* A way to see the effect of a taxonomy change before applying it.

This meant treating the taxonomy as a repository artefact rather than editorial guidance.

## Approach

One rule drives the implementation:

> **AI can propose semantic intent, but humans must approve it. Central tooling is used to change the canonical taxonomy.**

AI can make a useful first pass at questions such as which existing terms apply to a document or whether the vocabulary lacks an important concept. However, I do not let the model determine whether the taxonomy is valid or whether a new term becomes canonical.

A central set of tools is used to validate IDs and cardinality, check migration preconditions, determine whether documents need rewriting, and control changes to the canonical taxonomy. AI produces proposals, a person reviews them, and the tools apply these approved changes.

The design uses these constraints:

* **One source of truth.** Docusaurus, the authoring environment, and navigation use views generated from the same taxonomy.
* **Preflight before mutation.** The tooling checks taxonomy changes against the documentation corpus before changing files.
* **Explicit migrations.** Vocabulary changes have their own reviewable records.
* **Deprecation rather than automatic deletion.** The taxonomy retains old IDs and replacement relationships.
* **Human review for semantic changes.** Automation can suggest a change but cannot silently redefine the vocabulary.
* **Controlled authoring.** Writers select governed values without needing to know how the taxonomy works internally.

## Implementation

The system includes:

* A canonical taxonomy in YAML under Git version control.
* Controlled dimensions for content type, audience, topic, technology, and lifecycle.
* Tools for validation of taxonomy and document metadata.
* Generation of Docusaurus tags, editor controls, and navigation data.
* AI-assisted classification and vocabulary-gap detection.
* Reviewed taxonomy migrations with preconditions and dry runs.
* Corpus-wide checks before applying a taxonomy change.

Because this repository is small, I can show the implementation in [full](../implementation-details/taxonomy.md).

## Impact

The portfolio now has one canonical vocabulary and one supported path for changing it.

Canonical IDs and validation reduce vocabulary drift. The same source generates Docusaurus tags, editor configuration, and navigation instead of requiring separate maintenance. Taxonomy corrections use migrations with dry runs and preconditions, and the tooling identifies which documents need changes before applying a migration.

AI-assisted classification is advisory only. It can suggest a classification or new term, but it cannot make either canonical.

During one taxonomy correction, I prepared updates to five technology terms and ran the migration against all 26 portfolio documents. The first preflight run found stale derived state in a recently added document. I corrected that first, reran the checks, and then applied the migration.
