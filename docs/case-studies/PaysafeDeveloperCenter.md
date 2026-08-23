---
title: Building the Paysafe Developer Center
slug: /case-studies/paysafedevcenter
sidebar_position: 2
---

## Project overview

Following the merger of Skrill and Optimal Payments, I led the documentation work for the first Paysafe Developer Center, bringing payment APIs, SDKs and integration guides from previously separate businesses into a single site with consistent navigation. I defined the documentation strategy and information architecture, worked with the web team on the publishing platform, authored API and integration content, and managed three technical writers.

The Developer Center was highlighted in Paysafe's 2016 Annual Report as one of its key achievements under the company's “State-of-the-art technology” strategy. Paysafe described it as a developer self-service portal for merchants and the developer community. See [page 12 of the FCA-hosted Annual Report](https://data.fca.org.uk/artefacts/NSM/data-migration/130622071.pdf). The project was delivered during a period of rapid growth at Paysafe, which [reported 2016 revenue of just over $1 billion](https://www.lse.co.uk/rns/final-results-for-year-ended-31-december-2016-289578jyg4e347g.html).

## The challenge

The merger created several documentation challenges:

* Consolidate hundreds of pages of documentation from previously separate businesses into one developer portal.
* Design an information architecture for multiple APIs, SDKs and integration methods.
* Establish practical review processes involving writers, developers and product teams.
* Create repeatable documentation build and publishing processes.
* Train the writing team in Git, REST APIs and web-development fundamentals.

## My approach

I reviewed developer portals from PayPal, Braintree and Stripe and used the findings to shape how the site organised products, guides and API references, as well as its navigation and search features. From that research, I designed product landing pages, hierarchical navigation and the overall structure for API, SDK and integration content. I also helped define search requirements and tested the implementation delivered by the web development team.

For publishing, I worked with the web development team to define and test a CI-based workflow for the Git-managed documentation source. The workflow published builds to a staging environment for review, then pushed approved content to the CMS through a TYPO3 integration for public release.

I wrote migration tooling to move hundreds of pages from the previous Confluence-based Optimal Payments developer centre into the new platform.

Alongside the platform work, I authored new API and integration documentation and used Paysafe sandbox environments to build working integrations, validate the instructions and improve the documentation.

## Key contributions

* Led documentation delivery for the first Paysafe Developer Center.
* Designed the Developer Center information architecture.
* Introduced and administered Git-based source control for the writing team.
* Built legacy-content migration tooling.
* Authored API and integration documentation, including API reference documentation using API Blueprint.
* Created interactive JavaScript examples for Paysafe Checkout and Paysafe.js.
* Managed and trained three technical writers.

## What I would change

* Today, I would prefer a full docs-as-code approach using extended Markdown with automated quality checks rather than the hybrid Flare/XHTML model I used at the time. The documentation was already managed in Git, reviewed through pull requests and published through CI, but authors worked in Flare and the source remained in its proprietary XHTML-based format. Using extended Markdown would make the source easier for engineers and support staff to edit directly while still supporting requirements such as reuse and conditional content.

* I would also use Python HTML-parsing libraries such as Beautiful Soup to clean migrated content rather than relying on regular-expression replacements, which required more manual cleanup.
