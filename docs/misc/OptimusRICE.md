---
title: Optimus and RICE
taxonomy_tooltip_exclude:
  - optimus
  - rice
  - 'glossary:bitemporal data'
type:
  - reference-material
audiences:
  - developers
  - technical-writers
topics:
  - documentation-engineering
  - information-architecture
  - technical-writing
technologies:
  - optimus
  - rice
lifecycle:
  - current
tags:
  - documentation-engineering
  - information-architecture
  - optimus
  - rice
  - technical-writing
---

import DiagramFigure from '@site/src/components/DiagramFigure';

# Optimus and RICE - distributed computing and financial analytics

## Overview {/* #overview */}

Morgan Stanley's RICE (**RIsk Calculation Environment**) and Optimus support computationally intensive financial applications.

- **RICE** provides the financial analytics environment for pricing, valuation, trading and risk management. Morgan Stanley describes it as a Fixed Income risk framework and has advertised roles supporting the migration of Commodities products and workflows to it. [RICE engineering overview][rice-overview] · [Commodities Strategist role][commodities-role]
- **Optimus** is a Scala-based, graph-oriented computation framework built on functional programming principles. It manages computational dependencies and supports automatic parallelisation, asynchronous execution, caching and scenario evaluation. [Scala Days keynote][scala-days] · [Scenario evaluation patent][tweak-patent]

The public Optimus Cirrus repository includes **Data Access Layer (DAL)** code. A public RICE engineering post describes bitemporal object storage as one of the platform’s capabilities. [Optimus Cirrus DAL source][dal-source] · [RICE engineering overview][rice-overview]

## Platform architecture {/* #platform-architecture */}

### 1. Financial applications and analytics - RICE {/* #1-financial-applications-and-analytics---rice */}

RICE provides a platform for building financial models and applications for pricing, valuation, trading and risk. The platform's development and runtime teams provide services and components used by application developers. [Optimus/RICE pricing role][pricing-role] · [RICE engineering overview][rice-overview]

The ecosystem also includes declarative reactive interfaces for presenting financial data and results. [RICE engineering overview][rice-overview]

### 2. Graph computation framework - Optimus {/* #2-graph-computational-framework---optimus */}

Methods annotated with `@node` participate in the Optimus dependency graph. When one node calls another, the graph records the dependency so the runtime can coordinate their execution. The runtime can evaluate independent work in parallel and reuse cached results where applicable. [Scala Days keynote][scala-days] · [Scenario evaluation patent][tweak-patent]

**Referential transparency** is an important principle: results can be reused safely when a function's inputs and execution context remain unchanged. For scenario analysis, tweaks let nodes be evaluated under alternative assumptions while preserving the underlying immutable objects.

#### 1. Code example

The Scala-style pseudocode below illustrates that behaviour. Morgan Stanley's patent describes a sale with tweakable price and quantity and gives a separate example of a scoped price change using `given`. [Scenario evaluation patent][tweak-patent]

```scala
@entity
class Trade(
  @node(tweak = true) val price: Double,
  @node(tweak = true) val quantity: Int
) {
  @node
  def marketValue: Double = price * quantity
}

// Assuming price = 100 and quantity = 10
trade.marketValue  // 1000

given(trade.price := 120.0) {
  trade.marketValue  // 1200
}

trade.marketValue  // 1000 (original value)
```

#### 2. Dependency diagram

<DiagramFigure {...{
  "title": "Calculation dependencies and price tweaks",
  "shareId": "calculation-dependencies-and-price-tweaks",
  "legend": [
    {
      "role": "input",
      "label": "Original and scenario inputs"
    },
    {
      "role": "process",
      "label": "Calculated results"
    }
  ]
}}>

```mermaid
flowchart TD
    accTitle: Calculation dependencies and price tweaks
    accDescr {
      Market value depends on price and quantity.
      A price of 100 and quantity of 10 produce a market value of 1,000.
      Within an alternative scenario, changing price to 120 produces a market value of 1,200 while quantity remains unchanged.
      The original calculation remains unchanged outside that scenario.
    }
    P["price<br/>@node(tweak = true)<br/>100"]
    Q["quantity<br/>@node(tweak = true)<br/>10"]

    MV["marketValue<br/>@node<br/>1,000"]

    P --> MV
    Q --> MV

    P -. "given(price := 120.0)" .-> TP

    TP["Tweaked price<br/>120"]
    TMV["marketValue<br/>@node<br/>1,200"]

    TP --> TMV
    Q --> TMV
    class P,Q,TP input;
    class MV,TMV process;
```

</DiagramFigure>

### 3. Data access layer - DAL {/* #3-data-access-layer---dal */}

The platform uses **bitemporal object storage**, which tracks two distinct dimensions. [RICE engineering overview][rice-overview]

- **Valid time:** When information is effective in the business domain.
- **Transaction time:** When information is recorded in the data store.

This distinction lets users reconstruct which facts were effective at a given time and which facts the system knew at that time. [Valid time and transaction time][temporal]

