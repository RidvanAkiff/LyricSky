@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT=%STARTUP_DIR%\LyricSky.lnk"
set "TARGET=%~dp0LyricSky.vbs"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%'); $s.TargetPath='wscript.exe'; $s.Arguments='\"%TARGET%\"'; $s.WorkingDirectory='%~dp0'; $s.Description='LyricSky Live Lyrics Desktop Wallpaper'; $s.Save()"
echo [OK] LyricSky added to Windows Startup!
echo Location: %SHORTCUT%
pause
