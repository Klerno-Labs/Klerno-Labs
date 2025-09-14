@echo off
echo ===== Klerno Labs Launcher =====
echo Starting Python 3.11 application...

set PORT=10000

rem Check if port parameter is provided
if not "%1"=="" set PORT=%1

rem Check if Python 3.11 is installed
python --version 2>nul | findstr /c:"Python 3.11" >nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python 3.11 not found. Please install Python 3.11 from https://www.python.org/downloads/
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

rem Run the PowerShell script
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-311.ps1" -Port %PORT%

rem If we get here, the script exited
echo.
echo Server has stopped. Press any key to exit...
pause >nul