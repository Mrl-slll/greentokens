$ErrorActionPreference = 'Stop'
$installers = @(Get-ChildItem src-tauri/target/release/bundle/nsis/*.exe)
if ($installers.Count -ne 1) { throw 'Expected exactly one Windows installer.' }
if ($env:GITHUB_REF -like 'refs/tags/provider-v*') {
    foreach ($file in @('src-tauri/target/release/greentokens-provider.exe', $installers[0].FullName)) {
        $signature = Get-AuthenticodeSignature -LiteralPath $file
        if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $env:GT_WINDOWS_CERT_THUMBPRINT -or -not $signature.TimeStamperCertificate) {
            throw 'App executable and installer must both have a valid, timestamped release signature.'
        }
    }
}
New-Item -ItemType Directory -Force out | Out-Null
Copy-Item -LiteralPath $installers[0].FullName -Destination out/GreenTokens-Provider-Setup.exe
$hash = (Get-FileHash out/GreenTokens-Provider-Setup.exe -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  GreenTokens-Provider-Setup.exe" | Set-Content -Encoding ascii out/Windows-SHA256SUMS.txt
