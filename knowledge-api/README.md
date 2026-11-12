# Governed RAG API

FastAPI backend for the portfolio's published AI search page. It retrieves evidence from governed documentation using BM25 keyword search and optional FAISS semantic search, then optionally sends retrieved passages to DeepSeek for a cited answer.

## Architecture and deployment

The repository configures two separately deployed parts:

- **Frontend:** the GitHub Pages workflow in [deploy.yml](../.github/workflows/deploy.yml) builds Docusaurus with `RAG_SEARCH_ENABLED=true` and an HTTPS `RAG_API_URL` pointing to Azure Container Apps. The [search plugin](../plugins/rag-search.cjs) registers the legacy `/ai-search` route, whose `GovernedSearchPage` redirects to `/explore?view=ai-search` (under the site base URL). The [Explore page](../src/pages/explore/index.tsx) renders the AI Search tab using `GovernedSearchExperience`; the Docusaurus configuration adds navigation to Explore. `KnowledgeAssistant` and the MDX example are earlier components, not the published search route.
- **Backend:** [Terraform](../infra/azure/main.tf) configures an Azure Container App with external ingress on port 8000, a Consumption workload, 1 CPU, 2 GiB memory, and zero to one replicas. Its development IP allow rule is commented out, so it does not restrict public access. The app pulls the configured `portfolio-rag:v3` image from Azure Container Registry using a managed identity with `AcrPull`; registry admin access is disabled.
- **Retrieval:** the index builder reads `docs/**/*.md[x]` and the canonical taxonomy, running the existing taxonomy governance check by default. It writes `chunks.json`, `manifest.json`, and, for semantic retrieval, `vectors.faiss`. The API caches the snapshot in memory; no database is used.
- **Generation:** Terraform sets `RAG_CHAT_ENABLED=true` and references the Container Apps secret `deepseek-api-key`. The key is managed outside Terraform using Azure CLI. Chat requires both the flag and a nonempty key. Only chat sends the question and retrieved passages to the configured generation provider; search runs within the API process.

These statements describe checked-in configuration, not a live deployment audit. Terraform references an existing image and externally managed secret; applying it does not build an index or publish updated application code. The deployed image/runtime must contain the matching index, taxonomy, and any required model assets. The local Dockerfile alone copies application code, not the repository or a prebuilt index.

## Local setup

Prerequisites: Docker with Docker Compose, the repository's Node dependencies installed, and the governed source files present, including `scripts/taxonomy.py` and `taxonomy/taxonomy.yml`.

At the repository root:

```bash
cp knowledge-api/.env.example knowledge-api/.env
python scripts/taxonomy.py check --all
# Build a BM25-only index without downloading an embedding model:
docker compose -f compose.rag.yaml build
docker compose -f compose.rag.yaml run --rm knowledge-api python -m app.build_index --keyword-only
docker compose -f compose.rag.yaml up
```

