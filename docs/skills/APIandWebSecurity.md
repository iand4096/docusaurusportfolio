---
title: API and Web Security
sidebar_position: 6
slug: /apiwebsecurity
sidebar_custom_props:
  skillCard:
    tag: API and application security
    description: Practical experience implementing, testing, and documenting API and web-application security across financial-services and payment platforms, including authentication, encryption, certificates, signing, key management, and secure integration patterns.
    highlights:
      - OAuth, mTLS, PKI, JWT and digital signatures
      - Mastercard field-level encryption validation
      - Secure webhook and callback integration testing
      - Security-focused API documentation and gap analysis
    ariaLabel: Explore my API and Web security skills
---

## API authentication, Cryptography and transport security

Strong practical understanding of API and web application security gained through hands-on development, testing, and documentation of financial-services and payment platforms at Mastercard, Morgan Stanley, Paysafe, and other organisations.

* Experience with **OAuth 1.0, token-based authentication, signed API requests, API credentials, mTLS, PKI, X.509 certificates, HTTPS/TLS, and certificate-based client authentication**.
* Knowledge of **JOSE, JWT, digital signatures, symmetric and asymmetric encryption**, message integrity, trust chains, and secure transmission of structured data.
* Familiar with secure handling of **API keys, secrets, certificates, tokens, and cryptographic keys**, including **HSM-based key management** and key rotation.

## Encryption and secure API integration

* Hands-on experience implementing and documenting **field-level encryption** for Mastercard APIs. Developed cloud-hosted Python encryption and decryption integrations to validate actual API behaviour and identify gaps in developer documentation.
* Built full-stack sandbox integrations using **Python/Flask, Java, JavaScript, and Node.js**, providing practical understanding of security boundaries between browsers, backend services, and external APIs.
* Built and tested **webhook and asynchronous callback** integrations, including Mastercard payment and tokenisation workflows, with attention to endpoint authentication, request validation, integrity checking, HTTPS, and replay protection.

## Secure API and web application testing

* Used **Postman, Insomnia, Python, Java, and custom integration code** to test authentication, encryption, REST APIs, error handling, webhooks, and end-to-end integration flows.
* Practical awareness of common **OWASP web application and API security risks**, including injection, cross-site scripting, authentication and access-control weaknesses, insecure configuration, sensitive-data exposure, and untrusted input, reinforced through regular web-security training at Morgan Stanley.

## Security documentation and gap analysis

* Translate complex security mechanisms into accurate developer guidance covering authentication, encryption, certificates, signing, key handling, secure request construction, and troubleshooting.
* At Mastercard, I validated security behaviour using working integrations and avoided relying solely on specifications or engineering descriptions.
* Identified a security weakness in an early **Click to Pay** integration where security-relevant values were passed in custom HTTP headers that were not covered by Mastercard's OAuth 1 request signing. Raised the issue with the API team, resulting in a change to the API design.
