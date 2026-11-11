# Taxonomy governance

This directory holds the portfolio's canonical controlled vocabulary, validation schemas and reviewed vocabulary migrations. It supports document classification, Docusaurus tags, VS Code Front Matter choices, faceted navigation and the knowledge API's search filters.

The [implementation guide](../docs/implementation-details/taxonomy.md) explains the architecture and engineering decisions. This README covers routine maintenance from the repository root.

## Authority and files

[Taxonomy YAML](taxonomy.yml) is the source of truth. Document metadata uses canonical IDs; generated files are projections, not separate vocabularies. AI proposes classifications and vocabulary additions, while humans review them. The supported way to change the existing canonical vocabulary is a reviewed manifest applied by `taxonomy.py migrate`.

| File or tool | Purpose |
| --- | --- |
| [taxonomy.yml](taxonomy.yml) | Canonical dimensions, terms, technology kinds, cardinality and governance policy. |
| [schema.json](schema.json) | Taxonomy structure validation. |
| [taxonomy-migration.schema.json](taxonomy-migration.schema.json) | Migration manifest contract. |
| [migrations/](migrations/) | Versioned, reviewable vocabulary changes. |
| [taxonomy.py](../scripts/taxonomy.py) | Deterministic checks, tag sync, projection generation, audits and migrations. |
| [taxonomy_ai.py](../scripts/taxonomy_ai.py) | DeepSeek classification and advisory vocabulary proposals; applies saved reviewed document metadata separately. |
| [frontmatter.config.cjs](../frontmatter.config.cjs) | Loads generated editor choices and registers review, draft-migration and apply actions. |

The three generated projections are:

- [docs/tags.yml](../docs/tags.yml): Docusaurus tag definitions.
- [.frontmatter/generated-taxonomy.json](../.frontmatter/generated-taxonomy.json): Front Matter taxonomy choices and content-type fields.
- [src/generated/taxonomy-navigation.json](../src/generated/taxonomy-navigation.json): navigation terms and document metadata for the portfolio's browsing interface.

Do not edit these projections independently. Validation compares them with the expected output from the taxonomy and document metadata.

## Prerequisites

