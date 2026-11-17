param([Parameter(Mandatory=$true, Position=0)][string]$FilePath)
$ErrorActionPreference = 'Stop'
# The CA-issued certificate and its non-exportable key are provisioned on a protected
# release runner, not copied from GitHub secrets or committed to this repository.
$thumbprint = $env:GT_WINDOWS_CERT_THUMBPRINT
if ($thumbprint -notmatch '^[A-Fa-f0-9]{40}$' -or -not $env:GT_WINDOWS_PUBLISHER) {
    throw 'A trusted certificate thumbprint and verified publisher identity are required.'
}
$certificate = Get-Item -LiteralPath "Cert:\CurrentUser\My\$thumbprint"
if (-not $certificate.HasPrivateKey -or $certificate.NotAfter -le (Get-Date)) { throw 'Signing certificate/key unavailable or expired.' }
if ($certificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false) -ne $env:GT_WINDOWS_PUBLISHER) {
    throw 'Certificate publisher does not match release configuration.'
}
$tool = Get-ChildItem -Path "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" | Sort-Object FullName -Descending | Select-Object -First 1
if (-not $tool) { throw 'Windows SDK SignTool is required on the signing runner.' }
& $tool.FullName sign /sha1 $thumbprint /s My /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $FilePath
if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed.' }
& $tool.FullName verify /pa $FilePath
if ($LASTEXITCODE -ne 0) { throw 'Authenticode trust verification failed.' }
$signature = Get-AuthenticodeSignature -LiteralPath $FilePath
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $thumbprint -or -not $signature.TimeStamperCertificate) {
    throw 'Signature, publisher or timestamp verification failed.'
}
