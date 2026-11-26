@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LEGACY_LNK=%STARTUP_DIR%\LyricSky.lnk"
set "TARGET=%~dp0LyricSky.vbs"
set "WORKDIR=%~dp0"
if "%WORKDIR:~-1%"=="\" set "WORKDIR=%WORKDIR:~0,-1%"

if exist "%LEGACY_LNK%" del /f /q "%LEGACY_LNK%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop'; " ^
  "Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'LyricSky' -ErrorAction SilentlyContinue; " ^
  "try { " ^
  "  $act = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '\"%TARGET%\"' -WorkingDirectory '%WORKDIR%'; " ^
  "  $trig = New-ScheduledTaskTrigger -AtLogOn -User \"$env:USERDOMAIN\$env:USERNAME\"; " ^
  "  $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -Priority 4; " ^
  "  Register-ScheduledTask -TaskName 'LyricSky' -Action $act -Trigger $trig -Settings $set -Description 'LyricSky Live Lyrics Desktop Wallpaper' -Force | Out-Null; " ^
  "  Write-Output '[OK] LyricSky instant logon task registered (Task Scheduler: LyricSky).'; " ^
  "} catch { " ^
  "  Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'LyricSky' -Value 'wscript.exe \"%TARGET%\"'; " ^
  "  Write-Output '[OK] LyricSky added to Windows Startup (Registry Run).'; " ^
  "}"
pause
