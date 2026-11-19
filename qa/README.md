# QA finding identity and feedback continuity

## Problem

AI reviews are not deterministic. A later run can describe the same concern
using different words, quote a different passage, assign another category, or
omit the finding. The original finding ID hashes the file, source, category,
quoted passage and criticism. A wording change can therefore create a new ID.

Whole-document hashes introduce a separate problem: changing an unrelated
paragraph used to hide previous feedback even when the quoted passage and
criticism were unchanged. Linking a recurring issue and deciding whether an
earlier dismissal still applies are separate operations.

## Implemented

The implementation is in `scripts/qa_feedback.py` and
`scripts/ai_docs_review.py`.

### Three identities

| Field | Purpose |
| --- | --- |
| `issue_id` (`qa-…`) | Existing report reference. Old saved reports and copied challenge commands remain valid. |
| `persistent_issue_id` (`qai-…`) | Underlying feedback record, shared by exact recurring claims. Legacy IDs are derived from the original record key and stored when that record is next updated. |
| `occurrence_id` (`qao-…`) | Exact claim at a document-content hash and Git commit. A new commit can produce a new occurrence even when the document bytes are identical. |

New reports add these fields without rewriting the original saved report.
Challenge and resolution commands record the occurrences they act on. Normal
report generation and render-only refreshes read feedback without modifying the
feedback registry.

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

### Revalidation and reporting

For a changed document, the earlier rebuttal and evidence remain visible, but
the prior dismissal, revised wording and AI decision are not applied to the new
occurrence. The finding remains active and retains its normal CI eligibility.
An unchanged quotation does not prove that changes elsewhere are irrelevant:
the criticism may depend on missing context elsewhere in the document.

A human can review the new context and explicitly revalidate a decision without
another AI call:

```bash
python3 scripts/ai_docs_review.py resolve \
  --report path/to/new-report.json \
  --issue qa-REPLACE_WITH_NEW_REPORT_FINDING_ID \
  --decision dismissed \
  --reason "I checked the changed document; the earlier rebuttal still applies."
```

This verifies the report's source hash and quotation, finds the exact previous
claim, and records a human resolution for that document revision. It does not
turn the previous AI verdict into a verdict about the new source. Alternatively,
challenge the new occurrence with a fresh rebuttal and API call.

Refresh the displayed view afterwards:

```bash
python3 scripts/ai_docs_review.py render \
  --report path/to/new-report.json \
  --report-dir .qa/new-report-feedback
```

Rendering makes no review or AI calls. HTML, Markdown and JSON include current
decisions, discussion, evidence, persistent IDs, occurrence IDs, and a
revalidation count. Revised findings preserve the original criticism. Withdrawn
and human-dismissed findings appear in history. An AI withdrawal alone does not
remove CI eligibility; human dismissal is required.

AI findings are capped at medium severity in code, including when a saved
report is rendered again. `model_reported_severity` retains the model's original
severity for audit. Deterministic tools can still report high-severity defects.
Findings that explicitly describe themselves as not being defects are treated
as low-severity improvements. Heading-capitalisation-only checks belong to Vale.

The render output retains an original-report snapshot and separate review and
feedback timestamps. It refuses to overwrite the input report. Commit
`qa/feedback.json` to share decisions with future checkouts and CI runs.

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

New findings include a hash-verified source snapshot in `document_revision` so
uncommitted source remains reconstructable after the working file changes.
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

## Evidence-backed review policy

New AI reviews require a concrete reader impact, a rule or structural reason,
and exact supporting quotations bound to supplied files. Repetition and
consistency findings require two distinct passages. Source validation checks the
quotations; it does not prove the model's interpretation.

Checks with valid proposals make an additional verification request before
reporting findings. This increases API usage and latency. The verifier rejects
unsupported diagnoses, useful repetition and corrections that add facts; medium
severity requires separate justification. Invalid verification responses are check
errors, rather than successful clean reviews. Verification remains model judgment,
not an independent proof of correctness.

