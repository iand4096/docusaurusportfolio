---
title: Documenting Complex Enterprise Developer Frameworks
description: How I reverse-engineered and documented complex Scala frameworks at Morgan Stanley, 
  covering UI development, testing, interoperability and data ingestion.
slug: /case-studies/documenting-enterprise-developer-frameworks
sidebar_position: 2
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
    tag: Developer Frameworks · API Documentation
    description: Reverse-engineering and documenting complex Scala-based frameworks for enterprise 
      software engineers
    highlights:
      - Lead technical writing for Optimus and RICE frameworks
      - Source-code analysis and reverse engineering of undocumented APIs
      - SME interviews and consolidation of legacy documentation
      - Scala code examples, compilation and technical validation
      - Reactive UI, regression testing, interoperability and data ingestion
    ariaLabel: Read the enterprise developer framework documentation case study
tags:
  - api-documentation
  - c-plus-plus
  - developer-experience
  - information-architecture
  - jni
  - jvm
  - kafka
  - optimus
  - rice
  - scala
  - technical-writing
---


## Context

Alongside leading the development of Morgan Stanley's new [custom docs-as-code platform](ScalingADeveloperDocsPlatform.md), I served as the lead and sole technical writer for the Optimus and RICE frameworks.

My work involved creating developer documentation for sophisticated Scala-based systems, including reactive UI development, automated regression testing, cross-language interoperability and data ingestion.

## Challenge

These frameworks exposed complex programming abstractions and development workflows that required more than conventional API reference documentation. Engineers needed documentation that explained the underlying concepts, demonstrated how to use the framework capabilities, and provided practical guidance for implementing applications. The challenge was to translate highly technical engineering concepts into clear, accurate and maintainable developer documentation.

## My role

I produced documentation for developers and quantitative analysts building applications using Optimus and RICE. This required a strong understanding of Scala, C++, JVM/native interoperability and bitemporal database concepts.

## Documentation approach

To understand undocumented framework behaviour, I reverse-engineered functionality by reading source code and tracing execution paths through the monorepo. This research, combined with information gathered from multiple legacy documentation platforms, helped me prepare for interviews with subject-matter experts. The findings were used to create structured API documentation outlines for technical review, helping to resolve knowledge gaps and ensure accuracy. Where possible, Scala code examples were built, compiled and tested to ensure that documented functionality and usage patterns reflected the framework's actual behaviour.

## Sample technical documentation delivered

### Optimus UI

Created Scala API documentation for an MVVM (Model-View-ViewModel) UI framework that enabled developers to construct reactive user interfaces for server and desktop-based business applications using a single Scala domain-specific language (DSL).

Covered dependency-graph-based computation, interaction with bitemporal data, and the concepts and usage patterns needed for building reactive applications.

### Regression testing framework

Documented a large-scale internal automated testing framework supporting 400,000 tests, including functional tests, numerical regression tests and UI tests.

Covered test execution workflows, result interpretation and techniques for investigating potential regressions.

### Scala/C++ interoperability

Created developer documentation covering integration between Scala and native C++ code through JNI-based mechanisms, explaining cross-language interaction from the perspective of Scala developers.

### Backfiller framework

Documented historical data backfilling, Kafka-based event-stream processing and writing external data into a bitemporal data store.

## Morgan Stanley and Optimus references

- [Morgan Stanley Optimus Cirrus — GitHub](https://github.com/morganstanley/optimus-cirrus) — Official open-source repository for the Optimus Cirrus platform.
- [Supercharge Your Performance with the Optimus Cirrus Platform — Scala Days 2023](https://archives.scaladays.org/2023/madrid-2023/keynote3.html) — Presentation on Optimus, Scala and high-performance computing.
- [Optimus Cirrus — Scala Days Madrid 2023](https://www.youtube.com/watch?v=bCak15WmhXs) — Public engineering presentation.
- [Optimus Cirrus — Scala Days Seattle 2023](https://www.youtube.com/watch?v=g1jt3YLnRmk) — Public engineering presentation.
- [Optimus Cirrus — ScalaCon 2021](https://www.youtube.com/watch?v=V0jJvgiI_xs) — Public presentation on Optimus Cirrus.
- [Optimus — Scala Days 2018](https://www.youtube.com/watch?v=BW8S92jP5sE) — Earlier public presentation on Optimus.


## Other references

- [Bitemporal History — Martin Fowler](https://martinfowler.com/articles/bitemporal-history.html) — Introduction to bitemporal data modelling and historical data management.