---
title: Paysafe.js Developer Guide
sidebar_position: 3
---

## Project overview

I was tasked with creating the first version of the **Paysafe.js Developer Guide** for the newly released Paysafe.js product.

Paysafe.js allows merchants to add customisable payment forms to their websites while reducing their PCI DSS scope. Sensitive card details are collected through secure fields hosted by Paysafe in iframes, preventing the merchant’s systems from handling the card data directly. The library then returns a token that the merchant can use to make a payment request.

The original guide explained both this product model and the core integration workflow, from loading and configuring the JavaScript library to collecting payment details and receiving a token.

I also created the original CodePen examples and an interactive inline **Try Now** demonstration that allowed developers to explore the integration step by step.

The guide has since been expanded by other contributors to cover features including 3D Secure, Google Pay, Apple Pay, and Instant Withdrawal.

## The challenge

* Explain the security and compliance advantages of using Paysafe-hosted fields rather than collecting sensitive card data directly.
* Clarify how the iframe-based fields reduced the merchant’s PCI DSS scope and supported SAQ A compliance.
* Explain the relationship between browser-side data collection, tokenisation, and subsequent server-side payment requests.
* Provide working examples that developers could inspect, modify, and test.
* Make a security-sensitive integration approachable without omitting the configuration, validation, and error handling required for production use.
* Deliver the guide while managing the wider Paysafe Developer Centre and leading a team of three technical writers.

## My approach

I structured the guide around the developer’s end-to-end integration workflow rather than documenting the JavaScript API operation by operation. Developers could begin with a basic working implementation and then add configuration, validation, styling, and error handling.

I first explained the purpose of the hosted fields and tokenisation model. This helped developers understand why the sensitive fields appeared within Paysafe-hosted iframes, why card data did not pass through the merchant’s systems, and how this reduced the PCI DSS obligations associated with the integration.

I built CodePen examples so developers could inspect and modify working integrations without first creating a complete local project. I also developed an interactive **Try Now** demonstration that divided the integration into stages and showed how each part contributed to the completed payment form.

I tested the documented workflow against the Paysafe.js implementation and worked with product and engineering teams to ensure that the instructions and examples reflected the expected behaviour.

## Deliverables

* The first version of the **Paysafe.js Developer Guide**.
* An explanation of the product’s hosted-field architecture, tokenisation model, and PCI DSS advantages.
* Step-by-step documentation for the core browser-based tokenisation workflow.
* Original CodePen examples demonstrating working integrations.
* An interactive **Try Now** product demonstration inline within the documentation that guided developers through the integration.
* Supporting configuration, validation, styling, and error-handling guidance.
* API reference documentation.


:::note[Published guide]

The current version of the guide is publicly available on the [Paysafe Developer Centre](https://developer.paysafe.com/en/api-docs/paysafe-js/overview/).

:::

## Outcome

The guide gave developers a practical route from understanding Paysafe.js and its compliance benefits to completing a working browser-based payment-tokenisation integration.

The CodePen examples and interactive demonstration supplemented the documentation with working content that developers could explore and adapt.

The interactive inline demo within the documentation showcased the product and provided a way for developers to quickly test the integration flow with an example token.

The guide established the foundation for the current Paysafe.js documentation, which has since been extended to cover additional payment methods and functionality.


## What I would change

* Maintain the examples alongside the documentation source rather than on a separate platform such as CodePen. This would make them easier to version, review, test, and migrate with the guide.
* Introduce automated checks to confirm that the examples continue to work with each supported version of Paysafe.js.
* Add a sequence diagram showing how sensitive payment details passed directly from the Paysafe-hosted fields to Paysafe, while only the resulting token was returned to the merchant.
* Include a companion diagram showing how the merchant’s server could use that token to submit a payment through the server-side API.
