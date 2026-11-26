"""
LyricSky Interactive Setup & Language Wizard
--------------------------------------------
Zero-external-dependency visual installer wizard (uses stdlib tkinter with
automatic terminal fallback) allowing any GitHub user to select their preferred
UI language (12 languages supported) and Windows startup preferences.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import bridge

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"
STARTUP_SHORTCUT = (
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
    / "LyricSky.lnk"
)

LANG_CODES = list(bridge.LOCALES.keys())


def save_language_setting(lang_code: str) -> None:
    store = bridge.SettingsStore(SETTINGS_FILE)
    store.update({"language": lang_code})


def configure_autostart(enable: bool) -> None:
    """Register instant AtLogOn Task Scheduler startup (bypasses Windows Startup folder 2-4 min delay).
    Falls back to HKCU\\...\\Run if Task Scheduler is restricted. Cleans legacy Startup .lnk.
    """
    target = BASE_DIR / "LyricSky.vbs"
    escaped_target = str(target).replace("'", "''")
    escaped_dir = str(BASE_DIR).replace("'", "''")
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    # Always remove legacy slow Startup folder shortcut so LyricSky never launches twice
    try:
        if os.environ.get("APPDATA") and STARTUP_SHORTCUT.exists():
            STARTUP_SHORTCUT.unlink()
    except Exception:
        pass

    try:
        if enable:
            ps = (
                "$ErrorActionPreference='Stop'; "
                "Remove-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'LyricSky' -ErrorAction SilentlyContinue; "
                "try { "
                f"  $act = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '\"{escaped_target}\"' -WorkingDirectory '{escaped_dir}'; "
                "  $trig = New-ScheduledTaskTrigger -AtLogOn -User \"$env:USERDOMAIN\\$env:USERNAME\"; "
                "  $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -Priority 4; "
                "  Register-ScheduledTask -TaskName 'LyricSky' -Action $act -Trigger $trig -Settings $set -Description 'LyricSky Live Lyrics Desktop Wallpaper' -Force | Out-Null; "
                "} catch { "
                f"  Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'LyricSky' -Value 'wscript.exe \"{escaped_target}\"'; "
                "}"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                creationflags=creation_flags,
                check=False,
            )
        else:
            ps = (
                "Unregister-ScheduledTask -TaskName 'LyricSky' -Confirm:$false -ErrorAction SilentlyContinue; "
                "Remove-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -Name 'LyricSky' -ErrorAction SilentlyContinue"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                creationflags=creation_flags,
                check=False,
            )
    except Exception:
        pass


def launch_lyricsky_now() -> None:
    vbs = BASE_DIR / "LyricSky.vbs"
    try:
        if vbs.exists():
            subprocess.Popen(["wscript.exe", str(vbs)], cwd=str(BASE_DIR))
        else:
            subprocess.Popen([sys.executable, str(BASE_DIR / "wallpaper.py")], cwd=str(BASE_DIR))
    except Exception:
        pass


def run_cli_wizard(default_lang: str) -> None:
    print("\n=== LyricSky Setup ===\n")
    for idx, code in enumerate(LANG_CODES, 1):
        name = bridge.LOCALES[code].get("name", code)
        mark = " *" if code == default_lang else ""
        print(f"  {idx:2d}. {name} ({code}){mark}")
    choice = input(f"\nSelect language [1-{len(LANG_CODES)}] (Enter = {default_lang}): ").strip()
    lang = default_lang
    if choice.isdigit():
        i = int(choice) - 1
        if 0 <= i < len(LANG_CODES):
            lang = LANG_CODES[i]
    elif choice in bridge.LOCALES:
        lang = choice

    save_language_setting(lang)
    auto_q = input(f"{bridge.tr(lang, 'setupAutostart')} (y/N): ").strip().lower()
    configure_autostart(auto_q in ("y", "yes", "e", "evet", "1"))

    launch_q = input(f"{bridge.tr(lang, 'setupLaunchNow')} (Y/n): ").strip().lower()
    if launch_q not in ("n", "no", "h", "hayir", "hayır", "0"):
        launch_lyricsky_now()
    print(f"\n[OK] {bridge.tr(lang, 'setupDoneMsg')}")


def run_gui_wizard(default_lang: str) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.configure(bg="#0d1016")
    root.resizable(False, False)

    win_w, win_h = 540, 520
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}")

    # Apply tray icon if Pillow can render it
    try:
        ico = DATA_DIR / "lyricsky_tray.ico"
        if not ico.exists():
            import wallpaper
            wallpaper.ensure_tray_ico_file(ico)
        if ico.exists():
            root.iconbitmap(str(ico))
    except Exception:
        pass

    selected_lang = tk.StringVar(value=default_lang)
    autostart_var = tk.BooleanVar(value=STARTUP_SHORTCUT.exists())
    launch_var = tk.BooleanVar(value=True)

    # Colors matching LyricSky's dark glass palette
    BG = "#0d1016"
    CARD = "#151a24"
    BTN_BG = "#1b2230"
    BTN_ACTIVE = "#25344f"
    BORDER = "#2a3346"
    ACCENT = "#e8f1ff"
    GREEN = "#1db954"
    MUTED = "#98a3b8"

    container = tk.Frame(root, bg=BG, padx=26, pady=22)
    container.pack(fill="both", expand=True)

    # Header
    title_lbl = tk.Label(
        container,
        text="✦  LyricSky",
        font=("Segoe UI", 18, "bold"),
        fg="#ffffff",
        bg=BG,
        anchor="w",
    )
    title_lbl.pack(fill="x")

    sub_lbl = tk.Label(
        container,
        text="",
        font=("Segoe UI", 9),
        fg=MUTED,
        bg=BG,
        anchor="w",
        justify="left",
        wraplength=480,
    )
    sub_lbl.pack(fill="x", pady=(4, 16))

    # Language Card
    lang_sec_lbl = tk.Label(
        container, text="", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg=BG, anchor="w"
    )
    lang_sec_lbl.pack(fill="x", pady=(0, 6))

    lang_frame = tk.Frame(container, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=10, pady=10)
    lang_frame.pack(fill="x")

    lang_buttons: dict[str, tk.Button] = {}

    def select_lang(code: str) -> None:
        selected_lang.set(code)
        refresh_texts()

    for idx, code in enumerate(LANG_CODES):
        name = bridge.LOCALES[code].get("name", code)
        r, c = divmod(idx, 3)
        btn = tk.Button(
            lang_frame,
            text=name,
            font=("Segoe UI", 9),
            fg="#e2e8f0",
            bg=BTN_BG,
            activebackground=BTN_ACTIVE,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=7,
            command=lambda k=code: select_lang(k),
        )
        btn.grid(row=r, column=c, sticky="ew", padx=4, pady=4)
        lang_frame.grid_columnconfigure(c, weight=1)
        lang_buttons[code] = btn

    # Startup Options Card
    opt_sec_lbl = tk.Label(
        container, text="", font=("Segoe UI", 9, "bold"), fg="#cbd5e1", bg=BG, anchor="w"
    )
    opt_sec_lbl.pack(fill="x", pady=(16, 6))

    opt_frame = tk.Frame(container, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=12, pady=10)
    opt_frame.pack(fill="x")

    chk_auto = tk.Checkbutton(
        opt_frame,
        variable=autostart_var,
        font=("Segoe UI", 9),
        fg="#e2e8f0",
        bg=CARD,
        selectcolor="#0d1016",
        activebackground=CARD,
        activeforeground="#ffffff",
        anchor="w",
        cursor="hand2",
    )
    chk_auto.pack(fill="x", pady=3)

    chk_launch = tk.Checkbutton(
        opt_frame,
        variable=launch_var,
        font=("Segoe UI", 9),
        fg="#e2e8f0",
        bg=CARD,
        selectcolor="#0d1016",
        activebackground=CARD,
        activeforeground="#ffffff",
        anchor="w",
        cursor="hand2",
    )
    chk_launch.pack(fill="x", pady=3)

    # Action Buttons Row
    btn_row = tk.Frame(container, bg=BG)
    btn_row.pack(fill="x", side="bottom", pady=(18, 0))

    def on_finish() -> None:
        lang = selected_lang.get()
        save_language_setting(lang)
        configure_autostart(autostart_var.get())
        should_launch = launch_var.get()
        root.destroy()
        if should_launch:
            launch_lyricsky_now()

    cancel_btn = tk.Button(
        btn_row,
        font=("Segoe UI", 9),
        fg=MUTED,
        bg=BTN_BG,
        activebackground="#263042",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=18,
        pady=9,
        cursor="hand2",
        command=root.destroy,
    )
    cancel_btn.pack(side="left")

    finish_btn = tk.Button(
        btn_row,
        font=("Segoe UI", 10, "bold"),
        fg="#08110c",
        bg=GREEN,
        activebackground="#27d466",
        activeforeground="#08110c",
        relief="flat",
        bd=0,
        padx=24,
        pady=9,
        cursor="hand2",
        command=on_finish,
    )
    finish_btn.pack(side="right")

    def refresh_texts() -> None:
        lang = selected_lang.get()
        root.title(bridge.tr(lang, "setupWindowTitle", "LyricSky — Setup"))
        sub_lbl.config(text=bridge.tr(lang, "setupSubtitle"))
        lang_sec_lbl.config(text=bridge.tr(lang, "setupChooseLang"))
        opt_sec_lbl.config(text=bridge.tr(lang, "setupOptionsTitle"))
        chk_auto.config(text=bridge.tr(lang, "setupAutostart"))
        chk_launch.config(text=bridge.tr(lang, "setupLaunchNow"))
        finish_btn.config(text=bridge.tr(lang, "setupInstallBtn"))
        cancel_btn.config(text=bridge.tr(lang, "setupCancelBtn"))

        for code, b in lang_buttons.items():
            if code == lang:
                b.config(bg="#273a59", fg="#ffffff", highlightbackground=ACCENT, highlightthickness=1)
            else:
                b.config(bg=BTN_BG, fg="#cbd5e1", highlightthickness=0)

    refresh_texts()
    root.mainloop()


def main() -> None:
    store = bridge.SettingsStore(SETTINGS_FILE)
    default_lang = store.data.get("language") or bridge.detect_default_language()
    if default_lang not in bridge.LOCALES:
        default_lang = "en"

    if "--cli" in sys.argv:
        run_cli_wizard(default_lang)
        return

    try:
        run_gui_wizard(default_lang)
    except Exception:
        run_cli_wizard(default_lang)


if __name__ == "__main__":
    main()
