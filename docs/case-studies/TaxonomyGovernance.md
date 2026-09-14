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

I designed and implemented a governed taxonomy for a Docusaurus documentation site. The project combines information architecture, docs-as-code automation, editor integration, deterministic repository validation, and AI-assisted metadata review.

The aim was to make governed taxonomy metadata practical for authors without allowing convenience tooling or an LLM to become an independent taxonomy authority. Authors can select controlled taxonomy values in VS Code, run AI metadata reviews on individual documents or the wider corpus, and propose controlled-vocabulary changes when genuinely new concepts appear. Controlled-vocabulary changes remain explicit, reviewable repository operations.

## Problem

Documentation metadata supports several related documentation functions:

* **Search and discovery** — filtering, browsing, ranking, and findability.

* **Navigation generation** — menus, browse pages, indexes, and landing pages.

* **Vocabulary control** — preferred terms and approved metadata values.

* **Lifecycle management** — draft, current, deprecated, archived, and review states.

* **Audience targeting** — content for particular roles, groups, or experience levels.

* **Related-content generation** — connections by topic, product, task, technology, or audience.

* **Publishing automation** — controlling whether, where, or how content is published based on its metadata.

* **Content governance** — ownership, review dates, applicability, and maintenance responsibilities.

* **Analytics and gap analysis** — coverage measurement and identification of missing content.

* **AI and semantic retrieval** — structured context for semantic search, RAG, and knowledge graphs.

Free-form tags are easy to introduce but difficult to govern consistently as a documentation set grows. For this portfolio, I wanted metadata that:

* uses stable canonical term IDs rather than inconsistent free-text labels;

* supports content type, audience, topic, technology, and lifecycle dimensions;

* works consistently across Markdown and MDX;

* drives Docusaurus tags and faceted navigation;

* remains convenient to edit through VS Code Front Matter;

* uses AI where semantic judgement is useful without granting the LLM repository authority;

* can evolve safely when terms are added, corrected, replaced, or deprecated.

## Authority model

Authority is divided by concern.

[`taxonomy/taxonomy.yml`](../../taxonomy/taxonomy.yml) defines the canonical taxonomy, including its controlled vocabulary and taxonomy policy. `taxonomy_ai.py` can perform AI metadata review, including semantic classification and proposal generation, but fresh review runs do not modify the canonical taxonomy. Reviewers approve controlled-vocabulary changes through migration manifests, and `taxonomy.py` applies the approved manifests.

Generated files are projections of the canonical taxonomy and validated document metadata. Generated files are not independent sources of taxonomy data.

Concern

Authoritative mechanism

Canonical taxonomy: controlled vocabulary and policy

taxonomy/taxonomy.yml

AI metadata review and semantic classification

taxonomy_ai.py

Approval or rejection of AI-generated proposals

Human review

Document metadata changes proposed by AI

Review JSON applied through taxonomy_ai.py --apply-from

Controlled-vocabulary change contract

taxonomy/taxonomy-migration.schema.json

Approved migration manifests

taxonomy/migrations/*.yml

Applying canonical taxonomy changes

taxonomy.py migrate

Structural and repository validation

taxonomy.py

Final repository review

Git diff / pull-request review

The architecture enforces that separation:

```mermaid id="t6cb4k"

flowchart TD

    AI["`taxonomy_ai.py

    AI metadata review

    and migration drafting`"]

    REVIEW["`Human review

    Review package`"]

    APPLY["`taxonomy_ai.py --apply-from

    Apply reviewed document metadata`"]

    MIGRATION["`taxonomy/migrations/*.yml

    Approved migration manifest`"]

    ENGINE["`taxonomy.py migrate

    Deterministic migration

    and validation`"]

    DOCS["`docs/**/*.md[x]

    Governed document metadata`"]

    TAXONOMY["`taxonomy/taxonomy.yml

    Canonical taxonomy`"]

    DERIVED["`Derived repository state`"]

    AI --> REVIEW

    REVIEW -->|"approved review JSON"| APPLY

    APPLY --> DOCS

    REVIEW -->|"approved migration manifest"| MIGRATION

    MIGRATION -->|"dry-run / --apply"| ENGINE

    ENGINE --> TAXONOMY

    TAXONOMY --> DERIVED

    DOCS --> DERIVED

    AI -.->|"read only"| TAXONOMY

```

