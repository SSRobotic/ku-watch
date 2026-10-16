# Start one read-only real telemetry audit; preserve the previous result.
$auditRoot = Split-Path -Parent $PSScriptRoot
$auditDir = Join-Path $auditRoot 'output/soak_audit'
$auditStatus = Join-Path $auditDir 'status.json'
$auditLock = Join-Path $auditDir 'active.json'
if (Test-Path -LiteralPath $auditLock) {
    $auditPrevious = Get-Content -LiteralPath $auditLock -Raw | ConvertFrom-Json
    if (Get-Process -Id $auditPrevious.pid -ErrorAction SilentlyContinue) {
        throw 'An existing audit process is still running; no second audit was started.'
    }
}
$auditArchive = Join-Path $auditDir ('history/' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $auditArchive | Out-Null
foreach ($auditName in @('status.json','active.json','stdout.log','stderr.log')) {
    $auditOld = Join-Path $auditDir $auditName
    if (Test-Path -LiteralPath $auditOld) { Copy-Item -LiteralPath $auditOld -Destination $auditArchive }
}
$auditScript = Join-Path $PSScriptRoot 'soak_audit.cjs'
$auditProcess = Start-Process -FilePath 'C:/Program Files/nodejs/node.exe' -ArgumentList @(('"' + $auditScript + '"'),'--hours','24','--stop-on-failure') -WorkingDirectory $auditRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $auditDir 'stdout.log') -RedirectStandardError (Join-Path $auditDir 'stderr.log') -PassThru
Write-Output ('Read-only 24-hour audit started. PID=' + $auditProcess.Id + '; verify status.json receives real samples.')
