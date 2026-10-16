# Stop only the user's existing SS Windows hotspot for the authorized phone
# comparison. Preserve its settings so resume_hotspot.ps1 can restore it.
# Invoke with Windows PowerShell 5.1 for WinRT projection support.
$ErrorActionPreference = 'Stop'
$taskConnection = [Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime]::GetInternetConnectionProfile()
$taskTether = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]::CreateFromConnectionProfile($taskConnection)
if ($taskTether.GetCurrentAccessPointConfiguration().Ssid -ne 'SS') { throw 'The existing hotspot is not SS; no change made.' }
$taskBefore = $taskTether.TetheringOperationalState.ToString()
if ($taskBefore -eq 'On') {
    $taskOperation = $taskTether.StopTetheringAsync()
    $taskDeadline = (Get-Date).AddSeconds(20)
    while ($taskTether.TetheringOperationalState.ToString() -ne 'Off' -and (Get-Date) -lt $taskDeadline) { Start-Sleep -Milliseconds 250 }
}
[pscustomobject]@{Before=$taskBefore; State=$taskTether.TetheringOperationalState.ToString(); Ssid=$taskTether.GetCurrentAccessPointConfiguration().Ssid; Clients=$taskTether.ClientCount} | ConvertTo-Json -Compress
if ($taskTether.TetheringOperationalState.ToString() -ne 'Off') { exit 1 }
