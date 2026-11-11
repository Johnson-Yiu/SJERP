@echo off
setlocal EnableExtensions
set "ProjectRoot=%~dp0"
cd /d "%ProjectRoot%"
title Senju CRM ERP - Development Demo

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ProjectRoot%start-main-worktree.ps1"
if errorlevel 1 (
    echo.
    echo Startup failed. Review the error above.
    pause
    exit /b 1
)

echo.
echo Development demo started. Opening the system in your browser.
pause
