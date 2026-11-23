---
title: Philosophy
description: How I write for readers, make it easier to contribute, and keep technical knowledge accurate, discoverable and maintainable.
hide_table_of_contents: true
---

import CapabilityCard from '@site/src/components/CapabilityCard';

# Philosophy

I see technical writing and knowledge management as parts of the same job: helping people find reliable information, use it and keep it accurate. My responsibility extends across the knowledge lifecycle, from initial investigation through publication and ongoing maintenance.

<CapabilityCard autoColumns heading="h2" items={[
  {
    title: 'Writing for readers',
    icon: 'book-open',
    summary: <ul>
      <li><a href="#start-with-empathy-for-the-reader">Start with reader empathy</a></li>
      <li><a href="#verify-what-the-software-actually-does">Verify software behaviour</a></li>
      <li><a href="#use-evidence-to-inform-decisions">Use evidence to inform decisions</a></li>
    </ul>,
  },
  {
    title: 'Designing knowledge systems',
    icon: 'gears',
    summary: <ul>
      <li><a href="#make-good-contributions-easy">Make contributions easy</a></li>
      <li><a href="#maintain-one-authoritative-source-for-each-fact">Maintain an authoritative source</a></li>
      <li><a href="#build-quality-checks-into-the-workflow">Build in quality checks</a></li>
      <li><a href="#govern-knowledge-so-people-can-find-and-trust-it">Govern knowledge</a></li>
    </ul>,
  },
]} />

## Start with empathy for the reader

Empathy starts with understanding what readers are trying to accomplish, what they already know and where they might get stuck. Good documentation respects their time by making prerequisites clear, explaining how to recognise success and helping them recover when things go wrong.

[Mastercard’s MDES merchant guide](/docs/docs-samples/MDES4Merchants)

## Make good contributions easy

The harder documentation is to correct, the longer known problems are likely to remain published.

I want engineers to update documentation alongside code in familiar tools, while giving writers accessible ways to preview and review changes.

[Morgan Stanley’s docs-as-code workflow](/docs/case-studies/scalingdeveloperdocs#documentation-platform-workflow)

## Maintain one authoritative source for each fact

I apply the Don't Repeat Yourself (DRY) principle to information that must remain consistent. API contracts, examples and metadata definitions should have a clear source of authority, with a way to verify that published content reflects changes.

That doesn't mean eliminating useful repetition. A prerequisite may belong in several guides because readers need it at the point of use. What matters is that the underlying fact has one place of ownership.

[Portfolio architecture and publishing pipeline](/docs/implementation-details/portfolio-architecture-and-publishing-pipeline#code-excerpts-and-api-examples)

## Verify what the software actually does

Specifications and existing documentation are starting points for investigation. For important workflows, I want to run examples, observe results and understand failure cases before explaining the behaviour. Discrepancies between the specification and implementation need investigation.

[Testing the Mastercard MDES integration](/docs/docs-samples/MDES4Merchants)

## Use evidence to inform decisions

I want documentation priorities to reflect evidence, but analysis also has a cost. The effort involved should be proportionate to the decision it supports.

Generative AI can make data exploration and analysis more practical. I validate the results before using them to guide decisions.

[Using analytics to prioritise content migration](/docs/case-studies/scalingdeveloperdocs#design-priorities)

## Build quality checks into the workflow

I want quality checks to reach contributors in time for them to fix problems before publication. Repeatable checks should be automated, with results specific enough to act on.

The outcome of a check also needs to be clear. A checker that fails to run is different from one that runs successfully and finds no issues. Editorial findings need supporting evidence so reviewers can assess their validity.

[Documentation QA case study](/docs/case-studies/documentation-qa)

## Govern knowledge so people can find and trust it

I use structure where it improves discovery and maintenance. Controlled vocabularies help readers find relevant content and give maintainers a consistent way to manage its lifecycle. Contributors need to understand the available terms and have a way to propose additions.

Changing a term’s meaning can affect authoring, navigation and retrieval, so I treat changes to established terms as reviewable migrations. For AI-assisted search, I want readers to be able to inspect the source passages behind a result. Lifecycle filters help keep obsolete guidance out of normal results.

- [Taxonomy governance case study](/docs/case-studies/TaxonomyGovernance)
- [RAG search case study](/docs/case-studies/RagSearchCloudArchitecture)
