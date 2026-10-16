$taskRoot = Split-Path -Parent $PSScriptRoot
$taskPython = 'C:\Users\pomma\.platformio\penv\Scripts\python.exe'
try {
    $taskStatus = Invoke-RestMethod -Uri 'http://127.0.0.1:8871/status' -TimeoutSec 2
    exit 0
} catch {}
Start-Process -FilePath $taskPython -ArgumentList @(('"' + (Join-Path $PSScriptRoot 'influx_queue.py') + '"')) -WorkingDirectory $taskRoot -WindowStyle Hidden
