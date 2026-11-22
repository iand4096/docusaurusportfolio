---
title: Designing Cloud-Based RAG search for technical documentation
description: Designing and deploying cloud-based, metadata-governed retrieval-augmented generation 
  with Docker, Terraform and Azure.
sidebar_label: Cloud-Based RAG Search
sidebar_position: 5
sidebar_custom_props:
  caseStudyCard:
    title: Cloud-Based RAG Search
    tag: Search and retrieval
    description: Built documentation search with metadata filters and AI answers that link to sources.
    highlights:
      - Built keyword and semantic search with metadata filters and source-linked AI answers
      - Deployed a Python API on Azure using Docker and Terraform
    ariaLabel: Read the cloud-based RAG search case study
type:
  - case-study
audiences:
  - developers
  - technical-writers
topics:
  - documentation-governance
  - docs-as-code
  - information-architecture
  - taxonomy
  - developer-experience
technologies:
  - codex
  - agentic-ai
  - rag
  - docker
  - terraform
  - azure-container-apps
  - azure-container-registry
  - azure-log-analytics
  - azure-managed-identity
  - github-actions
  - github-pages
  - docusaurus
  - fastapi
  - pydantic
  - deepseek-api
  - sentence-transformers
  - faiss
  - bm25
  - reciprocal-rank-fusion
  - mermaid
  - markdown
  - mdx
  - python
  - https
  - cors
lifecycle:
  - current
tags:
  - agentic-ai
  - azure-container-apps
  - azure-container-registry
  - azure-log-analytics
  - azure-managed-identity
  - bm25
  - codex
  - cors
  - deepseek-api
  - developer-experience
  - docker
  - docs-as-code
  - documentation-governance
  - docusaurus
  - faiss
  - fastapi
  - github-actions
  - github-pages
  - https
  - information-architecture
  - markdown
  - mdx
  - mermaid
  - pydantic
  - python
  - rag
  - reciprocal-rank-fusion
  - sentence-transformers
  - taxonomy
  - terraform
---

import ApiEndpoint from '@site/src/components/ApiEndpoint';
import ApiExample from '@site/src/components/ApiExample';
import DiagramFigure from '@site/src/components/DiagramFigure';

import CaseStudySummary from '@site/src/components/CaseStudySummary';

<CaseStudySummary {...{
  "employer": "Independent project",
  "industry": "AI / Developer tooling",
  "projectType": "Cloud search application",
  "icon": "magnifying-glass",
  "summary": "Built and deployed portfolio search with governed retrieval and source-linked AI answers.",
  "role": "Sole architect, developer and deployment engineer",
  "scope": "Search and AI-assisted retrieval for my portfolio documentation",
  "decision": "Hybrid BM25/FAISS retrieval with metadata filters, separate from AI generation",
  "deliverables": "FastAPI service, ingestion pipeline, React interface and Terraform-managed Azure deployment",
  "evidenceTitle": "Delivered Capabilities",
  "evidence": [
    {
      "value": "3",
      "label": "Retrieval modes",
      "emphasis": "metric"
    },
    {
      "value": "Governed filters",
      "label": "Taxonomy and lifecycle constraints"
    },
    {
      "value": "Azure API",
      "label": "Containerised, source-linked search"
    }
  ]
}} />

## Project context {/* #project-overview */}

I designed and deployed a **cloud-based retrieval-augmented generation (RAG)** application to test how documentation governance can improve the way people find technical information. Visitors can search my portfolio using keywords, semantic similarity or hybrid retrieval, then inspect the original passages or request an AI-generated answer grounded in those passages.

The idea grew out of my experience integrating RAG search into a large docs-as-code developer portal I managed at an investment bank. I saw an opportunity to use document metadata, such as whether an API was current or deprecated, to control which content was retrieved. This could, for example, reduce the risk of developers inadvertently integrating with deprecated APIs.

