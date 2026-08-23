@echo off
setlocal
cd /d "%~dp0"
title Temporary SKU Management Launcher

if /I "%TEMP_SKU_SKIP_BROWSER%"=="1" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_temp_sku_management.ps1" -SkipBrowser
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_temp_sku_management.ps1"
)
if errorlevel 1 (
  echo.
  echo Temporary SKU management failed to start. Review the error above.
  pause
)
