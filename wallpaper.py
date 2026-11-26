"""
LyricSky Native Windows Live Wallpaper Host v2.0
------------------------------------------------
Zero-dependency-bloat standalone Windows 10 & Windows 11 (24H2/25H2+ Raised Desktop)
live constellation lyrics desktop wallpaper — requires NO third-party wallpaper
host apps (pure Win32 System Tray + isolated Edge renderer).

Features:
  - Integrated LyricSkyBridge HTTP/WebSocket + Windows SMTC + Word-by-Word Lyrics
  - Frameless hardware-accelerated Edge (--kiosk --edge-kiosk-type=fullscreen)
    embedded cleanly behind desktop icons (SHELLDLL_DefView)
  - 0ms normalized WebSocket desktop pointer bridge (click & drag controls directly
    from the Windows desktop at any DPI scaling)
  - Pure Win32 native Unicode System Tray icon & dynamic multi-language menu
  - Clean exit on Tray Quit, Ctrl+C, Console Close (X), or Windows Logoff/Shutdown
"""

from __future__ import annotations

import asyncio
import atexit
import ctypes
import ctypes.wintypes as wt
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

import win32api
import win32con
import win32gui
import win32process
from aiohttp import web
from PIL import Image, ImageDraw

# Enable Per-Monitor DPI Awareness v2 BEFORE GetSystemMetrics or window creation
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import bridge

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
EDGE_PROFILE_DIR = DATA_DIR / "edge_lyricsky_profile"
EDGE_PID_FILE = DATA_DIR / "edge.pid"
TRAY_ICON_PATH = DATA_DIR / "lyricsky_tray.ico"
LOG_FILE = DATA_DIR / "lyricsky.log"

WALLPAPER_URL = f"http://{bridge.HOST}:{bridge.PORT}/?mode=wallpaper"
CONTROL_URL = f"http://{bridge.HOST}:{bridge.PORT}/"
STATUS_URL = f"http://{bridge.HOST}:{bridge.PORT}/api/status"

log = logging.getLogger("lyricsky.wallpaper")


def setup_logging() -> None:
    """Configure console + data/lyricsky.log file logging when launched directly."""
    handlers: list[logging.Handler] = [logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )

# ============================================================================
# Win32 Constants & Native Signatures
# ============================================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SMTO_NORMAL = 0x0000
LWA_ALPHA = 0x00000002
GA_ROOT = 2
RDW_INVALIDATE = 0x0001
RDW_ERASE = 0x0004
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
ERROR_ALREADY_EXISTS = 183
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001

WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
WS_EX_NOREDIRECTIONBITMAP = 0x00200000

WM_TRAYICON = win32con.WM_USER + 20
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WH_MOUSE_LL = 14
WM_MOUSEWHEEL = 0x020A

TIMER_INPUT = 1
TIMER_WATCHDOG = 2
TIMER_STATUS = 3

# Menu Command IDs
IDM_PLAY_PAUSE = 1001
IDM_PREV = 1002
IDM_NEXT = 1003
IDM_TOGGLE_CLICK = 1004
IDM_TOGGLE_ICONS = 1005
IDM_TOGGLE_SETTINGS = 1006
IDM_OPEN_BROWSER = 1007
IDM_REALIGN = 1008
IDM_QUIT = 1009

THEME_MENU_IDS = [
    (1101, "overcast", "themeOvercast"),
    (1102, "midnight", "themeMidnight"),
    (1103, "ambient", "themeAmbient"),
    (1104, "dusk", "themeDusk"),
]

user32.SendMessageTimeoutW.argtypes = [
    wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM, wt.UINT, wt.UINT, ctypes.POINTER(ctypes.c_size_t)
]
user32.SendMessageTimeoutW.restype = ctypes.c_size_t
user32.SetLayeredWindowAttributes.argtypes = [wt.HWND, wt.COLORREF, wt.BYTE, wt.DWORD]
user32.SetLayeredWindowAttributes.restype = wt.BOOL
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.GetAncestor.restype = wt.HWND
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.RedrawWindow.argtypes = [wt.HWND, ctypes.c_void_p, wt.HRGN, wt.UINT]
user32.RedrawWindow.restype = wt.BOOL
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
kernel32.CreateMutexW.restype = wt.HANDLE
kernel32.GetLastError.argtypes = []
kernel32.GetLastError.restype = wt.DWORD
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
kernel32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
kernel32.TerminateProcess.restype = wt.BOOL
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL


class POINT(ctypes.Structure):
    _fields_ = [("x", wt.LONG), ("y", wt.LONG)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


LOWLEVELMOUSEPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wt.WPARAM, wt.LPARAM)

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wt.BOOL
user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wt.BOOL
user32.InvalidateRect.argtypes = [wt.HWND, ctypes.c_void_p, wt.BOOL]
user32.InvalidateRect.restype = wt.BOOL
user32.SetTimer.argtypes = [wt.HWND, ctypes.c_size_t, wt.UINT, ctypes.c_void_p]
user32.SetTimer.restype = ctypes.c_size_t
user32.KillTimer.argtypes = [wt.HWND, ctypes.c_size_t]
user32.KillTimer.restype = wt.BOOL
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LOWLEVELMOUSEPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
user32.UnhookWindowsHookEx.restype = wt.BOOL
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t


