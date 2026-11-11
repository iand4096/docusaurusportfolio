# Taxonomy AI review

Model: `deepseek-v4-flash`

> Advisory only. Repository taxonomy and deterministic validation remain authoritative.

**Document:** `docs/case-studies/RagSearchCloudArchitecture.md`

## Suggested page fields

None. The document already has usable top-level title and description fields, or DeepSeek did not return a usable suggestion.

## Suggested taxonomy metadata

Review these values before applying them.

```yaml
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
- opentelemetry
- azure-application-insights
- azure-monitor
- grafana
lifecycle:
- current
```

## Proposed new taxonomy terms

### `technologies.azure-container-apps` — Azure Container Apps — kind `container-platform`

**Why propose it:** The document describes deploying FastAPI on Azure Container Apps, including configuration and scaling, but no existing term covers this specific Azure container platform.

**Suggested definition**

```yaml
azure-container-apps:
  label: Azure Container Apps
  description: A serverless container hosting service on Azure.
  kind: container-platform
```

**Verified source evidence**

- `FastAPI on Azure Container Apps`
- `Azure Container Apps holds the DeepSeek API key`
- `**Docusaurus is built by GitHub Actions and published to GitHub Pages**; visitors’ browsers send HTTPS requests directly to **FastAPI on Azure Container Apps**.`

### `technologies.azure-container-registry` — Azure Container Registry — kind `container-platform`

**Why propose it:** The document uses Azure Container Registry to store Docker images and configures access via managed identity; no existing term covers this service.

**Suggested definition**

```yaml
azure-container-registry:
  label: Azure Container Registry
  description: A private Docker container registry service on Azure.
  kind: container-platform
  aliases:
  - ACR
```

**Verified source evidence**

- `A PowerShell build script then publishes version-tagged images to a private **Azure Container Registry (ACR)**.`
- `Filters can be combined across dimensions, and archived content is excluded unless the visitor explicitly includes it.`

### `technologies.azure-log-analytics` — Azure Log Analytics — kind `cloud-hosting-platform`

**Why propose it:** The document provisions and uses a Log Analytics workspace for platform and console logs; no existing term covers this Azure service.

**Suggested definition**

```yaml
azure-log-analytics:
  label: Azure Log Analytics
  description: A log analytics service in Azure Monitor.
  kind: cloud-hosting-platform
```

**Verified source evidence**

- `Azure Log Analytics`
- `Logs[("fa:fa-chart-line Azure Log Analytics<br/>Platform and console logs")]`

### `technologies.azure-managed-identity` — Azure managed identity — kind `security-cryptography`

**Why propose it:** The document uses a user-assigned managed identity to grant AcrPull permission without passwords; no existing term covers this Azure security feature.

**Suggested definition**

```yaml
azure-managed-identity:
  label: Azure managed identity
  description: A managed identity feature in Azure for secure authentication to 
    resources.
  kind: security-cryptography
```

**Verified source evidence**

- `user-assigned managed identity`
- `Managed identity: AcrPull`
- `ACR -->|Managed identity: AcrPull| ACA`

### `technologies.terraform` — Terraform — kind `infrastructure-platform`

**Why propose it:** The document uses Terraform with the AzureRM provider to provision Azure resources; no existing term covers Terraform.

**Suggested definition**

```yaml
terraform:
  label: Terraform
  description: An infrastructure-as-code tool for provisioning cloud resources.
  kind: infrastructure-platform
```

**Verified source evidence**

- `Terraform with the AzureRM provider`
- `terraform plan`
- `terraform apply`

### `technologies.fastapi` — FastAPI — kind `framework`

**Why propose it:** The document implements a FastAPI service with endpoints and validation; no existing term covers FastAPI.

**Suggested definition**

```yaml
fastapi:
  label: FastAPI
  description: A modern Python web framework for building APIs.
  kind: framework
```

**Verified source evidence**

- `FastAPI on Azure Container Apps`
- `I exposed a Python **FastAPI** service with `/taxonomy`, `/search` and `/chat` endpoints.`