Use Git and Python 3.12, matching the taxonomy CI workflow. Install the Python dependencies in a virtual environment. For example, in Bash:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-doc-review.txt
```

On Windows, activate the environment with `.venv\Scripts\Activate.ps1` in PowerShell. The commands below assume the environment is active and the working directory is the repository root.

Only fresh AI classification requires `DEEPSEEK_API_KEY` in the process environment and network access to DeepSeek. Deterministic maintenance and applying a saved review do not call an LLM or require a provider key. The Front Matter editor actions also require VS Code, the Front Matter extension and `python` available to the editor; the review action uses the `code` command to open its saved report.

## Document metadata

The current dimensions map to these front-matter fields:

| Dimension | Metadata field |
| --- | --- |
| Content type | `type` |
| Audience | `audiences` |
| Topic | `topics` |
| Technology | `technologies` |
| Lifecycle | `lifecycle` |

All governed fields use YAML lists of canonical IDs, including single-selection fields. Required fields, permitted counts and content-type-specific limits come from `taxonomy.yml`; do not infer them from the number of values in an example. Technology terms also have a controlled `kind` in the taxonomy, rather than an extra field on each document.

The validator rejects unknown or deprecated term IDs, duplicate values and invalid cardinality. The document's `tags` field is derived from dimensions configured with `docusaurus_tags`; use `sync` after editing governed metadata instead of maintaining tags separately.

## Routine maintenance

After editing document metadata using existing terms:

```bash
python scripts/taxonomy.py sync --all
python scripts/taxonomy.py check --all
git diff
```

`sync` writes derived tags in the selected documents and regenerates all three repository projections. It does not classify prose or repair invalid vocabulary selections. Correct invalid metadata before retrying.

| Command | Behaviour |
| --- | --- |
| `python scripts/taxonomy.py check --all` | Read-only validation of taxonomy structure and semantics, generated state and every document under `docs/`. |
| `python scripts/taxonomy.py check docs/case-studies/TaxonomyGovernance.md` | Checks generated state and the selected document's metadata. |
| `python scripts/taxonomy.py check --changed-base origin/main` | Checks documents changed between the Git merge base and HEAD; a canonical taxonomy change expands document validation to the full corpus. Fetch the base reference first. |
| `python scripts/taxonomy.py check --taxonomy-only` | Checks the taxonomy and generated state without the document metadata validation pass. Navigation projection construction still reads documents. |
| `python scripts/taxonomy.py sync --all` | Writes document tags and regenerates projections. Accepts explicit paths or `--changed-base` for document selection. |
| `python scripts/taxonomy.py generate` | Regenerates projections without synchronising document tags. |
| `python scripts/taxonomy.py audit-technologies` | Reports active technology kinds and heuristic warnings about organisation-like descriptions. |
| `python scripts/taxonomy.py audit-unused` | Reports active terms with no direct document references; defaults to AI-managed dimensions. |
| `python scripts/taxonomy.py audit-unused --dimension technologies` | Restricts the reference audit to the named dimension; repeat `--dimension` for multiple dimensions. |
| `python scripts/taxonomy.py migrate status` | Lists migration manifests and canonical taxonomy health. It does not track an applied-migration ledger. |

Audits are read-only. Both audit commands accept `--strict` to return exit code 1 when their findings are present. An unused term is a review candidate, not an instruction to delete it. Corpus-wide selection covers `docs/**/*.md` and `docs/**/*.mdx`, not blog posts or repository READMEs.

## AI review and saved application

Set `DEEPSEEK_API_KEY` in the environment, then request a review for a document or the full documentation corpus:

```bash
python scripts/taxonomy_ai.py docs/case-studies/TaxonomyGovernance.md
# Alternatively, review every document:
python scripts/taxonomy_ai.py --all
```

These are alternative review scopes. By default each run writes the same report paths, so preserve a review you intend to apply before starting another run:

```text
taxonomy/taxonomy-ai-suggestions.md
taxonomy/taxonomy-ai-suggestions.json
```

Use `--output` and `--json-output` to choose separate paths. `--changed-base` is also available for reviewing committed changes, and `--model` overrides the classifier's configured default. A classification request sends the document text and taxonomy context to DeepSeek.

Review the Markdown report and its accompanying JSON. Classification may suggest existing active IDs, missing title or description values, and genuinely missing vocabulary with source evidence. Proposals remain advisory. Review-only runs do not change document metadata or the canonical taxonomy.

After approving the saved classification, apply that exact JSON artefact:

```bash
python scripts/taxonomy_ai.py --apply-from taxonomy/taxonomy-ai-suggestions.json
python scripts/taxonomy.py check --all
git diff
```

`--apply-from` makes no model call. It validates the saved classification against the current taxonomy, writes document metadata, synchronises tags and regenerates projections. It fills missing or blank titles/descriptions without replacing usable existing values. It can create absent YAML front matter; malformed existing front matter fails.

If any selected ID is not an active canonical term, adopt the required vocabulary through a reviewed migration first, then apply the same saved review. Artefacts containing document-level classification errors cannot be applied. `--apply-from` cannot be combined with document-selection arguments, `--model` or `--apply`.

Targeted `--apply` remains a compatibility path that performs a fresh classification and immediate application. Prefer saved review followed by `--apply-from`. The combination `--all --apply` is rejected.

## Vocabulary changes and migrations

Create and review a YAML manifest under `taxonomy/migrations/` using the [migration schema](taxonomy-migration.schema.json) and existing manifests as structural references. Existing manifests describe historical changes; do not replay them as routine maintenance.

Schema-v2 manifests record a change type (`vocabulary-expansion`, `vocabulary-contraction`, `taxonomy-correction`, `term-replacement` or `policy-change`) and a trigger (`content-driven`, `taxonomy-review` or `policy-driven`). They carry governance provenance and preconditions. Update operations can assert expected current values, and manifests may also assert the taxonomy version or hash.

Preview first, inspect the proposed operations and document impact, then apply the approved manifest. Replace the example filename below with your new manifest:

```bash
python scripts/taxonomy.py migrate preview taxonomy/migrations/YYYY-MM-DD-description.yml
python scripts/taxonomy.py migrate apply taxonomy/migrations/YYYY-MM-DD-description.yml
```

`preview` writes nothing. Application behaviour depends on the operations:

- **Add-only changes:** validate and update only the canonical taxonomy. They do not scan unrelated documents or regenerate projections, so vocabulary can be adopted before fixing a document that needs the new terms.
- **Other changes:** validate the candidate taxonomy and document impact, perform required ID replacements, regenerate projections and run final validation. The migration engine restores captured files if application fails.
- **Vocabulary contraction:** rejects deprecation while documents still reference the affected terms. Review zero-reference terms and prefer an explicit deprecation migration over deletion.

After an add-only migration, apply any saved document classification or repair affected metadata, then finish with:

```bash
python scripts/taxonomy.py sync --all
python scripts/taxonomy.py generate
python scripts/taxonomy.py check --all
git diff
```

`sync` already generates projections; the explicit `generate` command can also be run independently when only projections need refreshing. Commit the reviewed manifest, taxonomy, affected metadata and generated changes together.

## VS Code Front Matter workflow

The actions registered in `frontmatter.config.cjs` operate on the active document:

1. **Review metadata with DeepSeek** runs [frontmatter_taxonomy.py](../scripts/frontmatter_taxonomy.py) and saves a Markdown/JSON review pair.
2. Review the suggestions. If new terms are needed, **Generate draft taxonomy migration** runs [frontmatter_taxonomy_migration.py](../scripts/frontmatter_taxonomy_migration.py) to create a schema-validated expansion manifest. Review it, then use `migrate preview` and `migrate apply`; generating the draft does not adopt terms.
3. **Apply reviewed taxonomy metadata** runs [frontmatter_taxonomy_apply.py](../scripts/frontmatter_taxonomy_apply.py), which applies the saved JSON through `--apply-from` without another model call.
4. Run `check --all` and review the Git diff.

Review files mirror the document's path under `docs/`. For example:

```text
docs/case-studies/TaxonomyGovernance.md
.frontmatter/taxonomy-reviews/case-studies/TaxonomyGovernance.review.md
.frontmatter/taxonomy-reviews/case-studies/TaxonomyGovernance.review.json
```

Front Matter is an authoring interface. Its generic vocabulary-editing controls are not the supported path for changing the canonical taxonomy.

## CI and current limitations

The [taxonomy-validation workflow](../.github/workflows/taxonomy-validation.yml) runs on pull requests to `main`. It installs Python dependencies and executes `check --changed-base` against the pull request's base SHA, with full Git history available. This validates generated state as well as selected document metadata without a provider key.

Saved AI reviews are checked against the current taxonomy and cardinality rules, but do not carry content/taxonomy fingerprints that fully detect stale reviews. Re-review when the source or classification context changes. Document application is not a repository-wide transaction; inspect the working-tree diff after an error. The rollback behaviour described above belongs to the migration engine.

[generate_taxonomy.py](../scripts/generate_taxonomy.py) is initial discovery tooling, and [upgrade_taxonomy.py](../scripts/upgrade_taxonomy.py) supports the historical v1-to-v2 transition. Neither is part of routine maintenance. Do not regenerate the canonical vocabulary with `--force` as a normal update step.
