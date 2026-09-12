---
title: Building the Paysafe Developer Center
description: Case study of leading the documentation work for the launch of the 
  Paysafe Developer Center
slug: /case-studies/paysafedevcenter
sidebar_position: 2
type:
  - case-study
audiences:
  - developers
  - documentation-managers
  - technical-writers
topics:
  - api-documentation
  - information-architecture
  - docs-as-code
  - documentation-engineering
  - developer-experience
technologies:
  - git
  - api-blueprint
  - hypothesis
  - typo3
  - rest
lifecycle:
  - historical
tags:
  - api-blueprint
  - api-documentation
  - developer-experience
  - docs-as-code
  - documentation-engineering
  - git
  - hypothesis
  - information-architecture
  - rest
  - typo3
---

## Context

Following the merger of Skrill and Optimal Payments to form Paysafe, I led the documentation work for the launch of the Paysafe Developer Center for Merchant developers integrating Paysafe's payment methods. This work brought payment API and SDK reference documentation and integration guides from previously separate businesses into a single modern developer site.

I defined the documentation strategy and information architecture, worked with the web development team on the publishing platform, and authored API and integration documentation, while managing a team of three technical writers.

## Challenge

* Consolidate hundreds of pages of documentation from previously separate businesses into one developer portal.
* Define an information architecture for multiple payment APIs, SDKs and integration methods.
* Establish a consistent structure for product, integration and reference documentation.
* Create a Git-based documentation workflow with repeatable build, review and publishing processes.
* Migrate existing documentation from the previous Optimal Payments developer centre and Skrill PDF documentation.
* Coordinate documentation across concurrent API, product and platform releases.
* Introduce the writing team to Git, MadCap Flare for structured authoring, and develop their understanding of REST APIs and web technologies.

## Approach

I reviewed developer portals from PayPal, Braintree and Stripe and used the findings to help define the features of the new site; how it should organise products, guides and API references; and the requirements for the documentation tool chain.

From this research, I designed the overall information architecture, including product landing pages, hierarchical navigation, and the structure for API / SDK reference guides and other integration content. I also defined search requirements and validated the implementation.

Working with Paysafe's web development team, I helped establish the documentation publishing workflow: source was maintained in Git, builds were published to a staging environment for review, and approved content was pushed to the public site through a custom CMS integration.

As Documentation Manager, I managed three technical writers and prioritised work across API documentation, SDK documentation, and platform improvements.

## Implementation

The Developer Center included:

* Product landing pages and hierarchical navigation for API, SDK and integration documentation.
* Git-based source control and documentation review.
* A CI-based staging and publishing process.
* Integration with the TYPO3 content-management system.
* Search functionality based on requirements I helped define and test.
* Rendered-page review using Hypothesis annotations, allowing reviewers to comment directly on pages rather than reviewing source files in isolation in Git.
* Page-level documentation feedback.

I developed migration tooling to move hundreds of pages from the previous Confluence-based Optimal Payments developer centre into the new site.

Alongside this work, I authored API and integration documentation, including API reference material using API Blueprint, and introduced documentation processes and training for the team of three technical writers.

## Impact

The first phase of the Developer Center launched in December 2016. Paysafe subsequently included the Developer Center launch in its [2016 Annual Report](https://data.fca.org.uk/artefacts/NSM/data-migration/130622071.pdf) as one of its achievements under its “State-of-the-art technology” strategy. Paysafe also mentioned the Developer Center in its January 2017 trading update. The launch was reported in the financial technology press, including [Finextra](https://www.finextra.com/pressarticle/67611/paysafe-expected-to-surpass-1-billion-revenue-milestone-in-fy-2016). Paysafe was a rapidly growing business at that time that reported 2016 revenue of just over $1 billion.

## Lessons learned

* Today, I would prefer a full docs-as-code approach using extended Markdown with automated quality checks rather than the hybrid Flare/XHTML model I used at the time. The documentation was already managed in Git, reviewed through pull requests and published through CI, but authors worked in Flare and the source remained in its proprietary XHTML-based format. Using extended Markdown would make the source easier for engineers and support staff to edit directly while supporting requirements such as reuse and conditional content.

* I would also use Python HTML-parsing libraries such as Beautiful Soup to clean migrated content rather than relying on regular-expression replacements, which required more manual clean-up.
