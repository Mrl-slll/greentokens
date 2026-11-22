# GreenTokens provider check (Windows). Read-only: installs and changes nothing.
# Run in PowerShell:  powershell -ExecutionPolicy Bypass -File provider_check.ps1 -Server <address you were given>
# Then send the printed block back to the GreenTokens operator.
param([string]$Server = "")
$ErrorActionPreference = "SilentlyContinue"

Write-Output "== GreenTokens provider check (Windows) =="
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Write-Output ("OS: {0} (build {1})" -f $os.Caption, $os.BuildNumber)
Write-Output ("CPU: {0} ({1} threads)" -f $cpu.Name.Trim(), $cpu.NumberOfLogicalProcessors)
Write-Output ("RAM: {0:N1} GB" -f ($os.TotalVisibleMemorySize / 1MB))

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $gpus = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
    foreach ($g in $gpus) { Write-Output "GPU: $g" }
    $cuda = (& nvidia-smi | Select-String "CUDA Version:\s*([0-9.]+)").Matches | Select-Object -First 1
    if ($cuda) { Write-Output ("CUDA supported by driver: {0}" -f $cuda.Groups[1].Value) }
} else {
    Write-Output "GPU: no NVIDIA driver found (nvidia-smi missing)"
}

$ips = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' }).IPAddress
Write-Output ("Network addresses: {0}" -f ($ips -join ", "))
Write-Output ("Network type: {0}" -f ((Get-NetConnectionProfile | ForEach-Object { "$($_.Name)=$($_.NetworkCategory)" }) -join ", "))
Write-Output ("Tailscale: {0}" -f $(if (Get-Command tailscale -ErrorAction SilentlyContinue) { "installed" } else { "not installed" }))
Write-Output ("Disk free on C: {0:N0} GB" -f ((Get-PSDrive C).Free / 1GB))

if ($Server) {
    $ok = (Test-NetConnection -ComputerName $Server -Port 6379 -WarningAction SilentlyContinue).TcpTestSucceeded
    Write-Output ("Can reach GreenTokens server {0}:6379 -> {1}" -f $Server, $(if ($ok) { "YES" } else { "NO" }))
}
Write-Output "== end =="
