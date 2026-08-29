@echo off
setlocal
cd /d "%~dp0"
title Senju CRM ERP

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "start-main-worktree.ps1"
if errorlevel 1 (
    echo.
    echo Startup failed. Review the error above.
    pause
    exit /b 1
)

echo.
echo Service started. Opening the system in your browser.
pause
