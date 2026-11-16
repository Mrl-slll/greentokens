# Read-only hardware summary for GreenTokens Provider. Fixed script; takes no input.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$cpu = Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1
$system = Get-CimInstance -ClassName Win32_ComputerSystem
$os = Get-CimInstance -ClassName Win32_OperatingSystem

# Win32_VideoController.AdapterRAM caps at 4 GB; the display driver registry key has the full size.
$registryVram = @{}
try {
    Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*' -ErrorAction SilentlyContinue |
        ForEach-Object {
            $size = $_.'HardwareInformation.qwMemorySize'
            if ($_.DriverDesc -and $size) { $registryVram[[string]$_.DriverDesc] = [double]$size }
        }
} catch { }

$gpus = @(Get-CimInstance -ClassName Win32_VideoController | Where-Object { $_.Name } | ForEach-Object {
    $name = [string]$_.Name
    [pscustomobject]@{
        name = $name.Trim()
        adapter_ram = [double]$_.AdapterRAM
        registry_vram = $(if ($registryVram.ContainsKey($name)) { $registryVram[$name] } else { $null })
    }
})

[pscustomobject]@{
    cpu_model = ([string]$cpu.Name).Trim()
    cores = [int]$cpu.NumberOfCores
    threads = [int]$cpu.NumberOfLogicalProcessors
    ram_bytes = [double]$system.TotalPhysicalMemory
    os = ([string]$os.Caption).Trim()
    os_version = [string]$os.Version
    hostname = [string]$env:COMPUTERNAME
    gpus = $gpus
} | ConvertTo-Json -Depth 4 -Compress