There is deliberately no direct write path from `taxonomy_ai.py` to `taxonomy.yml`.

## Repository components and derived repository state

### Steady-state components

Component

Operational role

taxonomy/taxonomy.yml

Defines the controlled vocabulary and taxonomy policy.

scripts/taxonomy.py

Validates taxonomy and document metadata, synchronises derived document tags, regenerates projections, performs audits, and applies migrations.

scripts/taxonomy_ai.py

Performs AI metadata review, including semantic classification, and produces document-metadata proposals and draft migration manifests for review.

taxonomy/taxonomy-migration.schema.json

Defines and validates the migration-manifest structure.

taxonomy/migrations/*.yml

Stores approved, auditable migration manifests.

frontmatter.config.cjs

Loads the generated Front Matter projection and registers repository actions in the frontmatter UI.

scripts/frontmatter_taxonomy.py

Creates a persistent single-document AI metadata review from VS Code Front Matter.

scripts/frontmatter_taxonomy_apply.py

Applies saved review JSON from a single-document review through taxonomy_ai.py --apply-from.

Because `taxonomy.py` does not call an LLM, CI can use its checks as deterministic gates.

### Generated projections

The canonical taxonomy and validated document metadata produce three main generated projections:

Generated file

Purpose

docs/tags.yml

Docusaurus tag definitions.

.frontmatter/generated-taxonomy.json

Allowed metadata values and content-type field definitions for VS Code Front Matter.

src/generated/taxonomy-navigation.json

Faceted navigation data derived from taxonomy terms and document metadata.

`taxonomy.py` checks generated projections against the output expected from the canonical taxonomy and validated document metadata. It detects manual edits or stale projections as repository drift rather than accepting them as independent taxonomy changes.

The generated navigation projection drives the site's [browse page](pathname:///browse/).

## VS Code Front Matter authoring workflow

Front Matter CMS provides the editor-facing content-management layer for Markdown and MDX files. In this project it is a controlled authoring interface: authors can work with structured fields and repository actions without manually remembering canonical term IDs or YAML structures.

1. **Structured metadata editing.** Front Matter presents governed front-matter fields as editor controls.

2. **Controlled taxonomy choices.** `taxonomy.py generate` creates `.frontmatter/generated-taxonomy.json`. `frontmatter.config.cjs` loads that file into `frontMatter.taxonomy.customTaxonomy` and `frontMatter.taxonomy.contentTypes`, so the editor reflects the current controlled vocabulary and content-type-specific constraints.

3. **Single-document AI metadata review.** A Front Matter action launches `frontmatter_taxonomy.py` for the active document. The wrapper invokes `taxonomy_ai.py` in review-only mode and stores the resulting document-specific review package in `.frontmatter/taxonomy-reviews/`.

4. **Reviewed apply.** A second action launches `frontmatter_taxonomy_apply.py`. It delegates to the saved-review application path and ultimately invokes `taxonomy_ai.py --apply-from <saved-review.json>`. It does not perform a fresh AI metadata review request.

```javascript id="6bbfcr"

"frontMatter.custom.scripts": [

  {

    "id": "suggest-taxonomy-deepseek",

    "title": "Review metadata with DeepSeek",

    "script": "./scripts/frontmatter_taxonomy.py",

    "command": "python",

    "type": "content"

  },

  {

    "id": "apply-taxonomy-review",

    "title": "Apply reviewed document metadata",

    "script": "./scripts/frontmatter_taxonomy_apply.py",

    "command": "python",

    "type": "content"

  }

]

```

For a document such as:

```text id="o2lw3p"

docs/case-studies/taxonomy.md

```

the review wrapper persists:

```mermaid id="v5qt0e"

flowchart TD

ROOT[".frontmatter/taxonomy-reviews/"]

CASES["case-studies/"]

REPORT["taxonomy.review.md"]

JSON["taxonomy.review.json"]

ROOT --> CASES

CASES --> REPORT

CASES --> JSON

```

The review report provides the human-readable review surface. The review JSON contains the exact machine-readable review that the apply operation consumes.

Front Matter can expose taxonomy-editing functionality of its own, but those editor-side operations are not the supported path for changing the controlled vocabulary. Controlled-vocabulary changes use the [governed migration workflow](#governed-taxonomy-migrations), which provides preconditions, corpus validation, and a reviewable Git diff.

### Single-document workflow

```mermaid id="0dt7x9"

flowchart TD

    DOC["`Open Markdown/MDX

    document in VS Code`"]

    REVIEW_ACTION["`Front Matter:

    Review metadata with DeepSeek`"]

    WRAPPER["`frontmatter_taxonomy.py`"]

    AI["`taxonomy_ai.py

    AI metadata review

    Review only`"]

    ARTEFACTS["`Review package

    .review.md + .review.json`"]

    HUMAN["`Human review`"]

    PROPOSAL{"`Requires new

    controlled-vocabulary term?`"}

    MIGRATION["`Reviewed

    vocabulary-expansion

    migration manifest`"]

    ENGINE["`taxonomy.py migrate`"]

    APPLY_ACTION["`Front Matter:

    Apply reviewed document metadata`"]

    APPLY_WRAPPER["`frontmatter_taxonomy_apply.py`"]

    APPLY_FROM["`taxonomy_ai.py --apply-from`"]

    UPDATED["`Updated document metadata`"]

    DOC --> REVIEW_ACTION

    REVIEW_ACTION --> WRAPPER

    WRAPPER --> AI

    AI --> ARTEFACTS

    ARTEFACTS --> HUMAN

    HUMAN --> PROPOSAL

    PROPOSAL -->|"yes"| MIGRATION

    MIGRATION --> ENGINE

    ENGINE --> APPLY_ACTION

    PROPOSAL -->|"no"| APPLY_ACTION

    APPLY_ACTION --> APPLY_WRAPPER

    APPLY_WRAPPER --> APPLY_FROM

    APPLY_FROM --> UPDATED

```

If the review references a proposed term that is not yet in the controlled vocabulary, the document cannot adopt it until a reviewer approves the migration manifest and `taxonomy.py` applies it.

## Operations

### Routine taxonomy maintenance

```powershell id="xl7xyf"

python scripts/taxonomy.py check --all

python scripts/taxonomy.py sync --all

python scripts/taxonomy.py generate

python scripts/taxonomy.py audit-technologies

python scripts/taxonomy.py audit-unused

```

Command

Purpose

check

Validate taxonomy structure, governed document metadata, and derived repository state.

sync

Synchronise derived document tags with governed taxonomy dimensions.

generate

Regenerate generated projections from the canonical taxonomy and validated document metadata.

audit-technologies

Identify questionable technology terms or technology-kind assignments.

audit-unused

Report active terms with no direct references in the document corpus.

migrate

Process an approved migration manifest in dry-run mode or apply it.

`audit-unused` is intentionally read-only. It identifies contraction candidates; it does not decide that an unused term should be removed or deprecated. See [Content-driven contraction](#content-driven-contraction).

### AI-assisted metadata review

The AI layer can perform an AI metadata review of an individual document or the complete document set:

```powershell id="hmkbda"

python scripts/taxonomy_ai.py docs/example.md

python scripts/taxonomy_ai.py --all

```

* classify content against active taxonomy terms;

* suggest missing title or description metadata;

* identify concepts that are not represented in the controlled vocabulary;

* produce a review package containing a Markdown review report and machine-readable review JSON;

* draft a migration manifest when a reusable concept appears to require controlled-vocabulary expansion.

Fresh AI metadata reviews are review-only.

After human review, `taxonomy_ai.py --apply-from` applies document metadata from the saved review JSON:

```powershell id="88d2hl"

python scripts/taxonomy_ai.py --apply-from taxonomy/taxonomy-ai-suggestions.json

```

`--apply-from` is the document-metadata write path in `taxonomy_ai.py`; it applies the saved review JSON instead of asking the model to perform a new AI metadata review.

The application fails if reviewed metadata references a term that is not in the controlled vocabulary. Controlled-vocabulary adoption is handled separately through the migration process below.

### Governed taxonomy migrations

Reviewers record canonical taxonomy changes as declarative YAML migration manifests, and `taxonomy.py` validates them against `taxonomy/taxonomy-migration.schema.json`.

Version 2 migration manifests record both the **intent** of the migration and the **trigger** that caused it.

Supported change types are:

* `vocabulary-expansion`

* `vocabulary-contraction`

* `taxonomy-correction`

* `term-replacement`

* `policy-change`

Supported triggers are:

* `content-driven`

* `taxonomy-review`

* `policy-driven`

Change type describes what changes; trigger describes why.

`taxonomy_ai.py` drafts migration manifests for genuinely missing reusable terms with a `vocabulary-expansion` change type and a `content-driven` trigger. `taxonomy_ai.py` validates each draft migration manifest before writing it; a reviewer approves the manifest before application.

#### Migration preconditions

Migrations can declare assumptions about the repository state they expect to modify.

A migration-level precondition can constrain the taxonomy version:

```yaml id="mpjhix"

preconditions:

  taxonomy_version: 2

```

Individual updates can also use `expect` to state the current value that must still be present:

```yaml id="hcnc5t"

json:

  expect:

    kind: markup-content-language

  set:

    kind: data-format

```

These checks provide stale-state protection. If the canonical taxonomy no longer matches the state the reviewer approved, `taxonomy.py` fails the migration rather than overwriting the newer value.

Preconditions therefore make the migration manifest both a change description and an assertion about the state to which that change is safe to apply.

#### Content-driven expansion

A new document may introduce a reusable concept missing from the controlled vocabulary.

In that situation:

```mermaid id="9r9sa1"

flowchart TD

CONTENT["new or changed content"]

AI_REVIEW["AI metadata review identifies a vocabulary gap"]

DRAFT["draft vocabulary-expansion migration manifest"]

HUMAN["human review"]

PREFLIGHT["migration preflight / dry-run mode"]

APPLY["approved migration application"]

CONTENT --> AI_REVIEW

AI_REVIEW --> DRAFT

DRAFT --> HUMAN

HUMAN --> PREFLIGHT

PREFLIGHT --> APPLY

```

An AI metadata review can identify and describe the gap, but adding the term requires an approved migration manifest.

#### Content-driven contraction

Deleting or reclassifying content can leave an active term with no direct document references. `taxonomy.py audit-unused` reports those terms as candidates for review.

`taxonomy.py` does not remove unused terms automatically. A reviewer decides whether to keep, replace, or deprecate the term.

Where contraction is appropriate, the system prefers **deprecation to deletion** so that canonical term IDs, provenance, Git history, and replacement relationships remain available.

`taxonomy.py` rejects contraction while documents still reference the target term.

#### Taxonomy correction

The controlled vocabulary can require correction even when the document corpus has not introduced or removed a concept.

A taxonomy review might identify an incorrect:

* classification;

* description;

* parent relationship;

* alias;

* technology kind;

* or other governed property.

Reviewers record those changes as `taxonomy-correction` migrations rather than as content-driven expansion or contraction.

#### Migration preflight

`taxonomy.py migrate` defaults to dry-run mode, in which it performs migration preflight without writing changes; `--apply` writes the changes:

```powershell id="3mp91m"

python scripts/taxonomy.py migrate `

  taxonomy/migrations/2026-09-01-correct-technology-kinds.yml

```

For the technology-kind correction described below, a successful preflight in dry-run mode produced:

```text id="gd6sgg"

migration: 2026-09-01-correct-technology-kinds

description: Correct technology kinds that conflict with the controlled kind definitions.

operations: update=5

documents scanned: 26

documents requiring deterministic rewrite: 0

dry-run passed; no files changed

use --apply to write the migration

```

`documents requiring deterministic rewrite` identifies documents whose front matter would need to change because of a canonical term ID operation.

Before writing repository state, the migration engine:

1. validates the migration manifest.

2. checks its preconditions.

3. constructs the candidate taxonomy.

4. validates that candidate taxonomy.

5. scans the document corpus for affected metadata.

6. determines any deterministic document rewrites required by canonical term ID changes.

```powershell id="3c03p3"

python scripts/taxonomy.py migrate `

  taxonomy/migrations/2026-09-01-correct-technology-kinds.yml `

  --apply

```

Reviewers can then inspect the resulting repository changes as a Git diff before merging them.

## Example: correcting technology kinds

During a taxonomy review, I found five technology terms whose assigned kinds did not match the controlled definitions.

The taxonomy assigned JSON, YAML, and XML to `markup-content-language`, but the controlled model defines them as `data-format`. It assigned Apple Pay and Google Pay to `software-platform`, although the controlled model provides `payment-technology` for those technologies.

I represented the correction as an approved migration manifest:

```yaml id="rzgd57"

schema_version: 2

id: 2026-09-01-correct-technology-kinds

change_type: taxonomy-correction

trigger: taxonomy-review

description: Correct technology kinds that conflict with the controlled kind definitions.

governance:

  date: "2026-09-01"

  source: migration

  reason: >-

    Align existing technology terms with the taxonomy's controlled kind definitions.

preconditions:

  taxonomy_version: 2

changes:

  technologies:

    update:

      json:

        expect:

          kind: markup-content-language

        set:

          kind: data-format

      yaml:

        expect:

          kind: markup-content-language

        set:

          kind: data-format

      xml:

        expect:

          kind: markup-content-language

        set:

          kind: data-format

      apple-pay:

        expect:

          kind: software-platform

        set:

          kind: payment-technology

      google-pay:

        expect:

          kind: software-platform

        set:

          kind: payment-technology

```

The `expect` clauses ensure that `taxonomy.py` applies the correction only to the taxonomy state the reviewer approved.

## Case study: preflight caught repository drift

The first preflight in dry-run mode for the technology-kind migration reported that one document required an update.

A full repository check showed that the newly added taxonomy case-study document already contained governed taxonomy metadata but had an empty derived document `tags` field. The generated navigation projection was also stale.

I repaired the derived repository state before continuing:

```powershell id="na87ha"

python scripts/taxonomy.py sync docs/case-studies/taxonomy.md

python scripts/taxonomy.py check --all

```

After the repair, the preflight in dry-run mode scanned all 26 documents and required no rewrites.

Preflight exposed unrelated repository drift and prevented stale derived repository state from entering the migration.

## Evolution of the tooling

The implementation evolved from one-off discovery and conversion scripts into the current governed maintenance model:

```mermaid id="avn081"

flowchart TD

GENERATE["generate_taxonomy.py"]

DISCOVERY["initial AI-assisted taxonomy discovery"]

UPGRADE["upgrade_taxonomy.py"]

CONVERSION["one-off taxonomy v1 → v2 conversion"]

CURRENT["taxonomy.py + taxonomy_ai.py"]

MAINTENANCE["ongoing controlled taxonomy maintenance"]

GENERATE --> DISCOVERY

DISCOVERY --> UPGRADE

UPGRADE --> CONVERSION

CONVERSION --> CURRENT

CURRENT --> MAINTENANCE

```

`generate_taxonomy.py` was useful for initial taxonomy discovery, and `upgrade_taxonomy.py` handled the historical version transition. Neither is part of the current workflow.

The current architecture concentrates repository authority in the maintained taxonomy and migration tooling instead of retaining multiple historical paths capable of shaping the canonical taxonomy.

## Outcomes, trade-offs, and next steps

### Measured outcome

In the technology-kind correction, the migration engine checked five controlled-vocabulary updates against all 26 portfolio documents before any repository state was changed.

The migration required no governed taxonomy metadata rewrites because it changed governed properties without changing the canonical term IDs.

The failed preflight exposed stale derived repository state before `taxonomy.py` applied the migration. Together, those results verified that the migration engine could check controlled-vocabulary changes against both the canonical taxonomy and the document corpus before writing them.

For authors, the same implementation provides controlled taxonomy choices and persistent review packages inside VS Code without requiring the editor integration to manage the controlled vocabulary directly.

### Trade-offs

The design deliberately favours explicit review over automatic taxonomy evolution.

That creates additional steps compared with automatically accepting AI suggestions or deleting unused terms. In return, reviewers can inspect AI review reports, proposed document-metadata changes, and controlled-vocabulary migration manifests separately, and can reproduce and audit repository changes through version control.

### Next steps

* Adding content and taxonomy fingerprints to review packages so `--apply-from` can reject stale reviews more precisely;

* Adding a local content-addressed cache for unchanged AI metadata review requests;

* Retiring or archiving the historical bootstrap and v1-to-v2 migration scripts;

* Continuing taxonomy review where the existing technology-kind model does not provide an unambiguous classification.

The main improvement is that components now own actions explicitly: reviewers **record/inspect**, `taxonomy.py` **checks/applies/rejects**, `taxonomy_ai.py` **reviews/proposes/applies document metadata**, and Front Matter **presents** controls.