---
title: Documentation Engineering
sidebar_position: 4
slug: /documentationeng
sidebar_custom_props:
  sampleCard:
    tag: Documentation engineering
    description: Designing and maintaining scalable docs-as-code platforms using
      software-engineering practices, automation, and continuous integration.
    highlights:
      - Helped scale a documentation platform from 700 to 3,200 pages
      - Built tooling to migrate approximately 900 legacy pages
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
  - react
lifecycle:
  - current
tags:
  - c4-model
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

import CapabilityGrid from '@site/src/components/CapabilityGrid';
import CapabilityCard from '@site/src/components/CapabilityCard';

I build documentation systems using software-engineering practices such as source control, CI/CD, parser and platform extensions, migration tooling, search and publishing automation.

## Docs-as-code {/* #docs-as-code */}

<CapabilityGrid>

* **Authoring and contribution**<br />
  Markdown and extended Markdown, with contributor workflows, standards and tooling that help engineers contribute through their normal development process.

* **Git workflows**<br />
  Branching, pull requests, command-line Git, rebasing and merge-conflict resolution. Git provides review history, versioning and traceability.

* **Repository structure**<br />
  Documentation in large repositories and monorepos, including the trade-offs between storing it alongside source code and maintaining a separate repository.

</CapabilityGrid>

## CI/CD and publishing {/* #cicd-and-publishing */}

I use CI/CD to automate documentation builds, validation and publishing.

<CapabilityGrid>

* **Pipeline implementation**<br />
  Jenkins and GitHub Actions pipelines for automated site builds and deployment.

* **Build and quality checks**<br />
  Link validation, build validation and documentation quality checks within publishing workflows.

* **Pipeline maintenance**<br />
  Diagnose failed builds and publishing issues, and improve pipeline performance and maintainability.

</CapabilityGrid>

## Static-site generators and platform engineering {/* #static-site-generators-and-platform-engineering */}

I have worked with Docusaurus, MkDocs and custom Markdown-based static-site generators, including modifying existing MkDocs plugins.

<CapabilityGrid>

* **Performance and scale**<br />
  Build performance, large documentation sets, incremental builds and caching.

* **Navigation and discovery**<br />
  Navigation, search and user feedback collection.

* **Extensions and contribution**<br />
  Markdown extensions, plugin compatibility, CI integration and contributor experience.

</CapabilityGrid>

## Examples from practice {/* #examples-from-practice */}

<CapabilityCard items={[
  {
    title: 'Scaling a developer platform',
    summary: 'At Morgan Stanley, I helped build and scale an internal developer-documentation platform. Over three years, the documentation estate grew from approximately 700 to more than 3,200 pages, with contributions from the wider engineering community.',
  },
  {
    title: 'Developing a static-site generator',
    summary: 'I led and specified the requirements for a custom static-site generator, contributed to its technical design, carried out all the user testing and later worked directly on its development.',
  },
  {
    title: 'Automating portfolio publishing',
    summary: 'This portfolio uses GitHub Actions to build and publish the Docusaurus site and run documentation quality checks. React components turn structured Markdown content into responsive layouts.',
  },
]} />

[Read the developer docs platform case study →](../case-studies/ScalingADeveloperDocsPlatform.md)

## Markdown and parser engineering {/* #markdown-and-parser-engineering */}

I have extended Markdown parsers and static-site tooling where standard Markdown could not represent the required content.

<CapabilityGrid>

* **Diagrams and mathematics**<br />
  PlantUML, Mermaid, Graphviz, C4 software architecture diagrams and LaTeX mathematical notation.

* **Reuse and code samples**<br />
  Content reuse, conditional text and code-sample injection.

* **Complex HTML structures**<br />
  Tools that convert complex HTML into embedded HTML or mixed Markdown and HTML, including tables with `rowspan`, `colspan` and multi-line cells.

</CapabilityGrid>

## Content migration and transformation {/* #content-migration-and-transformation */}

I build migration tools in Python and Scala to automate large documentation moves.

<CapabilityGrid>

* **Source conversion**<br />
  Wiki-to-Markdown, Sphinx-to-Markdown and Confluence XHTML to MadCap Flare XHTML conversion.

* **Structure and reuse**<br />
  HTML parsing, structural transformation and reusable-content conversion.

* **Links and metadata**<br />
  Link preservation and rewriting, absolute-to-relative link conversion, and frontmatter and metadata generation.

</CapabilityGrid>

I developed tooling that converted approximately **900 legacy pages** into the Morgan Stanley platform’s extended Markdown format. Migration work also includes validating generated Markdown and HTML. For large migrations, I use page-view analytics to identify high-value content and flag potentially obsolete material for review or archival.

## Documentation tooling and automation {/* #documentation-tooling-and-automation */}

<CapabilityGrid>

* **Content processing**<br />
  Migration scripts, frontmatter processing and automated landing-page generation.

* **Authoring workflows**<br />
  Diagram generation and Git workflow automation.

* **Editorial checks**<br />
  Automated grammar and spelling checks, link checking and LLM-assisted editorial review.

</CapabilityGrid>

## Validation and quality engineering {/* #validation-and-quality-engineering */}

I automate checks on pull requests to catch documentation defects before merge.

<CapabilityGrid variant="checklist">

* Link and Markdown syntax checks

* Grammar, spelling and Vale style-guide checks

* Accessibility checks

* Migration-output validation

* OCR checks for obsolete terminology in screenshots and legacy diagrams

* Automated quality checks on pull requests

</CapabilityGrid>

## Search and retrieval {/* #search-and-retrieval */}

I have integrated and tested traditional enterprise search, browser-based search using tools such as FlexSearch.js, and RAG-based retrieval.

My RAG work has included generating sitemaps for indexing, testing retrieval quality and identifying issues such as search returning deprecated content. I proposed metadata filtering to address that problem.

## Engineering for scale {/* #engineering-for-scale */}

<CapabilityGrid>

* **Large documentation estates**<br />
  Manage thousands of pages and improve build and publishing processes.

* **Distributed contribution**<br />
  Scale Git-based workflows and support engineering contributors with documentation standards and tooling.

* **Migration and reuse**<br />
  Automate large content migrations and reduce duplication through reusable content.

</CapabilityGrid>
