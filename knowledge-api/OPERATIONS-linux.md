# Governed RAG search: Linux command reference

Bash alternatives to the Windows PowerShell examples in [the operations runbook](OPERATIONS.md). Read that runbook's release boundaries, security guidance and recovery procedures first. These commands use the same existing infrastructure and do not provision a separate environment.

Use Bash, Python 3, Node/npm, Docker Engine with the Compose plugin, Azure CLI, Terraform and curl. No PowerShell installation is required. Commands assume a Linux host capable of running the production Linux container image. Ensure your account can use Docker; do not change socket permissions to bypass access controls.

Run commands in the same Bash session. `set -euo pipefail` stops on failed commands and unset variables; review each deployment step before executing it. Paths below are examples. Keep existing Terraform state and local variable configuration available for the Terraform path. Section 5 also documents an authorised image-only CLI alternative when that state is unavailable.

## 1. Set up the checkout

If using a dedicated WSL Azure login directory, set it before the first `az` command in every new shell. Use your established directory consistently; do not switch to a different credential profile accidentally:

```bash
export AZURE_CONFIG_DIR="$HOME/.azure-wsl"
az account show --query '{subscription:name,id:id}' -o json
# If login has expired or this profile has not been authenticated:
# az login --use-device-code
```

Confirm the intended subscription before continuing. A terminal restart loses exported variables even when the login remains cached. Azure CLI needs write access to its configuration directory; use your normal user account and approved execution permissions.

```bash
set -euo pipefail
cd "$HOME/DocusaurusSite"
repo_root="$PWD"
terraform_dir="$repo_root/infra/azure"
manifest_path="$repo_root/knowledge-api/data/manifest.json"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-doc-review.txt
npm ci

git status --short
docker info --format '{{.ServerVersion}}'
az account show --query '{subscription:name,id:id}' -o json
terraform -version
export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
test -n "$ARM_SUBSCRIPTION_ID"

if [[ ! -f knowledge-api/.env ]]; then
  cp knowledge-api/.env.example knowledge-api/.env
fi
git check-ignore knowledge-api/.env
```

Activate an existing virtual environment instead of recreating it if you already have one. On distributions without Python's venv support, install the appropriate OS package first. The activated environment supplies the `python` command used by repository tooling; inside Docker, `python` is already available. Never print the environment file's contents to a shared terminal or log.

Get resource identifiers from existing Terraform state:

```bash
resource_group=$(terraform -chdir="$terraform_dir" output -raw resource_group)
registry_server=$(terraform -chdir="$terraform_dir" output -raw registry_server)
registry_name=${registry_server%%.*}
api_url=$(terraform -chdir="$terraform_dir" output -raw api_url)
app_name=ca-portfolio-rag
site_origin=https://iand4096.github.io
```

Stop if the account or resources are wrong; do not create replacement infrastructure to make these commands succeed. If established state is unavailable, use the discovery steps in section 5 instead of these Terraform outputs.

## 2. Validate and build the index

```bash
cd "$repo_root"
python scripts/taxonomy.py sync --all
python scripts/taxonomy.py check --all
npm run lint:markdown
npm run see-also:generate
npm run see-also:check
npm run test:see-also
git diff --check
git status --short

docker compose -f compose.rag.yaml stop knowledge-api
docker compose -f compose.rag.yaml build knowledge-api
docker compose -f compose.rag.yaml run --rm knowledge-api python -m app.build_index

python - "$manifest_path" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
manifest = json.loads(path.read_text())
for name in ('chunks.json', 'vectors.faiss', 'manifest.json'):
    if not (path.parent / name).is_file():
        raise SystemExit(f'Missing artifact: {name}')
if not manifest.get('semantic_enabled') or manifest.get('chunks', 0) <= 0:
    raise SystemExit('Release requires a nonempty semantic index')
print(json.dumps(manifest, indent=2))
PY
expected_hash=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["source_hash"])' "$manifest_path")

docker compose -f compose.rag.yaml run --rm knowledge-api python -c \
  "from pathlib import Path; from app.ingest import manifest_hash; import json; actual=manifest_hash(Path('/workspace')); recorded=json.load(open('/app/data/manifest.json'))['source_hash']; print('Match:', actual == recorded); assert actual == recorded"

docker compose -f compose.rag.yaml run --rm -w /workspace/knowledge-api knowledge-api python -m pytest -q
```

