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
resolution is automatically applied. Matching is limited to AI-origin findings.

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

## Not implemented

- Semantic matching of differently worded criticisms, even when the document
  is unchanged. These still become separate issues unless a future matching
  mechanism links them.
- Fuzzy matching of edited quotations, Git rename detection, or matching across
  different files or categories.
- Automatic assessment of whether changed context invalidates a dismissal.
- A UI for confirming ambiguous matches or merging persistent records.
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
