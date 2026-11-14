@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-Alex.ps1" -ReportPath "%TEMP%\SJERP-ALEX-%COMPUTERNAME%.txt"
if not errorlevel 1 notepad.exe "%TEMP%\SJERP-ALEX-%COMPUTERNAME%.txt"
pause
