# Script to update n8n and related services (Project: self-hosted_n8n)
# Resolve script location to ensure it runs correctly from anywhere
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Join-Path $scriptPath ".."
Set-Location $projectRoot

Write-Host "Project Root: $projectRoot" -ForegroundColor Gray
Write-Host "Starting n8n update process..." -ForegroundColor Cyan

# 0. Cleanup Old Project Services (One-time cleanup)
# Because we renamed the project from 'n8n_supabase_self-host' to 'self-hosted_n8n',
# we need to make sure the old containers are stopped.
$oldContainers = docker ps -q --filter "name=n8n_supabase_self-host"
if ($oldContainers) {
    Write-Host "Found containers from old project name. Stopping and removing them..." -ForegroundColor Yellow
    docker stop $oldContainers
    docker rm $oldContainers
}

# 1. Pull the latest images
Write-Host "Pulling latest images..." -ForegroundColor Yellow
docker compose pull

# 2. Stop the current containers (Graceful shutdown)
Write-Host "Stopping current containers..." -ForegroundColor Yellow
docker compose down --remove-orphans

# 3. Start the containers in detached mode
Write-Host "Starting up containers..." -ForegroundColor Green
docker compose up -d

# 4. Prune unused images to save space
Write-Host "Cleaning up old images..." -ForegroundColor Gray
docker image prune -f

Write-Host "Update completed successfully!" -ForegroundColor Green
