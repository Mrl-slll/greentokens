$ErrorActionPreference = 'Stop'
$version = (Get-Content package.json -Raw | ConvertFrom-Json).version
if ($env:GITHUB_REF_NAME -ne "provider-v$version") { throw 'Release tag must match package.json version. Use a new version for every release.' }
if ($env:GT_WINDOWS_CERT_THUMBPRINT -notmatch '^[A-Fa-f0-9]{40}$' -or -not $env:GT_WINDOWS_PUBLISHER) {
    throw 'Signing has not been provisioned. Refusing to build an unsigned public release.'
}
$base = Get-Content src-tauri/tauri.conf.json -Raw | ConvertFrom-Json
$cargo = Get-Content src-tauri/Cargo.toml -Raw
if ($base.version -ne $version -or $cargo -notmatch ('(?m)^version = "' + [regex]::Escape($version) + '"')) { throw 'App, Cargo and package versions must match.' }
if ((Get-Content provider-server.json -Raw | ConvertFrom-Json).url -match '\.trycloudflare\.com') {
    throw 'Public signed releases need a permanent server hostname; temporary quick tunnels expire.'
}
$config = @{
    bundle = @{
        publisher = $env:GT_WINDOWS_PUBLISHER
        windows = @{
            signCommand = @{ cmd = 'pwsh'; args = @('-NoProfile', '-File', (Resolve-Path 'scripts/sign-windows.ps1').Path, '%1') }
        }
    }
}
# Contains only public metadata and a fixed command; never credentials.
$config | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 src-tauri/tauri.signing.conf.json
