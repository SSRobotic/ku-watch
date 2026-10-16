# Follow the currently running audit and retain timestamped report images.
$captureRoot = Split-Path -Parent $PSScriptRoot
$captureOutput = Join-Path $captureRoot 'output/presentation_evidence'
$captureStatus = Get-Content -LiteralPath (Join-Path $captureRoot 'output/soak_audit/status.json') -Raw | ConvertFrom-Json
if ($captureStatus.status -ne 'running') { throw 'The audit is not running; capture a final report with capture_test_evidence.cjs instead.' }
New-Item -ItemType Directory -Force -Path $captureOutput | Out-Null
$captureLock = Join-Path $captureOutput 'collector.json'
if (Test-Path -LiteralPath $captureLock) {
    $capturePrevious = Get-Content -LiteralPath $captureLock -Raw | ConvertFrom-Json
    if (Get-Process -Id $capturePrevious.pid -ErrorAction SilentlyContinue) { throw 'An evidence collector is already running.' }
}
$captureProcess = Start-Process -FilePath 'C:/Program Files/nodejs/node.exe' -ArgumentList @(('"' + (Join-Path $PSScriptRoot 'capture_test_evidence.cjs') + '"'),'--follow','--interval','300','--audit-pid',([string]$captureStatus.pid)) -WorkingDirectory $captureRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $captureOutput 'collector.stdout.log') -RedirectStandardError (Join-Path $captureOutput 'collector.stderr.log') -PassThru
Write-Output ('Evidence capture started. PID=' + $captureProcess.Id + '; audit PID=' + $captureStatus.pid + '. Verify latest.json and PNG before reporting success.')
