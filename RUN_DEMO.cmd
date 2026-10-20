@echo off
setlocal
start "KU Watch Demo" powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%~dp0tools\demo_launcher.ps1" -AutoStart
exit /b
