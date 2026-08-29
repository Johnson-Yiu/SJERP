@echo off
setlocal
cd /d "%~dp0"
title 森爵 CRM ERP - 主工作树

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-main-worktree.ps1"
if errorlevel 1 (
    echo.
    echo 服务启动失败，请查看上面的错误信息。
    pause
    exit /b 1
)

echo.
echo 服务已启动，浏览器正在打开系统页面。
pause
