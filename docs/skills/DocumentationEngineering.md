---
title: Documentation Engineering
sidebar_position: 4
slug: /documentationeng
sidebar_custom_props:
  sampleCard:
    tag: Documentation engineering
    description: Docs-as-code, documentation-platform ownership, CI/CD, static-site generators, 
      parser extensions, migration automation, validation, search and custom tooling for large-scale
      technical content.
    highlights:
      - Built and operated a custom docs-as-code platform
      - Scaled documentation from 700 to 3,200 pages
      - Automated migration of approximately 900 legacy pages
      - CI/CD, parser extensions, validation and search
    ariaLabel: Explore my documentation engineering skills
type:
  - skill
audiences:
  - technical-writers
  - documentation-managers
  - developers
topics:
  - docs-as-code
  - documentation-engineering
  - technical-writing
  - information-architecture
  - technical-validation
technologies:
  - git
  - github-actions
  - jenkins
  - docusaurus
  - mkdocs
  - markdown
  - plantuml
  - mermaid
  - graphviz
  - c4-model
  - python
  - sphinx
  - confluence
  - madcap-flare
  - vale
  - flexsearch
  - rag
  - codetreedocs
  - react
lifecycle:
  - current
tags:
  - c4-model
  - codetreedocs
  - confluence
  - docs-as-code
  - documentation-engineering
  - docusaurus
  - flexsearch
  - git
  - github-actions
  - graphviz
  - information-architecture
  - jenkins
  - madcap-flare
  - markdown
  - mermaid
  - mkdocs
  - plantuml
  - python
  - rag
  - react
  - sphinx
  - technical-validation
  - technical-writing
  - vale
---

I apply software-engineering practices to documentation systems, including version control, automated testing, CI/CD and tooling for repetitive tasks.

My experience includes docs-as-code, Git and CI/CD workflows, static-site generators, Markdown and parser extensions, large-scale content migration, documentation-platform development, search, validation and custom tooling.

## Docs-as-code

My docs-as-code experience includes:

* Markdown authoring
* Using Git branching and pull-request workflows to update the documentation
* Command-line Git, including rebasing and resolving merge conflicts.
* Documentation stored alongside source code, including the benefits and trade-offs of this approach.
* Hosting documentation in large repositories and monorepos
* Automating builds and publishing
* Promoting and enabling engineering documentation contributions
* Review, versioning and traceability through Git

I have also designed contributor workflows, standards and tooling that enable engineers to contribute documentation through normal development workflows.

## CI/CD and publishing

I use CI/CD to automate documentation build, validation and publishing workflows. My experience includes:

* Jenkins-based documentation pipelines
* GitHub Actions
* Automated site builds and deployment
* Link and build validation
* Documentation quality checks
* Diagnosing failed builds and publishing issues
* Improving pipeline performance and maintainability

My current portfolio, for example, uses GitHub Actions to build and publish the site and to run automated documentation quality checks.

## Static-site generators and platform engineering

I have worked with Docusaurus, MkDocs and custom Markdown-based static-site generators.

I have evaluated, extended and developed documentation platforms to meet requirements around:

* Build performance
* Large documentation sets
* Navigation
* Search
* Markdown extensions
* Plugin compatibility
* Incremental builds and caching
* CI integration
* Contributor experience
* User feedback collection

I have modified existing MkDocs plugins where required. I also led and specified the requirements for a custom static-site generator, was closely involved in its technical design and testing, and later contributed directly to its development.

## Markdown and parser engineering

Standard Markdown is not always sufficient for complex developer documentation.

I have extended Markdown parsers and static-site tooling to support features including:

* Diagrams-as-code formats such as PlantUML, Mermaid, and Graphviz
* C4 software architecture diagrams
* LaTeX mathematical notation
* Content reuse and conditional text
* Code-sample injection

I have also built tools to convert complex HTML into clean embedded HTML or mixed Markdown and HTML for structures that standard Markdown cannot represent, such as complex tables using `rowspan`, `colspan`, or multi-line cell content.

## Content migration and transformation

I use automation wherever possible when moving large documentation sets between platforms.

My migration work has included:

* Python and Scala migration tooling
* HTML parsing and transformation
* Wiki-to-Markdown conversion
* Sphinx-to-Markdown conversion
* Confluence XHTML to MadCap Flare XHTML conversion
* Link preservation and rewriting, including conversion of absolute links to relative link
* Front-matter and metadata generation
* Structural content transformation
* Reusable-content conversion
* Validating generated Markdown and HTML for errors

For large migrations, I use analytics such as page views to identify high-value content and flag potentially obsolete material for review or archival.

## Documentation tooling and automation

I build tools to remove repetitive documentation work and make documentation systems easier to maintain.

Examples include:

* Content migration scripts
* Front-matter processing
* Automated landing-page generation
* Diagram generation
* Git workflow automation
* Automated grammar and spelling checks
* Link checking
* LLM-assisted editorial checks

I also use web-development techniques where appropriate. This portfolio, for example, combines Docusaurus and React components to turn structured Markdown content into responsive visual layouts.

## Validation and quality engineering

I treat documentation as something that can be tested rather than relying entirely on manual review.

Examples include:

* Build validation
* Link checking
* Markdown validation
* Grammar and spelling checks
* Style-guide checks using Vale or similar
* Accessibility checks
* Rendering tests
* Migration-output validation
* OCR-based detection of obsolete terminology in screenshots and legacy diagrams
* Automated quality checks on pull requests

This approach allows quality controls to scale with the size of the documentation set and the number of contributors.

## Search and retrieval

Documentation engineering also includes making content discoverable once it has been published.

I have integrated traditional enterprise search, fast browser-based search using tools such as FlexSearch.js, and central RAG-based retrieval services. My RAG work has included generating sitemaps for indexing, testing retrieval quality, identifying issues such as deprecated APIs being surfaced, and proposing metadata and filtering to improve results.

## Engineering for scale

My experience engineering documentation systems for scale includes:

* Managing documentation estates containing thousands of pages
* Scaling Git-based contribution workflows
* Improving build and publishing processes
* Automating large content migrations
* Reducing duplication through reuse
* Supporting distributed engineering contributions
* Developing documentation standards and tooling

A key example is **Codetreedocs**, an internal developer-documentation platform at Morgan Stanley. I led the platform as product owner, defined its requirements, contributed to the design, did the majority of the testing, and later contributed directly to its development. The platform combined Markdown, Git, Jenkins, an IDE-based authoring experience, custom static-site generation, search and migration tooling.

Over three years, the documentation estate grew from approximately **700 pages to more than 3,200 pages**, supported by contributions from the wider engineering community. I also developed migration tooling that converted approximately **900 legacy pages** into the platform's extended Markdown format.

[Read the Codetreedocs case study →](../case-studies/ScalingADeveloperDocsPlatform.md)
