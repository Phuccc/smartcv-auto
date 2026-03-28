# Script to import Workflows and Credentials to n8n
# Resolve script location to ensure it runs correctly from anywhere
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Join-Path $scriptPath ".."
Set-Location $projectRoot

Write-Host "Project Root: $projectRoot" -ForegroundColor Gray
Write-Host "Starting n8n data import..." -ForegroundColor Cyan

# Check if n8n container is running
$n8nContainer = docker compose ps -q n8n
if (-not $n8nContainer) {
    Write-Host "Error: n8n container is not running. Please start the system first with 'docker compose up -d' or use update_n8n.ps1" -ForegroundColor Red
    exit 1
}

# 1. Import Workflows
Write-Host "Importing Workflows from n8n_storage/workflow..." -ForegroundColor Yellow
docker compose exec -u node n8n n8n import:workflow --separate --input=/data/workflow
if ($LASTEXITCODE -eq 0) {
    Write-Host "Workflows imported successfully." -ForegroundColor Green
} else {
    Write-Host "Failed to import workflows." -ForegroundColor Red
}

# 2. Import Credentials
Write-Host "`nImporting Credentials from n8n_storage/certificate..." -ForegroundColor Yellow
docker compose exec -u node n8n n8n import:credentials --separate --input=/data/certificate
if ($LASTEXITCODE -eq 0) {
    Write-Host "Credentials imported successfully." -ForegroundColor Green
} else {
    Write-Host "Failed to import credentials." -ForegroundColor Red
}

Write-Host "`nImport process completed!" -ForegroundColor Cyan
