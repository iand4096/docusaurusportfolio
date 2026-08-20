# Taxonomy v2 — improved extraction and AI classification

This package keeps the v2 taxonomy schema but strengthens both initial corpus
extraction and ongoing DeepSeek metadata classification.

The design goal is a broad, reviewable technology vocabulary suitable for a
long technical-writing/programming career, while keeping deterministic
repository state authoritative.

## What changed in this package

Compared with the earlier v2 scripts:

- Technology extraction now runs **once per document** with a high-recall prompt;
- content type, audience and topic discovery remains batch-based;
- a second **technology coverage-audit pass** asks DeepSeek specifically what
  the first extractor missed;
- deterministic coverage warnings flag likely omissions of foundational terms
  such as Python, Java, JavaScript, C++, C#, Node.js and OpenAPI;
- consolidation is explicitly forbidden from treating foundational technologies
  as duplicates of their frameworks/libraries/tools;
- validated foundational candidates are deterministically restored if the
  consolidation pass still drops them;
- company/employer/client/entity exclusion is enforced both in prompts and in
  deterministic validation;
- the technology-kind catalogue now also includes `data-format` and
  `payment-technology`;
- `taxonomy_ai.py` resolves existing terms by ID, label or alias;
- duplicate AI proposals for terms that already exist are folded into ordinary
  metadata instead of failing the document;
- AI evidence hints are verified against the real source document and exact
  source excerpts are recovered deterministically;
- a bad taxonomy proposal is dropped with a warning instead of invalidating the
  whole document classification;
- unknown optional AI metadata values are dropped with a warning;
- over-cardinality AI metadata is trimmed deterministically;
- accepted new proposals are added to the proposing document's metadata even if
  the model forgot to repeat the new ID in its metadata array;
- only document-level classification failures block `--apply`.

## Canonical model

Front matter remains simple:

```yaml
technologies:
  - python
  - openapi
  - docusaurus
```

The taxonomy carries the subclass information:

```yaml
technology_kinds:
  programming-language:
    label: Programming language
    description: A general-purpose or domain-specific programming language.

  data-format:
    label: Data format
    description: A structured data serialisation or interchange format.

  payment-technology:
    label: Payment technology
    description: A payment-specific technical product or platform.

  documentation-platform:
    label: Documentation platform
    description: A documentation site generator or publishing platform.

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

The limits above apply to **one document**, not to the number of technologies
allowed in the career taxonomy. The taxonomy can contain hundreds of approved
technology terms if the corpus supports them.

## Recommended workflow: regenerate the initial taxonomy

Because the earlier extractor omitted foundational terms before they ever
reached consolidation, regenerate rather than manually patching the old output.

Copy these package files over the corresponding files in your repository, then
run from the repository root:

```powershell
python -m pip install -r requirements-doc-review.txt
$env:DEEPSEEK_API_KEY = "your-key"

python scripts/generate_taxonomy.py --force
```

The generator now performs:

```text
Markdown/MDX corpus
      |
      +--> batch content-type/audience/topic discovery
      |
      +--> per-document HIGH-RECALL technology extraction
      |
      +--> repository technology coverage audit
      |
      +--> deterministic foundational coverage warnings
      |
      +--> repository-wide consolidation
      |
      +--> deterministic foundational-term restoration
      |
      +--> schema + semantic validation
      |
      +--> taxonomy/taxonomy.yml
      +--> taxonomy/taxonomy-generation.json
      +--> docs/tags.yml
      +--> .frontmatter/generated-taxonomy.json
```

The default model split is:

- extraction: `deepseek-v4-flash`;
- coverage audit: `deepseek-v4-flash`;
- consolidation: `deepseek-v4-pro`.

Because technology extraction is now per-document, the bootstrap run makes more
API calls than the earlier batch-only generator. For 29 Markdown/MDX files,
expect roughly 29 technology-extraction calls plus the non-technology batch
call(s), coverage-audit batch call(s), and one consolidation call. This is an
intentional one-off bootstrap trade-off for better recall.

You can override all three with the backward-compatible `--model` option:

```powershell
python scripts/generate_taxonomy.py --force --model deepseek-v4-pro
```

Or override them independently:

```powershell
python scripts/generate_taxonomy.py --force `
  --extraction-model deepseek-v4-flash `
  --coverage-model deepseek-v4-flash `
  --consolidation-model deepseek-v4-pro
```

