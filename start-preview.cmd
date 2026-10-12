@echo off
cd /d "%~dp0"
echo Starting the local database, API, and H4T Bot preview...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
if errorlevel 1 (
  echo.
  echo The preview did not start. Check the error above.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:5173/login"
