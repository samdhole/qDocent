#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host '====================================='
Write-Host '  DocQuery Uninstall'
Write-Host '====================================='
Write-Host ''
Write-Host 'This will:'
Write-Host '  - Stop and remove all Docker containers'
Write-Host '  - Remove Docker volumes (database will be wiped)'
Write-Host '  - Remove built Docker images'
Write-Host '  - Delete .env and r2r_gemini.toml'
Write-Host ''
$confirm = Read-Host 'Type "uninstall" to confirm'
if ($confirm -ne 'uninstall') {
    Write-Host 'Aborted.'
    exit 0
}

$dockerRunning = $false
try {
    $ErrorActionPreference = 'SilentlyContinue'
    & docker info | Out-Null
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch {
    $ErrorActionPreference = 'Stop'
}

Push-Location $repoRoot
try {
    if ($dockerRunning) {
        Write-Host 'Stopping stack and removing containers, volumes, and images...'
        docker compose down -v --rmi local
        Write-Host 'Docker resources removed.'
    } else {
        Write-Warning 'Docker is not running — skipping container/image removal.'
    }
} finally {
    Pop-Location
}

foreach ($f in @('.env', 'r2r_gemini.toml')) {
    $path = Join-Path $repoRoot $f
    if (Test-Path $path) {
        Remove-Item $path -Force
        Write-Host "Deleted: $f"
    }
}

Write-Host ''
Write-Host 'Uninstall complete. To reinstall, run: .\install\setup.ps1'
