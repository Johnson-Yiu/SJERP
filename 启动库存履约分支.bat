@echo off
setlocal
cd /d "%~dp0"
title Senju CRM - Inventory Fulfillment Branch
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-inventory-fulfillment.ps1"
if errorlevel 1 (
  echo.
  echo Inventory fulfillment branch failed to start. Review the error above.
  pause
  exit /b 1
)
echo.
echo Inventory fulfillment branch has opened in your browser.
pause
