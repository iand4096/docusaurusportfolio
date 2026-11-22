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

Morgan Stanley uses RICE and Optimus to run computationally intensive financial applications.

- **RICE (Risk Calculation Environment)** supports trading and risk management in [Fixed Income][rice-overview]. Morgan Stanley has also advertised roles to help move [Commodities products and workflows][commodities-role] onto RICE.
- **Optimus** runs Scala computations as a graph. The graph lets it [run independent tasks in parallel and reuse results][scala-days]. Developers can also [rerun calculations under different assumptions][tweak-patent].

## Platform architecture {/* #platform-architecture */}

### 1. Financial applications and analytics - RICE {/* #1-financial-applications-and-analytics---rice */}

Developers build pricing, valuation and risk applications on RICE. In one [public job description][pricing-role], Morgan Stanley describes a pricing system built on Optimus and RICE to run heavy calculations in parallel. The [RICE engineering overview][rice-overview] also describes reactive user interfaces for displaying financial data and results.

### 2. Graph computation framework - Optimus {/* #2-graph-computational-framework---optimus */}

Optimus builds its dependency graph from methods marked `@node`. When one node calls another, the runtime can tell which result it needs before it can continue. At [Scala Days][scala-days], Morgan Stanley showed how Optimus uses those dependencies to schedule work and cache results.

When a calculation has the same inputs and execution context, the runtime can reuse the result. This is the practical benefit of **referential transparency**. To test a scenario, a developer can temporarily override an input with a *tweak*. The original object keeps its value outside the scenario.

#### 1. Code example

In this Scala-style pseudocode, a price tweak changes the trade's value from 1,000 to 1,200 inside the `given` block. [Morgan Stanley's patent][tweak-patent] describes a sale with tweakable price and quantity and shows a separate example of a scoped price change using `given`.

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

Morgan Stanley publishes [Data Access Layer (DAL) code][dal-source] in the Optimus Cirrus repository. The [RICE engineering overview][rice-overview] describes **bitemporal object storage**, which records two kinds of time.

- **Valid time:** When information is effective in the business domain.
- **Transaction time:** When information is recorded in the data store.

Together, [valid time and transaction time][temporal] let you ask what was effective on a date and what the system knew about it when a calculation ran.

### 4. Distributed execution and infrastructure {/* #4-distributed-execution-and-infrastructure */}

In its [2023 Scala Days talk][scala-days], Morgan Stanley described Optimus Cirrus running across thousands of compute nodes with more than a petabyte of RAM in total.

AWS also reported at [re:Invent 2023][aws-hpc] that Morgan Stanley used AWS and Azure for compute-intensive RICE risk calculations.

### 5. Developer tooling and compiler infrastructure {/* #5-developer-tooling-and-compiler-infrastructure */}

The [RICE engineering overview][rice-overview] describes work on the Scala compiler, asynchronous execution and embedded query languages. The [Optimus Cirrus repository][cirrus] includes the code used to compile the **Optimus Build Tool (OBT)**, which distributes and caches compilation work. Morgan Stanley [demonstrated OBT][scala-days] on approximately 21 million lines of Scala and Java.

## End-to-end calculation workflow {/* #end-to-end-calculation-workflow */}

Here’s how the pieces could fit together in a valuation. The example draws on the public descriptions of [Optimus/RICE pricing][pricing-role], [DAL][dal-source] and [scenario evaluation][tweak-patent].

1. A financial application initiates a calculation using a model developed in the RICE environment.
2. Optimus evaluates the model's dependency graph, coordinating the computations and reusing eligible cached results.
3. The application and its computations obtain required financial information through DAL services, including historical data where appropriate.
4. Results are returned for use by financial applications, analytical services or user interfaces, with distributed compute and data infrastructure supporting the workload.

## Engineering significance {/* #engineering-significance */}

Suppose a price correction comes in on Tuesday and applies to Monday. To reproduce Monday’s original valuation, select prices valid on Monday and use the data the system had when it ran the calculation. To recalculate Monday’s valuation with the correction, keep Monday as the valid date and advance the transaction time to include Tuesday’s update. [Valid time and transaction time][temporal]

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