Review `taxonomy/taxonomy-generation.json`, especially:

```text
per_document_technology_counts
coverage_audit_additions
coverage_warnings
rejected_technology_candidates
restored_foundational_candidates
```

A non-empty `coverage_warnings` array means a known foundational technology
appeared in the corpus but still did not resolve to an extracted candidate and
should be reviewed before adopting the taxonomy.

## Ongoing DeepSeek metadata classification

After reviewing the regenerated taxonomy:

```powershell
python scripts/taxonomy_ai.py --all
```

The classifier is now intentionally tolerant of normal LLM variation.

For example, if the taxonomy contains:

```yaml
openapi-specification:
  label: OpenAPI
  aliases:
    - OpenAPI specification
```

and the model returns:

```json
"technologies": ["openapi"]
```

`taxonomy_ai.py` resolves the value to the canonical repository ID rather than
rejecting the whole document.

Likewise, if DeepSeek proposes `masterpass` as a new term but `masterpass`
already exists, the proposal is folded into the existing term and reported as a
normalisation note instead of a failure.

### Evidence handling

New proposals use AI `evidence_hints`, but the stored/report evidence is always
recovered from the real Markdown/MDX source. The script tries, in order:

1. exact evidence-hint matches;
2. case-insensitive exact matches;
3. label/alias matches;
4. deterministic token-overlap matching against source sentences/lines.

If no source evidence can be verified, **that proposal alone is dropped**. The
rest of the document classification remains usable.

### Review before applying

Review:

```text
taxonomy/taxonomy-ai-suggestions.md
taxonomy/taxonomy-ai-suggestions.json
```

Then:

```powershell
python scripts/taxonomy_ai.py --all --apply

git diff
```

`--apply` is refused only when one or more documents had no usable
classification. Proposal-level warnings are advisory and do not block the
successful documents.

## Existing v1 taxonomy migration

If you need to upgrade a version-1 taxonomy instead of regenerating it:

```powershell
python scripts/upgrade_taxonomy.py
```

Review:

```text
taxonomy/taxonomy-v2-upgrade.md
taxonomy/taxonomy-v2-upgrade.json
```

Then:

```powershell
python scripts/upgrade_taxonomy.py --apply
```

The upgrade script uses the same controlled technology-kind catalogue, marks
organisation/entity terms as deprecated rather than silently deleting them,
and regenerates the derived Docusaurus/Front Matter files.

## Deterministic checks

```powershell
# Taxonomy + all docs
python scripts/taxonomy.py check --all

# Taxonomy/schema/generated-file state only
python scripts/taxonomy.py check --taxonomy-only

# Changed docs
python scripts/taxonomy.py check --changed-base origin/main

# Regenerate derived Docusaurus/Front Matter files
python scripts/taxonomy.py generate

# Synchronise Docusaurus tags from governed metadata
python scripts/taxonomy.py sync --all

# Group technologies by subclass and flag suspicious organisation-like terms
python scripts/taxonomy.py audit-technologies
```

These commands never call an LLM and are suitable for blocking CI.

## Technology subclasses

The seed catalogue includes:

- programming language;
- shell and scripting;
- markup/content language;
- data format;
- framework;
- library;
- runtime;
- standard/specification;
- protocol;
- API tool;
- payment technology;
- documentation platform;
- authoring tool;
- documentation QA tool;
- CMS/wiki;
- developer platform/tool;
- IDE/editor;
- testing/debugging;
- network analysis;
- CI/CD and automation;
- version control;
- containers/orchestration;
- infrastructure;
- operating system/firmware;
- server/networking;
- cloud/hosting;
- diagramming/visualisation;
- modelling methodology;
- architecture style;
- technical technique;
- security/cryptography;
- AI/ML tool;
- data/analysis tool;
- design/graphics;
- engineering design;
- collaboration/project tooling;
- general software platform.

The catalogue is broad by design. It gives the technology history useful
structure without collapsing 25 years of experience into a short flat list.
