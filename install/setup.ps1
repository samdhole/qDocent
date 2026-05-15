#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$repoRoot  = Split-Path -Parent $PSScriptRoot
$envFile   = Join-Path $repoRoot '.env'
$tomlFile  = Join-Path $repoRoot 'r2r_gemini.toml'
$healthUrl = 'http://localhost:8000/health'
$appUrl    = 'http://localhost:3000'
$healthTimeout = 60
$pollInterval  = 3

Write-Host '====================================='
Write-Host '  DocQuery Setup Wizard'
Write-Host '====================================='
Write-Host ''

# Helper: convert SecureString → plaintext (PS 5.1 compatible)
function ConvertTo-PlainText {
    param([securestring]$SecureString)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

# Check Docker is running
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
    Write-Host 'Install from: https://www.docker.com/products/docker-desktop/'
    exit 1
}

# Prompt: Google API key (masked)
$apiKeySecure = Read-Host 'Enter your Google API key' -AsSecureString
$apiKey = ConvertTo-PlainText $apiKeySecure
if ([string]::IsNullOrEmpty($apiKey)) {
    Write-Error 'Google API key cannot be empty.'
    exit 1
}
if ($apiKey -match '[|\\&"#]') {
    Write-Error 'API key cannot contain |, \, &, ", or # characters.'
    exit 1
}

# Prompt: Admin email (default admin@example.com)
$adminEmail = Read-Host 'Admin email [admin@example.com]'
if ([string]::IsNullOrEmpty($adminEmail)) {
    $adminEmail = 'admin@example.com'
}

# Prompt: Admin password (masked, confirm, min 8 chars)
$adminPassword = $null
while ($true) {
    $pw1Secure = Read-Host 'Admin password (min 8 characters)' -AsSecureString
    $pw1 = ConvertTo-PlainText $pw1Secure

    if ($pw1.Length -lt 8) {
        Write-Warning 'Password must be at least 8 characters. Try again.'
        continue
    }

    if ($pw1 -match '[|\\&"#]') {
        Write-Warning 'Password cannot contain |, \, &, ", or # characters. Try again.'
        continue
    }

    $pw2Secure = Read-Host 'Confirm admin password' -AsSecureString
    $pw2 = ConvertTo-PlainText $pw2Secure

    if ($pw1 -ne $pw2) {
        Write-Warning 'Passwords do not match. Try again.'
        continue
    }

    $adminPassword = $pw1
    break
}

# Overwrite guard: warn if config files already exist (default: No)
$overwriteNeeded = $false
foreach ($f in @($envFile, $tomlFile)) {
    if (Test-Path $f) {
        Write-Warning "File already exists: $f"
        $overwriteNeeded = $true
    }
}

if ($overwriteNeeded) {
    $answer = Read-Host 'Overwrite existing files? [y/N]'
    if ($answer -notmatch '^[yY]$') {
        Write-Host 'Aborted — existing files not modified.'
        exit 0
    }
}

# Write .env: copy example, substitute GOOGLE_API_KEY
$envExample = Join-Path $repoRoot '.env.example.client'
$envContent = Get-Content $envExample -Raw
$envContent = ($envContent -split "`n" | ForEach-Object {
    if ($_ -match '^GOOGLE_API_KEY=') { "GOOGLE_API_KEY=$apiKey" } else { $_ }
}) -join "`n"
[System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.UTF8Encoding]::new($false))
Write-Host 'Written: .env'

# Write r2r_gemini.toml: copy example, substitute email and password
$tomlExample = Join-Path $repoRoot 'r2r_gemini.toml.example'
$tomlContent = Get-Content $tomlExample -Raw
$tomlContent = $tomlContent.Replace(
    'default_admin_email = "admin@example.com"',
    "default_admin_email = `"$adminEmail`""
)
$tomlContent = $tomlContent.Replace(
    'default_admin_password = "CHANGE_ME"',
    "default_admin_password = `"$adminPassword`""
)
[System.IO.File]::WriteAllText($tomlFile, $tomlContent, [System.Text.UTF8Encoding]::new($false))
Write-Host 'Written: r2r_gemini.toml'

# WSL chown: set data/ ownership for Linux containers (AC2.3)
Write-Host 'Setting data/ directory ownership via WSL...'
wsl mkdir -p data
wsl sudo chown -R 1001:1001 data
Write-Host 'Ownership set.'

# Build Docker images
Write-Host 'Building Docker images (this may take several minutes)...'
Push-Location $repoRoot
try {
    docker compose build

    # Start stack
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
} finally {
    Pop-Location
}

Start-Process $appUrl

Write-Host ''
Write-Host 'Setup complete! Next time, just run: .\install\start.ps1'
