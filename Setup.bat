@echo off
chcp 65001 >nul
title LyricSky — Setup
cd /d "%~dp0"

echo ========================================================
echo   LyricSky — Live Synced Lyrics Desktop Wallpaper Setup
echo ========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10+ was not found in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo ^(Make sure to check "Add Python to PATH" during installation.^)
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating isolated virtual environment ^(.venv^)...
    python -m venv .venv
    if errorlevel 1 (
        echo [WARN] Could not create .venv; falling back to user Python.
        goto :install_global
    )
)

echo [2/3] Installing dependencies into .venv...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import aiohttp, PIL, win32gui, winrt.windows.media.control" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependency verification failed. Please check your internet connection and re-run Setup.bat.
    pause
    exit /b 1
)
echo ok > ".venv\.ready"

echo [3/3] Opening Language ^& Startup Setup Wizard...
".venv\Scripts\python.exe" setup_wizard.py
exit /b 0

:install_global
echo [2/3] Installing dependencies...
python -m pip install --user --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [3/3] Opening Language ^& Startup Setup Wizard...
python setup_wizard.py
exit /b 0