On native Linux, the container runs as UID 10001. If it cannot write the bind-mounted `knowledge-api/data/`, create that directory and grant that UID write access using your host's ownership/ACL policy; inspect ownership first. Do not use world-writable permissions or run the production container as root as a workaround. Docker Desktop often handles bind-mount permissions differently.

Check changed documents' extracted passages, headings, metadata and source links before release. Do not use `--keyword-only` or `--skip-governance` for the full production index.

## 3. Define and run API smoke checks

This Bash function uses Python's standard library, so no requests or jq installation is needed. It waits for the expected full index, then checks taxonomy and all three search modes. It never calls `/chat`.

```bash
rag_check() {
  python - "$1" "$2" <<'PY'
import json
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
base, expected = sys.argv[1:]
base = base.rstrip('/')
def request(path, payload=None, timeout=15):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(base + path, data=data, headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)
deadline = time.monotonic() + 240
while True:
    try:
        health = request('/health')
        index = health.get('index') or {}
        if (health.get('index_loaded') and index.get('source_hash') == expected
                and index.get('semantic_enabled') and index.get('chunks', 0) > 0):
            break
    except (URLError, TimeoutError, ValueError, OSError):
        pass
    if time.monotonic() >= deadline:
        raise SystemExit('Readiness failed; inspect index and logs')
    time.sleep(5)
request('/taxonomy', timeout=30)
for mode in ('bm25', 'semantic', 'hybrid'):
    result = request('/search', {
        'query': 'documentation governance', 'mode': mode, 'top_k': 3,
        'filters': {}, 'include_archived': False,
    }, timeout=60)
    if (result.get('mode') != mode or result.get('index_version') != expected[:12]
            or not result.get('results')):
        raise SystemExit(f'Unexpected mode, index version or empty results for {mode}')
    print(mode, 'passed')
    for row in result['results']:
        print(row.get('title'), row.get('heading'), row.get('url'))
PY
}

docker compose -f compose.rag.yaml up -d knowledge-api
rag_check http://localhost:8000 "$expected_hash"
```

As in Windows, inspect relevance, a meaningful taxonomy filter, archived-content behaviour and actual destination links separately. HTTP 200 alone is not sufficient readiness evidence.

## 4. Build the release artifact and test it

The [Bash image builder](../scripts/build-azure-image.sh) is the counterpart of [the PowerShell script](../scripts/build-azure-image.ps1). Both stage the same application, taxonomy and index inputs and clean up the temporary build context on exit. Both publish only; neither deploys. Neither generally prevents overwriting tags: choose a new tag every time.

```bash
cd "$repo_root"
release_tag="rag-$(date -u +%Y%m%d-%H%M%S)"
git rev-parse HEAD
git status --short

# Optional early local build; ACR performs a separate build.
bash scripts/build-azure-image.sh --target Local --tag "$release_tag"

bash scripts/build-azure-image.sh --target Acr --tag "$release_tag" --registry "$registry_name"
az acr login --name "$registry_name"
image_tag="$registry_server/portfolio-rag:$release_tag"
docker pull "$image_tag"
image_digest=$(docker image inspect "$image_tag" --format '{{index .RepoDigests 0}}')
test -n "$image_digest"
printf 'Release artifact: %s\n' "$image_digest"
```

Run the HTTP smoke test in a subshell so its cleanup trap cannot replace traps in your interactive shell:

```bash
(
  set -euo pipefail
  container_name="portfolio-rag-preflight-$(date -u +%Y%m%d%H%M%S)-$$"
  container_started=false
  cleanup() {
    if [[ $container_started == true ]]; then docker stop "$container_name" >/dev/null; fi
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  docker run -d --rm --name "$container_name" -p 127.0.0.1:8001:8000 \
    -e RAG_CHAT_ENABLED=false -e "CORS_ORIGINS=$site_origin" "$image_digest"
  container_started=true
  rag_check http://localhost:8001 "$expected_hash"
  python - "$site_origin" <<'PY_CORS'
import sys
from urllib.request import Request, urlopen
origin = sys.argv[1]
req = Request('http://localhost:8001/search', method='OPTIONS', headers={
    'Origin': origin,
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'content-type',
})
with urlopen(req, timeout=30) as response:
    assert response.status == 200
    assert response.headers.get('Access-Control-Allow-Origin') == origin
print('Release image browser CORS passed')
PY_CORS
)
```

