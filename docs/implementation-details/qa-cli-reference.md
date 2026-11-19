---
title: Documentation QA CLI reference
description: Command-line options for running QA, rendering reports and managing feedback.
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

Run `python3 scripts/ai_docs_review.py [command] [options]` from the repository root. Omit the command to start a fresh review. Use `-h` or `--help` to display the options available in your checkout. Relative paths are interpreted from the repository root.

## Review scope and check presets

| Option | Behaviour |
| --- | --- |
| `--mode MODE` | `per-page` checks each document on its own. `site-wide` runs checks that compare documents, such as looking for conflicting terminology or guidance. `all` runs both kinds of checks. Batch tools selected by the preset, such as Vale or Remark, receive the full file list in every mode. |
| `--filter PRESET` | Chooses which checks to run. A preset is a named set of checks. For example, `--filter accessibility` runs only accessibility checks, while `--filter full` runs the deterministic checks and includes AI review for substantive defects. The list below covers every preset. |
| `--include-file PATH` | Adds a repository Markdown or MDX file to the default scope. Repeat for multiple files. `FAPI/` is excluded. |
| `--no-review-cache` | Bypasses reads and writes to the completed AI review cache for this run. |

Without an interactive terminal, or with `--ci`, the review defaults to `per-page` and `full`. In an interactive terminal, omitted mode and preset values are prompted for. The CLI switches scope when a preset requires a different mode.

### Presets that use AI

- `full` runs the deterministic checks and uses AI to look for substantive defects in language and structure. In `site-wide` or `all` mode, it also checks for inconsistencies across documents.
- `editorial` runs the page-level AI checks for language, structure, portfolio presentation, repetition and diagrams, alongside Vale and LTeX+.
- `portfolio` uses AI to review how case studies and documentation samples present the author's contribution, decisions and evidence.
- `repetition` uses AI to flag repeated material that adds little. It checks within pages, across documents, or both, depending on the mode.
- `mermaid` uses AI to suggest where a Mermaid diagram could clarify the text.
- `site-wide-consistency` uses AI to compare documents for conflicting terminology, claims or guidance. It switches `per-page` to `site-wide`.

For example, `site-wide-consistency` can flag two related pages that use different names for the same contributor role. [How the AI review compares documents](qa-ai-review.mdx#site-wide-comparison)

AI review requires `DEEPSEEK_API_KEY`. Set `DEEPSEEK_MODEL` to override the default model, `deepseek-flash`.

### Presets that run only deterministic checks

- `accessibility` checks page markup for issues such as missing image alt text, vague link text and skipped heading levels.
- `vale` checks prose against the repository's style and terminology rules.
- `ltex` uses LTeX+ to check spelling and grammar in British English.
- `lychee` uses Lychee to check external HTTP and HTTPS links.
- `links` checks local routes and file references and uses Lychee to check external links.
- `remark` checks Markdown and MDX syntax and configured lint rules.

## Reports and feedback files

| Option | Behaviour |
| --- | --- |
| `--report PATH_OR_URL` | Reads a saved JSON report from a local path or an accepted versioned GitHub Pages report URL. |
| `--report-dir DIR` | Writes HTML, JSON and Markdown reports to this directory. Fresh reviews default to `.qa/` locally and the repository root in GitHub Actions. `render` and `compare` default to `.qa/feedback-view/`. |
| `--findings-file PATH` | Fresh reviews save their findings here. `challenge` uses this file when no `--report` is supplied. Defaults to `qa/findings.json`. |
| `--feedback-file PATH` | Selects the feedback registry. Defaults to `qa/feedback.json`. |

## Saved reports and feedback commands

| Command | Required options and behaviour |
| --- | --- |
| `render` | `--report`. Applies current feedback to saved findings and writes refreshed reports. |
| `compare` | `--report` and `DEEPSEEK_API_KEY`. Also compares possible recurrence links using AI. |
| `challenge` | `--issue` and one of `--reason`, `--reason-file` or `--retry`. Requires `DEEPSEEK_API_KEY`. |
| `resolve` | `--issue`, `--decision` and `--reason`. Decisions are `accepted`, `dismissed`, `change_requested` or `pending`. |
| `link` | `--report`, `--issue`, `--previous`, `--decision` and `--reason`. Decisions are `confirmed` or `rejected`. Supply `--proposal` when a specific proposal must be selected. |
| `reuse` | `--report`, `--issue`, `--previous`, `--proposal` and `--reason`. Records human-approved reuse after revalidation. |

| Feedback option | Value |
| --- | --- |
| `--issue ID` | Finding ID copied from the report. |
| `--previous ID` | Previous feedback record ID. |
| `--proposal TOKEN` | Source-bound proposal token copied from the report. |
| `--decision VALUE` | Decision for `resolve` or `link`. |
| `--reason TEXT` | Rebuttal or explanation. Use shell quotes if the text contains spaces. |
| `--reason-file PATH` | Reads a challenge rebuttal from a UTF-8 file. |
| `--retry` | Retries a pending challenge using its recorded rebuttal. |

## CI thresholds

| Option | Behaviour |
| --- | --- |
| `--ci` | Disables prompts and makes a failed gate return exit code 1. `render` and `compare` use the original report thresholds. |
| `--fail-high N` | Fails a fresh review's gate when eligible high-severity findings exceed `N`. Default `0`. |
| `--fail-medium N` | Fails a fresh review's gate when eligible medium-severity findings exceed `N`. Default `25`. |
| `--fail-api-errors N` | Fails a fresh review's gate when API or checker errors exceed `N`. Default `0`. |

## Example

Run the deterministic accessibility check and write reports to a separate directory.

```bash
python3 scripts/ai_docs_review.py --mode per-page --filter accessibility --report-dir .qa/accessibility
```

For a worked example of refreshing a saved report, see [Refresh or rerun](qa-read-report.md#refresh-or-rerun).

[Documentation QA architecture](qa-architecture.mdx) · [Finding identity, feedback and recurrence](qa-feedback.md)
