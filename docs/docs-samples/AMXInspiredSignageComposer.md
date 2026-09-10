---
title: AMX Digital Signage User Manual
sidebar_position: 5
sidebar_custom_props:
  sampleCard:
    tag: User documentation
    description: Single-source user and administrator documentation for a networked digital-signage 
      platform, produced as context-sensitive HTML help and PDF from one MadCap Flare project.
    highlights:
      - Created role-specific HTML help and PDF outputs
      - Used conditional text and reusable content to minimise duplication
      - Documented configuration, permissions, publishing, and troubleshooting
      - Applied practical TCP/IP and device-connectivity knowledge
    ariaLabel: View the AMX Digital Signage User Manual documentation sample
type:
  - doc-sample
audiences:
  - end-users
  - system-administrators
  - technical-writers
topics:
  - technical-writing
  - information-architecture
technologies:
  - madcap-flare
  - mermaid
  - tcp-ip
  - vale
  - languagetool
lifecycle:
  - current
tags:
  - information-architecture
  - languagetool
  - madcap-flare
  - mermaid
  - tcp-ip
  - technical-writing
  - vale
---

## Project overview

I wrote the user documentation for version 5 of AMX Composer, a content-management application for the AMX Digital Signage platform. Version 5 was a complete rewrite of the original Windows client-server application with many new features including a redesigned user interface, and a new web-based technology stack.

The guide supported administrators and end users through the complete digital-signage workflow, from creating and approving content to publishing it to networked players. It also covered system configuration, permissions, reporting, troubleshooting, and advanced playlist concepts.

This work required a practical understanding of TCP/IP networking, 2D graphics and troubleshooting connectivity issues for networked digital-signage systems.

## The challenge

* Support administrators and end users without overwhelming either audience with irrelevant information.
* Produce context-sensitive HTML help and a printable PDF from the same source content.
* Minimise or eliminate duplicated content while allowing audience-specific variations.
* Understand and explain a complex digital-signage application clearly.

## My approach

I carried out extensive testing with the application and spent time discussing the concepts behind the product with the developers to help understand the problems Digital Signage user face and how Composer's features could be used to create high quality signage.

I created a single-source [MadCap Flare](../tools/Flare.md) project using reusable content, conditional text, separate build targets, and separate source TOCs. Shared concepts and procedures were maintained once, while administrator-only content was conditionally included in the relevant HTML and PDF outputs.

This approach produced audience-specific help without requiring separate documentation sets. I also used cross-references in place of HTML-only hyperlinks so that links remained usable in both the online and print outputs.

## Deliverables

* The primary output: two different context-sensitive HTML help bundles accessible within the application with the specific version determined by the user's role - either end user or administrator. 
* A secondary output: a PDF administrator manual containing the same content as the help bundles in print form. This PDF is the only version available without purchasing the application.

:::note[Published guide]

View the finished PDF manual on the [AMX website](https://www.amx.com/en/site_elements/reference-guide-composer-5-4-desktop-edition). Note the HTML help is not publicly available.

:::

## Outcome

The HTML help and PDF manual were successfully released with the product and received positive internal feedback from the developers and product manager.

## What I would change

* The PDF manual did not include a linked, page-numbered table of contents because I was unable to resolve an issue with Flare’s print output before the release deadline. I would now test print-navigation requirements earlier and allow more time to address output-specific issues.
* I would include the glossary from the HTML help in the PDF manual so that readers could access definitions without using the application.
* Take advantage of modern automated proofreading tools like [Vale](https://github.com/vale-cli/vale) and [LanguageTool](https://github.com/languagetool-org/languagetool). My [portfolio integrates these checks](../case-studies/DocusaurusPortfolio.md).
