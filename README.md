# ✦ LyricSky — Live Constellation Lyrics Desktop Wallpaper

A standalone, zero-bloat **Windows 10 & Windows 11 (including 24H2/25H2)** live desktop wallpaper that turns your currently playing music (Spotify, YouTube Music, Apple Music, or browser media) into an atmospheric cloudy sky with **real-time word-by-word constellation lyrics**, a translucent **Spotify Now-Playing card**, and a **Spotify-style scrolling lyrics stream** — **no Lively Wallpaper or Wallpaper Engine required.**

---

## ✨ Features

- **Native Frameless Desktop Wallpaper (No Third-Party Host App):** Embeds directly behind your Windows desktop icons (`SHELLDLL_DefView`) using native Win32 APIs (supports both Windows 11 24H2+ Raised Desktop and classic Windows 10/11 `WorkerW`), with a pure Win32 System Tray icon.
- **Exact Word-by-Word Synced Lyrics in All Languages:** Listens to Windows SMTC (`GlobalSystemMediaTransportControls`) and fetches millisecond-accurate word-synced lyrics (LyricsPlus / Apple Music / Musixmatch / LRCLIB) across Latin, Turkish, Japanese, Korean, Chinese, Cyrillic, Arabic, Greek, Spanish, French, German, and more.
- **Silky Constellation & Soft Dissolve:** Words appear as non-overlapping stars connected by animated starlight threads and tracked by a spring-physics reticle, gently melting into the clouds instead of disappearing abruptly.
- **Seamless Zero-Black-Frame Video Loop:** Dual-deck GPU crossfading continuously blends the background cloud video (`clouds.mp4`) without ever flashing black.
- **3-Panel Spatial Glass UI:**
  - **Bottom-Left:** Translucent Spotify Now-Playing screen card with high-res album artwork & live equalizer.
  - **Bottom-Center:** Interactive frosted glass media dock (clickable & draggable right from the desktop!) with expandable settings, 4 atmosphere themes (*Overcast*, *Midnight*, *Ambient*, *Dusk*), lyric sync offset, and one-click **Desktop Icons Show/Hide** (preserves exact icon layout!).
  - **Bottom-Right:** Spotify-style sentence-by-sentence lyric feed that smoothly fades over time (click any line to seek).
- **12 Built-in UI Languages (Interface Only — Songs & Lyrics Stay Original):**
  English, Türkçe, Deutsch, Español, Français, Português, Italiano, Русский, 日本語, 한국어, 简体中文, العربية. Changing the language only translates the LyricSky interface (setup wizard, settings, status badges, system tray); song titles, artist names, and synced lyrics always remain untouched in their original language.

---

## 🚀 Quick Install (Windows 10 / 11)

### Requirements
- **Windows 10 or Windows 11** (Microsoft Edge preinstalled)
- **Python 3.10+** ([python.org/downloads](https://www.python.org/downloads/) — check *"Add Python to PATH"*)

### 1-Click Setup
1. **Download** this repository (`Code → Download ZIP` and extract, or `git clone`).
2. Double-click **`Setup.bat`**.
   - Automatically creates an isolated `.venv` inside the folder (does not modify your system Python packages).
   - Installs lightweight dependencies from `requirements.txt`.
   - Opens the **LyricSky Setup Wizard** where you choose your **language** and **Windows autostart** preference, then launches LyricSky!

---

## 🎮 Daily Usage & Controls

| File | Purpose |
| --- | --- |
| `Setup.bat` | First-time installation & language/startup wizard |
| `LyricSky.vbs` | Start live desktop wallpaper silently (no console window) |
| `LyricSky.bat` | Start live desktop wallpaper with live console logs |
| `LyricSky_Stop.bat` | Stop LyricSky cleanly & restore your original Windows wallpaper |
| `install_startup.bat` / `uninstall_startup.bat` | Register / remove instant Windows login autostart (Task Scheduler) |

- **System Tray (Star Icon):** Right-click the star icon near your Windows clock to Play/Pause, switch themes, toggle desktop icons, open settings, re-align to desktop, or quit cleanly.
- **Custom Background Video:** Replace `clouds.mp4` with any MP4 video you like — the dual-deck crossfader automatically adapts to its duration!

---

## ⚖️ Disclaimer & Privacy

- **100% Local & Private:** `data/` (local lyric cache, settings, and isolated Edge profile) stays exclusively on your machine and is excluded via `.gitignore`.
- **No Affiliation:** LyricSky is an independent open-source project and is not affiliated with, endorsed by, or sponsored by Spotify AB, Apple Inc., or Microsoft Corporation. Lyrics are fetched dynamically from public community APIs for personal display only; no copyrighted lyrics are distributed in this repository.

## 📄 License

Licensed under the [MIT License](LICENSE).
