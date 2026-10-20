@echo off
if not exist "%~dp0index.html" (
  echo Please extract the entire ZIP first, then open OPEN_DEMO.cmd.
  pause
  exit /b 1
)
start "" "%~dp0index.html"
