# Taxonomy AI review

Model: `deepseek-v4-flash`

> Advisory only. Repository taxonomy and deterministic validation remain authoritative.

**Document:** `docs/case-studies/DocumentingComplexDeveloperFrameworks.md`

## Suggested page fields

None. The document already has usable top-level title and description fields, or DeepSeek did not return a usable suggestion.

## Suggested taxonomy metadata

Review these values before applying them.

```yaml
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
```

## Proposed new taxonomy terms

### `technologies.jvm` — JVM — kind `runtime`

**Why propose it:** The JVM is a foundational runtime platform materially referenced in the document as part of the technology stack, but no existing term accurately represents it.

**Suggested definition**

```yaml
jvm:
  label: JVM
  description: The Java Virtual Machine, a runtime environment for executing 
    Java and other JVM languages such as Scala.
  kind: runtime
  aliases:
  - Java Virtual Machine
```

**Verified source evidence**

- `JVM/native interoperability`
- `Scala, C++, JVM/native interoperability`
- `This required a strong understanding of Scala, C++, JVM/native interoperability and bitemporal database concepts.`

### `technologies.jni` — JNI — kind `standard-specification`

**Why propose it:** JNI is a specific interoperability technology materially documented in the case study, and no existing term covers it.

**Suggested definition**

```yaml
jni:
  label: JNI
  description: Java Native Interface, a framework for interoperability between 
    Java and native code.
  kind: standard-specification
  aliases:
  - Java Native Interface
```

**Verified source evidence**

- `JNI-based mechanisms`
- `Scala/C++ interoperability`
- `Created developer documentation covering integration between Scala and native C++ code through JNI-based mechanisms, explaining cross-language interaction from the perspective of Scala developers.`

### `technologies.optimus` — Optimus — kind `framework`

**Why propose it:** Optimus is a significant framework documented in the case study, and no existing term represents it.

**Suggested definition**

```yaml
optimus:
  label: Optimus
  description: A Scala-based framework for building reactive user interfaces and
    data processing applications.
  kind: framework
  aliases:
  - Optimus Cirrus
```

**Verified source evidence**

- `Optimus and RICE frameworks`
- `Optimus UI`
- `Alongside leading the development of Morgan Stanley's new [custom docs-as-code platform](ScalingADeveloperDocsPlatform.md), I served as the lead and sole technical writer for the Optimus and RICE frameworks.`

### `technologies.rice` — RICE — kind `framework`

**Why propose it:** RICE is a framework documented in the case study, and no existing term represents it.

**Suggested definition**

```yaml
rice:
  label: RICE
  description: An internal framework for regression testing and data ingestion 
    at Morgan Stanley.
  kind: framework
```

**Verified source evidence**

- `Optimus and RICE frameworks`
- `Regression testing framework`
- `Alongside leading the development of Morgan Stanley's new [custom docs-as-code platform](ScalingADeveloperDocsPlatform.md), I served as the lead and sole technical writer for the Optimus and RICE frameworks.`

### `technologies.kafka` — Kafka — kind `software-platform`

**Why propose it:** Kafka is materially used for event-stream processing in the Backfiller framework, and no existing term covers it.

**Suggested definition**

```yaml
kafka:
  label: Kafka
  description: A distributed event streaming platform.
  kind: software-platform
  aliases:
  - Apache Kafka
```

**Verified source evidence**

- `Kafka-based event-stream processing`
- `Documented historical data backfilling, Kafka-based event-stream processing and writing external data into a bitemporal data store.`

## Why these metadata values

- **type**: The page is a documented example of work, approach and outcomes, matching the case study definition.
- **audiences**: The content is aimed at developers using the frameworks, documentation managers overseeing documentation strategy, and technical writers creating similar documentation.
- **topics**: The page covers API documentation for Scala frameworks, developer experience through improved documentation, information architecture via structured outlines, and technical writing practice.
- **technologies**: Scala, C++, JVM, JNI, Kafka, Optimus and RICE are materially used and documented in the case study.
- **lifecycle**: The content represents current practice and portfolio material.

## Normalisation / validation notes

- Resolved metadata.technologies 'jvm' to canonical ID 'jvm'.
- Resolved metadata.technologies 'jni' to canonical ID 'jni'.
- Resolved metadata.technologies 'kafka' to canonical ID 'kafka'.
- Resolved metadata.technologies 'optimus' to canonical ID 'optimus'.
- Resolved metadata.technologies 'rice' to canonical ID 'rice'.
