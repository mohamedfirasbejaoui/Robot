@echo off
REM ========================================
REM Launch script for Windows
REM ========================================

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo 🤖 ROBOT NAVIGATION SYSTEM - WINDOWS LAUNCHER
echo ================================================================================
echo.

REM Check Python
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found!
    echo Install from: https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Check Webots
echo.
echo Checking Webots...
where webots >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Webots not in PATH
    echo Trying default locations...
    
    if exist "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe" (
        set WEBOTS_PATH=C:\Program Files\Webots
        echo ✅ Found Webots at: !WEBOTS_PATH!
    ) else (
        echo ❌ Webots not found!
        echo Install from: https://cyberbotics.com
        pause
        exit /b 1
    )
) else (
    for /f "delims=" %%i in ('where webots') do set WEBOTS_PATH=%%i
    echo ✅ Webots found
)

REM Set environment
set WEBOTS_HOME=%WEBOTS_PATH%
echo Setting WEBOTS_HOME=%WEBOTS_HOME%

REM Launch Python script
echo.
echo ================================================================================
echo 🚀 Launching simulation...
echo ================================================================================
echo.

cd /d "%~dp0"
python scripts\launch_simulation.py

REM Error handling
if errorlevel 1 (
    echo.
    echo ❌ Error during execution
    pause
    exit /b 1
)

echo.
echo ✅ Simulation completed
pause
