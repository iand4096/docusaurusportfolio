# Apply from an extracted patch folder, without touching taxonomy or CI files.
# Example: powershell -NoProfile -ExecutionPolicy Bypass -File .\rag-facet-patch\apply-governed-filters.ps1
[CmdletBinding()]
param(
    [string]$RepoPath = (Get-Location).Path,
    [switch]$SkipDocker
)
$ErrorActionPreference = 'Stop'
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
$sourceRoot = Join-Path $PSScriptRoot 'patch'
$compose = Join-Path $RepoPath 'compose.rag.yaml'
if (-not (Test-Path -LiteralPath $compose)) { throw "Not the RAG portfolio root: missing $compose" }
if (-not (Test-Path -LiteralPath (Join-Path $RepoPath 'taxonomy/taxonomy.yml'))) { throw 'Canonical taxonomy not found; no files copied.' }
if (-not (Test-Path -LiteralPath (Join-Path $RepoPath 'knowledge-api/app/main.py'))) { throw 'Existing RAG API not found; no files copied.' }
$files = @(
    'knowledge-api/app/main.py',
    'knowledge-api/app/retrieval.py',
    'knowledge-api/app/governance_filters.py',
    'knowledge-api/tests/test_governed_filters.py'
)
$backupDir = Join-Path ([System.IO.Path]::GetTempPath()) ("docusaurus-rag-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
Write-Host "Repository: $RepoPath"
Write-Host "Backing up existing versions (when present) to: $backupDir"
foreach ($relative in $files) {
    $native = $relative.Replace('/', [IO.Path]::DirectorySeparatorChar)
    $from = Join-Path $sourceRoot $native
    $to = Join-Path $RepoPath $native
    if (-not (Test-Path -LiteralPath $from)) { throw "Patch is incomplete: $from" }
    if (Test-Path -LiteralPath $to) {
        $backup = Join-Path $backupDir $native
        New-Item -Path (Split-Path $backup -Parent) -ItemType Directory -Force | Out-Null
        Copy-Item -LiteralPath $to -Destination $backup -Force
    }
    New-Item -Path (Split-Path $to -Parent) -ItemType Directory -Force | Out-Null
    Copy-Item -LiteralPath $from -Destination $to -Force
    Write-Host "Updated: $relative" -ForegroundColor Green
}
Write-Host 'Patch copied. Taxonomy, docs, Docker config and existing indexes are unchanged.' -ForegroundColor Green
if ($SkipDocker) {
    Write-Host 'Skipped Docker as requested. Run the commands in README.md when ready.'
    exit 0
}
Push-Location $RepoPath
try {
    Write-Host 'Building the application image (uses cached dependencies)...' -ForegroundColor Cyan
    & docker compose -f compose.rag.yaml build knowledge-api
    if ($LASTEXITCODE -ne 0) { throw 'Docker build failed; the old container is unchanged.' }

    Write-Host 'Running Python tests with host test directory mounted read-only...' -ForegroundColor Cyan
    $testVolume = (Join-Path $RepoPath 'knowledge-api/tests') + ':/app/tests:ro'
    & docker compose -f compose.rag.yaml run --rm --volume $testVolume knowledge-api python -m pytest -q /app/tests
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed; stopping before API restart.' }

    Write-Host 'Restarting FastAPI against the existing index...' -ForegroundColor Cyan
    & docker compose -f compose.rag.yaml up -d --force-recreate knowledge-api
    if ($LASTEXITCODE -ne 0) { throw 'API restart failed.' }
    Write-Host 'Ready. Check http://localhost:8000/docs and http://localhost:8000/taxonomy' -ForegroundColor Green
    Write-Host 'See README.md for sample faceted search requests.'
}
finally { Pop-Location }
