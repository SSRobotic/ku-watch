$ErrorActionPreference = 'Stop'
$taskSw = New-Object -ComObject SldWorks.Application
Write-Output ('SOLIDWORKS revision: ' + $taskSw.RevisionNumber())
Write-Output ('Visible: ' + $taskSw.Visible)
