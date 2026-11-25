@echo off
chcp 65001 >nul
title LyricSky — Live Lyrics Desktop
cd /d "%~dp0"

set "PY_EXE=python"
if exist ".venv\Scripts\python.exe" set "PY_EXE=.venv\Scripts\python.exe"

if "%PY_EXE%"=="python" (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3.10+ not found. Please run Setup.bat first.
        pause
        exit /b 1
    )
)

echo Starting LyricSky...
echo Manage or quit from the star icon in the Windows System Tray, or run LyricSky_Stop.bat.
echo.
"%PY_EXE%" wallpaper.py
if errorlevel 1 (
    echo.
    echo [ERROR] LyricSky exited unexpectedly. Try running Setup.bat to install dependencies.
    pause
)
