---
title: Run a documentation review
description: Set up a local QA run, choose the checks you need and locate the results.
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

## Run your first check

From the repository root, set up a Python environment for QA. On Linux x86-64, use Python 3.12 and the same locked dependencies as CI.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-doc-review-linux-py312.lock
source .venv/bin/activate
```

For other platforms, use `requirements-doc-review.txt` with a compatible Python and PyTorch environment. See the [workflow and dependency setup](qa-reports-and-ci.mdx#workflow-thresholds-and-publication) for the CI configuration.

Run the built-in accessibility check first. It needs the Python environment and repository files.

```bash
python3 scripts/ai_docs_review.py --mode per-page --filter accessibility
```

Open `.qa/ai-doc-review.html` to inspect the results. The same directory contains `ai-doc-review.json` for automation and `ai-doc-review.md` for reading or exporting the findings.

## Choose checks and tools

| If you want to check | Select | Additional setup |
| --- | --- | --- |
| Basic accessibility | `accessibility` | No external checker |
| Markdown or MDX | `remark` | Node.js and the repository's npm dependencies |
| Prose style or terminology | `vale` | Vale and `mdx2vast` on PATH, with the repository's Vale configuration |
| Spelling and grammar | `ltex` | Java and `ltex-cli-plus` on PATH, with the repository's LTeX+ configuration |
| Links | `links` or `lychee` | Lychee on PATH and network access for external links |
| Editorial issues or substantive defects | An AI preset such as `editorial` or `full` | `DEEPSEEK_API_KEY`, plus the tools selected by the preset. `full` uses all deterministic tools. |

See the [CLI reference](qa-cli-reference.md#review-scope-and-check-presets) for each preset and mode. AI checks send source text to DeepSeek. Use a deterministic preset when you only need a local check.

## Documents in scope

QA reviews the root README and licence, plus Markdown and MDX under `docs/`, `src/pages/`, `src/components/` and `knowledge-api/`. Untracked drafts in those directories are included. Generated QA reports and `FAPI/` are excluded. Repeat `--include-file PATH` to add other Markdown or MDX files in the repository.

## Troubleshoot a run

- **A checker is missing.** Read the named check error in the report and confirm the executable is on PATH. For setup failures in GitHub Actions, inspect the setup step log.
- **AI credentials are missing.** Configure `DEEPSEEK_API_KEY` for the review process or choose a deterministic preset. A fresh AI review checks for credentials before it starts.
- **CI failed.** Open the report and read the gate summary to see whether eligible findings or check errors exceeded a threshold. If no report was produced, start with the workflow logs. [Read a report and act on findings](qa-read-report.md) explains when a fresh run is needed.
