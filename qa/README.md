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

## Reworded complaints and category changes

For AI findings without an exact feedback match, report generation proposes up to
five previous challenges in the same file. Candidate retrieval uses normalised
quotation similarity (at least 0.7), including substantial containment. Categories
and criticism wording do not have to match. Similarity only shortlists candidates;
it does not establish that two allegations are equivalent.

A full AI QA run compares candidates using DeepSeek. For an existing saved report,
request comparisons without rerunning its documentation checks:

```bash
python3 scripts/ai_docs_review.py compare \
  --report .qa/local-review-2026-11-13/ai-doc-review.json \
  --report-dir .qa/recurrence-review
```

`compare` requires `DEEPSEEK_API_KEY`. The comparison receives the old and new
allegations, complete hash-verified source documents, and the previous rebuttal
and adjudication. It returns `same_complaint`, `different_complaint`, or `uncertain`,
with exact evidence checked against the supplied allegations and sources. Partial
overlap is uncertain; a shared quotation is insufficient. Responses are cached in
`.qa/feedback-index/comparisons.json`, keyed by comparison policy, model, findings,
source revisions and prior discussion. This disposable cache is not a vector
database and is not authoritative feedback. Failed requests and unverifiable
responses appear separately in the report and never dismiss a finding.

The HTML report shows previous/current quotations and allegations, prior rebuttals
and decisions, whether source hashes changed, and any AI comparison. It provides
copy buttons for confirm/reject commands; edit the placeholder reason before
running them. Markdown and JSON retain the comparison information too.

```bash
python3 scripts/ai_docs_review.py link \
  --report .qa/recurrence-review/ai-doc-review.json \
  --issue qa-NEW_FINDING \
  --previous qa-PREVIOUS_RECORD \
  --decision confirmed \
  --reason "Both allegations concern the same missing subject."
```

Use `--decision rejected` to reject a proposed relationship. Leave unresolved by
taking no action. These human commands require no AI key. They verify the source,
proposal and previous record, then append an audit event in `qa/feedback.json`.
A rejection suppresses that particular proposal while its finding snapshots remain
unchanged; changed source or proposed fixes can warrant fresh review.

Confirmation creates a separate record sharing the previous persistent issue ID,
with a snapshot of earlier discussion and decisions. It does **not** inherit the
previous human dismissal, AI withdrawal or revised wording, and it does not alter
the old feedback record. The new finding remains active, labelled **Linked —
awaiting human resolution**. Use the existing `resolve --report ...` command to
record a separate human decision, or `challenge` for fresh AI adjudication. Later
source or suggestion changes retain the existing revalidation safeguards.

Run `render` on the saved report after recording a link or resolution, and commit
`qa/feedback.json` to share the decisions. Render performs no AI calls. Report
creation and AI comparison do not write to the feedback registry. Challenge records
absent from the current findings are still not displayed as an independent archive.

## Not implemented

- Automatic semantic merging or dismissal. AI comparisons are recommendations only.
- Git rename detection or candidate matching across different files.
- Automatic assessment of whether changed context invalidates a dismissal.
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
