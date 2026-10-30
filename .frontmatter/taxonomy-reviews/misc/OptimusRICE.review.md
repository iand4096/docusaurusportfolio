# Taxonomy AI review

Model: `deepseek-v4-flash`

> Advisory only. Repository taxonomy and deterministic validation remain authoritative.

**Document:** `docs/misc/OptimusRICE.md`

## Suggested page fields

Only missing top-level fields are shown; existing title/description values are retained.

```yaml
description: An overview of Morgan Stanley's RICE financial analytics platform 
  and the Optimus graph computation framework, covering architecture, 
  distributed execution, bitemporal data storage, and engineering significance.
```

## Suggested taxonomy metadata

Review these values before applying them.

```yaml
type:
- case-study
audiences:
- developers
- technical-writers
topics:
- documentation-engineering
- information-architecture
- technical-writing
technologies:
- scala
- mermaid
- rest
- optimus
- rice
- bitemporal-storage
lifecycle:
- current
```

## Proposed new taxonomy terms

### `technologies.optimus` — Optimus — kind `framework`

**Why propose it:** Optimus is a central technology in the document, materially described and demonstrated, but no existing term covers it.

**Suggested definition**

```yaml
optimus:
  label: Optimus
  description: A Scala-based graph-oriented computation framework for 
    distributed financial analytics.
  kind: framework
  aliases:
  - Optimus Cirrus
```

**Verified source evidence**

- `Optimus uses a dependency-driven computation graph`
- `Optimus Cirrus`
- `# Optimus and RICE - distributed computing and financial analytics`

### `technologies.rice` — RICE — kind `software-platform`

**Why propose it:** RICE is a major platform described in the document, but it is not represented in the existing taxonomy.

**Suggested definition**

```yaml
rice:
  label: RICE
  description: Morgan Stanley's Risk Calculation Environment for financial 
    analytics and risk management.
  kind: software-platform
  aliases:
  - Risk Calculation Environment
```

**Verified source evidence**

- `RICE is the broader financial risk platform`
- `# Optimus and RICE - distributed computing and financial analytics`
- `Morgan Stanley's RICE (**RIsk Calculation Environment**) and Optimus support computationally intensive financial applications.`

### `technologies.bitemporal-storage` — Bitemporal storage — kind `technical-technique`

**Why propose it:** Bitemporal storage is a key technical concept explained in the document, but no existing term captures it.

**Suggested definition**

```yaml
bitemporal-storage:
  label: Bitemporal storage
  description: A data storage technique that tracks both valid time and 
    transaction time for historical reconstruction.
  kind: technical-technique
  aliases:
  - bitemporal object storage
```

**Verified source evidence**

- `bitemporal object storage`
- `tracks two distinct dimensions`
- `Valid time`

## Why these metadata values

- **type**: The document is a documented example of a technical platform (RICE and Optimus), describing architecture, workflow, and engineering significance, matching the case-study type.
- **audiences**: The content is aimed at developers who need to understand the platform's computation model and data access, and at technical writers who may document such systems.
- **topics**: The page demonstrates documentation engineering through its structured explanation of a complex system, information architecture in its layered breakdown, and technical writing in its clear prose and examples.
- **technologies**: Scala is the implementation language of Optimus; Mermaid is used for the dependency graph diagram; Kafka, MongoDB, and PostgreSQL are named as data technologies in DAL; REST is implied by the reactive interfaces and data services.
- **lifecycle**: The content describes a current platform and is presented as current portfolio material.

## Normalisation / validation notes

- Dropped unresolved metadata.technologies value 'kafka'.
- Dropped unresolved metadata.technologies value 'mongodb'.
- Dropped unresolved metadata.technologies value 'postgresql'.
- Added proposed term 'optimus' to metadata.technologies because the proposal has verified document evidence.
- Added proposed term 'rice' to metadata.technologies because the proposal has verified document evidence.
- Added proposed term 'bitemporal-storage' to metadata.technologies because the proposal has verified document evidence.
