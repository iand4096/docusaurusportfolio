# Taxonomy v2 — typed technologies

This package upgrades the portfolio taxonomy model so a large career technology vocabulary remains useful rather than becoming one flat list.

## What changed

Taxonomy v2 adds:

- a controlled `technology_kinds` catalogue;
- a required `kind` on every **active** technology term;
- explicit DeepSeek rules that exclude companies, employers, clients, customers and corporate entities from technologies;
- support for technical methods such as modelling methodologies, architecture styles and technical techniques;
- content-type-specific cardinality limits, so the overall taxonomy can contain hundreds of technologies while individual pages remain selective;
- a deterministic technology audit command;
- a migration script for an existing taxonomy v1.

Front matter stays simple. Documents still reference technology IDs:

```yaml
technologies:
  - python
  - openapi
  - docusaurus
```

The taxonomy contains the classification detail:

```yaml
technology_kinds:
  programming-language:
    label: Programming language
    description: A general-purpose or domain-specific programming language.

  documentation-platform:
    label: Documentation platform
    description: A documentation site generator or platform used to publish technical content.

# ...

dimensions:
  technologies:
    metadata_field: technologies
    min: 0
    max: 50
    constraints_by_type:
      case-study:
        min: 0
        max: 15
      skill:
        min: 0
        max: 20
      tool:
        min: 0
        max: 40

    terms:
      python:
        label: Python
        description: A general-purpose programming language.
        kind: programming-language
        governance:
          status: active
          introduced: '2026-08-14'
          source: initial-taxonomy
          review: annual
```

The global `max` applies to broad/other page types. `constraints_by_type` overrides it for known content types. This is deliberately different from limiting the total number of terms in the taxonomy.

## Existing taxonomy: recommended migration

If you already have `taxonomy/taxonomy.yml` version 1, copy these files into your repository first:

```text
scripts/taxonomy.py
scripts/taxonomy_ai.py
scripts/upgrade_taxonomy.py
taxonomy/schema.json
requirements-doc-review.txt
```

From PowerShell at the repository root:

```powershell
python -m pip install -r requirements-doc-review.txt
$env:DEEPSEEK_API_KEY = "your-key"

# 1. Review how every existing technology will be typed.
python scripts/upgrade_taxonomy.py
```

Review:

```text
taxonomy/taxonomy-v2-upgrade.md
taxonomy/taxonomy-v2-upgrade.json
```

The report deliberately separates genuine technologies/methods from organisations.

When satisfied:

```powershell
# 2. Apply the taxonomy-only migration.
python scripts/upgrade_taxonomy.py --apply

git diff
```

`--apply`:

- changes `version: 1` to `version: 2`;
- adds the `technology_kinds` catalogue;
- adds `kind` to genuine technology terms;
- marks organisation/entity terms as deprecated rather than silently deleting them;
- adds content-type-specific technology limits when matching content types exist;
- regenerates `docs/tags.yml` and `.frontmatter/generated-taxonomy.json`;
- does **not** rewrite document metadata.

Documents that still reference newly deprecated company/entity terms will then be intentionally invalid. Use the ordinary AI classifier to propose corrected document metadata:

```powershell
# 3. Review reclassification against the cleaned v2 taxonomy.
python scripts/taxonomy_ai.py --all

# 4. After reviewing the report, apply to the working tree.
python scripts/taxonomy_ai.py --all --apply

git diff

# 5. Deterministic gate.
python scripts/taxonomy.py check --all
```

## New portfolio / regenerate from the corpus

For a fresh taxonomy:

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
python scripts/generate_taxonomy.py
```

The generator uses two passes: batch evidence extraction followed by repository-wide consolidation. It deliberately tells DeepSeek that a long-career portfolio may have a large technology vocabulary and that one-document technologies can be retained when materially demonstrated.

It writes:

```text
taxonomy/taxonomy.yml
taxonomy/taxonomy-generation.json
docs/tags.yml
.frontmatter/generated-taxonomy.json
```

Review those files before applying AI-generated front matter.

## Ongoing metadata and taxonomy proposals

```powershell
# One document
python scripts/taxonomy_ai.py docs/tools/OpenAPIandAPITools.md

# Changed documents
python scripts/taxonomy_ai.py --changed-base origin/main

# Whole corpus
python scripts/taxonomy_ai.py --all
```

DeepSeek may propose a new technology term, but every proposal must include an approved `kind`:

```yaml
new-tool:
  label: New Tool
  description: A developer tool used to inspect API behaviour.
  kind: api-tool
```

A company/entity-like technology proposal is rejected before it can be applied.

## Deterministic checks

```powershell
# Taxonomy + all docs
python scripts/taxonomy.py check --all

# Only taxonomy/schema/generated-file state
python scripts/taxonomy.py check --taxonomy-only

# Changed docs in CI/local PR workflow
python scripts/taxonomy.py check --changed-base origin/main

# Regenerate Docusaurus/Front Matter derived files
python scripts/taxonomy.py generate

# Synchronise Docusaurus front-matter tags
python scripts/taxonomy.py sync --all

# Summarise technologies by subclass and flag organisation-like descriptions
python scripts/taxonomy.py audit-technologies

# Optional strict audit exit code
python scripts/taxonomy.py audit-technologies --strict
```

## Technology subclasses

The seed catalogue covers categories such as:

- programming languages;
- shell/scripting;
- markup/content languages;
- frameworks and libraries;
- runtimes;
- standards/specifications and protocols;
- API tools;
- documentation platforms and authoring tools;
- documentation QA tools;
- CMS/wiki systems;
- developer platforms/tools and IDEs;
- testing/debugging and network analysis;
- CI/CD, version control, containers and infrastructure;
- operating systems/firmware and server/networking technologies;
- cloud/hosting platforms;
- diagramming/visualisation;
- modelling methodologies;
- architecture styles;
- technical techniques;
- security/cryptography;
- AI/ML tools;
- data/analysis tools;
- design/graphics and engineering-design tools;
- collaboration/project tools;
- general software platforms.

The catalogue is broad by design. It gives deterministic structure without erasing the breadth expected from a long technical career.
