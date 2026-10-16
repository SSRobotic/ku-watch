# Read the existing Windows hotspot only; never start/stop or reconfigure it.
# Invoke through Windows PowerShell 5.1 for WinRT projection support.
$ErrorActionPreference = 'Stop'
$taskConnection = [Windows.Networking.Connectivity.NetworkInformation,Windows.Networking.Connectivity,ContentType=WindowsRuntime]::GetInternetConnectionProfile()
$taskTether = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager,Windows.Networking.NetworkOperators,ContentType=WindowsRuntime]::CreateFromConnectionProfile($taskConnection)
[pscustomobject]@{State=$taskTether.TetheringOperationalState.ToString(); Ssid=$taskTether.GetCurrentAccessPointConfiguration().Ssid; Clients=$taskTether.ClientCount} | ConvertTo-Json -Compress