### 4. Distributed execution and infrastructure {/* #4-distributed-execution-and-infrastructure */}

At Scala Days 2023, Morgan Stanley described **Optimus Cirrus** as automatically caching and parallelising tasks across thousands of compute nodes with more than a petabyte of aggregate RAM. [Scala Days keynote][scala-days]

AWS reported in 2023 that Morgan Stanley used AWS and Azure to run compute-intensive RICE risk calculations. [AWS re:Invent HPC presentation][aws-hpc]

### 5. Developer tooling and compiler infrastructure {/* #5-developer-tooling-and-compiler-infrastructure */}

The ecosystem includes specialised Scala compiler development, asynchronous programming semantics, embedded query languages and developer tooling. [RICE engineering overview][rice-overview] · [Optimus Cirrus source][cirrus]

One related capability is the **Optimus Build Tool (OBT)**, which applies distributed computation and caching techniques to software compilation. Morgan Stanley has demonstrated the approach on a codebase containing approximately 21 million lines of Scala and Java. OBT applies Optimus concepts outside the financial calculation workflow. [Scala Days keynote][scala-days]

## End-to-end calculation workflow {/* #end-to-end-calculation-workflow */}

This illustrative valuation or risk calculation combines the roles described in public sources. [Optimus/RICE pricing role][pricing-role] · [Optimus Cirrus DAL source][dal-source] · [Scenario evaluation patent][tweak-patent]

1. A financial application initiates a calculation using a model developed in the RICE environment.
2. Optimus evaluates the model's dependency graph, coordinating the computations and reusing eligible cached results.
3. The application and its computations obtain required financial information through DAL services, including historical data where appropriate.
4. Results are returned for use by financial applications, analytical services or user interfaces, with distributed compute and data infrastructure supporting the workload.

## Engineering significance {/* #engineering-significance */}

When reproducing a past valuation, use valid time to select the inputs that applied on the valuation date. Use transaction time to see which of those inputs the system had recorded when it ran the calculation. A correction recorded later can change the result for the same valuation date. [Valid time and transaction time][temporal]

## Public references {/* #public-references */}

1. **Morgan Stanley — Optimus Cirrus GitHub Repository**  
   Public source code, project scope, licensing and technical presentations.  
   https://github.com/morganstanley/optimus-cirrus

2. **Scala Days 2023 — Supercharge Your Performance with the Optimus Cirrus Platform**  
   Functional programming, parallelisation, caching, distributed computation and OBT.  
   https://archives.scaladays.org/2023/seattle-2023/supercharge-your-performance-with-the-optimus-cirrus-platform.html

3. **Morgan Stanley — Simulated Change of Immutable Objects During Execution Runtime**\
   Patent describing referentially transparent nodes, tweaks, scenario-based evaluation and caching.  
   https://patents.google.com/patent/US20220121462A1/en

4. **University of Cambridge — Functional Languages and Financial Models (2014)**\
   Graph programming, functional financial models, Scala and risk infrastructure.  
   https://www.cst.cam.ac.uk/seminars/list/55917

5. **Morgan Stanley — Scala Developer, Interest Rate Derivatives**\
   Public description of valuation systems built on the Optimus/RICE platform.  
   https://en.wizbii.com/company/morgan-staney/job/scala-developer-7

6. **Morgan Stanley — Commodities Strategist**\
   Public evidence of Commodities products and workflows being migrated to the RICE platform.  
   https://ms.wd5.myworkdayjobs.com/en-US/External/job/Commodities-Strategist_JR041944

7. [Peter Fraenkel — RICE engineering overview][rice-overview]\
   Describes RICE's Fixed Income role and platform capabilities. Morgan Stanley also publishes [DAL source code][dal-source] in the Optimus Cirrus repository.

8. [AWS re:Invent 2023 — Confidently run your production HPC workloads on AWS][aws-hpc]\
   Reports the use of AWS and Azure for RICE risk calculations.

9. [Jensen and Snodgrass — Bitemporal Interval][temporal]\
   Defines valid time and transaction time for bitemporal data.

[cirrus]: https://github.com/morganstanley/optimus-cirrus

[scala-days]: https://archives.scaladays.org/2023/seattle-2023/supercharge-your-performance-with-the-optimus-cirrus-platform.html

[tweak-patent]: https://patents.google.com/patent/US20220121462A1/en

[pricing-role]: https://en.wizbii.com/company/morgan-staney/job/scala-developer-7

[commodities-role]: https://ms.wd5.myworkdayjobs.com/en-US/External/job/Commodities-Strategist_JR041944

[rice-overview]: https://www.linkedin.com/posts/peter-fraenkel-3849493_hiring-activity-6877297325576904704-bYFO

[dal-source]: https://github.com/morganstanley/optimus-cirrus/tree/main/optimus/platform/projects/dal_core

[aws-hpc]: https://d1.awsstatic.com/events/Summits/reinvent2023/CMP213_Confidently-run-your-production-HPC-workloads-on-AWS.pdf

[temporal]: https://www2.cs.arizona.edu/~rts/pubs/TRmerged.pdf
