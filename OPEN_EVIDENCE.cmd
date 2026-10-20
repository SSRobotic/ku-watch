@echo off
if exist "%~dp0output\demo_evidence\index.html" (
  start "" "%~dp0output\demo_evidence\index.html"
  exit /b 0
)
if exist "%~dp0submission\final-2026-10-20\04_Evidence\index.html" (
  start "" "%~dp0submission\final-2026-10-20\04_Evidence\index.html"
  exit /b 0
)
echo Evidence index was not found. See docs/FINAL_SUBMISSION.md.
pause
exit /b 1
