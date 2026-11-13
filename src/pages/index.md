---
title: Technical Writing Portfolio
description: Ian Drewett's technical-writing and documentation-engineering portfolio, featuring developer documentation, APIs, docs-as-code, developer experience, and AI-ready knowledge systems.
hide_table_of_contents: true
---

import Link from '@docusaurus/Link';
import CapabilityGrid from '@site/src/components/CapabilityGrid';

<div className="portfolio-hero">
  <p className="portfolio-eyebrow">Principal Technical Writer · Documentation Engineer · AI Information Architect</p>
  <h1>Ian Drewett</h1>
  <p className="portfolio-lead">I lead the design and delivery of developer documentation platforms, combining technical writing, documentation engineering and strategy.</p>

  <div className="portfolio-hero-actions">
    <Link className="button button--primary" to="#case-studies">Explore selected work</Link>
    <Link className="button button--secondary" to="/browse?contentType=case-study&contentType=doc-sample">Browse all work</Link>
  </div>
</div>

## Case studies {/* #case-studies */}

<div className="portfolio-grid">

  <div className="portfolio-card">
    <span className="card-tag">Docs-as-Code · Developer Portal · Platform Strategy</span>
    <h3>Scaling an Enterprise Developer Documentation Platform</h3>
    <div className="card-description">
      <p>Led the design and evolution of an internal enterprise documentation platform that grew from 700 pages to more than 3,200 for an audience of quantitative analysts and software developers. My responsibilities also included creating documentation for <a className="card-external-link" href="https://github.com/morganstanley/optimus-cirrus" target="_blank" rel="noopener noreferrer">Optimus Cirrus</a>, a distributed Scala graph-based compute engine, and RICE, Morgan Stanley’s fixed-income pricing and risk framework.</p>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/case-studies/scalingdeveloperdocs" aria-label="Read the Scaling an Enterprise Developer Documentation Platform case study">Read case study →</Link>
  </div>

  <div className="portfolio-card">
    <span className="card-tag">Developer Portal · API Documentation · Platform Delivery</span>
    <h3>Building the Paysafe Developer Center</h3>
    <div className="card-description">
      <p>Delivered a unified developer site during Paysafe's rapid expansion to more than $1 billion in annual revenue. Brought together API and SDK references, integration guides and product information from the <a className="card-external-link" href="https://www.paysafe.com/gb-en/paysafegroup/news/detail/optimal-payments-becomes-paysafe-in-game-changing-global-rebrand/" target="_blank" rel="noopener noreferrer">Optimal Payments</a> and <a className="card-external-link" href="https://www.skrill.com/" target="_blank" rel="noopener noreferrer">Skrill</a> businesses. Built migration tools and connected the authoring, review and publishing systems.</p>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/case-studies/paysafedevcenter" aria-label="Read the Building the Paysafe Developer Center case study">Read case study →</Link>
  </div>


  <div className="portfolio-card">
    <span className="card-tag">Secure REST API · Python · Integration validation</span>
    <h3>Mastercard MDES for Merchants</h3>
    <div className="card-description">
      <p>Built and tested a Python payment API integration with Mastercard MDES, the tokenisation infrastructure behind <strong>Apple Pay</strong>. Developed custom OAuth authentication code, implemented encryption and asynchronous webhooks, validated merchant workflows, identified documentation defects and authored the MDES for Merchants Use-Case Guide.</p>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/docs-samples/MDES4Merchants" aria-label="Read the Mastercard MDES for Merchants case study">Read case study →</Link>
  </div>

</div>

## Leadership and delivery {/* #leadership-and-delivery */}

<CapabilityGrid items={[
  {
    title: 'Team leadership and capability development',
    icon: 'people-group',
    summary: 'Led and developed a three-person team at Paysafe.',
    detail: 'Established workflows and mentored colleagues in Git and API technologies. Trained the team to maintain the documentation platform independently.',
  },
  {
    title: 'Architecture and technical direction',
    icon: 'sitemap',
    summary: "Set technical direction for Morgan Stanley's internal developer documentation platform.",
    detail: 'Led its design and evolution, defining requirements, quality standards and the authoring experience in collaboration with an engineering team.',
  },
  {
    title: 'Cross-functional project delivery',
    icon: 'list-check',
    summary: 'Coordinated delivery of the Paysafe Developer Center.',
    detail: "Coordinated technical writers, Paysafe's web developers and external specialists on the migration and publishing work.",
  },
]} />

## Core expertise {/* #core-expertise */}

<CapabilityGrid items={[
  {
    title: 'Developer documentation',
    icon: 'code',
    summary: 'APIs, SDKs, integration guides, tutorials, code examples, OpenAPI references and developer portals',
  },
  {
    title: 'User documentation',
    icon: 'book-open',
    summary: 'User, administration and installation guides for complex SaaS products using single-sourcing to reuse content across guides and outputs',
  },
  {
    title: 'Documentation engineering',
    icon: 'gears',
    summary: 'Docs-as-code platforms, CI/CD publishing, content migrations, automation and quality tooling',
  },
  {
    title: 'AI knowledge management & governance',
    icon: 'diagram-project',
    summary: 'Knowledge architecture, content and taxonomy governance, AI-ready documentation and AI-assisted quality assurance',
  },
  {
    title: 'Technical validation',
    icon: 'circle-check',
    summary: 'API implementation and testing, security validation, software debugging and verification of documented behaviour',
  },
]} />

## Software engineering background {/* #engineering-background */}

I have an M.Sc. in Computer Science and a degree in Physics, with professional software-engineering experience in device drivers, graphics/CAD/VR, C, and C++/STL.

Recent development work includes Scala tooling and API test integrations using Python/Flask and JavaScript, including full-stack and cloud-based implementations.

## Employment history {/* #employment-history */}

For employment history and professional experience, visit my [LinkedIn profile](https://www.linkedin.com/in/ian-drewett/).

:::tip[Automated documentation QA]

My portfolio has a QA pipeline implemented using GitHub Actions which runs automatically on any committed changes as part of Continuous Integration. It combines AI-assisted editorial review with additional tests for grammar and punctuation, accessibility, Markdown formatting, style guide compliance, links and spelling.

**[View the live report →](pathname:///qa/)**

:::