def _terminate_edge_pid(pid: int) -> bool:
    """Safely terminate a process ONLY if it is an msedge.exe instance (<1ms Win32)."""
    if pid <= 0:
        return False
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE, False, pid)
    if not h:
        return False
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wt.DWORD(512)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            if os.path.basename(buf.value).lower() == "msedge.exe":
                kernel32.TerminateProcess(h, 0)
                return True
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(h)
    return False


def _save_edge_pid(pid: int) -> None:
    try:
        if pid > 0:
            EDGE_PID_FILE.write_text(str(pid), encoding="ascii")
        elif EDGE_PID_FILE.exists():
            EDGE_PID_FILE.unlink()
    except Exception:
        pass


def cleanup_stale_edge_wallpaper(allow_powershell_fallback: bool = False) -> None:
    """Terminate leftover LyricSky Edge processes in <1ms via saved PID file (zero boot delay)."""
    if EDGE_PID_FILE.exists():
        try:
            old_pid = int(EDGE_PID_FILE.read_text(encoding="ascii").strip())
            _terminate_edge_pid(old_pid)
        except Exception:
            pass
        try:
            EDGE_PID_FILE.unlink()
        except Exception:
            pass
        if not allow_powershell_fallback:
            return

    if not allow_powershell_fallback:
        return

    try:
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
            "Where-Object { $_.CommandLine -match 'edge_lyricsky_profile|edge_wallpaper_profile' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            creationflags=creation_flags,
            timeout=5.0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def refresh_windows_wallpaper() -> None:
    """Cleanly repaint Windows Progman/WorkerW without altering the user's wallpaper setting."""
    try:
        flags = RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW
        progman = win32gui.FindWindow("Progman", None)
        if progman:
            user32.RedrawWindow(progman, None, 0, flags)
            workerw = win32gui.FindWindowEx(progman, 0, "WorkerW", None)
            if workerw:
                user32.RedrawWindow(workerw, None, 0, flags)
        user32.InvalidateRect(0, None, True)
    except Exception:
        pass


def get_primary_monitor_rect() -> tuple[int, int, int, int]:
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return 0, 0, max(640, w), max(480, h)


def find_msedge_exe() -> str | None:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return shutil.which("msedge.exe") or shutil.which("msedge")


def ensure_tray_ico_file(path: Path) -> Path:
    """Generate a crisp anti-aliased star-reticle multi-size .ico file via Pillow (cached)."""
    if path.is_file() and path.stat().st_size > 1000:
        return path
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark circular obsidian badge with soft luminous rim
    draw.ellipse((14, 14, size - 14, size - 14), fill=(16, 20, 28, 245), outline=(255, 255, 255, 110), width=9)

    # Astronomical reticle ring
    draw.ellipse((68, 68, size - 68, size - 68), outline=(235, 244, 255, 235), width=10)

    # Four cardinal precision ticks
    c = size // 2
    draw.line((c, 36, c, 90), fill=(235, 244, 255, 235), width=10)
    draw.line((c, size - 90, c, size - 36), fill=(235, 244, 255, 235), width=10)
    draw.line((36, c, 90, c), fill=(235, 244, 255, 235), width=10)
    draw.line((size - 90, c, size - 36, c), fill=(235, 244, 255, 235), width=10)

    # Bright center star
    draw.ellipse((c - 17, c - 17, c + 17, c + 17), fill=(255, 255, 255, 255))

    img.save(path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])
    return path


# ============================================================================
# Integrated LyricSkyBridge Thread
# ============================================================================

class BridgeThread(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True, name="LyricSkyBridgeThread")
        self.bridge_svc = bridge.LyricSkyBridge()
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self.ready = threading.Event()
        self.error: Exception | None = None

    def run(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._serve())
        except Exception as exc:
            self.error = exc
            log.error("Bridge server error: %s", exc)
            self.ready.set()
        finally:
            try:
                self.loop.close()
            except Exception:
                pass

    async def _serve(self) -> None:
        self._stop_event = asyncio.Event()
        app = self.bridge_svc.create_app()
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, bridge.HOST, bridge.PORT)
        await site.start()
        log.info("Built-in LyricSky bridge ready at %s", CONTROL_URL)
        self.ready.set()
        await self._stop_event.wait()
        await runner.cleanup()

    def stop(self) -> None:
        if self.loop and self._stop_event and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._stop_event.set)


# ============================================================================
# Windows 10 & Windows 11 (24H2+) Frameless Desktop Embedding Engine
# ============================================================================

