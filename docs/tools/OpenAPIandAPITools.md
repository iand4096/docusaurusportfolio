---
title: OpenAPI and API tools
description: Maintaining API contracts and executable integration tests to improve the accuracy and usability of developer documentation.
sidebar_position: 2
slug: /openapitools
sidebar_custom_props:
  sampleCard:
    tag: API specifications
    description: >-
      Maintaining API contracts and executable integration tests to improve the
      accuracy and usability of developer documentation.
    highlights:
      - Designed reusable OpenAPI schemas and security definitions
      - Extended Insomnia plugins for custom authentication and encryption
    ariaLabel: Explore my API specification and API testing tools
type:
  - tool
audiences:
  - developers
  - technical-writers
topics:
  - api-documentation
  - technical-validation
  - developer-experience
technologies:
  - openapi
  - api-blueprint
  - postman
  - insomnia
  - curl
  - json
  - yaml
  - python
  - scala
  - rest
  - javascript
  - node-js
lifecycle:
  - current
tags:
  - api-blueprint
  - api-documentation
  - curl
  - developer-experience
  - insomnia
  - javascript
  - json
  - node-js
  - openapi
  - postman
  - python
  - rest
  - scala
  - technical-validation
  - yaml
---

import CapabilityGrid from '@site/src/components/CapabilityGrid';

I maintain API specifications and test them against live API behaviour using Postman, Insomnia, cURL and custom tooling.

## OpenAPI, Postman, Insomnia, cURL {/* #openapi-postman-insomnia-curl */}

<CapabilityGrid>

* **Specifications**<br />
  Maintained Swagger 2.0 / OpenAPI 2.0 specifications at Mastercard for generated API reference documentation. Covered HTTP methods, status codes, headers, query-string and path parameters, request and response bodies, and authentication mechanisms. Used API Blueprint at Paysafe.

* **Reusable schemas**<br />
  Designed reusable OpenAPI definitions using `$ref`, shared schemas, parameters, responses and security definitions to reduce duplication and maintain consistency across large specifications.

* **Request collections**<br />
  Created and maintained Postman and Insomnia collections with executable API requests, authentication configuration and representative examples for external developers.

* **API validation**<br />
  Used Postman, Insomnia and cURL to execute authenticated requests, validate examples and troubleshoot live responses. Compared API contracts with implemented REST behaviour, identified discrepancies in parameters, schemas, status codes, authentication and responses, and worked with engineers to resolve issues and update specifications and documentation.

* **Custom authentication**<br />
  Modified JavaScript/Node.js plugins for Insomnia to support custom authentication and encryption/decryption workflows when testing APIs with non-standard security requirements.

* **Data tooling**<br />
  Used JSON and YAML for OpenAPI specifications, application and tooling configuration, documentation metadata and Markdown frontmatter. Developed Python and Scala utilities to call authenticated REST APIs, process responses, and generate, parse and transform JSON and YAML.

</CapabilityGrid>