Check offline model loading and semantic retrieval separately:

```bash
(
  set -euo pipefail
  container_name="portfolio-rag-offline-$(date -u +%Y%m%d%H%M%S)-$$"
  container_started=false
  cleanup() {
    if [[ $container_started == true ]]; then docker stop "$container_name" >/dev/null; fi
  }
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  docker run -d --rm --network none --name "$container_name" \
    -e RAG_CHAT_ENABLED=false "$image_digest" python -c 'import time; time.sleep(600)'
  container_started=true
  docker exec "$container_name" python -c \
    "from app.main import health, perform_search, SearchRequest; h=health(); assert h['index_loaded'] and h['index']['semantic_enabled']; r=perform_search(SearchRequest(query='documentation governance', mode='semantic')); assert r['mode']=='semantic' and r['results']; print('Offline model and retrieval passed')"
)
```

Do not deploy if either preflight fails. Record the digest, source hash, Git SHA and model/build configuration as described in the main runbook.

## 5. Terraform deployment and frontend publication

Prefer the tested digest for the image reference in `infra/azure/main.tf`. A unique tag is an alternative only if it still resolves to that digest. Keep existing identity, secret references and configuration intact unless intentionally changing them.

```bash
terraform -chdir="$terraform_dir" fmt
terraform -chdir="$terraform_dir" validate
terraform -chdir="$terraform_dir" plan -out=release.tfplan
terraform -chdir="$terraform_dir" show release.tfplan
```

Stop and review the plan before executing the next block. Do not apply unexpected replacements or deletions. Saved plans are private and ignored by Git.

```bash
terraform -chdir="$terraform_dir" apply release.tfplan
python - "$terraform_dir/release.tfplan" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).unlink()
PY
az containerapp show -n "$app_name" -g "$resource_group" \
  --query 'properties.template.containers[0].image' -o tsv
az containerapp revision list -n "$app_name" -g "$resource_group" -o table
api_url=$(terraform -chdir="$terraform_dir" output -raw api_url)
rag_check "$api_url" "$expected_hash"
```

### Image-only CLI alternative without Terraform state