### `technologies.pydantic` — Pydantic — kind `library`

**Why propose it:** The document uses Pydantic for request validation; no existing term covers Pydantic.

**Suggested definition**

```yaml
pydantic:
  label: Pydantic
  description: A data validation library for Python.
  kind: library
```

**Verified source evidence**

- `Requests are validated with Pydantic`
- `Requests are validated with Pydantic before search filters are checked against the governed taxonomy.`

### `technologies.sentence-transformers` — sentence-transformers — kind `library`

**Why propose it:** The document uses sentence-transformers/all-MiniLM-L6-v2 to generate embeddings; no existing term covers this library.

**Suggested definition**

```yaml
sentence-transformers:
  label: sentence-transformers
  description: A Python library for generating sentence embeddings.
  kind: library
```

**Verified source evidence**

- `- **Semantic search:** `sentence-transformers/all-MiniLM-L6-v2` generates embeddings, searched through a FAISS vector index to find related concepts expressed in different words.`
- `Embed["fa:fa-gears MiniLM<br/>document embeddings"]`

### `technologies.faiss` — FAISS — kind `library`

**Why propose it:** The document uses FAISS for vector search; no existing term covers FAISS.

**Suggested definition**

```yaml
faiss:
  label: FAISS
  description: A library for efficient similarity search and clustering of dense
    vectors.
  kind: library
```

**Verified source evidence**

- `FAISS vector index`
- `FAISS vectors`
- `- **Semantic search:** `sentence-transformers/all-MiniLM-L6-v2` generates embeddings, searched through a FAISS vector index to find related concepts expressed in different words.`

### `technologies.bm25` — BM25 — kind `technical-technique`

**Why propose it:** The document implements BM25 for keyword search; no existing term covers BM25.

**Suggested definition**

```yaml
bm25:
  label: BM25
  description: A ranking function used in information retrieval.
  kind: technical-technique
```

**Verified source evidence**

- `BM25 ranks matches`
- `- **Keyword search:** BM25 ranks matches for exact terms, API names and technical identifiers.`

### `technologies.reciprocal-rank-fusion` — Reciprocal Rank Fusion — kind `technical-technique`

**Why propose it:** The document uses Reciprocal Rank Fusion to combine BM25 and semantic rankings; no existing term covers this technique.

**Suggested definition**

```yaml
reciprocal-rank-fusion:
  label: Reciprocal Rank Fusion
  description: A method for combining ranked lists from multiple retrieval 
    systems.
  kind: technical-technique
  aliases:
  - RRF
```

**Verified source evidence**

- `Reciprocal Rank Fusion (RRF) combines BM25 and semantic rankings`
- `- **Hybrid search:** Reciprocal Rank Fusion (RRF) combines BM25 and semantic rankings without assuming their raw scores are directly comparable.`

### `technologies.cors` — CORS — kind `standard-specification`

**Why propose it:** The document configures CORS and discusses CORS preflight issues; no existing term covers CORS.

**Suggested definition**

```yaml
cors:
  label: CORS
  description: Cross-Origin Resource Sharing, a mechanism for allowing web 
    requests from different origins.
  kind: standard-specification
```

**Verified source evidence**

- `CORS explicitly permits the GitHub Pages origin`
- `CORS preflight`
- `CORS explicitly permits the GitHub Pages origin.`

### `technologies.opentelemetry` — OpenTelemetry — kind `technical-technique`

**Why propose it:** The document plans to use OpenTelemetry for tracing and metrics; no existing term covers OpenTelemetry.

**Suggested definition**

```yaml
opentelemetry:
  label: OpenTelemetry
  description: An observability framework for cloud-native software.
  kind: technical-technique
```

**Verified source evidence**

- `- **Add application observability.** Instrument the FastAPI request lifecycle and RAG stages—model initialisation, query embedding, BM25, FAISS, ranking and DeepSeek generation—with **OpenTelemetry** traces and metrics.`

### `technologies.azure-application-insights` — Azure Application Insights — kind `cloud-hosting-platform`

