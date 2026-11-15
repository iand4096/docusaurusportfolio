---
organisations:
  - mastercard
title: Masterpass Integration Guide
sidebar_position: 3
sidebar_custom_props:
  sampleCard:
    tag: API integration
    description: Developer documentation for integrating Mastercard's Masterpass digital wallet into
      merchant checkout flows across web and mobile applications.
    highlights:
      - Built working integrations to validate multiple checkout flows
      - Corrected OpenAPI reference issues and created PlantUML sequence diagrams
    ariaLabel: View the Masterpass Integration Guide documentation sample
type:
  - doc-sample
audiences:
  - developers
  - technical-writers
topics:
  - api-documentation
  - technical-writing
  - developer-experience
  - docs-as-code
  - payments
technologies:
  - masterpass
  - openapi
  - plantuml
  - brightspot-cms
lifecycle:
  - historical
tags:
  - api-documentation
  - brightspot-cms
  - developer-experience
  - docs-as-code
  - mastercard
  - masterpass
  - openapi
  - payments
  - plantuml
  - technical-writing
---

import SemanticLabel, {SemanticLabelGroup} from '@site/src/components/SemanticLabel';

## Project overview {/* #project-overview */}

The **Masterpass Merchant Integration Guide** explained how merchant developers could integrate Masterpass's digital-wallet checkout into their websites and applications.

<SemanticLabel type="contribution">
  Maintained the merchant integration guide while working at Mastercard, built test integrations for the supported checkout flows, added sequence diagrams, corrected the API reference, and updated the mobile SDK guidance.
</SemanticLabel>

The content has received minor updates from other contributors since I left Mastercard but is mostly unchanged as it is now a legacy product replaced by Click to Pay.

## The challenge {/* #the-challenge */}

* Understand and test several related checkout flows with different request, response, and callback sequences.
* Explain interactions between merchant systems, Masterpass services, and users clearly.
* Identify and correct inconsistencies between the integration guides and the API reference maintained in OpenAPI format.

## My approach {/* #my-approach */}

<SemanticLabel type="validation">
  Tested each checkout flow against the documented procedure to identify missing steps, unclear explanations and discrepancies in the API reference.
</SemanticLabel>

I created detailed sequence diagrams using PlantUML to show the order of interactions between the merchant, the customer, and Masterpass. The diagrams made complex checkout flows easier to understand and provided developers with a visual overview before they followed the integration instructions.

I worked with the product owner to correct errors and omissions in the underlying OpenAPI definitions as well as the related guide content. I also reviewed and updated the Masterpass mobile SDK documentation to keep it aligned with the main merchant integration guidance.

<SemanticLabelGroup>

<SemanticLabel type="constraint" appearance="row">
  Brightspot, the marketing-focused CMS used for the documentation, made structured authoring, content reuse, version control and technical review difficult.
</SemanticLabel>

<SemanticLabel type="contribution" appearance="row">
  Worked with another technical writer to advocate for a docs-as-code alternative, define requirements and test early prototypes of Mastercard's first docs-as-code documentation platform.
</SemanticLabel>

</SemanticLabelGroup>

## Deliverables {/* #deliverables */}

* Updated Masterpass merchant integration documentation covering the supported checkout flows.
* Working test integrations used to validate the documented procedures.
* PlantUML sequence diagrams illustrating the interactions within each checkout flow.
* Corrections and improvements to the OpenAPI-based API reference.
* Updated Masterpass mobile SDK integration guides.
* Requirements and testing feedback for Mastercard’s first docs-as-code developer-documentation platform with features such as conditional text and content reuse.

:::note[Published guide]

The guide is publicly available on Mastercard Developers. A direct link is omitted to comply with the site’s linking terms. Go to https://developer.mastercard.com/, press **Ctrl + K** to open search, type **Masterpass Merchant Integration** and select the first item in the list.

:::

## Outcome {/* #outcome */}

* Provided clearer and more accurate instructions based on tested checkout integrations. The sequence diagrams made the relationships between systems and the order of API interactions easier for merchant developers to understand.
* Corrected the underlying OpenAPI definitions to improve the consistency between the narrative guides and the API reference.
* The docs-as-code platform that we advocated for, specified, and tested was subsequently adopted by Mastercard.

## What I would change {/* #what-i-would-change */}

* Move the documentation to a docs-as-code workflow earlier in the project to reduce the time spent working around the limitations of the Brightspot CMS.
