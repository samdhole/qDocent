#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

$dockerRunning = $false
try {
    $ErrorActionPreference = 'SilentlyContinue'
    & docker info | Out-Null
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $ErrorActionPreference = 'Stop'
}

if (-not $dockerRunning) {
    Write-Error 'Docker is not running. Please start Docker Desktop and try again.'
    exit 1
}

Push-Location $repoRoot
try {
    Write-Host 'Stopping DocQuery stack...'
    docker compose down
    Write-Host 'Stack stopped.'
} finally {
    Pop-Location
}
