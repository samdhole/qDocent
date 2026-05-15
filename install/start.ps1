#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$envFile  = Join-Path $repoRoot '.env'
$healthUrl = 'http://localhost:8000/health'
$appUrl    = 'http://localhost:3000'
$healthTimeout = 60
$pollInterval  = 3

# Check Docker is running
$dockerRunning = $false
try {
    $null = docker info 2>$null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch { }

if (-not $dockerRunning) {
    Write-Error 'Docker is not running. Please start Docker Desktop and try again.'
    exit 1
}

# Check .env exists — run setup first if missing
if (-not (Test-Path $envFile)) {
    Write-Error '.env not found. Run install\setup.ps1 first.'
    exit 1
}

Push-Location $repoRoot
try {
    # Check if API container already running
    $runningServices = docker compose ps --status running 2>$null
    if ($runningServices -match '(?m)(^| )api( |$)') {
        Write-Host 'Stack is already running. Opening browser...'
    } else {
        Write-Host 'Starting stack...'
        docker compose up -d

        # Health wait loop: poll every 3 s for up to 60 s
        $elapsed = 0
        $healthy = $false
        Write-Host 'Waiting for API to be healthy...'
        while ($elapsed -lt $healthTimeout) {
            try {
                $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
                if ($resp.StatusCode -eq 200) {
                    $healthy = $true
                    Write-Host 'API is healthy.'
                    break
                }
            } catch {
                # not ready yet — continue polling
            }
            Start-Sleep -Seconds $pollInterval
            $elapsed += $pollInterval
        }

        if (-not $healthy) {
            docker compose logs --tail=20 api
            Write-Error "API did not become healthy within ${healthTimeout}s. See logs above."
            exit 1
        }
    }
} finally {
    Pop-Location
}

Start-Process $appUrl
