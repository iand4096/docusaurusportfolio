---
title: MDES for Merchants Guide
sidebar_position: 2
sidebar_custom_props:
  sampleCard:
    tag: API integration
    description: Mastercard tokenisation documentation developed through custom Python integration 
      testing, OAuth 1.0 authentication, field-level encryption, and webhook validation.
    highlights:
      - Wrote the first MDES for Merchants use-case guide
      - Built custom Python test integrations
      - Validated OAuth, encryption, and webhooks
      - Improved the supporting OpenAPI reference
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

### Project overview

I wrote the first version of the MDES for Merchants Use Case Guide in late 2017, during my first few months at Mastercard. The guide explained how merchant developers can use the MDES Digital Enablement API to replace payment card numbers (PANs) with secure payment tokens, reducing the need to store card details.

This API provides access to Mastercard Digital Enablement Service (MDES), the tokenisation technology that also supports digital wallets such as **Apple Pay**.

In addition to their security benefits, tokens can often remain valid when the underlying payment card is replaced or reported lost, helping to avoid interruptions to recurring payments.

Other contributors subsequently made minor updates to the published guide.

## The challenge

- Explain an unfamiliar and technically complex tokenisation workflow to merchant developers alongside its API security requirements.
- Test the MDES Digital Enablement API, which could not be tested using Postman at the time because:
  - Postman did not support [RSA signatures for OAuth 1.0](https://github.com/postmanlabs/postman-app-support/issues/2302), as required by Mastercard. Support was added in 2020.
  - Mastercard's field-level encryption and decryption required custom cryptographic code that Postman did not provide.
- Test asynchronous webhook notifications, which were blocked by the corporate firewall.
- Identify and resolve errors and omissions in the supporting Digital Enablement API reference.
- Work with Mastercard's custom CMS integration, which had reliability problems affecting both authoring and publishing. It also had poor code-block formatting, limited preview capabilities and inadequate support for content reuse.

## My approach

I had little previous practical experience of cryptography and had never used cryptographic libraries in Python. To understand and test the Digital Enablement API, I developed an end-to-end Python integration for tokenisation and webhook handling, using Flask, Requests and open-source cryptography libraries.

Mastercard's field-level encryption combined symmetric (AES) and asymmetric (RSA) encryption. Sensitive cardholder data was encrypted using a one-time AES session key. The session key was then encrypted using Mastercard's RSA public key and sent with the encrypted data.

I had to learn how to:

1. Load RSA keys and certificates in the formats required by the Python libraries.
2. Implement Mastercard's OAuth 1.0 RSA-SHA256 request signing, including request-body hashing.
3. Implement AES encryption and RSA session-key encryption.
4. Decrypt the encrypted API responses.

Getting the integration to work involved extensive research and trial and error, particularly with binary data and character encoding, AES and RSA padding, request-body hashing and certificate formats. I spent several weekends investigating and resolving these problems.

I also developed a small cloud-hosted Flask application on PythonAnywhere to receive and decrypt asynchronous webhook notifications, which were blocked within the corporate firewall.

Once I had working integrations, I used them to test the API workflows and check the reference documentation. I found errors and omissions in the OpenAPI definitions and worked with the product owner to correct them.

I structured the guide around the tasks merchants needed to perform, rather than individual API endpoints. It covered tokenising new and existing cards, managing token lifecycle events, displaying payment information, making payments and handling customer service scenarios.

I created PlantUML sequence diagrams to illustrate the API interactions. The guide also included practical guidance on bulk-tokenisation rate limits, using webhook notifications to maintain token state rather than polling the API, and the requirements for recurring payments and cryptogram storage.

## Deliverables

### Published guide

The first version of the **MDES for Merchants Use Case Guide** was published on Mastercard Developers.

The guide is no longer available on the live site, but an [archived version](https://web.archive.org/web/20211101102056/https://developer.mastercard.com/mdes-digital-enablement/documentation/use-cases/mdes-for-merchants-use-cases/) is available through the Internet Archive. You may need to select the capture dated 1 November 2021.

### Internal deliverables

I shared my Python integration code and Flask webhook receiver with the product owner and other technical writers so they could test the API themselves.

After completing the guide, I also helped recommend and test an early version of Mastercard's replacement docs-as-code authoring system. Mastercard subsequently adopted docs-as-code for its Developer Center.

## Outcome

The integration testing led to corrections and improvements to the supporting OpenAPI reference and helped me write accurate integration documentation for MDES for Merchants. Sharing the test code also gave other technical writers and the product owner a way to investigate the API directly, helping to encourage a culture of hands-on API testing that had previously been hindered by the API's technical complexity.

The project required me to learn an unfamiliar technical subject, test the API myself and apply what I learned to the developer documentation.

## What I would change

If security restrictions allowed, I would provide public runnable examples demonstrating authentication, encryption, decryption and webhook handling.

I did not include these originally because maintaining security-sensitive code in multiple programming languages, using approved cryptography libraries, would have required significant ongoing work.