Reports expose supporting evidence and relate findings quoting the same passage
at the same location. Related findings keep separate identities and decisions;
this conservative grouping does not semantically merge different allegations.
Existing saved reports and feedback remain readable. Rendering does not rerun
verification; a fresh review is needed to evaluate the new policy.

Regression tests cover evidence validation, verification response handling and
preservation of finding identities. They use controlled model responses; live
precision and recall improvements still require a labelled model evaluation.

## Caching unchanged AI reviews

Successful AI checks, including zero findings and completed verification, are
cached locally in `.qa/review-cache/`. A cache hit skips both DeepSeek requests.
Keys include the complete source text and paths, check, scope, model, API endpoint,
policy and an implementation fingerprint computed once per run. The fingerprint
covers the AI review package and its shared source, policy, check and cache code.
Prompt or review-code changes invalidate results. Report template changes keep
cached results reusable. Site-wide checks depend on their complete supplied
document set. Failed checks are not cached. Corrupt entries are recomputed, and unavailable
cache writes do not fail a review. Logs show hits and misses.

Use `--no-review-cache` to bypass reads and writes for a deliberately fresh run.
The model's rolling alias may change without changing its name; use this flag or
remove the local cache when intentionally reassessing unchanged content with the
provider's latest model. There is no automatic expiry.

Only completed findings are cached, before revision decoration and feedback.
Current source revisions, human feedback, recurrence handling, deterministic
checks, report timestamps and CI thresholds are applied on every fresh run.

Both QA and deployment workflows restore `.qa/review-cache/` with
`actions/cache/restore@v4` and save it with `actions/cache/save@v4`, including after
QA threshold failures. Each run uses a new immutable snapshot key; a common prefix
restores the most recent accessible snapshot. GitHub stores these snapshots in
repository Actions cache storage, subject to its normal branch scope and eviction.
PR caches are scoped to the PR merge ref and do not seed main's deployment cache;
PR runs can restore accessible default-branch caches. Concurrent runs can save
snapshots missing each other's new entries, causing extra calls on later misses.

The cache directory is ignored by Git and excluded from the explicit report and
Pages artifact paths. It contains review text, not API keys. GitHub Actions caches
are not private secret storage; use this workflow only for documentation suitable
for the repository's cache access permissions.

## Example report for quiet QA runs

When there are five or fewer active findings, the HTML report offers “See example
QA report with errors”. Rendering also writes `qa-example.html` beside the real
report. The separate example illustrates every source, severity filtering and a
simulated check failure. Its banner explicitly identifies synthetic findings;
source links and feedback actions are disabled. Example data never enters real
JSON/Markdown exports, feedback records, caches or CI decisions. Generating the
example makes no API calls. Deployment publishes it alongside the real report,
and Actions artifacts include it when present.

## Substantive AI defects versus optional editorial review

The default `--filter full` preserves every deterministic checker and runs AI
language, structure and site-consistency checks for substantive defects only.
Portfolio presentation, repetition and Mermaid opportunities require an optional
preset. `--filter editorial` requests all page-level AI editorial checks plus
Vale and LTeX; individual `portfolio`, `repetition` and `mermaid` presets remain.

The defect verifier first considers the strongest reasonable reading, then must
identify an actual failure, its consequence and why that reading cannot resolve
it. Ambiguity requires two distinct interpretations with materially different
outcomes. Missing verification fields are check errors, not silent approval.
Optional improvements cannot enter a default report even if a generator returns
them. The existing CI eligibility rules remain in force.

The two withdrawn findings about coordinated verbs and display labels are prompt
examples, not automatic exclusions or inherited human decisions. Earlier feedback
remains source-bound. Policy v7 and cache keys distinguish defect-only from
editorial runs; old cached findings are not reused under the new review policy.
Rendering a saved report preserves its original findings and policy instead of
retroactively filtering it. No finding minimum or maximum is imposed.

Regression tests check routing, response validation and retention of concrete
failures with controlled model responses. These tests do not establish live
precision or recall; model behaviour still needs labelled evaluation.
