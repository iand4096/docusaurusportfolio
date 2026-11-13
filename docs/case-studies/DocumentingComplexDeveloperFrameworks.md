---
organisations:
  - morgan-stanley
title: Documenting Complex Enterprise Developer Frameworks
description: How I reverse-engineered and documented complex Scala frameworks at Morgan Stanley,
  covering UI development, testing, interoperability and data ingestion.
slug: /case-studies/documenting-enterprise-developer-frameworks
sidebar_position: 4
type:
  - case-study
audiences:
  - developers
  - documentation-managers
  - technical-writers
topics:
  - api-documentation
  - developer-experience
  - information-architecture
  - technical-writing
technologies:
  - scala
  - c-plus-plus
  - jvm
  - jni
  - kafka
  - optimus
  - rice
lifecycle:
  - current
sidebar_custom_props:
  caseStudyCard:
    title: Complex Developer Frameworks
    tag: Framework documentation
    description: Wrote documentation for enterprise Scala frameworks by investigating source code.
    highlights:
      - Lead and sole technical writer for Morgan Stanley’s Optimus and RICE frameworks
      - Reverse-engineered undocumented Scala APIs and tested examples where possible
    ariaLabel: Read the Optimus and RICE documentation case study
tags:
  - api-documentation
  - c-plus-plus
  - developer-experience
  - information-architecture
  - jni
  - jvm
  - kafka
  - morgan-stanley
  - optimus
  - rice
  - scala
  - technical-writing
---

## Context {/* #context */}

Alongside leading the development of Morgan Stanley's new [custom docs-as-code platform](ScalingADeveloperDocsPlatform.md), I served as the lead and sole technical writer for the Optimus and RICE frameworks.

I produced developer documentation for engineers and quantitative analysts building applications with these sophisticated Scala-based systems. The documentation covered Scala and C++ interoperability, bitemporal data, reactive UI development, automated regression testing and data ingestion.

## Documentation approach {/* #documentation-approach */}

To understand undocumented framework behaviour, I reverse-engineered functionality by reading source code and tracing execution paths through the monorepo. I compared what I found in the source code with legacy documentation, where present, and used the gaps and inconsistencies to prepare questions for subject-matter experts. I drafted API documentation outlines for technical review before developing the full content. Where possible, I compiled and ran the Scala examples to check that they worked as documented.

## Sample technical documentation delivered {/* #sample-technical-documentation-delivered */}

### Optimus UI {/* #optimus-ui */}

Created Scala API documentation for an MVVM (Model-View-ViewModel) UI framework that enabled developers to construct reactive user interfaces for server- and desktop-based business applications using a single Scala domain-specific language (DSL).

Explained dependency-graph-based computation, interaction with bitemporal data, and the concepts and usage patterns needed for building reactive applications.

### Regression testing framework {/* #regression-testing-framework */}

Documented a large-scale internal automated testing framework supporting 400,000 tests, including functional tests, numerical regression tests and UI tests.

Provided guidance on test execution workflows, result interpretation and techniques for investigating potential regressions.

### Scala/C++ interoperability {/* #scalac-interoperability */}

Created developer documentation covering integration between Scala and native C++ code through JNI-based mechanisms, explaining cross-language interaction from the perspective of Scala developers.

### Backfiller framework {/* #backfiller-framework */}

Documented historical data backfilling, Kafka-based event-stream processing and writing external data into a bitemporal data store.

## Morgan Stanley and Optimus references {/* #morgan-stanley-and-optimus-references */}

- [Morgan Stanley Optimus Cirrus — GitHub](https://github.com/morganstanley/optimus-cirrus) — Official open-source repository for the Optimus Cirrus platform.
- [Supercharge Your Performance with the Optimus Cirrus Platform — Scala Days 2023](https://archives.scaladays.org/2023/madrid-2023/keynote3.html) — Presentation on Optimus, Scala and high-performance computing.
- [Optimus Cirrus — Scala Days Madrid 2023](https://www.youtube.com/watch?v=bCak15WmhXs) — Public engineering presentation.
- [Optimus Cirrus — Scala Days Seattle 2023](https://www.youtube.com/watch?v=g1jt3YLnRmk) — Public engineering presentation.
- [Optimus Cirrus — ScalaCon 2021](https://www.youtube.com/watch?v=V0jJvgiI_xs) — Public presentation on Optimus Cirrus.
- [Optimus — Scala Days 2018](https://www.youtube.com/watch?v=BW8S92jP5sE) — Earlier public presentation on Optimus.

## Other references {/* #other-references */}

- [Bitemporal History — Martin Fowler](https://martinfowler.com/articles/bitemporal-history.html) — Introduction to bitemporal data modelling and historical data management.
