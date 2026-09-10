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

At Morgan Stanley, I led the design and evolution of **Codetreedocs**, a custom internal docs-as-code platform and developer portal supporting an API platform whose developer mailing list had approximately 1,200 subscribers. This documentation was used by Quantitive Analysts and Developers to create applications supporting Morgan Stanley's Institutional Securities business.

Codetreedocs was designed to replace fragmented legacy wiki-based documentation with a Git-based publishing workflow to make it easier for engineers and technical writers to create, maintain, review, and discover documentation.

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

* **Markdown-based documentation stored and reviewed in Git**. This provided stronger version control than the previous wiki-based platforms, allowing users to update multiple pages in a single, reviewable atomic change. It also made the documentation easier to integrate with GenAI-assisted authoring and maintenance workflows.

* **A Jenkins-based documentation build and publishing pipeline with automated quality checks**. Checks such as link validation caught issues before publication, preventing broken internal links and improving the reliability of the documentation.

* **An IntelliJ plugin for documentation authoring and live preview**. This lowered the barrier for developers to contribute documentation by allowing them to edit and preview changes directly within their existing development environment.

* **Support for diagrams-as-code, including software architecture diagrams**. This enabled engineers to create and maintain explanatory diagrams without requiring specialist graphical skills, while keeping diagrams version-controlled alongside the documentation.

* **Search and navigation for a growing documentation set**. Fast, responsive search using FlexSearch.js supported routine lookup, while slower but more authoritative RAG-based search supported more complex natural-language queries.

* **The ability to reuse content in multiple locations and embed code samples directly from source**. This reduced duplication and maintenance effort by allowing shared content and code examples to be updated centrally.

I also led the successful migration of the platform to the firm's new Docker-based web-hosting environment. In parallel, I developed automated content migration tooling for the internal wiki and Sphinx, followed by an end-user-focused IDE-based migration tool. Together, these tools reduced the manual effort and risk involved in moving legacy documentation, enabling approximately 900 legacy wiki pages to be converted to the platform’s extended Markdown format while preserving information hierarchy, images, internal links, complex tables, code samples, mathematical equations, and Dot-format diagrams. The later IDE-based tooling allowed content owners to migrate and validate their own documentation, making the migration process more scalable.

As the platform matured, I contributed directly to its codebase using Amp and agentic AI-assisted development. This work included adding support for PlantUML, Mermaid, and C4 diagrams and LaTeX mathematical notation, as well as diagnosing and fixing bugs in the link-checking implementation.

## Impact

Codetreedocs grew from approximately **700 pages to more than 3,200 pages over three years**, through a combination of my own documentation work and contributions from the wider engineering community.

The project helped establish documentation as a normal part of the engineering workflow. Engineers were able to avoid context switching from their IDE to a separate documentation tool. This reduced friction led to a sustained increase in contributions and corrections.

## Lessons learned

* Define and implement a structured documentation metadata taxonomy, covering ownership, lifecycle status, audience, review cadence, and content type, before a corpus grows to several thousand pages. My current portfolio integrates [a canonical taxonomy and associated governance system](./TaxonomyGovernance.md).

* Add a full set of automated quality checks to documentation pull requests beyond simple link checking, using tools such as Vale and LanguageTool together with AI-assisted checks for style-guide conformance, consistency, and other content-quality issues. This would help to ensure that quality scales with the growth of the site once manual review of every PR is no longer practical. My [portfolio integrates these checks](./DocusaurusPortfolio.md).
