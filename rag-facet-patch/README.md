# Governed facet-filter patch for Docusaurus RAG MVP

This is an incremental patch for the original `docusaurus_governed_rag_mvp.zip` starter. It does **not** modify your existing Docusaurus content, canonical taxonomy, taxonomy validator, Dockerfile, Compose file, or deployment workflows.

## Changes

- Canonical query filtering using `taxonomy/taxonomy.yml`, including `type`, `audiences`, `topics`, `technologies`, and `lifecycle`.
- Rejects unknown facets, inactive/deprecated term IDs, and empty filters with HTTP 422.
- OR within facet values; AND between facets.
- Archived content excluded by default; available using `include_archived: true` **or** `filters.lifecycle: ["archived"]`.
- Filtering occurs before top-K selection and is applied to both BM25 and optional FAISS results.
- Adds unit and HTTP API tests.

**No index rebuild or Docker image rebuild required** when your existing `chunks.json` already includes `facets` (as the starter does). Run `docker compose -f compose.rag.yaml up -d --force-recreate knowledge-api` to restart FastAPI with updated source files. If your image copies the Python source and Compose does not mount it, run `docker compose -f compose.rag.yaml build knowledge-api` first (without `--no-cache`).

## Applying from PowerShell

1. Extract `governed-facet-filter-patch.zip` in your Docusaurus repository root, keeping the directory layout; **or** run the included `apply-governed-filters.ps1` with the patch ZIP located beside it.
2. The PowerShell script backs up any replaced files into a timestamped `.rag-patch-backup/` folder, copies the patch, runs Python syntax checks, and prints commands for the Docker verification. It does not alter your taxonomy.
3. Test and restart:

```powershell
# Files are mounted under /workspace (read-only), app files live in /app.
docker compose -f compose.rag.yaml run --rm knowledge-api python -m pytest -q /app/tests
# If tests are not in the image and not mounted: rebuild using the normal cache first.
docker compose -f compose.rag.yaml build knowledge-api
docker compose -f compose.rag.yaml run --rm knowledge-api python -m pytest -q /app/tests
docker compose -f compose.rag.yaml up -d --force-recreate knowledge-api
```

**Important:** In the original starter `app/` and `tests/` are copied into the Docker image by its Dockerfile, not bind-mounted. Consequently, after changing either, run `docker compose -f compose.rag.yaml build knowledge-api` to incorporate the patch. Because `requirements.txt` is unchanged, Docker reuses its cached dependency installation layer. Do *not* use `--no-cache`.

## PowerShell API examples

```powershell
$body = @{ query = 'API documentation'; top_k = 5; filters = @{ technologies = @('openapi'); lifecycle = @('current') } } | ConvertTo-Json -Depth 5
(Invoke-RestMethod -Uri 'http://localhost:8000/search' -Method Post -ContentType 'application/json' -Body $body).results | Select-Object title, heading, url | Format-Table -Wrap

# Archived documents are opt-in using an explicit lifecycle constraint.
$archived = @{ query = 'API documentation'; filters = @{ lifecycle = @('archived') } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri 'http://localhost:8000/search' -Method Post -ContentType 'application/json' -Body $archived

# Unknown values are rejected with 422.
$invalid = @{ query = 'API documentation'; filters = @{ technologies = @('not-a-valid-id') } } | ConvertTo-Json -Depth 5
try { Invoke-RestMethod -Uri 'http://localhost:8000/search' -Method Post -ContentType 'application/json' -Body $invalid } catch { $_.Exception.Message }
```

See `/taxonomy` for current approved values; filter values must use canonical **IDs** (for example `openapi`) rather than display labels (`OpenAPI`). No AI classification, query expansion, or relevance boosting is introduced by this patch. Filtering uses pre-existing, validated document metadata.
