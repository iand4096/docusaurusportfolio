---
title: QA finding identity and feedback continuity
description: Understand how QA preserves finding identities, review decisions and recurrence evidence.
type:
  - implementation-guide
audiences:
  - developers
  - technical-writers
topics:
  - docs-as-code
  - documentation-engineering
technologies:
  - python
lifecycle:
  - current
tags:
  - docs-as-code
  - documentation-engineering
  - python
---

See the [documentation QA architecture](qa-architecture.mdx) for the pipeline and maintainer guides.

## Finding matching and revalidation

A later AI review can rephrase a criticism or cite a different passage. The pipeline first looks for an exact claim match to recover its history, then checks whether the earlier decision still applies to the current source and proposed fix.

The implementation is in [`scripts/qa_feedback.py`](../../scripts/qa_feedback.py) and
[`scripts/ai_docs_review.py`](../../scripts/ai_docs_review.py). See the [QA identifiers table](qa-key-concepts.md#qa-identifiers) for the report, occurrence, feedback and precedent IDs.

Older saved reports and copied challenge commands keep working. Legacy feedback record IDs are derived from the original record key and stored when the record is next updated. Challenge and resolution commands record the occurrence they act on. Report generation and render-only refreshes read the registry without modifying it.

### Exact matching

Matching compares the repository-relative file path, check source, category,
quoted passage and criticism. Text comparisons ignore capitalisation and
whitespace differences. This is exact normalised matching, not semantic matching.
Line numbers, severity and confidence do not identify the underlying claim.

The matcher searches the feedback records rather than relying only on the new
report's `issue_id`. More than one matching record is marked ambiguous; no
resolution is automatically applied. Matching is limited to AI-origin findings. Exact matching remains the only automatic path;
reworded claims can now be proposed and explicitly linked as described below.

| Case | Implemented behaviour |
| --- | --- |
| Same document bytes, same normalised claim and suggestion | Reuse feedback and its resolution. |
| New Git commit, same document bytes and claim | New occurrence; same persistent issue and applicable feedback. |
| Document changed elsewhere; passage and criticism unchanged | Link previous history; mark **Needs revalidation**. |
| Passage moved within the same file; passage and criticism unchanged | Link previous history; changed document hash requires revalidation. |
| Same claim but proposed fix changed | Keep the link; require revalidation even if the source bytes are unchanged. |
| Different criticism about the same quotation | Do not automatically link. |
| Different category, edited quotation or renamed file | Do not automatically link. |
| Duplicate matching feedback records | Report ambiguity; do not automatically dismiss the occurrence. |

### Revalidation after a source change

A changed document keeps the earlier rebuttal and evidence visible. The previous decision and revised wording do not apply automatically to the new occurrence. Even an unchanged quotation can depend on context elsewhere in the file. An explicit resolution verifies the new source hash and quotation before binding the decision to that revision.

See [Read a QA report and act on findings](qa-read-report.md#record-a-decision) for the revalidation and refresh commands.

## Semantic recurrence retrieval and applicability

Recurrence detection has two stages. It proposes up to **15** previous challenges
from the same file, then uses DeepSeek to assess the complaints and prior decisions.
An exact claim with changed source or a changed suggestion enters this comparison
path too. It remains **Needs revalidation** until a human takes action.

### Candidate retrieval

The shortlist combines normalised quotation overlap with local embeddings of the
criticism and suggested correction. It uses the pinned
`sentence-transformers/all-MiniLM-L6-v2` model at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, on CPU with safetensors and remote model
code disabled. Normalised embeddings are cached by model revision and complaint
text under `.qa/feedback-index/embeddings.json`.

Candidates qualify through quotation similarity of at least `0.7` (including
containment), or complaint cosine similarity of at least `0.4`. The latter cutoff
retains a rewritten MkDocs pilot quotation in the labelled smoke set; it is a
retrieval heuristic, not a probability of equivalence. Ranking weights complaint
similarity at `0.75` and quotation similarity at `0.25`. Exact-but-stale matches
have priority. Shared quotations may still retrieve different complaints; the
second stage must distinguish them.

The comparison path populates embeddings. Render-only refreshes read cached
vectors or retain valid source-bound proposals embedded in saved reports; they
never load or download a model. If embedding generation fails, quotation fallback
remains available and the failure is reported. Neither path changes CI eligibility.

### Comparison and immutable precedents

A full AI QA run compares candidates. To compare an existing report without
rerunning its documentation checks:

```bash
python3 scripts/ai_docs_review.py compare \
  --report .qa/ai-doc-review.json \
  --report-dir .qa/recurrence-review
```

`compare` requires `DEEPSEEK_API_KEY`. The model receives complete hash-verified
old and new sources, allegations, prior rebuttals, adjudications and immutable
precedents. It returns three independent classifications:

| Field | Values |
| --- | --- |
| `complaint_relationship` | `equivalent`, `narrower`, `broader`, `different`, `uncertain` |
| `prior_decision_applicability` | `applicable`, `not_applicable`, `uncertain` |
| `document_change_impact` | `unchanged`, `not_material`, `material`, `uncertain` |

The code validates controlled values and exact supporting quotations. Applicability
requires source evidence from both versions. Different complaints, new requirements,
material changes, uncertain evidence, legacy bindings or conflicting decisions
cannot qualify for reuse. The legacy `verdict` display field is retained for report
compatibility; it describes complaint relationship, not decision applicability.

Comparisons are disposable cached recommendations, bound to policy, model,
source revisions, immutable precedents and discussion history. They never change
feedback or resolve a finding. HTML, Markdown and JSON expose all classifications.

New findings include a hash-verified source snapshot in `document_revision`.
This snapshot lets reviewers reconstruct the original uncommitted source after the working file changes.
New challenge and resolution decisions append content-addressed `qap-…` precedents
containing the exact finding, rebuttal, decision, rationale, evidence and revision.
They are never updated when `latest_finding` changes. Legacy history is preserved
but cannot be retroactively represented as a verified original claim binding.

### Human confirmation and decision reuse

The existing `link` command confirms or rejects a recurrence relationship without
inheriting decisions. It continues to preserve the previous record. For exact-but-
stale findings use revalidation instead of creating a second record for the claim.

When an immutable precedent is applicable and no conflicts are found, reports offer
an explicit human revalidation command:

```bash
python3 scripts/ai_docs_review.py reuse \
  --report .qa/recurrence-review/ai-doc-review.json \
  --issue qa-NEW_FINDING \
  --previous qa-PREVIOUS_RECORD \
  --proposal TOKEN_COPIED_FROM_REPORT \
  --reason "I checked both versions; the earlier evidence and decision still apply."
```

This command requires no AI key. It verifies the current comparison, proposal,
source hashes, precedent and decision history before writing an audit event.
Any history change invalidates the approval token. For an exact stale claim it
revalidates the existing record; for a reworded claim it creates a separate record
sharing the persistent identity. Original precedents remain unchanged. Source or
suggestion changes after approval require revalidation again.

A prior human resolution can be reused only through this explicit action. Reusing
an AI withdrawal alone does **not** dismiss the finding or remove CI eligibility.
Material changes, conflicting decisions and unresolved applicability require a
fresh `resolve --report ...` or `challenge`, not a reuse command.

Run `render` after recording a link, resolution or reuse, and commit
`qa/feedback.json` to share it. Rendering and comparison do not write feedback.
Published reports may contain complete source snapshots of reviewed documents;
only review content appropriate for publication when publishing QA reports.

### Dependencies and evaluation

CI installs a wheel-only, SHA-256-locked CPU runtime from
`requirements-doc-review-linux-py312.lock` (Linux x86_64, Python 3.12). Portable
direct dependency declarations are in `requirements-qa-recurrence.txt` and included
by `requirements-doc-review.txt`. The lock includes transitive dependencies and
uses the official PyTorch CPU wheel URL. Update manifests and lock together.
The ML stack adds installation and model-download cost; the deployed search API
has its own separate dependency manifest.

Run deterministic recurrence and feedback tests without API calls:

```bash
python3 -m unittest discover -s scripts/tests -p 'test_qa*.py'
```

Run the real embedding retrieval smoke evaluation on labelled variants of the
repository's historical feedback records:

```bash
python3 scripts/evaluate_qa_recurrence.py
```

The first run downloads the pinned model; cached runs can use `HF_HUB_OFFLINE=1`.
The fixture identifies synthetic paraphrases explicitly. It reports candidate
ranks and cosine scores, not measured DeepSeek adjudication accuracy. Distinct
complaints may still enter the shortlist through quotation overlap. Regression
tests separately exercise the comparison contract and decision-reuse safeguards
with controlled model responses.

## Not implemented

- Automatic semantic merging or dismissal. AI comparisons are recommendations only.
- Git rename detection or candidate matching across different files.
- Browser-side writes or merging existing feedback records. Reports copy local CLI
  commands; ambiguous exact matches still require manual investigation.
- Reliable distinction between two identical quotations in different parts of
  the same file. The existing exact-finding deduplication remains in place.
- Automatic closure when a finding disappears. Absence in a nondeterministic
  review is not evidence that the issue was fixed; the feedback record remains.
- A full history of every occurrence in every QA run. Only challenged or
  explicitly resolved occurrences are added to the feedback registry; reports
  carry their own occurrence IDs.
- Independent resolution state for every historical revision. After a record
  is revalidated against newer source, an older report may require revalidation
  again. Historical decisions remain available as audit evidence.
- Automatic Git commits, feedback write-back from CI, report archival across
  deployments, or publishing feedback views. The render command produces local
  artefacts; it does not deploy them.

## Verification

Regression tests cover unchanged content in a new commit, changed document
hashes, moved passages, normalisation, changed suggestions, reworded criticisms,
renamed files, ambiguous records, and manual revalidation without AI calls.
Report tests cover decision display, source binding, snapshots, CI policy and
rendering without an API key.

```bash
python3 -m unittest discover -s scripts/tests -v
```
