# Start the GreenTokens server on THIS computer for a test day: backend + public tunnel.
# Run from the project folder:  powershell -ExecutionPolicy Bypass -File scripts\start_server.ps1
# Helpers run in hidden windows. They keep running after this script ends; stop their processes to end the test.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$home_gt = Join-Path $HOME ".greentokens"
New-Item -ItemType Directory -Force $home_gt | Out-Null
$python = Join-Path $root ".venv\Scripts\python.exe"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

function Healthy { try { (Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 3).status -eq "ok" } catch { $false } }

# 1. Backend (database + storage containers, API, scheduler). Needs Docker Desktop running.
if (Healthy) {
    $health = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 3
    if ($health.provider_auth -ne "password-v1") { throw "An older backend is running. Stop that backend and rerun this script to apply the provider sign-in upgrade." }
    Write-Host "1/3 Backend already running."
}
else {
    Write-Host "1/3 Starting the backend (needs Docker Desktop)..."
    Start-Process -FilePath $python -ArgumentList "-m", "scripts.local_stack" -WorkingDirectory $root -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes(4)
    while (-not (Healthy)) {
        if ((Get-Date) -gt $deadline) { throw "The backend did not start. Check Docker Desktop; run python -m scripts.local_stack in a terminal to see startup errors." }
        Start-Sleep 3
    }
    Write-Host "    Backend is up."
}

# 2. Public tunnel to the API port only (database, storage and Ray stay private).
$urlFile = Join-Path $home_gt "server_url.txt"
$log = Join-Path $home_gt "tunnel.log"
$running = Get-Process cloudflared -ErrorAction SilentlyContinue
$url = if ((Test-Path $urlFile) -and $running) { (Get-Content $urlFile -Raw).Trim() } else { "" }
if ($url) { try { Invoke-RestMethod "$url/health" -TimeoutSec 10 | Out-Null } catch { $url = "" } }
if ($url) { Write-Host "2/3 Tunnel already running: $url" }
else {
    if (-not (Test-Path $cloudflared)) { throw "cloudflared is not installed. Run: winget install Cloudflare.cloudflared" }
    $running | Stop-Process -Force -ErrorAction SilentlyContinue
    Remove-Item $log -ErrorAction SilentlyContinue
    Write-Host "2/3 Starting the public tunnel..."
    Start-Process -FilePath $cloudflared -ArgumentList "tunnel", "--no-autoupdate", "--logfile", "`"$log`"", "--url", "http://127.0.0.1:8000" -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes(2)
    while (-not $url) {
        if ((Get-Date) -gt $deadline) { throw "The tunnel did not report an address. See $log" }
        Start-Sleep 2
        if (Test-Path $log) { $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1; if ($m) { $url = $m.Matches[0].Value } }
    }
    Set-Content $urlFile $url
    Write-Host "    Public address: $url"
    Write-Host "    New temporary address for this PC's test session."
}

# Refresh a temporary preview origin while preserving a configured stable server.
$node = Join-Path $root ".tools\node-v24.22.3-win-x64\node.exe"
if (-not (Test-Path $node)) { $node = (Get-Command node -ErrorAction Stop).Source }
$providerOrigin = (Get-Content -Raw (Join-Path $root "apps\provider_app\provider-server.json") | ConvertFrom-Json).url
if (([uri]$providerOrigin).Host.EndsWith(".trycloudflare.com")) {
    & $node (Join-Path $root "apps\provider_app\scripts\configure-server.mjs") $url
    if ($LASTEXITCODE -ne 0) { throw "Could not configure the provider app server address." }
} else {
    Write-Host "Keeping the provider app's configured server: $providerOrigin"
}

# 3. Point your Databricks notebooks at it.
Write-Host "3/3 Updating your Databricks secret greentokens/url..."
& $python scripts\set_databricks_url.py $url

Write-Host ""
Write-Host "Ready. Server address: $url"
Write-Host "Providers create their own accounts in the new app. No invite codes are needed."
Write-Host "The public address above is for this PC's test backend."
Write-Host "See who is connected:                    .\.venv\Scripts\python.exe -m scripts.providers"
