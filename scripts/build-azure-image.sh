#!/usr/bin/env bash
# Linux/Bash counterpart of build-azure-image.ps1; publishes images, never deploys.
set -euo pipefail

target=Local
tag=local-test
registry=drewettknowledgeapi
usage() {
  echo 'Usage: bash scripts/build-azure-image.sh [--target Local|Acr] [--tag TAG] [--registry NAME]'
}
while (($#)); do
  case "$1" in
    --target|--tag|--registry)
      if (($# < 2)); then usage >&2; exit 2; fi
      case "$1" in
        --target) target=$2 ;;
        --tag) tag=$2 ;;
        --registry) registry=$2 ;;
      esac
      shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ $target == Local || $target == Acr ]] || { usage >&2; exit 2; }
[[ $tag =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$ ]] || { echo 'Invalid image tag' >&2; exit 2; }
[[ $registry =~ ^[a-zA-Z0-9]{5,50}$ ]] || { echo 'Invalid ACR registry name' >&2; exit 2; }
if [[ $target == Acr && $tag == v1 ]]; then
  echo 'Refusing to overwrite the previously deployed v1 tag. Choose a new tag.' >&2
  exit 2
fi

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
api="$repo/knowledge-api"
for file in "$api/Dockerfile.azure" "$api/requirements.txt" "$repo/taxonomy/taxonomy.yml" \
  "$api/data/chunks.json" "$api/data/vectors.faiss" "$api/data/manifest.json"; do
  [[ -f $file ]] || { echo "Required source missing: $file" >&2; exit 1; }
done
[[ -d $api/app ]] || { echo "Required source missing: $api/app" >&2; exit 1; }
if [[ $target == Local ]]; then command -v docker >/dev/null; else command -v az >/dev/null; fi

context=$(mktemp -d "${TMPDIR:-/tmp}/portfolio-rag-build-XXXXXXXX")
cleanup() { rm -rf -- "$context"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "$context/knowledge-api/data" "$context/taxonomy"
cp "$api/Dockerfile.azure" "$context/Dockerfile"
cp "$api/requirements.txt" "$context/knowledge-api/requirements.txt"
cp -R "$api/app" "$context/knowledge-api/app"
for file in chunks.json vectors.faiss manifest.json; do
  cp "$api/data/$file" "$context/knowledge-api/data/$file"
done
cp "$repo/taxonomy/taxonomy.yml" "$context/taxonomy/taxonomy.yml"
cat > "$context/.dockerignore" <<'IGNORE'
**/.env
**/.env.*
**/*.tfstate
**/*.tfstate.*
**/__pycache__/**
**/*.pyc
IGNORE

echo "Staged approved build inputs at $context"
if [[ $target == Local ]]; then
  docker build --file "$context/Dockerfile" --tag "portfolio-rag:$tag" "$context"
  echo "Built image: portfolio-rag:$tag"
else
  az acr build --registry "$registry" --image "portfolio-rag:$tag" --file "$context/Dockerfile" "$context"
  echo "Pushed $registry.azurecr.io/portfolio-rag:$tag"
  echo 'This does not change your running Container App or Terraform image tag.'
fi
