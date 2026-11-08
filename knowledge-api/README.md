# Governed RAG API — local stub MVP

This is an **additive overlay**, not a replacement for the portfolio. It reads docs/ and taxonomy/ read-only, and does not modify your existing Docusaurus build or GitHub Actions workflow.

## Before you start

- Docker + Docker Compose, Node dependencies already installed for Docusaurus.
- Ensure you have the current repo files including `scripts/taxonomy.py`, `taxonomy/taxonomy.yml`, `.frontmatter/`, `src/generated/`, and `docs/tags.yml`.
- On first semantic build, Sentence Transformers downloads a model. No database is needed.

## Local setup

At repository root:

```bash
cp knowledge-api/.env.example knowledge-api/.env
# Optionally set DEEPSEEK_API_KEY in knowledge-api/.env for /chat
python scripts/taxonomy.py check --all
# Build a fast BM25-only index first (no embedding download):
docker compose -f compose.rag.yaml build
docker compose -f compose.rag.yaml run --rm knowledge-api python -m app.build_index --keyword-only
# Start API:
docker compose -f compose.rag.yaml up
```

Open `http://localhost:8000/docs` for the interactive API documentation, then try:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"taxonomy governance","top_k":5}'
```

For local semantic + hybrid retrieval, **stop the API** and build the full index:

```bash
docker compose -f compose.rag.yaml run --rm knowledge-api python -m app.build_index
# Then restart:
docker compose -f compose.rag.yaml up
```

The embedding model and its cache consume local memory and disk; initial download needs network access. The API loads the model only if the index manifest declares semantic search enabled.

## Frontend preview (not auto-published)

The ZIP adds `src/components/KnowledgeAssistant`, but does **not** register a new route or alter your published navigation. To preview it locally, copy the *body* of `knowledge-api/examples/knowledge-assistant.mdx` into a new Docusaurus MDX page of your choosing and use your existing taxonomy governance workflow to add the required valid frontmatter. Do **not** copy the example frontmatter unchanged into `docs/`: it deliberately omits your governed facets.

Run `npm run start` at the repo root. The frontend communicates with `http://localhost:8000`. It is intentionally a local-only component until you deploy and configure a backend URL.

## Tests

Within an installed Python environment:

```bash
cd knowledge-api
python -m pytest -q
```

Tests do not require a DeepSeek API key or model downloads. The initial API endpoint test is a smoke test.

## API

- `GET /health`: current index manifest, or missing-index state
- `GET /taxonomy`: active canonical controlled-vocabulary terms
- `POST /search`: BM25 and optional FAISS search with explicit facet filters
- `POST /chat`: DeepSeek answer with a numbered source list; requires key

Sample explicit facet filters:

```json
{"query":"API documentation","filters":{"lifecycle":["historical"],"technologies":["openapi"]},"include_archived":false,"top_k":5}
```

`archived` is excluded by default, even if explicitly filtered, unless `include_archived=true`. This is an intentional *MVP policy*, not a claim about the repository's current publishing governance.

## Limitations and decisions

- **Documentation only:** indexes `docs/**/*.md[x]`; blog is left out until its URL mapping is designed.
- **MDX extraction is conservative:** custom JSX-rendered content may be omitted or noisy. Review the generated `chunks.json` before any public use.
- **URL mapping:** supports `slug` and conventional `docs/` paths; unusual generated routes may need custom rules.
- **Keyword fallback:** use `--keyword-only` to validate the architecture without embedding libraries/model downloads.
- **Governance:** existing `taxonomy.py check --all` is a mandatory build gate by default; no new canonical validation logic is invented.
- **Snapshot:** stop API before rebuilding; only files are replaced, not a fully atomic directory switch. A later production iteration should use immutable snapshot directories and active-version pointers.
- **Security:** local API only; no authentication, production rate limits, prompt-injection mitigation beyond a basic instruction boundary, or security review yet. Never deploy it directly publicly without these controls.
- **Citation grounding:** cited source list reflects retrieved evidence; model-generated inline numbers are not yet programmatically verified.
- **Performance:** scoring is simple and not yet benchmarked; API lazy-loads model on first semantic request.
- **Dependency ranges:** deliberately broad MVP constraints. Lock exact compatible versions before CI/production.

## Files this overlay touches

Only `knowledge-api/`, `compose.rag.yaml`, and `src/components/KnowledgeAssistant/`. It does not overwrite `package.json`, governance scripts, generated taxonomy artifacts, or CI workflows. Review `unzip -l` before extraction.
