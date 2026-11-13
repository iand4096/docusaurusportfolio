---
title: Technical Writing Portfolio
description: Ian Drewett's technical-writing and documentation-engineering portfolio, featuring developer documentation, APIs, docs-as-code, developer experience, and AI-ready knowledge systems.
hide_table_of_contents: true
---

import Link from '@docusaurus/Link';
import CapabilityGrid from '@site/src/components/CapabilityGrid';

<div className="portfolio-hero">
  <p className="portfolio-eyebrow">API documentation · Developer platforms · Documentation engineering · AI knowledge systems</p>
  <h1>Ian Drewett</h1>
  <p className="portfolio-lead">Documenting complex software and frameworks and building public and internal developer portals</p>
  <p className="portfolio-intro">Principal Technical Writer, Documentation Engineer and AI Information Architect, with an M.Sc. in Computer Science and a <Link to="#engineering-background">software-engineering background</Link>.</p>

  <div className="portfolio-hero-actions">
    <Link className="button button--primary" to="#case-studies">Explore selected work</Link>
    <Link className="button button--secondary" to="/browse?contentType=case-study&contentType=doc-sample">Browse all work</Link>
  </div>
</div>

## Case studies {/* #case-studies */}

<div className="portfolio-grid">


<div className="portfolio-card">
  <span className="card-tag">
    Docs-as-Code · Developer Portal · Platform Strategy
  </span>

  <h3>Scaling an Enterprise Developer Documentation Platform</h3>

  <div className="card-description">
    Led the design and evolution of an internal enterprise documentation
    platform that grew from 700 pages to more than 3,200 for an audience
    of quantitative analysts and software developers. My responsibilities
    also included creating documentation for
    [Optimus Cirrus](https://github.com/morganstanley/optimus-cirrus),
    a distributed Scala graph-based compute engine, and RICE,
    Morgan Stanley’s fixed-income pricing and risk framework.
  </div>

  <Link
    className="card-link"
    to="/docs/case-studies/scalingdeveloperdocs"
    aria-label="Read the Scaling an Enterprise Developer Documentation Platform case study"
  >
    Read case study →
  </Link>
</div>

<Link
  className="portfolio-card"
  to="/docs/case-studies/paysafedevcenter"
  aria-label="Read the Paysafe Developer Center case study"
>
  <span className="card-tag">
    Developer Portal · API Documentation · Platform Delivery
  </span>

  <h3>Building the Paysafe Developer Center</h3>

 <div className="card-description">
  Led the documentation work for the first Paysafe Developer Center during a period of exceptional expansion as the company delivered 21% organic revenue growth, and surpassed $1 billion in annual revenue for the first time.
</div>

  <span className="card-link">Read case study →</span>
</Link>

<Link
  className="portfolio-card"
  to="/docs/docs-samples/MDES4Merchants"
  aria-label="Read the Mastercard MDES for Merchants case study"
>
  <span className="card-tag">Secure REST API · Python · Integration validation</span>
  <h3>Mastercard MDES for Merchants</h3>

  <div className="card-description">
    Developed and tested a complete payment API integration using Python, OAuth 1.0 RSA-SHA256, encryption and asynchronous webhooks. Used the working implementation to validate complex merchant workflows and identify documentation defects.
  </div>

  <span className="card-link">Read case study →</span>
</Link>

</div>

## Core expertise {/* #core-expertise */}

<CapabilityGrid> 

* **Developer documentation:**
  APIs, SDKs, integration guides, tutorials, code examples, OpenAPI references, and developer portals

* **User documentation:**
 User, administration and installation guides for complex SaaS products using single-sourcing techniques for scalability and maintenance

* **Documentation engineering:**
  Docs-as-code, CI/CD, documentation platforms, migrations, automation, testing, and quality tooling

* **AI knowledge management & governance:**
  Knowledge architecture, content and taxonomy governance, AI-ready documentation, and AI-assisted quality assurance

* **Technical validation & engineering:**
API implementation and testing, security validation, software debugging, automation, and developer tooling

</CapabilityGrid>

## Software engineering background {/* #engineering-background */}

I have an M.Sc. in Computer Science and a degree in Physics, with professional software-engineering experience in device drivers, graphics/CAD/VR, C, and C++/STL. 

Recent development work includes using Scala for documentation engineering and building full-stack test API integrations with Python/Flask and JavaScript to validate technical documentation. This engineering background informs my approach to technical writing: it helps me verify implementation details, work effectively and quickly with Subject-Matter Experts, APIs and docs-as-code tool chains, and test documentation against real software behaviour.

## Employment history {/* #employment-history */}

For employment history and professional experience, visit my
[LinkedIn profile](https://www.linkedin.com/in/ian-drewett/).

:::tip[Automated documentation QA]

My portfolio has a QA pipeline implemented using GitHub Actions which runs automatically on any committed changes as part of Continuous Integration. It combines AI-assisted editorial review with additional tests for grammar and punctuation, accessibility, Markdown formatting, style guide compliance, links and spelling.

**[View the live report →](pathname:///qa/)**
:::
