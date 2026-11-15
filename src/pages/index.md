---
title: Technical Writing Portfolio
description: Ian Drewett's technical-writing and documentation-engineering portfolio, featuring developer documentation, APIs, docs-as-code, developer experience, and AI-ready knowledge systems.
hide_table_of_contents: true
---

import Link from '@docusaurus/Link';
import CapabilityCard from '@site/src/components/CapabilityCard';

<div className="portfolio-hero">
  <p className="portfolio-eyebrow">Principal Technical Writer · Documentation Engineer · AI Information Architect</p>
  <h1>Ian Drewett</h1>
  <p className="portfolio-lead">I lead the design and delivery of developer documentation platforms, combining technical writing, documentation engineering and strategy.</p>

  <div className="portfolio-hero-actions">
    <Link className="button button--primary" to="#case-studies">Explore selected work</Link>
    <Link className="button button--secondary" to="/explore?view=browse&contentType=case-study&contentType=doc-sample">Browse all work</Link>
    <Link className="button button--outline button--primary" to="https://www.linkedin.com/in/ian-drewett/">Connect on LinkedIn</Link>
  </div>
</div>

## Selected Work {/* #case-studies */}

<div className="portfolio-grid">

  <div className="portfolio-card">
    <span className="card-tag">Docs-as-Code · Developer Portal · Platform Strategy</span>
    <h3>Scaling an Enterprise Developer Documentation Platform</h3>
    <div className="card-description">
      <p>Led the design and evolution of an enterprise documentation platform.</p>
      <ul>
        <li>Grew from 700 to more than 3,200 pages for quantitative analysts and developers.</li>
        <li>Created documentation for <a className="card-external-link" href="https://github.com/morganstanley/optimus-cirrus" target="_blank" rel="noopener noreferrer">Optimus Cirrus</a> and RICE, Morgan Stanley’s fixed-income pricing and risk framework.</li>
      </ul>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/case-studies/scalingdeveloperdocs" aria-label="Read the Scaling an Enterprise Developer Documentation Platform case study">Read case study →</Link>
  </div>

  <div className="portfolio-card">
    <span className="card-tag">Developer Portal · API Documentation · Platform Delivery</span>
    <h3>Building the Paysafe Developer Center</h3>
    <div className="card-description">
      <p>Delivered a new unified developer site during Paysafe’s expansion to more than $1 billion in annual revenue.</p>
      <ul>
        <li>Brought together documentation from <a className="card-external-link" href="https://www.paysafe.com/gb-en/paysafegroup/news/detail/optimal-payments-becomes-paysafe-in-game-changing-global-rebrand/" target="_blank" rel="noopener noreferrer">Optimal Payments</a> and <a className="card-external-link" href="https://www.skrill.com/" target="_blank" rel="noopener noreferrer">Skrill</a>.</li>
        <li>Unified API and SDK references, integration guides and product information.</li>
      </ul>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/case-studies/paysafedevcenter" aria-label="Read the Building the Paysafe Developer Center case study">Read case study →</Link>
  </div>


  <div className="portfolio-card">
    <span className="card-tag">Secure REST API · Python · Integration validation</span>
    <h3>Mastercard MDES for Merchants</h3>
    <div className="card-description">
      <p>Built and tested a Python integration with Mastercard MDES, the tokenisation infrastructure behind <strong>Apple Pay</strong>.</p>
      <ul>
        <li>Implemented encryption and asynchronous webhooks, and validated merchant workflows.</li>
        <li>Identified documentation defects and authored the MDES for Merchants Use-Case Guide.</li>
      </ul>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/docs-samples/MDES4Merchants" aria-label="Read the Mastercard MDES for Merchants case study">Read case study →</Link>
  </div>

  <div className="portfolio-card">
    <span className="card-tag">Azure · Hybrid Retrieval · Documentation Governance</span>
    <h3>Cloud-Based RAG Search</h3>
    <div className="card-description">
      <p>Designed and deployed documentation search on Azure using Docker, Terraform and FastAPI.</p>
      <ul>
        <li>Combined BM25 keyword search, FAISS semantic search and hybrid retrieval.</li>
        <li>Applied governed metadata filters and provided source-linked AI answers.</li>
      </ul>
    </div>
    <Link className="card-link card-stretched-link" to="/docs/case-studies/RagSearchCloudArchitecture" aria-label="Read the Cloud-Based RAG Search case study">Read case study →</Link>
  </div>

</div>

## Leadership and delivery {/* #leadership-and-delivery */}

<CapabilityCard items={[
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

<CapabilityCard items={[
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
