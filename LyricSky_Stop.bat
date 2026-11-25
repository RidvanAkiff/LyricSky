@echo off
chcp 65001 >nul
title Stopping LyricSky...

echo Stopping LyricSky and restoring your original Windows wallpaper...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { ($_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match 'wallpaper\.py|bridge\.py') -or ($_.Name -eq 'msedge.exe' -and $_.CommandLine -match 'edge_lyricsky_profile|edge_wallpaper_profile') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; " ^
  "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Wp { [DllImport(\"user32.dll\")] public static extern bool SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni); [DllImport(\"user32.dll\")] public static extern bool InvalidateRect(IntPtr hWnd, IntPtr lpRect, bool bErase); }'; " ^
  "[Wp]::SystemParametersInfo(0x0014, 0, $null, 0x0002) | Out-Null; " ^
  "[Wp]::InvalidateRect([IntPtr]::Zero, [IntPtr]::Zero, $true) | Out-Null"

echo [OK] LyricSky stopped cleanly and your original wallpaper was restored.
timeout /t 2 /nobreak >nul
