param([string]$Action='Inspect',[string]$OutDir)
$ErrorActionPreference='Stop'
$taskApiRoot='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS (2)\api\redist'
Add-Type -Path ($taskApiRoot+'\SolidWorks.Interop.sldworks.dll')
Add-Type -Path ($taskApiRoot+'\SolidWorks.Interop.swconst.dll')
Add-Type -AssemblyName System.Web.Extensions
Add-Type -ReferencedAssemblies @(($taskApiRoot+'\SolidWorks.Interop.sldworks.dll'),($taskApiRoot+'\SolidWorks.Interop.swconst.dll'),'System.Web.Extensions.dll') -Path (Join-Path $PSScriptRoot 'sw_cad.cs')
[SwCad]::Run($Action,$OutDir)
