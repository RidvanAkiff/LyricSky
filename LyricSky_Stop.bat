@echo off
chcp 65001 >nul
title Stopping LyricSky...

echo Stopping LyricSky and restoring your original Windows wallpaper...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { ($_.Name -match '^pythonw?\.exe$' -and $_.CommandLine -match 'wallpaper\.py|bridge\.py') -or ($_.Name -eq 'msedge.exe' -and $_.CommandLine -match 'edge_lyricsky_profile|edge_wallpaper_profile') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; " ^
  "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class Wp { [DllImport(\"user32.dll\", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindow(string c, string t); [DllImport(\"user32.dll\", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr a, string c, string t); [DllImport(\"user32.dll\")] public static extern bool RedrawWindow(IntPtr h, IntPtr r, IntPtr hr, uint f); [DllImport(\"user32.dll\")] public static extern bool InvalidateRect(IntPtr hWnd, IntPtr lpRect, bool bErase); }'; " ^
  "$pm = [Wp]::FindWindow('Progman', $null); if ($pm -ne [IntPtr]::Zero) { [Wp]::RedrawWindow($pm, [IntPtr]::Zero, [IntPtr]::Zero, 0x0185) | Out-Null; $ww = [Wp]::FindWindowEx($pm, [IntPtr]::Zero, 'WorkerW', $null); if ($ww -ne [IntPtr]::Zero) { [Wp]::RedrawWindow($ww, [IntPtr]::Zero, [IntPtr]::Zero, 0x0185) | Out-Null } }; " ^
  "[Wp]::InvalidateRect([IntPtr]::Zero, [IntPtr]::Zero, $true) | Out-Null"

echo [OK] LyricSky stopped cleanly and your original wallpaper was restored.
timeout /t 2 /nobreak >nul
