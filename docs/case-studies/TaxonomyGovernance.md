---
title: Governed documentation taxonomy
description: >
  A case study describing the design and implementation of a governed documentation
  taxonomy for a Docusaurus portfolio, including AI-assisted classification,
  repository validation, and controlled taxonomy changes.
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

## Project overview

I built the taxonomy for this Docusaurus portfolio after encountering governance problems while managing a large docs-as-code portal at a financial institution.

In large documentation repositories, metadata affects more than tags. It feeds navigation, search, content ownership, lifecycle information, publishing automation, and repository-wide maintenance. Small inconsistencies are manageable when they affect one or two pages. They are much harder to correct once they have spread across a large corpus and multiple contributors.

For this portfolio, I wanted to build a smaller version of the controls I would have found useful in that environment.

The taxonomy is a controlled vocabulary stored in Git rather than a set of free-form tags. It supplies document metadata, Docusaurus tags, editor controls, and faceted navigation. See this in action on [the browse page](pathname:///browse/).

One rule drives the implementation:

> **AI suggests metadata and vocabulary changes; humans review them; repository tooling applies approved changes.**

The system includes:

* A canonical taxonomy in YAML, versioned in Git
* Controlled dimensions for content type, audience, topic, technology, and lifecycle
* Validation of taxonomy and document metadata
* Generated Docusaurus tags, editor controls, and navigation data - all produced from the taxonomy.
* AI-assisted classification and vocabulary-gap detection
* Reviewable taxonomy migration files with preconditions and dry runs
* Repository-wide checks before taxonomy changes are applied

## The problem

On large docs-as-code portals, taxonomy problems often start with reasonable local decisions.

A writer could not find an exact term, so they added another one. Similar concepts end up with slightly different names. Metadata conventions change, but older documents keep previous values. Navigation configuration and authoring tools sometimes develop their own versions of the same information.

None of those changes are especially serious on its own. The difficulty comes later, when the same concepts have to be searched, renamed, deprecated, or changed across many documents.

I wanted the repository to enforce more of the metadata model itself instead of relying on contributors to remember conventions.

### Moving the rules into the repository

I wanted:

* Stable IDs for canonical concepts
* One authoritative list of valid values
* Authoring tools generated from that list
* Automatic detection of invalid metadata
* Reproducible generated files
* A way to detect generated-state drift
* Explicit handling of renames, corrections, replacements, and deprecations
* A way to see the effect of a taxonomy change before applying it

That required treating the taxonomy as repository state, not just editorial guidance.

### Where AI fits

Some taxonomy decisions need judgement.

An AI model can make a useful first pass at questions such as:

* What is this document about?
* Which existing terms apply?
* Is an important concept missing from the current vocabulary?

I did not want the model deciding whether repository state was valid or whether a new term should become canonical.

That responsibility stays with the repository tooling. It validates IDs and cardinality, checks migration preconditions, identifies documents that need metadata updates, and controls changes to the canonical taxonomy.

AI produces proposals. A person reviews them. Repository tooling applies these approved changes.

## Scaling the model

The portfolio itself is small. The design comes from problems that become noticeable in a much larger documentation estate.

As the number of documents, repositories, contributors, product versions, and automated consumers increases, metadata changes become harder to treat as isolated edits.

The system therefore has a few deliberate constraints:

* **One source of truth.** Docusaurus, the authoring environment, and navigation use generated views of the same taxonomy.
* **Repository validation.** Validation and migration checks
* **Preflight checks.** A taxonomy change can be checked against the corpus before any files are updated.
* **Explicit migration files** Vocabulary changes have their own reviewable records.
* **Deprecation rather than automatic deletion.** Old IDs and replacement relationships remain visible.
* **Human review for semantic changes.** The LLM can suggest a change but cannot add or redefine canonical vocabulary on its own.
* **Controlled authoring.** Writers select governed values using provided tooling without needing to know how the taxonomy is implemented.

## Outcome

The portfolio now has one canonical vocabulary and one supported path for changing it.

Canonical IDs and repository validation reduce vocabulary drift. Docusaurus tags, editor configuration, and navigation are generated from the same source instead of being maintained separately. Taxonomy corrections are handled through migrations with dry runs and preconditions. The tooling also identifies which documents would require metadata updates before a migration is applied.

AI-assisted classification is separate from the tooling that changes the canonical taxonomy. It can suggest a classification or a new term, but it cannot make either canonical.

The migration workflow has already caught issues outside the change being tested. During one taxonomy correction, I prepared updates to five technology terms and checked the migration against all 26 portfolio documents. The first preflight run found stale derived state in a recently added document. I corrected that first, reran the checks, and only then applied the taxonomy migration.

Because the portfolio is small, I can show the implementation in [full](../implementation-details/taxonomy.md). These controls are based on problems I have already seen become difficult to manage in a much larger docs-as-code environment.