[Try the portfolio search](https://iand4096.github.io/docusaurusportfolio/ai-search).

## The challenge

Conventional keyword search works well when readers know the terminology, but it can miss relevant material described in different words. Semantic search can find related passages even when they use different terminology, yet similarity alone does not establish whether a document belongs to the right topic, audience or lifecycle state.

I wanted to test whether document metadata could control which passages a RAG system retrieved. The application also needed to preserve links to the source documentation and support conventional search without relying on an LLM.

The cloud deployment needed to control running costs, keep provider credentials out of the frontend and limit paid AI requests.

## My approach

I used Codex as an agentic coding assistant while building the search API and portfolio search interface.

### Treat metadata as part of the retrieval architecture

I used the portfolio's Markdown and MDX documents as the knowledge source. The ingestion pipeline validates their taxonomy before indexing, extracts frontmatter and headings, and creates heading-aware, paragraph-aligned passages of up to 1,500 characters. Each indexed passage retains its title, source location and governed facets: **content type, audience, topic, technology and lifecycle**.

The API validates the selected facets against the canonical taxonomy and uses them to filter retrieval results. Filters can be combined across dimensions, and archived content is excluded unless the visitor explicitly includes it.

### Combine lexical and semantic retrieval

I implemented three search modes with different strengths:

- **Keyword search:** BM25 ranks matches for exact terms, API names and technical identifiers.
- **Semantic search:** `sentence-transformers/all-MiniLM-L6-v2` generates embeddings, searched through a FAISS vector index to find related concepts expressed in different words.
- **Hybrid search:** Reciprocal Rank Fusion (RRF) combines BM25 and semantic rankings without assuming their raw scores are directly comparable.

The index is generated ahead of deployment and packaged with the backend. A cached index snapshot supports subsequent requests without reloading the retrieval model each time. The public interface defaults to hybrid search and displays ranked evidence with links back to its source documentation.

### Separate evidence retrieval from AI answer generation

I exposed three endpoints through a Python **FastAPI** service. Requests are validated with Pydantic before search filters are checked against the governed taxonomy.

- The taxonomy endpoint (<ApiEndpoint operationId="taxonomy" />) lists filter dimensions and their active terms.
- The search endpoint (<ApiEndpoint operationId="search" />) returns passages with source links without calling an LLM.
- For AI-generated answers, the chat endpoint (<ApiEndpoint operationId="chat" />) supplies retrieved passages to **DeepSeek**. It asks DeepSeek to answer from the supplied evidence, cite numbered sources and acknowledge gaps. The interface displays the supporting sources and warns visitors to verify AI-generated answers against the original material. Prompt instructions reduce risk but do not guarantee factual correctness.

The request below uses `taxonomy`, one of the topic terms listed by `/taxonomy`, to filter a keyword search. The response shows the top-ranked passage and a link to its source section.

<ApiExample operationId="search" example="taxonomy-filter" />

### Indexing and query flow {/* #architecture */}

The diagram shows the implemented indexing and query paths. **Taxonomy selection is manual at query time**, not an automatic query-classification stage.

<DiagramFigure {...{
  "title": "Documentation indexing and search",
  "shareId": "documentation-indexing-and-search",
  "legend": [
    {
      "role": "input",
      "label": "Inputs and build preparation"
    },
    {
      "role": "process",
      "label": "Processing and delivery"
    },
    {
      "role": "storage",
      "label": "Stored data and telemetry"
    },
    {
      "role": "decision",
      "label": "Decisions"
    },
    {
      "role": "interaction",
      "label": "User interaction and results"
    },
    {
      "role": "generation",
      "label": "AI generation"
    }
  ]
}}>

<div className="diagram-columns">

<div className="diagram-panel" data-diagram-panel-id="indexing-before-deployment">

#### Indexing before deployment

```mermaid
%%{init: {
  "flowchart": {"useMaxWidth": true, "nodeSpacing": 45, "rankSpacing": 55},
  "themeVariables": {"fontSize": "17px"}
}}%%
flowchart TB
    accTitle: Indexing before deployment
    accDescr {
      Markdown and MDX documents with governed metadata undergo taxonomy validation and are divided into heading-aware passages with source links.
      These passages produce BM25 records.
      MiniLM generates document embeddings for a FAISS vector index.
      Both indexes are prepared before deployment.
    }
Docs["Markdown / MDX documents<br/>Governed frontmatter"]
Validate{"Validate<br/>canonical taxonomy"}
Chunk["Heading-aware passages<br/>Metadata and source links"]
Records[("BM25<br/>chunk records")]
Embed["MiniLM<br/>document embeddings"]
Vector[("FAISS<br/>vector index")]
Docs --> Validate --> Chunk
Chunk --> Records
Chunk --> Embed --> Vector

    class Docs input;
    class Validate,Chunk,Embed process;
    class Records,Vector storage;
```

</div>

<div className="diagram-panel" data-diagram-panel-id="search-and-answer-generation">

#### Search and answer generation

```mermaid
%%{init: {
  "flowchart": {"useMaxWidth": true, "nodeSpacing": 45, "rankSpacing": 55},
  "themeVariables": {"fontSize": "17px"}
}}%%
flowchart TB
    accTitle: Search and answer generation
    accDescr {
      The Docusaurus interface sends requests to FastAPI for validation and rate limiting.
      Manually selected taxonomy and lifecycle filters are validated before keyword, semantic, or hybrid retrieval ranks source passages.
      Readers can view the original evidence or request a DeepSeek-generated answer with numbered citations and supporting sources.
    }
UI["Docusaurus UI<br/>GitHub Pages"]
API["FastAPI<br/>Request validation and rate limiting"]
Facets["Validate manually selected<br/>taxonomy and lifecycle filters"]
Retrieve["BM25, semantic<br/>or hybrid retrieval"]
Rank["Ranked passages<br/>with source links"]
Choice{"Output selected?"}
Sources["Display<br/>original evidence"]
LLM["DeepSeek generation<br/>using retrieved passages"]
Answer["Answer with numbered citations<br/>and supporting sources"]
UI --> API --> Facets --> Retrieve --> Rank --> Choice
Choice -->|Sources| Sources
Choice -->|AI answer| LLM --> Answer

    class UI,Sources,Answer interaction;
    class API,Facets,Retrieve,Rank process;
    class Choice decision;
    class LLM generation;
```

</div>

</div>

</DiagramFigure>

The retrieval step uses the prebuilt BM25 chunk records and FAISS vector index produced by the indexing flow.

### Deployment on Azure {/* #cloud-architecture-docker-terraform-and-azure */}

I separated the static frontend from the Python service. **Docusaurus is built by GitHub Actions and published to GitHub Pages**; visitors’ browsers send HTTPS requests directly to **FastAPI on Azure Container Apps**. The portfolio remains a static site; retrieval and AI generation run in the Azure-hosted API. CORS explicitly permits the GitHub Pages origin.

**Docker** packages the FastAPI application, its Python dependencies, the embedding model and the prebuilt search-index artifacts. A PowerShell build script then publishes version-tagged images to a private **Azure Container Registry (ACR)**. Index generation happens before deployment, not when each container starts. Docker Compose provides a separate local development path.

I use **Terraform with the AzureRM provider** to provision the Azure resource group, ACR, Container Apps environment and application, **Log Analytics** workspace, and a **user-assigned managed identity**. The identity receives scoped `AcrPull` permission; this allows the Container App to retrieve the private image without an ACR administrator password. After publishing an image, I update its tag in Terraform, review `terraform plan` and run `terraform apply` to deploy a new Container Apps revision.

<DiagramFigure {...{
  "title": "Azure deployment architecture",
  "shareId": "azure-deployment-architecture",
  "subgraphNotes": {
    "PACKAGE": "The versioned Docker image bundles FastAPI with a prebuilt search index. Azure Container Apps pulls it from the private registry using managed identity.",
    "FRONTEND": "GitHub Actions builds the static Docusaurus site for GitHub Pages. The visitor’s browser calls the Azure API directly for search and optional AI answers."
  },
  "legend": [
    {
      "role": "input",
      "label": "Source code and prebuilt index"
    },
    {
      "role": "process",
      "label": "Processing and delivery"
    },
    {
      "role": "storage",
      "label": "Stored data and telemetry"
    },
    {
      "role": "infra",
      "label": "Infrastructure configuration"
    },
    {
      "role": "interaction",
      "label": "User-facing site and browser"
    },
    {
      "role": "generation",
      "label": "AI generation"
    }
  ]
}}>

```mermaid
%%{init: {
  "flowchart": {"useMaxWidth": false, "nodeSpacing": 20, "rankSpacing": 45},
  "themeVariables": {"fontSize": "17px"}
}}%%
flowchart TB
    accTitle: Azure deployment architecture
    accDescr {
      GitHub Actions builds the static Docusaurus frontend for GitHub Pages.
      Docker packages FastAPI and the prebuilt search index into a versioned image stored in Azure Container Registry.
      Azure Container Apps retrieves that image using managed identity.
      Browsers call the backend directly for search and chat.
      The backend optionally calls DeepSeek and sends logs to Azure Log Analytics.
      Terraform provisions the registry, application, and logging resources.
    }
    subgraph PACKAGE["Backend packaging & image publishing"]
        Source["FastAPI source<br/>and prebuilt search index"]
        Docker["Docker build<br/>Version-tagged image"]
        ACR[("Private Azure<br/>Container Registry")]
        Source --> Docker --> ACR
    end

        Terraform["Terraform<br/>Azure resources and configuration"]

    subgraph FRONTEND["Static frontend"]
        Actions["GitHub Actions<br/>Docusaurus build"]
        Pages["GitHub Pages<br/>Docusaurus site"]
        Actions --> Pages
    end

        Browser["Visitor browser"]
        ACA["Azure Container Apps<br/>FastAPI service"]
        DeepSeek["DeepSeek API<br/>Optional AI generation"]
        Logs[("Azure Log Analytics<br/>Platform and console logs")]
        Browser -->|Loads site| Pages
        Browser -->|HTTPS /search and /chat| ACA
        ACA -->|AI generation| DeepSeek
        ACA -->|Logs| Logs

    ACR -->|Managed identity AcrPull| ACA
    Terraform -.->|Provisions| ACR
    Terraform -.->|Provisions| ACA
    Terraform -.->|Provisions| Logs

    class Source input;
    class Docker,Actions,ACA process;
    class ACR,Logs storage;
    class Terraform infra;
    class Pages,Browser interaction;
    class DeepSeek generation;

    class PACKAGE group-process;
    class FRONTEND group-interaction;
```

</DiagramFigure>

The Container App uses the **Consumption** workload profile with **one vCPU, 2 GB memory and zero-to-one replicas**. Scale-to-zero limits idle compute costs, at the expense of first-request latency. Azure Container Apps holds the DeepSeek API key as a secret and injects it into FastAPI through an environment-variable reference; the key is not embedded in the browser application or managed as a Terraform secret value.

As this is a publicly accessible server, I added per-client rate limits, input bounds, concurrency controls and a feature flag for paid generation. These controls reduce abuse but are **not equivalent to authentication, document-level authorisation or a durable spending quota**. The existing Log Analytics integration provides platform and console logs; distributed tracing and application performance dashboards are future work.

## Deliverables

- A [public governed RAG search interface](https://iand4096.github.io/docusaurusportfolio/ai-search) with keyword, semantic and hybrid retrieval, manually selected taxonomy filters, source links and an AI-answer option.
- [Search API reference](pathname:///search-api).
- A documentation ingestion and indexing pipeline that produces passage metadata, FAISS vectors and a source manifest after taxonomy validation.
- A FastAPI retrieval and generation API, with validation and controls for public requests.
- Versioned Docker image builds and Terraform-managed Azure infrastructure, including private registry access through managed identity and operational logs.
- Rate-limiter unit tests and deployment checks covering API behaviour, revision state, logs and browser access.

## Outcome

The portfolio now exposes a working, source-linked RAG search interface through GitHub Pages, backed by a separately deployed, containerised Azure API. Direct search tests returned indexed passages, and the abuse-protection tests passed for rate-limit expiry, independent endpoint limits and forwarded-header handling.

Two deployment issues provided useful operational evidence. A GitHub Pages request initially failed its CORS preflight because the API allowed only localhost origins; after I added the published site's origin, the same `OPTIONS /search` check returned **HTTP 200** with the expected CORS header. Azure system logs also showed an image pull taking **62.22 seconds** after scale-to-zero, demonstrating how image pulls contributed to first-request latency before the application started.

The application is deployed and its core retrieval and generation workflows have been tested. However, I have not yet measured retrieval relevance, search time or answer accuracy against a representative evaluation set.

## What I would change

- **Infer taxonomy filters from search queries.** This is the part of the original idea I have not yet implemented. I want to test whether a user's question can be mapped reliably to the approved taxonomy, with suggested filters shown for confirmation or adjustment. I would evaluate both retrieval relevance and the risk of incorrectly excluding relevant documents.

- **Introduce RAG evaluation.** Build a labelled set of representative questions and expected source passages; measure retrieval using metrics such as Recall@k and MRR, and review AI answers for groundedness and citation accuracy. I could then compare chunking strategies, embedding models and retrieval parameters against the same questions.

- **Add application observability.** Instrument the FastAPI request lifecycle and RAG stages (model initialisation, query embedding, BM25, FAISS, ranking and DeepSeek generation) with **OpenTelemetry** traces and metrics. Export telemetry to **Azure Application Insights / Azure Monitor** alongside the existing Log Analytics logs, using sampling and avoiding sensitive queries, evidence text and credentials. Track request latency, errors, rate-limit responses and external dependency time; evaluate **Grafana** later if a dedicated dashboard adds value. This is planned instrumentation, not a currently deployed monitoring stack.

- **Improve cold-start performance and operational safeguards.** Separate lightweight liveness checks from retrieval readiness and reduce the CPU-serving image size. If public usage grows, replace the in-memory abuse counters with a durable quota mechanism and add more explicit provider-usage monitoring.
