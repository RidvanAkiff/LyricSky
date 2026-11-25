@echo off
chcp 65001 >nul
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_DIR%\LyricSky.lnk" del /f /q "%STARTUP_DIR%\LyricSky.lnk"
echo [OK] LyricSky removed from Windows Startup.
pause
