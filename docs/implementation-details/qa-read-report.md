---
title: Read a QA report and act on findings
description: Interpret findings and checker errors, record decisions and refresh a saved report.
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

## Walk through a report

Use a report from a [local run](qa-run-review.md) or open the [published report](pathname:///qa/). When there are five or fewer active findings, the HTML report links to **See example QA report with errors**. Rendering also writes `qa-example.html` beside the main report. The example contains synthetic findings and a simulated error. Its feedback actions are disabled.

| What you see | What to do |
| --- | --- |
| An active finding | Filter by source or severity, then follow the file and line link. Read the quoted text and evidence before deciding whether to fix the document or challenge an AI finding. A broken local link is an example you can fix and verify with a fresh run. |
| A checker error | Read the **API/check errors** section and the check's log. For example, an external-link service timeout means the check could not complete. Fix the underlying failure and rerun the check. |
| **Needs revalidation** | Compare the current source and proposed fix with the earlier decision. If it still applies, record a resolution against the new report. If you want a new AI assessment, challenge the new occurrence. |

Severity describes the impact of a finding. Confidence describes how certain the reviewer is about it. The gate summary shows which findings count. A withdrawn AI finding appears in history and can still count toward CI until a human dismisses it. See [gate eligibility](qa-reports-and-ci.mdx#gate-eligibility-and-verification).

## Record a decision

In a real report, **Challenge AI** copies a command for that saved finding. Run it locally with `DEEPSEEK_API_KEY` configured to record a rebuttal and AI adjudication. Use `resolve` to record a human decision. Pass the new report when revalidating a finding after a source change.

```bash
python3 scripts/ai_docs_review.py resolve   --report path/to/new-report.json   --issue qa-REPLACE_WITH_FINDING_ID   --decision dismissed   --reason "I checked the changed document and the earlier rebuttal still applies."
```

Commit `qa/feedback.json` to share recorded decisions with CI and other checkouts. See the [CLI reference](qa-cli-reference.md#saved-reports-and-feedback-commands) for command options and [finding identity and recurrence](qa-feedback.md) for how prior decisions are matched and reused.

## Refresh or rerun

Refresh a saved report when only the feedback has changed. The CLI writes HTML, JSON and Markdown plus `original-report.json` in a separate directory. It preserves the original review date and adds a feedback timestamp.

```bash
python3 scripts/ai_docs_review.py render   --report path/to/saved-report.json   --report-dir .qa/feedback-preview
```

Run a fresh review after editing the source, changing the checks or resolving a checker failure. A refresh applies current feedback to the saved findings without invoking checkers or calling AI. It does not publish the refreshed files.
