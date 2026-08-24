---
title: MDES for Merchants Guide
sidebar_position: 2
sidebar_custom_props:
  sampleCard:
    tag: API integration
    description: Mastercard tokenisation documentation developed through custom Python integration testing, OAuth 1.0 authentication, field-level encryption, and webhook validation.
    highlights:
      - Wrote the first MDES for Merchants use-case guide
      - Built custom Python test integrations
      - Validated OAuth, encryption, and webhooks
      - Improved the supporting OpenAPI reference
    ariaLabel: View the MDES for Merchants documentation sample
---

## Project overview

I wrote the first version of the **MDES for Merchants Use Case Guide** while working at Mastercard. The guide explains how merchants can use the Mastercard Digital Enablement API to replace payment card numbers - Primary Account Numbers, or PANs - with securely stored payment tokens.

Unlike card numbers, tokens can continue to work when the underlying card is replaced or reported lost, making them particularly useful for recurring and subscription payments.

The Digital Enablement API provides access to Mastercard Digital Enablement Service (MDES), Mastercard’s card-tokenisation platform. The published guide has since received minor updates from other contributors.

## The challenge

* Explain a technically complex and unfamiliar tokenisation workflow to merchant developers.
* Document non-standard API security requirements, including OAuth 1.0 authentication and field-level encryption.
* Test an API that did not work with standard REST API testing tools such as Postman.
* Receive and validate asynchronous webhook notifications during end-to-end testing.
* Identify and resolve problems in the Mastercard Digital Enablement API which the guide depended on.

## My approach

To understand and verify the complete integration workflow, I created custom test code in Python using the Requests library and open-source cryptography libraries. This allowed me to generate the required OAuth 1.0 authentication data, encrypt and decrypt protected fields, send API requests, and inspect the responses.

I also developed a cloud-hosted Flask application on PythonAnywhere to provide a publicly accessible endpoint for receiving and examining webhook notifications. This provided the means to test asynchronous parts of the merchant tokenisation lifecycle that could not be validated through local requests alone.

While testing the documented workflows, I found issues and omissions in the supporting API reference. I worked with the product owner to correct these problems.

## Deliverables

* The first version of the **MDES for Merchants Use Case Guide**, covering the end-to-end merchant tokenisation workflow.
* Technical guidance for OAuth 1.0 authentication, field-level encryption, API requests, responses, and webhook notifications.
* Corrections and improvements to the supporting Digital Enablement API reference documentation in OpenAPI schema format.

Two internal deliverables provided to the product manager and other technical writers to encourage a culture of end-to-end product testing:

* Custom Python code used to test and validate the integration.
* A cloud-hosted Flask implementation used to receive webhook notifications.

:::note[Published guide]

The guide is publicly available on Mastercard Developers. A direct link is omitted to comply with the site’s linking terms. Search for **"MDES for Merchants Use Case Guide"** to view the current publication.

:::

## Outcome

The guide gave merchant developers a practical explanation of how to integrate with a complex tokenisation API whose security and testing requirements could not be demonstrated using standard REST API tools.

The investigation required to produce the guide also led to extensive improvements to the underlying API reference documentation. The original guide was published on Mastercard Developers and has since received minor updates from other contributors.

## What I would change

If security restrictions allowed, I would provide developers with public runnable examples demonstrating authentication, encryption, decryption, and webhook handling. This was originally omitted due to the burden of maintaining this security-critical code in multiple target languages using approved cryptography libraries.
