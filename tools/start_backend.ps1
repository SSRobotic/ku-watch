# Reuse existing databases, flows and credentials. Do not create a new database.
$backendRoot = Split-Path -Parent $PSScriptRoot
$backendLog = Join-Path $backendRoot 'output/backend_logs'
New-Item -ItemType Directory -Force -Path $backendLog | Out-Null
& 'C:/Users/pomma/.platformio/penv/Scripts/python.exe' (Join-Path $PSScriptRoot 'repoint_backend.py')
if ($LASTEXITCODE -ne 0) { throw 'Node-RED workspace paths could not be verified' }
function Test-BackendPort([int] $Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}
if (-not (Test-BackendPort 8181)) {
    $backendInflux = 'D:/iot2026/influxdb/influxdb3.exe'
    if (-not (Test-Path -LiteralPath $backendInflux)) { throw 'Existing InfluxDB executable was not found' }
    Start-Process -FilePath $backendInflux -ArgumentList @('serve','--node-id','SSFOCUS-node','--object-store','file','--data-dir','C:/Users/pomma/.influxdb','--http-bind','127.0.0.1:8181') -WorkingDirectory 'D:/iot2026/influxdb' -WindowStyle Hidden -RedirectStandardOutput (Join-Path $backendLog 'influx.stdout.log') -RedirectStandardError (Join-Path $backendLog 'influx.stderr.log')
}
& (Join-Path $PSScriptRoot 'start_influx_queue.ps1')
if (-not (Test-BackendPort 1880)) {
    Start-Process -FilePath 'C:/Program Files/nodejs/node.exe' -ArgumentList @('C:/Users/pomma/AppData/Roaming/npm/node_modules/node-red/red.js','--userDir','C:/Users/pomma/.node-red','--settings','C:/Users/pomma/.node-red/settings-ku-watch.js') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $backendLog 'nodered.stdout.log') -RedirectStandardError (Join-Path $backendLog 'nodered.stderr.log')
}
Write-Output 'Started existing backend components that were offline; verify API health before assuming ready.'
