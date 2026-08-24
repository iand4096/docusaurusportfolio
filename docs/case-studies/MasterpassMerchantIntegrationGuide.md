---
title: Masterpass Integration Guide
sidebar_position: 4
---

## Project overview

I maintained and updated the **Masterpass Merchant Integration Guide** while working at Mastercard. The guide explained how merchants could integrate the Masterpass digital-wallet checkout flows into their websites and applications.

My main contribution was to build test integrations for each checkout flow and use the results to improve the accuracy and clarity of the documentation. I also added detailed sequence diagrams, corrected issues in the supporting API reference, and updated the Masterpass mobile SDK guides.

The content has received minor updates from other contributors since I left Mastercard as it is now a legacy product replaced by Click to Pay.

## The challenge

* Understand and test several related checkout flows with different request, response, and callback sequences.
* Explain interactions between merchant systems, Masterpass services, and users clearly.
* Identify and correct inconsistencies between the integration guides and the API reference maintained in OpenAPI format.
* Maintain developer documentation in Brightspot, a marketing-focused content-management system that was not designed for structured technical documentation.

## My approach

I built working test integrations for the supported Masterpass checkout flows so that I could validate the documented procedures against the behaviour of the APIs. This allowed me to identify missing steps, unclear explanations, and discrepancies in the supporting API reference.

I created detailed sequence diagrams using PlantUML to show the order of interactions between the merchant, the customer, and Masterpass. The diagrams made complex checkout flows easier to understand and provided developers with a visual overview before they followed the detailed integration instructions.

When I found errors or omissions in the API reference, I corrected the underlying OpenAPI definitions as well as the related guide content. I also reviewed and updated the Masterpass mobile SDK documentation to keep it aligned with the main merchant integration guidance.

Brightspot made structured authoring, content reuse, version control, and technical review difficult. Working with another technical writer who joined at the same time, I advocated for a docs-as-code alternative. Together, we specified the requirements for the first version of the new platform and tested its authoring and publishing workflow.

## Deliverables

* Updated Masterpass merchant integration documentation covering the supported checkout flows.
* Working test integrations used to validate the documented procedures.
* PlantUML sequence diagrams illustrating the interactions within each checkout flow.
* Corrections and improvements to the OpenAPI-based API reference.
* Updated Masterpass mobile SDK integration guides.
* Requirements and testing feedback for Mastercard’s first docs-as-code developer-documentation platform with features such as conditional text and content re-use.

:::note[Published guide]

The guide is publicly available on Mastercard Developers. A direct link is omitted to comply with the site’s linking terms. Search for **"Masterpass Merchant Integration Guide"** to view the current publication.

:::

## Outcome

* Provided clearer and more accurate instructions based on tested checkout integrations. The sequence diagrams made the relationships between systems and the order of API interactions easier for merchant developers to understand.
* Corrected the underlying OpenAPI definitions to improve the consistency between the narrative guides and the API reference.
* The docs-as-code platform that we advocated for, specified, and tested was subsequently adopted by Mastercard.

## What I would change

* Move the documentation to a docs-as-code workflow earlier in the project to reduce the time spent working around the limitations of the Brightspot CMS.
