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
  - git
  - markdown
  - intellij-idea
  - plantuml
  - mermaid
  - c4-model
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
      - Git, Markdown and CI/CD publishing workflows
      - IDE tooling, migration automation and diagrams-as-code
      - Large-scale adoption, governance and platform evolution
    ariaLabel: Read the enterprise developer documentation platform case study
tags:
  - agentic-ai
  - amp
  - c4-model
  - developer-experience
  - docs-as-code
  - documentation-engineering
  - documentation-governance
  - git
  - information-architecture
  - intellij-idea
  - languagetool
  - markdown
  - mermaid
  - plantuml
  - vale
---

## Context

At Morgan Stanley, I led the design and evolution of a custom internal docs-as-code platform and developer portal that consolidated existing documentation into a single modern system. It hosted documentation for a large internal API platform with a large developer audience. The documentation was used by quantitative analysts and developers building applications across the business.

The new platform was designed to replace fragmented legacy documentation with a Git-based publishing workflow to make it easier for engineers and technical writers to create, maintain, review, and discover documentation.

I owned the product direction, requirements, testing, and quality. I initially worked with a dedicated engineering team on the design and later contributed directly to the codebase, once they had implemented the main features. My efforts included extending the platform and resolving issues as the site scaled.

## Challenge

* Replace fragmented documentation spread across legacy documentation systems with a single platform.
* Make documentation contributions practical and as easy as possible for a large engineering community.
* Store the documentation in Git alongside application source.
* Provide scalable publishing, search, and navigation.
* Migrate valuable legacy content without manually rewriting hundreds of pages.
* Maintain and evolve the platform as usage and content volume increased.

## Approach

### Why docs as code and why build a custom platform

Developers were already writing simple Markdown files alongside their code instead of using the existing wiki-based authoring tools, but they had no dedicated tooling or publishing environment to support that way of working.

Instead of trying to move developers back into a separate documentation system, I chose to support the way they were already working and keep ownership with the teams closest to the technical knowledge.

Initially, I built a docs-as-code pilot using MkDocs, a migrated version of the existing content, and multiple customised plugins. The pilot helped test the approach in practice and showed the limitations of an off-the-shelf solution.

It became clear that to meet the full set of requirements, would require a custom platform. That required more investment, but provided capabilities existing tools could not offer, including Markdown extensions such as source-code injection combined with tight IDE integration, and documentation that rendered the same within the IDE as on the published site.

### Design priorities

The design focused on four priorities:

* reducing friction for documentation contributions and corrections
* supporting authoring within engineers' existing development environment
* designing search and information architecture that could scale with a large technical documentation set
* using analytics to identify high-value legacy content and prioritise migration.

## Implementation

I worked with engineers from the internal tooling team to improve the authoring experience and create a published developer portal.

* **Markdown-based documentation stored and reviewed in Git alongside the code**. This provided stronger version control than the previous wiki-based platforms, allowing users to update multiple pages in a single, reviewable atomic change. It also made the documentation easier to integrate with GenAI workflows.

* **A CI/CD-based documentation build and publishing pipeline with automated quality checks**. Checks such as link validation caught issues before publication, preventing broken internal links and improving the reliability of the documentation.

* **An IntelliJ plugin for documentation authoring and live preview**. This lowered the barrier for developers to contribute documentation by allowing them to edit and preview changes directly within their existing development environment.

* **Support for diagrams-as-code, including software architecture diagrams**. This enabled engineers to create and maintain explanatory diagrams without requiring specialist graphical skills, while keeping diagrams version-controlled alongside the documentation.

* **Search and navigation for a growing documentation set**. I designed the search approach, combining keyword based JavaScript client-side lookup and slower RAG-based search for more complex natural-language queries. I also tested search behaviour and retrieval quality; the engineering team implemented the solution.

* **The ability to reuse content in multiple locations and embed code samples directly from source**. This reduced duplication and maintenance effort by allowing shared content and code examples to be updated centrally.

### Containerised hosting migration

I led the successful migration of the documentation platform to the firm’s new containerised hosting solution with a custom domain, implementing redirects for legacy URLs and resolving post-launch issues. A major contribution was my proposal to serve the generated documentation from an attached file system instead of copying the content into the container reducing the build time by approximately **15 minutes**.

### Content migration

I developed automated content migration tooling for several legacy documentation systems, followed by an end-user-focused IDE-based migration tool. Together, these tools reduced the manual effort and risk associated with moving existing documentation, enabling approximately **900 pages** to be converted to the platform’s extended Markdown format while preserving information hierarchy, images, internal links, complex tables, code samples, mathematical equations, and Dot-format diagrams. I subsequently created IDE-based tooling to allow content owners to migrate and validate their own documentation, making the process more scalable.

As the platform matured, I contributed directly to its codebase using agentic AI-assisted development. This work included adding support for a variety of diagrams-as-code formats including PlantUML, Mermaid as well as C4 / Structurizr architecture diagrams. I also personally diagnosed and fixed bugs in the link-checking implementation.

## Impact

The platform grew from approximately **700 pages to more than 3,000 pages over three years**, through a combination of my own documentation work, content migrations, and contributions from the wider engineering community.

The project helped establish documentation as a normal part of the engineering workflow. Engineers were able to avoid context switching from their IDE to a separate documentation tool. This reduced friction led to a sustained increase in contributions and corrections.

## Lessons learned

* Define and implement a structured documentation metadata taxonomy, covering ownership, lifecycle status, audience, review cadence, and content type, early in the development of a documentation platform. My current portfolio integrates [a canonical taxonomy and associated governance system](./TaxonomyGovernance.md).

* Add a full set of automated quality checks to documentation pull requests beyond simple link checking, using tools such as Vale and LanguageTool together with AI-assisted checks for style-guide conformance, consistency, and other content-quality issues. This would help to ensure that quality scales with the growth of the site once manual review of every PR is no longer practical and is especially important when engineers use GenAI assisted authoring. My [portfolio integrates these checks](./DocusaurusPortfolio.md).
