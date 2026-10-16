# Run with Windows PowerShell 5.1 (WinRT projection is unavailable in PowerShell 7).
# Restore the existing hotspot; preserve its SSID, passphrase and band.
$ErrorActionPreference = 'Stop'
$taskConnection = [Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime]::GetInternetConnectionProfile()
$taskTether = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]::CreateFromConnectionProfile($taskConnection)
$taskBefore = $taskTether.TetheringOperationalState.ToString()
if ($taskBefore -eq 'Off') {
    $taskOperation = $taskTether.StartTetheringAsync()
    $taskDeadline = (Get-Date).AddSeconds(20)
    while ($taskTether.TetheringOperationalState.ToString() -ne 'On' -and (Get-Date) -lt $taskDeadline) { Start-Sleep -Milliseconds 250 }
}
[pscustomobject]@{Before=$taskBefore; State=$taskTether.TetheringOperationalState.ToString(); Ssid=$taskTether.GetCurrentAccessPointConfiguration().Ssid; Clients=$taskTether.ClientCount} | ConvertTo-Json -Compress
if ($taskTether.TetheringOperationalState.ToString() -ne 'On') { exit 1 }