**Why propose it:** The document plans to export telemetry to Azure Application Insights; no existing term covers this service.

**Suggested definition**

```yaml
azure-application-insights:
  label: Azure Application Insights
  description: An application performance management service in Azure.
  kind: cloud-hosting-platform
```

**Verified source evidence**

- `Azure Application Insights / Azure Monitor`
- `Export telemetry to **Azure Application Insights / Azure Monitor** alongside the existing Log Analytics logs, using sampling and avoiding sensitive queries, evidence text and credentials.`

### `technologies.azure-monitor` — Azure Monitor — kind `cloud-hosting-platform`

**Why propose it:** The document plans to use Azure Monitor alongside Application Insights; no existing term covers this service.

**Suggested definition**

```yaml
azure-monitor:
  label: Azure Monitor
  description: A comprehensive monitoring service in Azure.
  kind: cloud-hosting-platform
```

**Verified source evidence**

- `Azure Application Insights / Azure Monitor`
- `Export telemetry to **Azure Application Insights / Azure Monitor** alongside the existing Log Analytics logs, using sampling and avoiding sensitive queries, evidence text and credentials.`

### `technologies.grafana` — Grafana — kind `data-analysis-tool`

**Why propose it:** The document mentions evaluating Grafana for dashboards; no existing term covers Grafana.

**Suggested definition**

```yaml
grafana:
  label: Grafana
  description: An open-source analytics and monitoring platform.
  kind: data-analysis-tool
```

**Verified source evidence**

- `Track request latency, errors, rate-limit responses and external dependency time; evaluate **Grafana** later if a dedicated dashboard adds value.`

## Why these metadata values

- **type**: The page documents a specific project, its approach, architecture, deliverables and outcomes, matching the case-study definition.
- **audiences**: The content is aimed at developers who consume APIs and technical writers interested in documentation governance and retrieval systems.
- **topics**: The project centres on using document metadata and taxonomy to govern retrieval, treating documentation as code with CI/CD, and improving developer experience through better search.
- **technologies**: The page materially uses and documents RAG, Docker, Terraform, Azure services, GitHub Actions, Docusaurus, FastAPI, Pydantic, DeepSeek, sentence-transformers, FAISS, BM25, RRF, Mermaid, Markdown, MDX, Python, HTTPS, CORS, OpenTelemetry, Azure monitoring tools and Grafana.
- **lifecycle**: The application is deployed and described as current practice, with future improvements noted but not yet implemented.

## Normalisation / validation notes

- Resolved metadata.technologies 'terraform' to canonical ID 'terraform'.
- Resolved metadata.technologies 'azure-container-apps' to canonical ID 'azure-container-apps'.
- Resolved metadata.technologies 'azure-container-registry' to canonical ID 'azure-container-registry'.
- Resolved metadata.technologies 'azure-log-analytics' to canonical ID 'azure-log-analytics'.
- Resolved metadata.technologies 'azure-managed-identity' to canonical ID 'azure-managed-identity'.
- Resolved metadata.technologies 'fastapi' to canonical ID 'fastapi'.
- Resolved metadata.technologies 'pydantic' to canonical ID 'pydantic'.
- Resolved metadata.technologies 'sentence-transformers' to canonical ID 'sentence-transformers'.
- Resolved metadata.technologies 'faiss' to canonical ID 'faiss'.
- Resolved metadata.technologies 'bm25' to canonical ID 'bm25'.
- Resolved metadata.technologies 'reciprocal-rank-fusion' to canonical ID 'reciprocal-rank-fusion'.
- Resolved metadata.technologies 'cors' to canonical ID 'cors'.
- Resolved metadata.technologies 'opentelemetry' to canonical ID 'opentelemetry'.
- Resolved metadata.technologies 'azure-application-insights' to canonical ID 'azure-application-insights'.
- Resolved metadata.technologies 'azure-monitor' to canonical ID 'azure-monitor'.
- Resolved metadata.technologies 'grafana' to canonical ID 'grafana'.
