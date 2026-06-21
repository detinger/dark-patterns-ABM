@echo off
REM Windows batch wrapper for PowerShell setup script
powershell -ExecutionPolicy Bypass -File "%~dp0setup-local.ps1"
pause
