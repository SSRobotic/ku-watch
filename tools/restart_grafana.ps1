# Run in an administrator terminal only if Windows denies service access.
# Configuration is prepared separately; this does not change accounts or data.
$ErrorActionPreference = 'Stop'
Restart-Service -Name Grafana
(Get-Service -Name Grafana).WaitForStatus('Running', [TimeSpan]::FromSeconds(30))
$grafanaHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:3000/api/health' -TimeoutSec 10
if ($grafanaHealth.database -ne 'ok') { throw 'Grafana database health did not return ok' }
Write-Output 'Grafana restarted; database health is ok. Verify the loaded KU dashboard refresh separately.'
