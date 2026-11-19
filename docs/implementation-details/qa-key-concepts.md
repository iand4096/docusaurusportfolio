---
title: Documentation QA key concepts
description: How checks, evidence, feedback, caching and CI decisions fit together.
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

## Scope, presets and modes

**Scope** determines which files enter a review. The CLI starts with the portfolio's documentation paths and can include additional files on request. A **preset** selects which checks are available for the run. A **mode** selects whether to check each document on its own, compare documents, or do both. Selected batch tools such as Vale receive the full file list. [CLI reference](qa-cli-reference.md#review-scope-and-check-presets)

## Deterministic checks and AI review

Deterministic checks apply explicit rules. For example, the local link checker looks up a link target, and Vale checks configured terminology and prose rules. AI review handles questions that require reading context, such as whether two instructions contradict each other. In a site-wide review, DeepSeek receives the selected documents together with paths, genre labels and line numbers so it can compare related pages. [AI review guide](qa-ai-review.mdx)

## Check adapters and shared results

The runner builds one plan and shares the same loaded text between page and site-wide checks. External tools use adapters that validate their setup, run the executable and translate its diagnostics into the same finding format. The shared result carries findings and check errors separately, so a failed tool can be reported alongside results from the other checks. [Add a documentation checker](qa-add-checker.mdx)

The execution wrapper turns a tool or parser exception into a reportable check error.

```python source=scripts/qa_checks/base.py#qa-check-result
```

## Evidence and verification

Source validation checks that the AI's supporting quotations appear in the supplied text. A separate verification request asks DeepSeek whether those quotations support the criticism. [Evidence-backed review policy](qa-ai-review.mdx#evidence-backed-review-policy)

The response validator accepts an explicit empty list and raises an error for malformed output.

```python source=scripts/qa_ai/validation.py#qa-response-validation
```

## Findings, errors and the CI gate

A **finding** describes a problem or improvement a check identified in the documentation. A **check error** means the check could not complete, for example because a tool was missing. An invalid model response is also a check error. A completed check can return zero findings.

Every checker uses the same core finding fields. The example below shows a broken local link. `original` is the source text, `message` explains the problem, and `suggestion` describes a possible fix. Severity describes impact, while confidence describes how certain the check is.

```json
{
  "file": "docs/example.md",
  "line": 14,
  "source": "static",
  "type": "defect",
  "category": "links",
  "severity": "high",
  "confidence": "high",
  "original": "[Setup guide](missing-guide.md)",
  "message": "The local link points to a file that does not exist.",
  "suggestion": "Correct the path or restore the missing guide."
}
```

The **CI gate** counts eligible findings by severity and counts check errors separately. Deterministic findings keep their assigned severity. An AI finding can count when it is a high-confidence defect and has no human dismissal. Reports can still be published when the gate fails, so readers can see what triggered it. [Gate eligibility and publication](qa-reports-and-ci.mdx#gate-eligibility-and-verification)

The gate uses an explicit eligibility rule before applying severity thresholds.

```python source=scripts/qa_policy.py#qa-ci-eligibility
```

## Finding identity and human decisions

A feedback decision applies to the source and proposed fix it was made against. Changes to either can require revalidation, while earlier discussion stays available. When a claim is reworded, recurrence retrieval uses semantic similarity and quotation overlap to shortlist earlier findings for comparison. [How candidate retrieval works](qa-feedback.md#candidate-retrieval) · [Exact matching and revalidation](qa-feedback.md#exact-matching)

### QA identifiers

<div className="qa-identifiers-table">

| Field | Prefix | What it identifies | Python fragment |
| --- | --- | --- | --- |
| `issue_id` | `qa-…` | A specific criticism of a source passage. Use it for `challenge` and `resolve`. Moving the same passage to a different line leaves the ID intact. | `return 'qa-' + fingerprint` |
| `occurrence_id` | `qao-…` | That criticism at a particular document content hash and Git commit. A new commit can produce a new occurrence even when the document bytes are unchanged. | `hashlib.sha256(value.encode())` hashes the claim and revision. |
| `persistent_issue_id` | `qai-…` | The feedback record that connects linked occurrences to an ongoing discussion and decision history. | `record.get('persistent_issue_id')` retrieves an existing ID. For a legacy record, the script hashes the record key. |
| `precedent_id` | `qap-…` | An immutable snapshot of an earlier claim, source revision and decision that a human can consider for reuse. | `json.dumps(snapshot, sort_keys=True)` serialises the snapshot before hashing. |

</div>

The report stores the hash of the document bytes in `document_revision.content_sha256`. This captures local edits as well as committed text.

## Cache hits and saved-report refreshes

A fresh review can reuse completed AI checks from the cache and still runs the selected deterministic checks and applies current feedback. A **saved-report refresh** applies feedback to existing findings without rerunning the checks. [AI cache behaviour](qa-ai-review.mdx#caching-unchanged-ai-reviews) · [Refresh or rerun](qa-read-report.md#refresh-or-rerun)

## Structured reports and publication

HTML, JSON and Markdown are generated from one report model. The saved JSON has five top-level fields.

| Field | What it contains |
| --- | --- |
| `metadata` | When the review ran, which checks it selected, and the review mode, preset and model. |
| `ci` | The gate decision, eligible counts, thresholds and reasons for failure. |
| `summary` | Counts for readers, including active findings, feedback history and findings that need revalidation. |
| `issues` | Individual findings with source locations, evidence and feedback when available. |
| `errors` | Checker failures, including the check name, location and error message. |

The JSON also serves as input for feedback commands and saved-report refreshes. During deployment, the workflow verifies that the reports came from the current run and publishes them under commit-specific filenames. The latest-report link points readers to that version. [Reports and CI](qa-reports-and-ci.mdx#workflow-thresholds-and-publication)

For the execution paths and which modules own each step, see the [QA architecture](qa-architecture.mdx).
