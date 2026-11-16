# Dot-source this file to prepare the current terminal: . .\scripts\terminal.ps1
$greenTokensRoot = Split-Path -Parent $PSScriptRoot
$greenTokensVenv = Join-Path $greenTokensRoot '.venv'
$greenTokensSdk = Join-Path $greenTokensRoot 'sdk'
$greenTokensNode = Get-ChildItem (Join-Path $greenTokensRoot '.tools') -Directory -Filter 'node-*-win-x64' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1

if (-not (Test-Path (Join-Path $greenTokensVenv 'Scripts\python.exe'))) {
    throw 'Project Python environment is missing. See docs/local-development.md.'
}

Set-Location -LiteralPath $greenTokensRoot
. (Join-Path $greenTokensVenv 'Scripts\Activate.ps1')

if ($greenTokensNode) {
    $greenTokensNodePath = $greenTokensNode.FullName
    $env:PATH = (@($greenTokensNodePath) + @($env:PATH -split ';' | Where-Object { $_ -and $_ -ne $greenTokensNodePath })) -join ';'
}
$env:PYTHONPATH = (@($greenTokensSdk) + @($env:PYTHONPATH -split ';' | Where-Object { $_ -and $_ -ne $greenTokensSdk })) -join ';'

function global:greentokens {
    & (Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe') -m greentokens @args
}

Write-Host 'GreenTokens terminal ready: Python environment, SDK command, and local Node.js.'
Write-Host 'Try: greentokens check | greentokens --help | npm.cmd run dev'
