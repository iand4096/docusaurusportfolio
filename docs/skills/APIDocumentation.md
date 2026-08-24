---
title: API Documentation and Technical Validation
sidebar_position: 3
slug: /apidocumentation
sidebar_custom_props:
  sampleCard:
    tag: API documentation
    description: >-
      API and SDK documentation validated through working integrations, API testing,
      authentication and encryption workflows, and hands-on technical investigation.
    highlights:
      - OpenAPI, SDK and integration documentation
      - Python, Java and JavaScript test integrations
      - Authentication, encryption and webhook validation
      - Test-driven documentation and defect investigation
    ariaLabel: Explore my API documentation and technical validation skills
---

Twelve years of experience creating API and SDK documentation for financial-services and payments platforms at Morgan Stanley, Mastercard and Paysafe, supported by a software-development background.

I do not rely solely on specifications or subject-matter expert interviews. Where practical, I build and test realistic integrations, reproduce developer workflows and validate security and API behaviour before documenting them. This helps me identify gaps between specifications, implementation and published guidance.

## API and SDK documentation

My experience includes:

* Conceptual guides, integration tutorials, use-case documentation, SDK documentation and REST API reference content
* OpenAPI authoring and maintenance for generated reference documentation
* Handwritten SDKs and language-specific clients generated from OpenAPI specifications
* Relationships between REST endpoints, SDK methods, request and response models and authentication configuration
* Multi-step API workflows and sequence diagrams
* Authentication and encryption
* Webhooks and asynchronous processing
* Error handling, retries and resilience patterns
* Code examples designed around realistic developer tasks

I focus on the complete developer journey rather than documenting individual endpoints in isolation.

## Integration development and technical validation

I build working integrations where doing so provides a more reliable basis for documentation.

My experience includes:

* Python applications using `requests` for authenticated API calls
* Flask applications exposing API endpoints and rendering browser-based workflows
* Java integrations using embedded Jetty services
* JavaScript and browser-based integrations
* Postman, Insomnia and cURL
* Cloud-hosted Flask applications for receiving and processing webhooks
* Multi-step synchronous and asynchronous transaction flows
* Sandbox and production-like test environments

I use these integrations to compare documented behaviour with actual system behaviour and to investigate missing, ambiguous or incorrect guidance.

At Mastercard, for example, internal network restrictions made some externally initiated workflows difficult to test. I created cloud-hosted encryption, decryption and webhook integrations so that I could validate real API and asynchronous behaviour rather than relying entirely on mocked responses or specifications.

## API testing and developer tooling

I use testing as part of the documentation process rather than treating validation as a final editorial check.

This includes:

* Building reusable Postman and Insomnia request collections
* Testing request parameters, headers and payloads
* Exercising authentication and encryption flows
* Testing error responses and edge cases
* Validating webhook and callback behaviour
* Creating repeatable scenarios for multi-step API workflows
* Comparing observed behaviour with OpenAPI definitions, generated clients and written documentation
* Testing documented procedures and code examples before publication

I have also extended developer tooling where standard functionality was insufficient. For example, I created Node.js extensions for Insomnia to support non-standard authentication requirements including Mastercard OAuth 1.0.

## Authentication, encryption and API security

I have practical experience implementing, testing and documenting security mechanisms used by financial-services and payment APIs, including:

* OAuth 1.0 and signed API requests
* Mutual TLS
* X.509 certificates and PKI
* JWT and JOSE
* Digital signatures
* Symmetric and asymmetric encryption
* Field-level encryption and decryption
* HTTPS/TLS
* API credentials, tokens and secrets
* Certificate and cryptographic-key handling
* Secure webhook and callback processing

I have written Python code to process certificates, encrypt and decrypt payloads, create and validate tokens and test secure integrations in sandbox environments.

My role is not to position myself as an application-security specialist. The value of this experience is that I can investigate security-sensitive API behaviour directly and translate complex authentication and cryptography requirements into accurate developer guidance.

### Security validation in practice

At Mastercard, I identified a weakness in an early Click to Pay integration in which security-relevant values were supplied through custom HTTP headers that were not covered by OAuth request signing.

I raised the issue with the API team, resulting in a change to the API design.

This is representative of my approach to API documentation: implementation and validation can uncover issues that are difficult to identify from specifications alone.

## Test-driven documentation

I apply a test-driven approach to technical writing.

Rather than assuming an existing specification, implementation or document is correct, I verify technical claims where practical by using the software itself.

This can involve:

1. Building a realistic integration.
2. Following the documented workflow.
3. Exercising normal and edge-case behaviour.
4. Comparing the results with the specification and documentation.
5. Investigating discrepancies.
6. Updating the guidance only after the expected behaviour is understood.

This approach has helped me identify:

* Undocumented behaviour
* Incomplete integration guidance
* Incorrect assumptions about API behaviour
* Authentication and encryption issues
* Differences between sandbox and production behaviour
* Confusing error handling
* Problems in developer workflows

It also reduces dependency on subject-matter experts because I can resolve many implementation questions independently and reserve their time for issues requiring specialist product knowledge.

## Technical investigation

My software-development background is useful when API behaviour is poorly documented or the original subject-matter expertise is no longer available.

For example, I have analysed complex Scala implementation code to reconstruct undocumented API behaviour and then validated my understanding before documenting it.

I am comfortable moving between specifications, source code, logs, API clients, working integrations and developer documentation to establish what a system actually does.

## Defect investigation and release readiness

My testing experience extends beyond documentation-specific validation.

I have performed black-box, component, integration, release and usability testing and have experience:

* Identifying and reproducing software defects
* Recording expected and actual behaviour
* Providing clear reproduction steps and supporting evidence
* Raising and managing defects through Jira
* Working with engineers to clarify issues
* Retesting fixes
* Helping prioritise defects based on severity, customer impact, security and release readiness

Earlier in my career, I took on dedicated QA responsibilities for a software project alongside my documentation work. I raised approximately **600 issues**, helping the team move the product towards a more stable and releasable state.

That experience continues to influence how I approach technical documentation: I treat unexpected behaviour as something to investigate rather than something to explain away.

## Documentation grounded in working software

My development and testing experience allows me to work as both a technical writer and a technical investigator.

For API documentation, that means being able to move beyond describing endpoints and instead answer questions such as:

* Can a developer actually complete this integration?
* Does the implementation behave as the specification says?
* Are authentication and encryption instructions complete?
* Do code examples execute successfully?
* What happens outside the happy path?
* Are sandbox behaviours representative of production?
* Are asynchronous workflows and callbacks testable?
* Does the documentation explain enough for a developer to diagnose failures?

The objective is documentation that has been validated against real developer workflows and gives developers a reliable basis for building secure, robust integrations.
