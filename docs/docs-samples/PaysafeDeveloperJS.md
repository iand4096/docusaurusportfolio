---
organisations:
  - paysafe
title: Paysafe.js Developer Guide
sidebar_position: 4
sidebar_custom_props:
  sampleCard:
    tag: JavaScript integration
    description: Developer documentation for integrating Paysafe.js hosted payment fields, covering
      secure tokenisation, PCI DSS scope reduction, and browser-based payment workflows.
    highlights:
      - Wrote the first Paysafe.js Developer Guide
      - Built working CodePen examples and an interactive Try Now demonstration
    ariaLabel: View the Paysafe.js Developer Guide documentation sample
type:
  - doc-sample
audiences:
  - developers
topics:
  - api-documentation
  - payments
  - technical-writing
technologies:
  - paysafe-js
  - codepen
  - 3d-secure
  - google-pay
  - apple-pay
  - pci-dss
  - saq-a
  - tokenisation
lifecycle:
  - current
tags:
  - 3d-secure
  - api-documentation
  - apple-pay
  - codepen
  - google-pay
  - payments
  - paysafe
  - paysafe-js
  - pci-dss
  - saq-a
  - technical-writing
  - tokenisation
---

import SemanticLabel, {SemanticLabelGroup} from '@site/src/components/SemanticLabel';

## Project overview {/* #project-overview */}

<SemanticLabel type="contribution">
  Created the first version of the **Paysafe.js Developer Guide** for the newly released product, the original CodePen examples and the inline Try Now demonstration.
</SemanticLabel>

Paysafe.js allows merchants to add attractive, customisable payment forms to their websites while reducing their PCI DSS scope. Sensitive card details are collected through secure fields hosted on Paysafe’s servers using iframes, preventing the merchant’s systems from handling the card data directly. The library then returns a token that the merchant’s systems can use to make a payment request.

The original guide explained both this product model and the core integration workflow, from loading and configuring the JavaScript library to collecting payment details and receiving a token.

The guide has since been expanded by other contributors to cover features including 3D Secure, Google Pay, Apple Pay, and Instant Withdrawal.

## The challenge {/* #the-challenge */}

* Explain the security and compliance advantages of using Paysafe-hosted fields over collecting sensitive card data directly.
* Clarify how the iframe-based fields reduced the merchant’s PCI DSS scope and supported SAQ A compliance.
* Explain the relationship between browser-side data collection, tokenisation, and subsequent server-side payment requests.
* Provide working examples that developers could inspect, modify, and test.
* Make a security-sensitive integration approachable without omitting the configuration, validation, and error handling required for production use.
* Deliver the guide while managing the wider Paysafe Developer Center and leading a team of three technical writers.

## My approach {/* #my-approach */}

<SemanticLabelGroup>

<SemanticLabel type="decision" appearance="row">
  Structure the guide around a complete integration workflow, introducing a basic working implementation before configuration, validation, styling and error handling.
</SemanticLabel>

<SemanticLabel type="rationale" appearance="row">
  Give developers a practical starting point while explaining how browser-side tokenisation connects to subsequent server-side payment requests.
</SemanticLabel>

</SemanticLabelGroup>

The guide first explained the purpose of the hosted fields and tokenisation model. This helped developers understand why sensitive fields appeared within Paysafe-hosted iframes, why card data did not pass through the merchant’s systems, and how this reduced the PCI DSS obligations associated with the integration.

<SemanticLabel type="validation">
  Tested the documented workflow against Paysafe.js, with input from product and engineering teams to ensure that the instructions and examples reflected the expected behaviour.
</SemanticLabel>

## Deliverables {/* #deliverables */}

* The first version of the **Paysafe.js Developer Guide**.
* An explanation of the product’s hosted-field architecture, tokenisation model, and PCI DSS advantages.
* Step-by-step documentation for the core browser-based tokenisation workflow.
* Original CodePen examples demonstrating working integrations.
* An interactive **Try Now** product demonstration inline within the documentation that guided developers through the integration.
* Supporting configuration, validation, styling, and error-handling guidance.
* API reference documentation.

:::note[Published guide]

The current version of the Paysafe.js Developer Guide can be found here on the [Paysafe Developer Center](https://developer.paysafe.com/en/api-docs/paysafe-js/overview/).

:::

## Outcome {/* #outcome */}

The guide gave developers a practical route from understanding Paysafe.js and its compliance benefits to completing a working browser-based payment-tokenisation integration.

## What I would change {/* #what-i-would-change */}

* Maintain the examples alongside the documentation source in place of a separate platform such as CodePen. This would make them easier to version, review, test, and migrate with the guide.
* Introduce automated checks to confirm that the examples continue to work with each supported version of Paysafe.js.
* Add a sequence diagram showing how sensitive payment details pass directly from the Paysafe-hosted fields to Paysafe, while only the resulting token is returned to the merchant.
* Include a companion diagram showing how the merchant’s systems could use that token to submit a payment through the server-side API.
