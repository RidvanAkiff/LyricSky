@echo off
chcp 65001 >nul
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP_DIR%\LyricSky.lnk" del /f /q "%STARTUP_DIR%\LyricSky.lnk"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Unregister-ScheduledTask -TaskName 'LyricSky' -Confirm:$false -ErrorAction SilentlyContinue; " ^
  "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'LyricSky' -ErrorAction SilentlyContinue"
echo [OK] LyricSky removed from Windows Startup.
pause
