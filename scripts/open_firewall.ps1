# Opens the ports GreenTokens training needs, on PRIVATE networks only.
# Run from a normal PowerShell:  powershell -ExecutionPolicy Bypass -File scripts\open_firewall.ps1
# Windows will show a Yes/No permission prompt; choose Yes. Safe to run more than once.
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Asking Windows for permission (choose Yes)..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`""
    exit
}

$python = Join-Path $env:LOCALAPPDATA 'ai.greentokens.provider\python\cpython-3.12-windows-x86_64-none\python.exe'
$rules = @(
    @{ Name = 'GreenTokens job head'; Args = @{ Protocol = 'TCP'; LocalPort = '6501-6507', '10200-10299' } },
    @{ Name = 'GreenTokens training python'; Args = @{ Program = $python } }
)
foreach ($rule in $rules) {
    if (Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue) {
        Write-Host "Already exists: $($rule.Name)"
        continue
    }
    $params = $rule.Args
    New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Profile Private -Action Allow @params | Out-Null
    Write-Host "Created: $($rule.Name)"
}
Write-Host ""
Get-NetFirewallRule -DisplayName 'GreenTokens*' | Select-Object DisplayName, Enabled, Profile | Format-Table
Read-Host "Done. Press Enter to close"
