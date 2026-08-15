@echo off
setlocal
cd /d "%~dp0"
title Senju CRM - Service Launcher

if not exist ".venv\Scripts\python.exe" goto setup
if not exist "frontend\node_modules" goto setup
goto start

:setup
echo First-time setup in progress. This may take a few minutes...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto failed

:start
echo Starting service...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 goto failed
echo.
echo The system has opened in your browser. You may close this window.
pause
exit /b 0

:failed
echo.
echo Service startup failed. Please review the error above.
pause
exit /b 1
