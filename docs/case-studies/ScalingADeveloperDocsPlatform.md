---
title: Scaling an Enterprise Developer Docs Platform
slug: /case-studies/scalingdeveloperdocs
sidebar_position: 1
sidebar_custom_props:
  caseStudyCard:
    tag: Docs-as-Code · Developer Portal
    description: Scaling a custom enterprise documentation platform from 700 to more than 3,200 pages for a developer community of approximately 1,200 users.
    highlights:
      - Documentation platform strategy and product ownership
      - Git, Markdown and Jenkins publishing workflows
      - IDE tooling, migration automation and diagrams-as-code
      - Large-scale adoption, governance and platform evolution
    ariaLabel: Read the enterprise developer documentation platform case study
---

## Project overview

At Morgan Stanley, I led the design and evolution of **Codetreedocs**, a custom internal docs-as-code platform and developer portal supporting an API platform used by approximately **1,200 developers**.

Codetreedocs was designed to replace fragmented legacy documentation with a Git-based publishing workflow that made it easier for engineers to create, maintain, review, and discover technical content alongside source code.

I owned product direction, requirements, solution design, testing, and quality. I initially worked with a dedicated engineering team on the core implementation and later contributed directly to the codebase to extend the platform and resolve issues as it scaled.

## The challenge

* Replace fragmented documentation spread across legacy TWiki and Sphinx-based systems.
* Make documentation contribution practical for a large engineering community.
* Support documentation stored in Git within a large monorepo.
* Provide a scalable build, publishing, search, and navigation experience.
* Migrate valuable legacy content without manually rewriting hundreds of pages.
* Maintain and evolve the platform as usage and content volume increased.

## My approach

I treated the documentation platform as a product, working with engineers and internal tooling teams to improve both the authoring experience and the published developer portal.

Key elements included:

* Markdown-based documentation stored and reviewed in Git.
* Jenkins-based documentation build and publishing pipelines.
* An IntelliJ plugin providing live documentation preview.
* Support for diagrams-as-code, including software architecture diagrams.
* Search and information architecture designed for a large technical documentation set.
* Analytics used to identify high-value legacy content and prioritise migration.
* Contribution workflows designed to encourage engineers to create and maintain documentation.

I developed migration scripts and later helped create a more user-focused IDE-based migration tool that converted approximately **900 legacy TWiki pages** into the platform's extended Markdown format. I also wrote tooling to migrate documentation from Sphinx.

As the platform matured, I contributed directly to its codebase and used agentic AI tools and spec-driven development techniques to accelerate platform enhancements and repetitive documentation tasks.

## Deliverables

* A large-scale internal docs-as-code platform and developer portal.
* Git and Markdown-based authoring and review workflows.
* Jenkins-based CI and publishing infrastructure.
* IntelliJ documentation authoring and live-preview tooling.
* Support for diagrams-as-code and architecture documentation.
* Automated migration tooling for legacy wiki and Sphinx content.
* Search, navigation, and information architecture for a growing documentation corpus.
* Migration of the platform to the firm's strategic Docker-based web-hosting environment.

## Outcome

Codetreedocs grew from approximately **700 pages to more than 3,200 pages over three years**, through a combination of my own documentation work and contributions from the wider engineering community.

The project helped establish documentation as a normal part of engineering practice rather than something maintained only by a central documentation team.

It also gave me experience spanning **documentation strategy, product ownership, developer experience, docs-as-code, information architecture, migration automation, platform engineering, and hands-on software development**.

## What I would change

* Define and implement a structured documentation metadata taxonomy, covering ownership, lifecycle status, audience, review cadence, and content type, before the corpus grew to several thousand pages.
* Establish more comprehensive documentation analytics and contribution metrics earlier to measure adoption, content quality, usage, and maintenance needs more systematically.
* Add automated quality checks to documentation pull requests using tools such as Vale and LanguageTool, together with AI-assisted checks for style-guide conformance, consistency, and other content-quality issues, so that quality could scale with the growth of the site once manual review of every PR was no longer practical. My [portfolio integrates these checks](./DocusaurusPortfolio.md)
