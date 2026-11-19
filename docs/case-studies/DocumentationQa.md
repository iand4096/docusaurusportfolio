---
title: Building documentation QA into the publishing workflow
description: How I built a documentation review pipeline with source-backed AI findings,
  human decisions and commit-specific reports.
slug: /case-studies/documentation-qa
sidebar_position: 8
sidebar_custom_props:
  caseStudyCard:
    title: Documentation QA
    tag: Documentation engineering
    description: Built a review pipeline that combines rule-based checks with AI editorial review.
    highlights:
      - Requires source quotations and verification for AI findings
      - Publishes commit-specific reports with findings, checker failures and human decisions
    ariaLabel: Read the documentation QA case study
type:
  - case-study
audiences:
  - developers
  - documentation-managers
  - technical-writers
topics:
  - docs-as-code
  - documentation-engineering
  - documentation-governance
technologies:
  - deepseek-api
  - docusaurus
  - github-actions
  - python
  - vale
lifecycle:
  - current
tags:
  - deepseek-api
  - docs-as-code
  - documentation-engineering
  - documentation-governance
  - docusaurus
  - github-actions
  - python
  - vale
---

import CaseStudySummary from '@site/src/components/CaseStudySummary';

<CaseStudySummary {...{
  "employer": "Independent project",
  "industry": "Documentation engineering",
  "projectType": "Documentation QA",
  "summary": "I built a QA pipeline for this portfolio that checks documentation before publication and gives reviewers the evidence behind each AI finding.",
  "role": "Designed and implemented the review pipeline and CI policy",
  "scope": "Local reviews, pull request checks and report publication",
  "decision": "Require source evidence for AI findings and bind human decisions to the reviewed revision",
  "deliverables": "Python CLI, checker adapters, review reports and GitHub Actions workflows",
  "evidenceTitle": "What reviewers can inspect",
  "evidence": [
    {"value": "Source evidence", "label": "Compare an AI criticism with the passages it cites"},
    {"value": "Decision history", "label": "See earlier decisions and whether they need revalidation"},
    {"value": "Commit-specific reports", "label": "Inspect what the workflow checked and why the gate failed"}
  ]
}} />

## Context {/* #context */}

A link checker can tell me whether a local link resolves. It takes a different kind of review to spot two guides giving incompatible instructions for the same task. I built a shared review pipeline for this Docusaurus portfolio so I could run both kinds of checks locally and in GitHub Actions, then inspect their results in one report.

## Challenge {/* #challenge */}

A report needed to distinguish a clean check from a failed checker. A reviewer also needed enough context to decide whether an AI criticism was valid. A quotation can be accurate while the conclusion drawn from it is wrong. The surrounding text might resolve the apparent ambiguity, or the suggested rewrite might introduce a fact the source never established.

Decisions needed a lifetime of their own. If I dismissed a criticism and later edited the page, the original reasoning should still be available. The new revision needed a fresh decision because a change elsewhere in the page could affect how the passage reads.

## Approach {/* #approach */}

I used deterministic checks for conditions such as broken local links and Vale style rules. I used AI review for questions that depend on meaning, including contradictions between pages. For cross-page review, the model receives the selected documents with file paths and line numbers so it can cite both passages and identify the page to fix.

I require each AI proposal to explain the reader impact and quote the text it relies on. The pipeline checks the quotations against the supplied source, then sends valid proposals through a separate verification request. For a substantive defect, the verifier considers the strongest reasonable reading and checks whether the problem still holds. That extra request adds latency and API usage. Completed reviews, including those with no findings, can be reused when the source and review configuration match. [AI review and caching](../implementation-details/qa-ai-review.mdx)

## Implementation {/* #implementation */}

The Python CLI selects the documents and checks for each run. Adapters translate tool output into shared findings and record checker errors separately. One report model produces HTML for inspection, JSON for subsequent commands and Markdown for review. The saved JSON can be rendered again with current feedback and recalculated gate counts without rerunning the checks. [Pipeline and report flows](../implementation-details/qa-architecture.mdx)

I tied feedback to the document revision and proposed fix. For example, if a passage moves within the same file, the previous discussion can still appear alongside the new finding. The report marks the old decision as needing revalidation because the document bytes changed. Reworded criticisms can be shortlisted using quotation overlap and embeddings, then compared by the model. A reviewer decides whether to link them. [Finding matching and revalidation](../implementation-details/qa-feedback.md)

I put the CI eligibility rules in Python. An AI finding counts towards the gate when it is a high-confidence defect with no human dismissal, and its severity is capped at medium. Checker errors have a separate threshold. The deployment workflow verifies that the report belongs to the current run and publishes it with the site before surfacing a failed QA gate. [Report publication and CI policy](../implementation-details/qa-reports-and-ci.mdx)

## Impact {/* #impact */}

A contributor can run a review before opening a pull request. On deployment, the portfolio publishes a report tied to the commit it checked. The report lets me inspect the quoted evidence, see prior decisions and tell whether the gate failed because of findings or a checker error. When a human decision changes, I can refresh the report without paying for another AI review.

The [latest QA report](pathname:///qa/) shows the output on this site. When the report has few active findings, it offers a separate example with synthetic findings and a simulated checker failure. The [Documentation QA guide](../implementation-details/qa-overview.md) covers how to run a review and act on the results.
