---
organisations:
  - mastercard
title: MDES for Merchants Guide
sidebar_position: 2
sidebar_custom_props:
  sampleCard:
    tag: API integration
    description: Developer documentation for integrating Mastercard's Digital Enablement Service
      (MDES) to support secure payment tokenisation in merchant applications.
    highlights:
      - Wrote the first MDES for Merchants use-case guide
      - Built custom cryptographic Python test integrations
    ariaLabel: View the MDES for Merchants documentation sample
type:
  - doc-sample
audiences:
  - developers
topics:
  - api-documentation
  - api-security
  - technical-validation
  - payments
technologies:
  - python
  - requests
  - flask
  - pythonanywhere
  - openapi
  - oauth
  - mdes
  - digital-enablement-api
  - postman
lifecycle:
  - current
tags:
  - api-documentation
  - api-security
  - digital-enablement-api
  - flask
  - mastercard
  - mdes
  - oauth
  - openapi
  - payments
  - postman
  - python
  - pythonanywhere
  - requests
  - technical-validation
---

import SemanticLabel, {SemanticLabelGroup} from '@site/src/components/SemanticLabel';

## Project overview {/* #project-overview */}

The MDES for Merchants Use Case Guide explained how merchant developers can use the MDES Digital Enablement API to replace payment card numbers (PANs) with secure payment tokens, reducing the need to store card details.

<SemanticLabel type="contribution">
  Wrote the first version of the guide in late 2017, during my first few months at Mastercard, developed the test integration and webhook receiver, and created sequence diagrams explaining the API interactions.
</SemanticLabel>

This API provides access to Mastercard's Digital Enablement Service (MDES), the tokenisation technology that also supports digital wallets such as **Apple Pay**.

In addition to their security benefits, tokens can often remain valid when the underlying payment card is replaced or reported lost, helping to avoid interruptions to recurring payments.

Other contributors subsequently made minor updates to the published guide.

## The challenge {/* #the-challenge */}

- Explain an unfamiliar and technically complex tokenisation workflow to developers.
- Identify and resolve errors and omissions in the supporting Digital Enablement API reference.
- Work with Mastercard's custom CMS integration, which had reliability problems affecting both authoring and publishing. It also had poor code-block formatting, limited preview capabilities and inadequate support for content reuse.

## My approach {/* #my-approach */}

<SemanticLabelGroup>

<SemanticLabel type="constraint" appearance="row">
  The available tooling could not handle the required request signing and field-level encryption, while the corporate firewall blocked incoming webhooks.
</SemanticLabel>

<SemanticLabel type="decision" appearance="row">
  Build an end-to-end Python integration and a cloud-hosted Flask webhook receiver to test the tokenisation workflows.
</SemanticLabel>

</SemanticLabelGroup>

At the time, Postman did not support [RSA signatures for OAuth 1.0](https://github.com/postmanlabs/postman-app-support/issues/2302), as required by Mastercard; support was only added in 2020. Field-level encryption and decryption also required custom cryptographic code that Postman did not provide.

I had little previous practical experience of cryptography and had never used cryptographic libraries in Python. The integration used Flask, Requests and open-source cryptography libraries.

Mastercard's field-level encryption combined symmetric (AES) and asymmetric (RSA) encryption. Sensitive cardholder data was encrypted using a one-time AES session key. The session key was then encrypted using Mastercard's RSA public key and sent with the encrypted data.

I had to learn how to:

1. Load RSA keys and certificates in the formats required by the Python libraries.
2. Implement Mastercard's OAuth 1.0 RSA-SHA256 request signing, including request-body hashing.
3. Implement AES encryption and RSA session-key encryption.
4. Decrypt the encrypted API responses.

Getting the integration to work involved extensive research and trial and error, particularly with the following:

* binary data and character encoding
* AES and RSA padding
* request-body hashing
* certificate formats

I spent several weekends investigating and resolving these problems.

The webhook receiver ran on [PythonAnywhere](https://www.pythonanywhere.com/) and received and decrypted asynchronous notifications.

<SemanticLabel type="validation">
  Used the working integration to check API behaviour against the OpenAPI reference, then worked with the product owner to correct identified errors and omissions.
</SemanticLabel>

I structured the guide around the tasks merchants needed to perform, rather than individual API endpoints. It covered tokenising new and existing cards, managing token lifecycle events, displaying payment information, making payments and handling customer service scenarios.

The guide also included practical guidance on bulk-tokenisation rate limits, using webhook notifications to maintain token state rather than polling the API, and the requirements for recurring payments and cryptogram storage. The sequence diagrams were created in PlantUML.

## Deliverables {/* #deliverables */}

### Published guide {/* #published-guide */}

The first version of the **MDES for Merchants Use Case Guide** was published on Mastercard Developers.

The guide is no longer available on the live site, but an [archived version](https://web.archive.org/web/20211101102056/https://developer.mastercard.com/mdes-digital-enablement/documentation/use-cases/mdes-for-merchants-use-cases/) is available through the Internet Archive. You may need to select the capture dated 1 November 2021.

### Internal deliverables {/* #internal-deliverables */}

I shared my Python integration code and Flask webhook receiver with the product owner and other technical writers so they could test the API themselves.

After completing the guide, I also helped recommend and test an early version of Mastercard's replacement docs-as-code authoring system. Mastercard subsequently adopted docs-as-code for its Developer Center.

## Outcome {/* #outcome */}

The tested workflows informed the integration guidance. The shared test code helped encourage a culture of hands-on API testing that the API's technical complexity had previously hindered.

The project required me to learn an unfamiliar technical subject, test the API myself and apply what I learned to the developer documentation.

## What I would change {/* #what-i-would-change */}

If security restrictions allowed, I would provide public runnable examples demonstrating authentication, encryption, decryption and webhook handling.

I did not include these originally because maintaining security-sensitive code in multiple programming languages, using approved cryptography libraries, would have required ongoing security review and maintenance.
