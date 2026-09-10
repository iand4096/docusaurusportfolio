---
title: Scaling an Enterprise Developer Docs Platform
description: How I scaled a custom enterprise docs-as-code platform from 700 to 
  over 3,200 pages for a large developer community
slug: /case-studies/scalingdeveloperdocs
sidebar_position: 1
type:
  - case-study
audiences:
  - developers
  - documentation-managers
  - technical-writers
topics:
  - docs-as-code
  - documentation-engineering
  - developer-experience
  - information-architecture
  - documentation-governance
technologies:
  - codetreedocs
  - git
  - markdown
  - jenkins
  - intellij-idea
  - plantuml
  - mermaid
  - c4-model
  - sphinx
  - docker
  - amp
  - agentic-ai
  - vale
  - languagetool
lifecycle:
  - current
sidebar_custom_props:
  caseStudyCard:
    tag: Docs-as-Code · Developer Portal
    description: Scaling a custom enterprise documentation platform from 700 to more than 3,200 
      pages for a large developer community
    highlights:
      - Documentation platform strategy and product ownership
      - Git, Markdown and Jenkins publishing workflows
      - IDE tooling, migration automation and diagrams-as-code
      - Large-scale adoption, governance and platform evolution
    ariaLabel: Read the enterprise developer documentation platform case study
tags:
  - agentic-ai
  - amp
  - c4-model
  - codetreedocs
  - developer-experience
  - docker
  - docs-as-code
  - documentation-engineering
  - documentation-governance
  - git
  - information-architecture
  - intellij-idea
  - jenkins
  - languagetool
  - markdown
  - mermaid
  - plantuml
  - sphinx
  - vale
---

## Context

At Morgan Stanley, I led the design and evolution of **Codetreedocs**, a custom internal docs-as-code platform and developer portal supporting an API platform whose developer mailing list had approximately 1,200 subscribers.

Codetreedocs was designed to replace fragmented legacy wiki-based documentation with a Git-based publishing workflow to make it easier for engineers to create, maintain, review, and discover documentation.

I owned the product direction, requirements, testing, and quality. I initially worked with a dedicated engineering team on the design and core implementation and later contributed directly to the codebase to extend the platform and resolve issues that arose as the platform scaled.

## Challenge

* Replace fragmented documentation spread across legacy wiki and docs-as-code-based systems with a single platform.
* Make documentation contributions practical and as easy as possible for a large engineering community.
* Support documentation stored in Git alongside the code in a large monorepo.
* Provide scalable documentation publishing, search, and navigation.
* Migrate valuable legacy content without manually rewriting hundreds of pages.
* Maintain and evolve the platform as usage and content volume increased.

## Approach

I worked with engineers from the internal tooling team to improve the authoring experience and create a published developer portal.

The approach focused on:

* Storing and reviewing documentation in Git alongside source code.
* Reducing friction for documentation contributions.
* Designing search and information architecture for a large technical documentation set.
* Using analytics to identify high-value legacy content and prioritise migration.
* Supporting documentation authoring within engineers' existing development environment.

## Implementation

The platform included:

* Markdown-based documentation stored and reviewed in Git.
* A Jenkins-based documentation build and publishing pipeline with basic quality checks such as link-checking for new documentation.
* An IntelliJ plugin for documentation authoring and live preview.
* Support for diagrams-as-code, including software architecture diagrams.
* Search and navigation for a growing documentation set.
* The ability to reuse content in multiple locations and insert code samples into the documentation.

I also led the successful migration of the platform to the firm's new Docker-based web-hosting environment. Additionally, I developed content migration scripts for the internal wiki and Sphinx, followed by an end-user-focused IDE-based migration tool, collectively converting approximately **900 legacy wiki pages** to the platform’s extended Markdown format.

As the platform matured, I contributed directly to its codebase using Amp and agentic AI-assisted development. This work included adding support for PlantUML, Mermaid, and C4 diagrams and LaTeX mathematical notation, as well as diagnosing and fixing bugs in the link-checking implementation.

## Impact

Codetreedocs grew from approximately **700 pages to more than 3,200 pages over three years**, through a combination of my own documentation work and contributions from the wider engineering community.

The project helped establish documentation as a normal part of the engineering workflow. Engineers were able to avoid context switching from their IDE to a separate documentation tool. This reduced friction led to a sustained increase in contributions and corrections.

## Lessons learned

* Define and implement a structured documentation metadata taxonomy, covering ownership, lifecycle status, audience, review cadence, and content type, before a corpus grows to several thousand pages. My current portfolio integrates [a canonical taxonomy and associated governance system](./TaxonomyGovernance.md).

* Add automated quality checks to documentation pull requests beyond simple link checking, using tools such as Vale and LanguageTool together with AI-assisted checks for style-guide conformance, consistency, and other content-quality issues. This would help to ensure that quality scales with the growth of the site once manual review of every PR is no longer practical. My [portfolio integrates these checks](./DocusaurusPortfolio.md).
