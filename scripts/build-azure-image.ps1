# Builds the Azure backend without uploading the full repository or local secrets.
# From repo root: .\scripts\build-azure-image.ps1 -Target Local -Tag local-test
# To ACR (pushes, does NOT deploy): .\scripts\build-azure-image.ps1 -Target Acr -Tag v2
[CmdletBinding()]
param(
    [ValidateSet('Local', 'Acr')]
    [string]$Target = 'Local',
    [ValidatePattern('^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$')]
    [string]$Tag = 'local-test',
    [string]$Registry = 'drewettknowledgeapi'
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$api = Join-Path $repo 'knowledge-api'
$dockerfile = Join-Path $api 'Dockerfile.azure'
$taxonomy = Join-Path $repo 'taxonomy/taxonomy.yml'
$requirements = Join-Path $api 'requirements.txt'
$appDir = Join-Path $api 'app'
$dataDir = Join-Path $api 'data'
$indexFiles = @('chunks.json', 'vectors.faiss', 'manifest.json')

foreach ($path in @($dockerfile, $taxonomy, $requirements, $appDir, $dataDir)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required source missing: $path"
    }
}
foreach ($file in $indexFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $dataDir $file))) {
        throw "Missing search index: $(Join-Path $dataDir $file). Rebuild the index before packaging."
    }
}
if ($Target -eq 'Acr' -and $Tag -eq 'v1') {
    throw 'Refusing to overwrite the previously deployed v1 tag. Choose a new tag, e.g. v2.'
}

$context = Join-Path ([System.IO.Path]::GetTempPath()) ("portfolio-rag-build-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $context -Force | Out-Null

try {
    $stageApi = Join-Path $context 'knowledge-api'
    $stageTaxonomy = Join-Path $context 'taxonomy'
    New-Item -ItemType Directory -Path $stageApi, $stageTaxonomy | Out-Null
    Copy-Item -LiteralPath $dockerfile -Destination (Join-Path $context 'Dockerfile')
    Copy-Item -LiteralPath $requirements -Destination (Join-Path $stageApi 'requirements.txt')
    Copy-Item -LiteralPath $appDir -Destination $stageApi -Recurse

    $stageData = Join-Path $stageApi 'data'
    New-Item -ItemType Directory -Path $stageData | Out-Null
    foreach ($file in $indexFiles) {
        Copy-Item -LiteralPath (Join-Path $dataDir $file) -Destination $stageData
    }
    Copy-Item -LiteralPath $taxonomy -Destination (Join-Path $stageTaxonomy 'taxonomy.yml')

    # Defense in depth in case the app folder contains local environment files.
    @'
**/.env
**/.env.*
**/*.tfstate
**/*.tfstate.*
**/__pycache__/**
**/*.pyc
'@ | Set-Content -LiteralPath (Join-Path $context '.dockerignore') -Encoding utf8

    Write-Host "Staged approved build inputs at $context"
    if ($Target -eq 'Local') {
        & docker build --file (Join-Path $context 'Dockerfile') --tag "portfolio-rag:$Tag" $context
        if ($LASTEXITCODE -ne 0) { throw "Local Docker build failed ($LASTEXITCODE)." }
        Write-Host "Built image: portfolio-rag:$Tag"
        Write-Host "Try: docker run --rm -p 127.0.0.1:8001:8000 portfolio-rag:$Tag"
    } else {
        & az acr build --registry $Registry --image "portfolio-rag:$Tag" --file (Join-Path $context 'Dockerfile') $context
        if ($LASTEXITCODE -ne 0) { throw "ACR build failed ($LASTEXITCODE)." }
        Write-Host "Pushed $Registry.azurecr.io/portfolio-rag:$Tag"
        Write-Host 'This does not change your running Container App or Terraform image tag.'
    }
} finally {
    if (Test-Path -LiteralPath $context) {
        Remove-Item -LiteralPath $context -Recurse -Force
    }
}