Follow the [main runbook's alternative deployment guidance](OPERATIONS.md#image-only-azure-cli-alternative). Confirm the subscription and discover the existing resources, then set variables from their returned identifiers:

```bash
az account show --query '{subscription:name,id:id}' -o json
az containerapp list --query '[].{name:name,resourceGroup:resourceGroup}' -o table
az acr list --query '[].{name:name,resourceGroup:resourceGroup,server:loginServer}' -o table
resource_group='<CONFIRMED_RESOURCE_GROUP>'
app_name='<CONFIRMED_APP_NAME>'
registry_name='<CONFIRMED_REGISTRY_NAME>'
registry_server=$(az acr show -n "$registry_name" --query loginServer -o tsv)
site_origin=https://iand4096.github.io
```

Replace placeholders before running subsequent commands. Restore `image_digest` (the full registry/repository@sha256 reference) and `expected_hash` from the release record, and complete section 4 preflight first. Inspect existing configuration locally and record rollback identifiers. Update only the image:

```bash
az containerapp show -n "$app_name" -g "$resource_group" \
  --query '{image:properties.template.containers[0].image,readyRevision:properties.latestReadyRevisionName,mode:properties.configuration.activeRevisionsMode}' -o json
az containerapp update -n "$app_name" -g "$resource_group" --image "$image_digest" \
  --query '{image:properties.template.containers[0].image,latestRevision:properties.latestRevisionName,readyRevision:properties.latestReadyRevisionName}' -o json
api_host=$(az containerapp show -n "$app_name" -g "$resource_group" \
  --query 'properties.configuration.ingress.fqdn' -o tsv)
test -n "$api_host"
api_url="https://$api_host"
```

Align `infra/azure/main.tf` with the deployed digest and run `terraform -chdir="$terraform_dir" fmt`. Do not initialise new state or apply Terraform without the established state. Record the CLI deployment method; review a fresh plan when that state becomes available again. For rollback, use the recorded known-good digest through the same image-only path and verify its recorded hash.

### Verify completion for either deployment path

An update can succeed before the new revision is ready. Inspect revision status:

```bash
az containerapp revision list -n "$app_name" -g "$resource_group" \
  --query '[].{name:name,active:properties.active,health:properties.healthState,running:properties.runningState,replicas:properties.replicas,traffic:properties.trafficWeight,image:properties.template.containers[0].image}' -o json
rag_check "$api_url" "$expected_hash"
```

For this single-revision app, require the intended revision to be healthy with a running replica and 100% of traffic. Confirm the image digest, expected chunk count and taxonomy version, meaningful filtering, archived exclusion and changed source links, then run section 6's public CORS check and verify the returned allowed origin. Record “live verified” only after all checks pass. On timeout, inspect logs before repeating the update.

Preview the frontend with build-time environment variables scoped to that build:

```bash
cd "$repo_root"
RAG_SEARCH_ENABLED=true RAG_API_URL="$api_url" npm run build
npm run serve
```

Open `/docusaurusportfolio/explore?view=ai-search` on localhost port 3000. Stop the server before continuing. Follow the main runbook's reviewed staging/merge and Pages verification steps; no push or merge is performed by these scripts.

## 6. Diagnostics, CORS and secret rotation

```bash
az containerapp show -n "$app_name" -g "$resource_group" \
  --query 'properties.configuration.ingress.ipSecurityRestrictions' -o json
az containerapp show -n "$app_name" -g "$resource_group" \
  --query 'properties.template.containers[0].env' -o json
az containerapp logs show -n "$app_name" -g "$resource_group" --type console --tail 100
az containerapp logs show -n "$app_name" -g "$resource_group" --type system --tail 100

curl --fail-with-body --silent --show-error --max-time 60 -D - -o /dev/null \
  -X OPTIONS "$api_url/search" \
  -H "Origin: $site_origin" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type'
```

Expect HTTP 200 and the configured allowed origin. Review logs locally before sharing. Provider-key rotation can use the Azure Portal on either OS; never paste key values into shell history. After updating the app-level secret, identify and restart the serving revision:

```bash
az containerapp revision list -n "$app_name" -g "$resource_group" -o table
active_revision='<SERVING_REVISION_NAME>'
az containerapp revision restart -n "$app_name" -g "$resource_group" --revision "$active_revision"
rag_check "$api_url" "$expected_hash"
```

Replace the revision placeholder before executing. Use the intended deployed release's hash if the local index has since changed. For rollback, update the Terraform image to the known-good release, review/apply the plan, and check against that release's recorded hash and frontend URLs. The main runbook's incident, cost, security and private-record guidance applies equally to Linux.

## 7. Resume an interrupted release

Follow the [main runbook's recovery procedure](OPERATIONS.md#resume-after-a-terminal-or-wsl-crash). Restore the checkout variables, Azure configuration directory, subscription and `rag_check` function in the new shell. Load the recorded release tag, full digest reference, source hash, expected counts and rollback identifiers from private durable storage. Do not replace the intended release hash with a newer local index's hash.

```bash
docker image inspect "$image_digest" --format '{{json .RepoDigests}}'
docker ps -a --format '{{.Names}} {{.Status}} {{.Image}}'
az containerapp show -n "$app_name" -g "$resource_group" \
  --query '{image:properties.template.containers[0].image,latestRevision:properties.latestRevisionName,readyRevision:properties.latestReadyRevisionName}' -o json
az containerapp revision list -n "$app_name" -g "$resource_group" -o table
```

Compare the local digest with the release record. Resume preflight if the image is available; if Azure already references it, inspect readiness and run live checks before repeating an update. Identify and stop only leftover preflight containers belonging to this release; crash recovery may bypass cleanup traps.

For slow pulls, distinguish downloading from unpacking. Check `docker info`, `docker system df`, `df -h` and `free -h`, plus WSL VM limits where applicable. Avoid concurrent pulls or deleting Docker storage as a routine fix. A locally available matching digest can be tested without rebuilding or republishing.

Maintain the [release record](OPERATIONS.md#10-release-record) with UTC timestamps and evidence at **published**, **preflight passed**, **deployed** and **live verified** checkpoints. Store it privately outside temporary shell state; record artifact identifiers and test summaries without credentials, token values, secret values or Terraform state contents.