Compose binds the API to `127.0.0.1:8000`, mounts the repository read-only, and provides writable index storage and a model cache. Open `http://localhost:8000/docs` for interactive API documentation:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"taxonomy governance","top_k":5}'
```

For semantic and hybrid retrieval, stop the API before rebuilding, then restart it:

```bash
docker compose -f compose.rag.yaml stop knowledge-api
docker compose -f compose.rag.yaml run --rm knowledge-api python -m app.build_index
docker compose -f compose.rag.yaml up
```

The first semantic build downloads the configured Sentence Transformers model and needs network access, memory, and disk space. The API loads it when the snapshot is first accessed if the manifest enables semantic retrieval, including through `/health`.

To preview the current frontend locally:

```bash
RAG_SEARCH_ENABLED=true RAG_API_URL=http://localhost:8000 npm run start
```

Open `/docusaurusportfolio/explore?view=ai-search` for the AI Search tab. The legacy `/docusaurusportfolio/ai-search` URL redirects there. Production frontend builds require an HTTPS API URL. For local chat, set both `DEEPSEEK_API_KEY` and `RAG_CHAT_ENABLED=true` in `knowledge-api/.env`, then recreate the API container. Without them, `/chat` returns 503 and `/search` remains available.

## API

| Endpoint | Behaviour |
| --- | --- |
| `GET /health` | Returns the index manifest and `index_loaded`; a missing index still returns `status: "ok"`, so check `index_loaded` for readiness. |
| `GET /taxonomy` | Returns active canonical controlled-vocabulary terms; returns 503 if the taxonomy is unavailable. |
| `POST /search` | Retrieves evidence with canonical facet filters and `bm25`, `semantic`, or `hybrid` mode. |
| `POST /chat` | Retrieves evidence and requests a DeepSeek answer with a numbered source list; requires the chat flag and key. |

Example search request:

```json
{"query":"API documentation","filters":{"lifecycle":["historical"],"technologies":["openapi"]},"include_archived":false,"top_k":5,"mode":"hybrid"}
```

Queries must contain 2–500 characters; `top_k` defaults to 5 and must be 1–10. Filters are validated against the active taxonomy. Archived content is excluded by default. Setting `include_archived=true` removes that default exclusion; explicitly including `archived` in `filters.lifecycle` also allows archived content, even when `include_archived=false`. Explicit lifecycle filters still apply when `include_archived=true`, so a filter for `current` does not also return archived content. Hybrid mode falls back to BM25 on a keyword-only index; explicit semantic mode returns 409 without a semantic index. Responses identify the effective mode and index version. Search returns 503 if the index is missing.

## Security and resource controls

The API is configured for public access without application authentication. The implemented controls in [main.py](app/main.py) and [abuse_protection.py](app/abuse_protection.py) limit resource use; they do not provide a distributed abuse-prevention service.

| Control | Implemented behaviour |
| --- | --- |
| Rate limits | Enabled by default: per client identity, per rolling 60 seconds, 20 `POST /search`, 60 `GET /taxonomy`, and 3 `POST /chat` requests. Rejections return 429 with `Retry-After`. `/health` is not rate limited. |
| Limiter memory | Tracks at most 10,000 client/route keys; refuses new keys if expired entries cannot free capacity. Counters are in memory, reset on restart or scale-to-zero, and are not shared across workers or replicas. |
| Client identity | Uses the socket peer by default. `RAG_TRUST_AZURE_XFF=true` opts into using the rightmost valid IP in `X-Forwarded-For`, only where requests cannot bypass trusted Azure ingress. Terraform does not currently set this flag; distinct public users may therefore share a proxy identity and rate budget. |
| Concurrency | At most two simultaneous retrieval operations and one chat operation per process. Chat retrieval shares the search slots. Capacity exhaustion returns 503 with `Retry-After: 2`. |
| Request and generation caps | Query length and result count are validated as above. Provider calls use a 45-second SDK timeout and `max_tokens=600`. These are not a total HTTP body-size limit or a global spending cap. |
| Chat switch | `RAG_CHAT_ENABLED` defaults to false in code; Terraform explicitly enables it. A provider key is also required. `RAG_RATE_LIMIT_ENABLED=false` disables the limiter; Terraform leaves it enabled by default. |
| Browser access | CORS allows configured origins and GET/POST with `Content-Type`. Terraform allows the portfolio's GitHub Pages origin and listed localhost origins. CORS is a browser policy, not authentication, and does not block direct HTTP clients. |
| Prompt and error handling | The system instruction requires evidence-based answers and treats retrieved text as untrusted data. Provider failures return a generic 502 without exposing provider payloads or credentials to browsers. Prompt instructions do not guarantee resistance to injection. |
| Container and secrets | The Dockerfile runs Uvicorn as a non-root user with one worker by default. The provider key is referenced as a Container Apps secret rather than committed in Terraform. |

The one-replica configuration matches the process-local design, but limits are not durable quotas. Increasing workers or replicas creates independent budgets. There is no application authentication, distributed rate limiter, or programmatic verification of generated inline citations. Account for these boundaries when changing exposure, scaling, or paid-generation usage.

## Index operations and limitations

- **Source coverage:** only documentation is indexed; blog content is excluded. MDX extraction is conservative, so custom JSX content may be omitted or noisy. Review generated chunks after source or extraction changes.
- **URLs:** mapping supports frontmatter `slug` and conventional documentation paths; unusual generated routes may require additional mapping rules.
- **Governance:** `taxonomy.py check --all` is the default build gate. `--skip-governance` is intended for test fixtures.
- **Snapshot updates:** generation stages files before replacing them individually; the directory update is not atomic. Stop the API before rebuilding and restart afterward to clear the cached snapshot. Deploy matching source, taxonomy, and index artifacts together.
- **Grounding:** returned sources are retrieved evidence, but model-generated inline citation numbers are not programmatically verified.
- **Performance and dependencies:** retrieval has not been benchmarked here. Semantic snapshot loading adds startup latency and memory use. Python requirements use version ranges rather than a fully locked dependency set.

## Tests

Within a Python environment with `knowledge-api/requirements.txt` and pytest installed:

```bash
cd knowledge-api
python -m pytest -q
```

The tests cover retrieval modes, taxonomy filters, ingestion and heading links, API behaviour, and abuse controls without requiring a provider key or embedding-model download.
