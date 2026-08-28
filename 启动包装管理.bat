@echo off
setlocal
cd /d "%~dp0"
title Senju CRM - Packaging Management
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-packaging-management.ps1"
if errorlevel 1 (
  echo.
  echo Packaging management failed to start. Review the error above.
  pause
  exit /b 1
)
echo.
echo Packaging management has opened in your browser.
pause