class DesktopWallpaperEngine:
    def __init__(self) -> None:
        self.proc: subprocess.Popen[Any] | None = None
        self.edge_pid: int = 0
        self.hwnd: int = 0
        self.render_hwnd: int = 0
        self.embed_mode: str = "none"
        self.parent_hwnd: int = 0
        self.defview_hwnd: int = 0
        self.child_workerw_hwnd: int = 0
        self._rect: tuple[int, int, int, int] = get_primary_monitor_rect()

    def _find_desktop_targets(self) -> tuple[str, int, int]:
        progman = win32gui.FindWindow("Progman", None)
        if not progman:
            return "none", 0, 0

        res = ctypes.c_size_t(0)
        user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, SMTO_NORMAL, 1000, ctypes.byref(res))
        user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, SMTO_NORMAL, 1000, ctypes.byref(res))
        time.sleep(0.12)

        defview_in_progman = win32gui.FindWindowEx(progman, 0, "SHELLDLL_DefView", None)
        workerw_in_progman = win32gui.FindWindowEx(progman, 0, "WorkerW", None)
        progman_ex = win32gui.GetWindowLong(progman, win32con.GWL_EXSTYLE)
        is_raised = bool(defview_in_progman) and (
            bool(workerw_in_progman) or bool(progman_ex & WS_EX_NOREDIRECTIONBITMAP)
        )
        if is_raised:
            log.info(
                "Windows 11 24H2+ Raised Desktop detected (Progman=%s, DefView=%s)",
                hex(progman),
                hex(defview_in_progman),
            )
            return "win11_24h2", progman, defview_in_progman

        found_workerw = 0
        found_defview = 0

        def enum_cb(top_hwnd: int, _extra: Any) -> bool:
            nonlocal found_workerw, found_defview
            dv = win32gui.FindWindowEx(top_hwnd, 0, "SHELLDLL_DefView", None)
            if dv:
                found_defview = dv
                next_w = win32gui.FindWindowEx(0, top_hwnd, "WorkerW", None)
                if next_w:
                    found_workerw = next_w
            return True

        win32gui.EnumWindows(enum_cb, None)
        if found_workerw:
            log.info("Classic WorkerW desktop detected (WorkerW=%s)", hex(found_workerw))
            return "classic_workerw", found_workerw, found_defview

        if defview_in_progman:
            return "win11_24h2", progman, defview_in_progman

        return "none", progman, 0

    @staticmethod
    def _snapshot_chrome_windows() -> tuple[set[int], set[int]]:
        """Capture all existing Chromium/Edge top-level windows and PIDs before launch."""
        hwnds: set[int] = set()
        pids: set[int] = set()

        def enum_cb(hwnd: int, _extra: Any) -> bool:
            try:
                if win32gui.GetClassName(hwnd) == "Chrome_WidgetWin_1":
                    hwnds.add(hwnd)
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid:
                        pids.add(pid)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_cb, None)
        return hwnds, pids

    def launch_renderer(self) -> bool:
        edge_exe = find_msedge_exe()
        if not edge_exe:
            log.error("Microsoft Edge was not found on this system.")
            return False

        if self.hwnd or self.proc or self.edge_pid:
            self.stop_renderer()
        else:
            cleanup_stale_edge_wallpaper(allow_powershell_fallback=False)
        self._rect = get_primary_monitor_rect()
        x, y, w, h = self._rect

        # Snapshot every already-open Edge/Chrome window so we NEVER hijack a user's
        # existing browser tab (e.g. GitHub's RidvanAkiff/LyricSky page!).
        existing_hwnds, existing_pids = self._snapshot_chrome_windows()

        EDGE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        cmd = [
            edge_exe,
            "--kiosk",
            WALLPAPER_URL,
            "--edge-kiosk-type=fullscreen",
            f"--user-data-dir={EDGE_PROFILE_DIR}",
            f"--window-position={x},{y}",
            f"--window-size={w},{h}",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-features=CalculateNativeWinOcclusion,OverscrollHistoryNavigation,msEdgeSidebarV2,Translate",
            "--hide-scrollbars",
        ]

        log.info("Launching frameless Edge wallpaper renderer (%dx%d)...", w, h)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(cmd, creationflags=creation_flags)

        target_hwnd = self._wait_for_edge_window(existing_hwnds, existing_pids, timeout_sec=14.0)
        if not target_hwnd:
            log.error("Timed out waiting for Edge wallpaper window.")
            return False

        self.hwnd = target_hwnd
        _, self.edge_pid = win32process.GetWindowThreadProcessId(self.hwnd)
        _save_edge_pid(self.edge_pid)
        title = win32gui.GetWindowText(self.hwnd) or ""
        rect = win32gui.GetWindowRect(self.hwnd)
        log.info(
            "Wallpaper window acquired: %s (PID=%d, root_pid=%d, title=%r, rect=%s)",
            hex(self.hwnd),
            self.edge_pid,
            self.proc.pid if self.proc else -1,
            title,
            rect,
        )
        return self.attach_to_desktop(wait_for_desktop_sec=25.0)

    def _wait_for_edge_window(
        self,
        existing_hwnds: set[int],
        existing_pids: set[int],
        timeout_sec: float = 14.0,
    ) -> int:
        start = time.monotonic()
        deadline = start + timeout_sec
        root_pid = self.proc.pid if self.proc else -1
        fallback_hwnd = 0

        while time.monotonic() < deadline:
            candidates: list[tuple[int, int]] = []

            def enum_cb(hwnd: int, _extra: Any) -> bool:
                nonlocal fallback_hwnd
                if hwnd in existing_hwnds:
                    return True
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                    if win32gui.GetClassName(hwnd) != "Chrome_WidgetWin_1":
                        return True
                    l, t, r, b = win32gui.GetWindowRect(hwnd)
                    if (r - l) < 400 or (b - t) < 300:
                        return True
                    title = win32gui.GetWindowText(hwnd) or ""
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    return True

                # Strictly ignore any pre-existing Edge/Chrome browser process
                if pid in existing_pids:
                    return True

                if "LyricSky" in title:
                    score = 100 if pid == root_pid else 85
                    candidates.append((score, hwnd))
                elif pid == root_pid:
                    fallback_hwnd = hwnd
                return True

            win32gui.EnumWindows(enum_cb, None)
            if candidates:
                candidates.sort(key=lambda item: item[0], reverse=True)
                return candidates[0][1]
            # If our own newly launched root_pid window is already open and visible,
            # allow up to 4.5s for the page title to load, then use it directly.
            if fallback_hwnd and (time.monotonic() - start) >= 4.5 and win32gui.IsWindow(fallback_hwnd):
                return fallback_hwnd
            time.sleep(0.15)
        return fallback_hwnd if (fallback_hwnd and win32gui.IsWindow(fallback_hwnd)) else 0

    def _find_render_child(self) -> int:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return 0
        found = 0

        def enum_child(ch: int, _extra: Any) -> bool:
            nonlocal found
            if win32gui.GetClassName(ch) == "Chrome_RenderWidgetHostHWND":
                found = ch
                return False
            return True

        try:
            win32gui.EnumChildWindows(self.hwnd, enum_child, None)
        except Exception:
            pass
        self.render_hwnd = found or self.hwnd
        return self.render_hwnd

    def _measure_chrome_insets(self) -> tuple[int, int, int, int]:
        """Measure any residual Edge --app frame (left, top, right, bottom) around Chrome_RenderWidgetHostHWND."""
        render_ch = self._find_render_child()
        if not render_ch or render_ch == self.hwnd:
            return 0, 0, 0, 0
        try:
            w_l, w_t, w_r, w_b = win32gui.GetWindowRect(self.hwnd)
            r_l, r_t, r_r, r_b = win32gui.GetWindowRect(render_ch)
            left = r_l - w_l if 0 <= (r_l - w_l) <= 30 else 0
            top = r_t - w_t if 0 <= (r_t - w_t) <= 80 else 0
            right = w_r - r_r if 0 <= (w_r - r_r) <= 30 else 0
            bottom = w_b - r_b if 0 <= (w_b - r_b) <= 30 else 0
            return left, top, right, bottom
        except Exception:
            return 0, 0, 0, 0

    def _position_embedded_window(self) -> tuple[int, int, int, int]:
        """Position self.hwnd inside parent_hwnd so the inner web viewport fills (0, 0, w, h) seamlessly."""
        x, y, w, h = self._rect
        pt = POINT(x, y)
        user32.ScreenToClient(self.parent_hwnd, ctypes.byref(pt))

        in_l, in_t, in_r, in_b = self._measure_chrome_insets()
        pos_x = pt.x - in_l
        pos_y = pt.y - in_t
        pos_w = w + in_l + in_r
        pos_h = h + in_t + in_b

        if self.embed_mode == "win11_24h2":
            insert_after = self.defview_hwnd if self.defview_hwnd else win32con.HWND_BOTTOM
            win32gui.SetWindowPos(
                self.hwnd,
                insert_after,
                pos_x,
                pos_y,
                pos_w,
                pos_h,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED,
            )
            child_workerw = win32gui.FindWindowEx(self.parent_hwnd, 0, "WorkerW", None)
            self.child_workerw_hwnd = child_workerw
            if child_workerw and child_workerw != self.hwnd:
                try:
                    win32gui.SetWindowPos(
                        child_workerw,
                        self.hwnd,
                        0,
                        0,
                        0,
                        0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                    )
                except Exception:
                    pass
        else:
            win32gui.SetWindowPos(
                self.hwnd,
                0,
                pos_x,
                pos_y,
                pos_w,
                pos_h,
                win32con.SWP_NOZORDER
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_SHOWWINDOW
                | win32con.SWP_FRAMECHANGED,
            )
        return in_l, in_t, in_r, in_b

    def attach_to_desktop(self, wait_for_desktop_sec: float = 2.0) -> bool:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return False

        # Wait gracefully for Explorer's Progman/SHELLDLL_DefView right after Windows login
        deadline = time.monotonic() + max(0.0, wait_for_desktop_sec)
        mode, parent_hwnd, defview_hwnd = self._find_desktop_targets()
        while (mode == "none" or not parent_hwnd) and time.monotonic() < deadline:
            time.sleep(0.25)
            mode, parent_hwnd, defview_hwnd = self._find_desktop_targets()

        if mode == "none" or not parent_hwnd:
            log.error("Could not locate Windows desktop layer (Progman/WorkerW).")
            return False

        self.embed_mode = mode
        self.parent_hwnd = parent_hwnd
        self.defview_hwnd = defview_hwnd
        self._rect = get_primary_monitor_rect()
        x, y, w, h = self._rect

        style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
        strip_style = (
            win32con.WS_CAPTION
            | win32con.WS_THICKFRAME
            | win32con.WS_MINIMIZEBOX
            | win32con.WS_MAXIMIZEBOX
            | win32con.WS_SYSMENU
            | win32con.WS_BORDER
            | win32con.WS_DLGFRAME
            | win32con.WS_POPUP
        )
        style = (style & ~strip_style) | win32con.WS_CHILD | win32con.WS_VISIBLE
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)

        ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        strip_ex = (
            WS_EX_APPWINDOW
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_WINDOWEDGE
            | win32con.WS_EX_CLIENTEDGE
            | win32con.WS_EX_DLGMODALFRAME
        )
        ex_style = (ex_style & ~strip_ex) | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE

        if mode == "win11_24h2":
            ex_style |= WS_EX_LAYERED
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, ex_style)
            user32.SetLayeredWindowAttributes(self.hwnd, 0, 255, LWA_ALPHA)
            win32gui.SetParent(self.hwnd, parent_hwnd)
            user32.SetLayeredWindowAttributes(self.hwnd, 0, 255, LWA_ALPHA)
        else:
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, ex_style)
            win32gui.SetParent(self.hwnd, parent_hwnd)

        # First positioning pass, then let Edge settle layout & re-measure any residual frame
        self._position_embedded_window()
        time.sleep(0.28)
        insets = self._position_embedded_window()

        self._find_render_child()
        log.info("Attached frameless wallpaper [%s] (%dx%d, insets=%s).", mode, w, h, insets)
        return True

    def ensure_attached(self) -> None:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return
        cur_parent = win32gui.GetParent(self.hwnd)
        cur_rect = get_primary_monitor_rect()
        if cur_parent != self.parent_hwnd or not win32gui.IsWindow(self.parent_hwnd) or cur_rect != self._rect:
            log.info("Desktop layout changed — re-aligning...")
            self.attach_to_desktop()
            return

        # Re-crop if Edge changed its inner chrome height after settling
        render_ch = self._find_render_child()
        if render_ch and render_ch != self.hwnd:
            try:
                rl, rt, rr, rb = win32gui.GetWindowRect(render_ch)
                x, y, w, h = self._rect
                if abs(rl - x) > 2 or abs(rt - y) > 2 or abs((rr - rl) - w) > 4 or abs((rb - rt) - h) > 4:
                    self._position_embedded_window()
            except Exception:
                pass

        if self.embed_mode == "win11_24h2" and self.defview_hwnd and win32gui.IsWindow(self.defview_hwnd):
            next_after_defview = win32gui.GetWindow(self.defview_hwnd, win32con.GW_HWNDNEXT)
            if next_after_defview != self.hwnd:
                win32gui.SetWindowPos(
                    self.hwnd,
                    self.defview_hwnd,
                    0,
                    0,
                    0,
                    0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE,
                )

    def read_desktop_pointer(self, pt_x: int, pt_y: int) -> tuple[bool, float, float]:
        if not self.hwnd or not win32gui.IsWindow(self.hwnd):
            return False, 0.0, 0.0

        pt = POINT(pt_x, pt_y)
        hit_hwnd = user32.WindowFromPoint(pt)
        if not hit_hwnd:
            return False, 0.0, 0.0
        try:
            if hit_hwnd == self.hwnd or win32gui.IsChild(self.hwnd, hit_hwnd):
                return False, 0.0, 0.0
            hit_cls = win32gui.GetClassName(hit_hwnd)
            root_hwnd = user32.GetAncestor(hit_hwnd, GA_ROOT)
            root_cls = win32gui.GetClassName(root_hwnd) if root_hwnd else ""
        except Exception:
            return False, 0.0, 0.0

        desktop_classes = {"SysListView32", "SHELLDLL_DefView", "WorkerW", "Progman"}
        if hit_cls not in desktop_classes and root_cls not in {"Progman", "WorkerW"}:
            return False, 0.0, 0.0

        x, y, w, h = self._rect
        rx, ry = pt_x - x, pt_y - y
        if rx < 0 or ry < 0 or rx > w or ry > h or w <= 0 or h <= 0:
            return False, 0.0, 0.0

        return True, rx / float(w), ry / float(h)

    def stop_renderer(self) -> None:
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            try:
                win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
                win32gui.SetParent(self.hwnd, 0)
                win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
            except Exception:
                pass
            for _ in range(10):
                if not win32gui.IsWindow(self.hwnd):
                    break
                time.sleep(0.08)

        if self.proc is not None:
            try:
                if self.proc.poll() is None:
                    self.proc.terminate()
                    self.proc.wait(timeout=1.5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        if self.edge_pid:
            _terminate_edge_pid(self.edge_pid)
            self.edge_pid = 0

        _save_edge_pid(0)
        cleanup_stale_edge_wallpaper(allow_powershell_fallback=False)
        self.hwnd = 0
        self.render_hwnd = 0
        refresh_windows_wallpaper()


# ============================================================================
# Pure Win32 Native Multilingual System Tray Application (Zero Qt Dependency)
# ============================================================================

class LyricSkyDesktopApp:
    def __init__(self) -> None:
        self.bridge_thread = BridgeThread()
        self.engine = DesktopWallpaperEngine()
        self.desktop_click_enabled = True
        self._last_lbutton = False
        self._last_pos = (-1, -1)
        self._was_on_desktop = False
        self._last_hover_sent = 0.0
        self._shutting_down = False
        self.tray_hwnd: int = 0
        self.hicon: int = 0
        self._tray_added = False
        self._mouse_hook: Any = None
        self._mouse_hook_proc: Any = None
        self._pending_wheels: list[tuple[int, int, int]] = []

    def _lang(self) -> str:
        return str(self.bridge_thread.bridge_svc.settings.data.get("language", "en"))

    def _t(self, key: str, fallback: str = "") -> str:
        return bridge.tr(self._lang(), key, fallback)

    def _send_cmd(self, payload: dict[str, Any]) -> None:
        self.bridge_thread.bridge_svc.dispatch_command_threadsafe(payload)

    def _broadcast(self, payload: dict[str, Any]) -> None:
        self.bridge_thread.bridge_svc.broadcast_threadsafe(payload)

    def _add_tray_icon(self, show_balloon: bool = False) -> None:
        if not self.tray_hwnd or not self.hicon:
            return
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        tip = self._t("trayTooltip", "LyricSky")[:127]
        for _ in range(4):
            try:
                win32gui.Shell_NotifyIcon(
                    win32gui.NIM_ADD,
                    (self.tray_hwnd, 0, flags, WM_TRAYICON, self.hicon, tip),
                )
                self._tray_added = True
                break
            except Exception as exc:
                log.debug("Shell_NotifyIcon NIM_ADD retry: %s", exc)
                time.sleep(0.25)

        if self._tray_added and show_balloon:
            try:
                win32gui.Shell_NotifyIcon(
                    win32gui.NIM_MODIFY,
                    (
                        self.tray_hwnd,
                        0,
                        win32gui.NIF_INFO,
                        WM_TRAYICON,
                        self.hicon,
                        tip,
                        self._t("trayStartedMsg", "LyricSky is running.")[:255],
                        3200,
                        self._t("trayStartedTitle", "LyricSky")[:63],
                        win32gui.NIIF_NOSOUND,
                    ),
                )
            except Exception:
                pass

    def _on_taskbar_created(self, _hwnd: int, _msg: int, _wparam: int, _lparam: int) -> int:
        self._tray_added = False
        self._add_tray_icon(show_balloon=False)
        self.engine.attach_to_desktop()
        return 0

    def _create_tray_window(self) -> None:
        hinst = win32api.GetModuleHandle(None)
        cls_name = "LyricSkyTrayWindowClass"
        taskbar_msg = win32gui.RegisterWindowMessage("TaskbarCreated")

        wc = win32gui.WNDCLASS()
        wc.hInstance = hinst
        wc.lpszClassName = cls_name
        wc.lpfnWndProc = {
            WM_TRAYICON: self._on_tray_event,
            taskbar_msg: self._on_taskbar_created,
            win32con.WM_COMMAND: self._on_menu_command,
            win32con.WM_TIMER: self._on_timer,
            win32con.WM_CLOSE: self._on_close,
            win32con.WM_DESTROY: self._on_destroy,
            WM_QUERYENDSESSION: self._on_end_session,
            WM_ENDSESSION: self._on_end_session,
        }
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        self.tray_hwnd = win32gui.CreateWindow(
            cls_name,
            "LyricSkyTray",
            win32con.WS_OVERLAPPED,
            0,
            0,
            0,
            0,
            0,
            0,
            hinst,
            None,
        )
        win32gui.UpdateWindow(self.tray_hwnd)

        ico_file = ensure_tray_ico_file(TRAY_ICON_PATH)
        self.hicon = win32gui.LoadImage(
            0,
            str(ico_file),
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

        self._add_tray_icon(show_balloon=True)
        self._install_wheel_hook()

        user32.SetTimer(self.tray_hwnd, TIMER_INPUT, 22, None)
        user32.SetTimer(self.tray_hwnd, TIMER_WATCHDOG, 3000, None)
        user32.SetTimer(self.tray_hwnd, TIMER_STATUS, 1800, None)

    def _install_wheel_hook(self) -> None:
        """Install an ultra-lightweight WH_MOUSE_LL observer for desktop scroll-wheel events."""
        if self._mouse_hook:
            return

        def _proc(n_code: int, wparam: int, lparam: int) -> int:
            if n_code >= 0 and wparam == WM_MOUSEWHEEL and self.desktop_click_enabled:
                try:
                    info = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    delta = ctypes.c_short((info.mouseData >> 16) & 0xFFFF).value
                    if delta:
                        self._pending_wheels.append((info.pt.x, info.pt.y, int(delta)))
                        if len(self._pending_wheels) > 64:
                            del self._pending_wheels[:-32]
                except Exception:
                    pass
            return int(user32.CallNextHookEx(self._mouse_hook or 0, n_code, wparam, lparam))

        self._mouse_hook_proc = LOWLEVELMOUSEPROC(_proc)
        hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_hook_proc, 0, 0)
        if hook:
            self._mouse_hook = hook
        else:
            log.debug("WH_MOUSE_LL wheel hook could not be installed.")

    def _remove_wheel_hook(self) -> None:
        if self._mouse_hook:
            try:
                user32.UnhookWindowsHookEx(self._mouse_hook)
            except Exception:
                pass
            self._mouse_hook = None
            self._mouse_hook_proc = None

    def _on_tray_event(self, _hwnd: int, _msg: int, _wparam: int, lparam: int) -> int:
        if lparam == win32con.WM_LBUTTONDBLCLK:
            webbrowser.open(CONTROL_URL)
        elif lparam in (win32con.WM_RBUTTONUP, win32con.WM_CONTEXTMENU):
            self._show_context_menu()
        return 0

    def _show_context_menu(self) -> None:
        menu = win32gui.CreatePopupMenu()

        clk = self.bridge_thread.bridge_svc.clock
        if clk.get("active") and clk.get("title"):
            icon = "▶" if clk.get("playing") else "❚❚"
            artist = clk.get("artist") or ""
            now_label = f"{icon} {clk['title']}" + (f" — {artist}" if artist else "")
            if len(now_label) > 52:
                now_label = now_label[:49] + "..."
        else:
            now_label = self._t("trayNoMedia", "No music playing")

        win32gui.AppendMenu(menu, win32con.MF_STRING | win32con.MF_GRAYED, 0, now_label)
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")

        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_PLAY_PAUSE, self._t("trayPlayPause"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_PREV, self._t("trayPrev"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_NEXT, self._t("trayNext"))
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")

        # Theme submenu
        theme_menu = win32gui.CreatePopupMenu()
        cur_theme = self.bridge_thread.bridge_svc.settings.data.get("theme", "overcast")
        for mid, key, tkey in THEME_MENU_IDS:
            flags = win32con.MF_STRING | (win32con.MF_CHECKED if cur_theme == key else 0)
            win32gui.AppendMenu(theme_menu, flags, mid, self._t(tkey, key.title()))
        win32gui.AppendMenu(menu, win32con.MF_POPUP, theme_menu, self._t("trayTheme"))

        click_flags = win32con.MF_STRING | (win32con.MF_CHECKED if self.desktop_click_enabled else 0)
        win32gui.AppendMenu(menu, click_flags, IDM_TOGGLE_CLICK, self._t("trayDesktopClick"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_TOGGLE_ICONS, self._t("trayToggleIcons"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_TOGGLE_SETTINGS, self._t("trayToggleSettings"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_OPEN_BROWSER, self._t("trayOpenBrowser"))
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_REALIGN, self._t("trayRealign"))
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, IDM_QUIT, self._t("trayQuit"))

        pt = win32gui.GetCursorPos()
        try:
            win32gui.SetForegroundWindow(self.tray_hwnd)
        except Exception:
            pass
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_BOTTOMALIGN | win32con.TPM_RIGHTBUTTON,
            pt[0],
            pt[1],
            0,
            self.tray_hwnd,
            None,
        )
        win32gui.PostMessage(self.tray_hwnd, win32con.WM_NULL, 0, 0)
        win32gui.DestroyMenu(menu)

    def _on_menu_command(self, _hwnd: int, _msg: int, wparam: int, _lparam: int) -> int:
        cmd_id = win32api.LOWORD(wparam)
        if cmd_id == IDM_PLAY_PAUSE:
            self._send_cmd({"cmd": "toggle"})
        elif cmd_id == IDM_PREV:
            self._send_cmd({"cmd": "prev"})
        elif cmd_id == IDM_NEXT:
            self._send_cmd({"cmd": "next"})
        elif cmd_id == IDM_TOGGLE_CLICK:
            self.desktop_click_enabled = not self.desktop_click_enabled
        elif cmd_id == IDM_TOGGLE_ICONS:
            self._send_cmd({"cmd": "toggle_desktop_icons"})
        elif cmd_id == IDM_TOGGLE_SETTINGS:
            self._broadcast({"type": "toggle_settings"})
        elif cmd_id == IDM_OPEN_BROWSER:
            webbrowser.open(CONTROL_URL)
        elif cmd_id == IDM_REALIGN:
            self.engine.attach_to_desktop()
        elif cmd_id == IDM_QUIT:
            self.shutdown()
        else:
            for mid, key, _tkey in THEME_MENU_IDS:
                if cmd_id == mid:
                    self._send_cmd({"cmd": "update_settings", "settings": {"theme": key}})
                    break
        return 0

    def _on_timer(self, _hwnd: int, _msg: int, wparam: int, _lparam: int) -> int:
        if wparam == TIMER_INPUT:
            self._tick_desktop_input()
        elif wparam == TIMER_WATCHDOG:
            self.engine.ensure_attached()
        elif wparam == TIMER_STATUS:
            self._tick_tray_tooltip()
        return 0

    def _tick_desktop_input(self) -> None:
        if not self.desktop_click_enabled:
            self._pending_wheels.clear()
            return

        # 1) Drain queued scroll-wheel ticks first (forwards ONLY when cursor is on Desktop)
        if self._pending_wheels:
            events = self._pending_wheels[:]
            self._pending_wheels.clear()
            wx, wy, _ = events[-1]
            total_delta = sum(ev[2] for ev in events)
            if total_delta:
                on_desk_w, wnx, wny = self.engine.read_desktop_pointer(wx, wy)
                if on_desk_w:
                    # Standard Windows wheel notch = +120 (up) / -120 (down) -> ~84px smooth scroll
                    self._broadcast(
                        {
                            "type": "desktop_pointer",
                            "action": "wheel",
                            "nx": round(wnx, 5),
                            "ny": round(wny, 5),
                            "deltaY": round(-total_delta * 0.72, 1),
                        }
                    )

        pt = POINT()
        if not user32.GetCursorPos(ctypes.byref(pt)):
            return

        lbtn = bool(user32.GetAsyncKeyState(0x01) & 0x8000)
        click_down = lbtn and not self._last_lbutton
        click_up = (not lbtn) and self._last_lbutton
        moved = (pt.x, pt.y) != self._last_pos

        if not (moved or click_down or click_up):
            return

        self._last_pos = (pt.x, pt.y)
        self._last_lbutton = lbtn

        on_desktop, nx, ny = self.engine.read_desktop_pointer(pt.x, pt.y)
        if not on_desktop:
            if self._was_on_desktop:
                self._was_on_desktop = False
                self._broadcast({"type": "desktop_pointer", "action": "leave"})
            return

        self._was_on_desktop = True
        now = time.monotonic()

        if click_down:
            self._broadcast({"type": "desktop_pointer", "action": "down", "nx": round(nx, 5), "ny": round(ny, 5)})
            self._last_hover_sent = now
        elif click_up:
            self._broadcast({"type": "desktop_pointer", "action": "up", "nx": round(nx, 5), "ny": round(ny, 5)})
            self._last_hover_sent = now
        elif moved and (lbtn or (now - self._last_hover_sent) >= 0.04):
            self._broadcast(
                {
                    "type": "desktop_pointer",
                    "action": "move",
                    "nx": round(nx, 5),
                    "ny": round(ny, 5),
                    "pressed": lbtn,
                }
            )
            self._last_hover_sent = now

    def _tick_tray_tooltip(self) -> None:
        if not self._tray_added:
            return
        clk = self.bridge_thread.bridge_svc.clock
        if clk.get("active") and clk.get("title"):
            artist = clk.get("artist") or ""
            tip = f"LyricSky — {clk['title']}" + (f" ({artist})" if artist else "")
        else:
            tip = self._t("trayTooltip", "LyricSky")
        try:
            win32gui.Shell_NotifyIcon(
                win32gui.NIM_MODIFY,
                (self.tray_hwnd, 0, win32gui.NIF_TIP, WM_TRAYICON, self.hicon, tip[:127]),
            )
        except Exception:
            pass

    def _on_close(self, _hwnd: int, _msg: int, _wparam: int, _lparam: int) -> int:
        self.shutdown()
        return 0

    def _on_end_session(self, _hwnd: int, _msg: int, _wparam: int, _lparam: int) -> int:
        self.shutdown()
        return 1

    def _on_destroy(self, _hwnd: int, _msg: int, _wparam: int, _lparam: int) -> int:
        win32gui.PostQuitMessage(0)
        return 0

    def start(self) -> bool:
        self.bridge_thread.start()
        self.bridge_thread.ready.wait(timeout=8.0)
        if self.bridge_thread.error is not None:
            log.error("Bridge failed to start: %s", self.bridge_thread.error)
            return False

        if not self.engine.launch_renderer():
            return False

        self._create_tray_window()
        log.info("LyricSky is active! Quit via System Tray star icon, Ctrl+C, or LyricSky_Stop.bat.")
        return True

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        log.info("Shutting down LyricSky and restoring original Windows wallpaper...")
        self._remove_wheel_hook()
        if self.tray_hwnd and win32gui.IsWindow(self.tray_hwnd):
            for tid in (TIMER_INPUT, TIMER_WATCHDOG, TIMER_STATUS):
                try:
                    user32.KillTimer(self.tray_hwnd, tid)
                except Exception:
                    pass
        if self._tray_added:
            try:
                win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.tray_hwnd, 0))
            except Exception:
                pass
            self._tray_added = False
        self.engine.stop_renderer()
        self.bridge_thread.stop()
        if self.tray_hwnd and win32gui.IsWindow(self.tray_hwnd):
            try:
                win32gui.PostMessage(self.tray_hwnd, win32con.WM_DESTROY, 0, 0)
            except Exception:
                pass


def main() -> None:
    setup_logging()
    mutex = kernel32.CreateMutexW(None, False, "Local\\LyricSkyWallpaperSingleton")
    if mutex and kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        log.info("LyricSky is already running — skipping duplicate launch.")
        kernel32.CloseHandle(mutex)
        return
    app = LyricSkyDesktopApp()
    atexit.register(app.shutdown)

    def _console_ctrl_handler(_ctrl_type: int) -> bool:
        app.shutdown()
        return True

    try:
        win32api.SetConsoleCtrlHandler(_console_ctrl_handler, True)
    except Exception:
        pass

    signal.signal(signal.SIGINT, lambda *_: app.shutdown())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: app.shutdown())

    if not app.start():
        log.error("LyricSky could not be started.")
        if sys.stdout is None:
            try:
                user32.MessageBoxW(
                    0,
                    f"LyricSky could not start.\nSee log: {LOG_FILE}\n\nTry running Setup.bat first.",
                    "LyricSky",
                    0x10,
                )
            except Exception:
                pass
        app.shutdown()
        sys.exit(1)

    try:
        win32gui.PumpMessages()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
