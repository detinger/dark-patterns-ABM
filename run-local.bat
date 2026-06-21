@echo off
REM Windows batch wrapper for PowerShell run script
powershell -ExecutionPolicy Bypass -File "%~dp0run-local.ps1"
pause
