"""
LyricSky Bridge v2.0
--------------------
Windows SMTC (System Media Transport Controls) + Multi-Language Word-by-Word
Synced Lyrics (LyricsPlus / Apple Music / Musixmatch / LRCLIB) + Album Art +
Unified HTTP & WebSocket Server on 127.0.0.1:8765.
"""

from __future__ import annotations

import asyncio
import base64
import colorsys
import ctypes
import io
import json
import locale
import logging
import mimetypes
import os
import re
import signal
import sys
import time
import unicodedata
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    from winrt.windows.storage.streams import Buffer, InputStreamOptions
    WINRT_AVAILABLE = True
except ImportError:
    MediaManager = None
    PlaybackStatus = None
    Buffer = None
    InputStreamOptions = None
    WINRT_AVAILABLE = False

# --- Paths & Config ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CACHE_FILE = DATA_DIR / "lyrics_cache.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
LOCALES_FILE = BASE_DIR / "locales.json"

HOST = os.environ.get("LYRICSKY_HOST", os.environ.get("SWEATER_HOST", "127.0.0.1"))
PORT = int(os.environ.get("LYRICSKY_PORT", os.environ.get("SWEATER_PORT", "8765")))
USER_AGENT = "LyricSky/2.0 (Open-Source Live Lyrics Wallpaper)"
MAX_CACHE_ENTRIES = 300
NEGATIVE_CACHE_TTL_SEC = 600  # 10 min for not-found tracks
POSITIVE_CACHE_TTL_SEC = 30 * 24 * 3600  # 30 days

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("lyricsky.bridge")

# Ensure common web MIME types are known on Windows
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/json", ".json")


# ============================================================================
# Internationalization (i18n) Loader
# ============================================================================

def load_locales() -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(LOCALES_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw:
            return raw
    except Exception as exc:
        log.warning("Could not read locales.json (%s); falling back to English.", exc)
    return {"en": {"name": "English", "locale": "en-US", "rtl": False}}


LOCALES: dict[str, dict[str, Any]] = load_locales()


def detect_default_language() -> str:
    """Detect user's OS UI language and match to a supported LyricSky locale."""
    try:
        # Windows native UI language check first
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        primary = lang_id & 0x3FF
        win_map = {
            0x09: "en",
            0x1F: "tr",
            0x07: "de",
            0x0A: "es",
            0x0C: "fr",
            0x16: "pt",
            0x10: "it",
            0x19: "ru",
            0x11: "ja",
            0x12: "ko",
            0x04: "zh",
            0x01: "ar",
        }
        code = win_map.get(primary)
        if code and code in LOCALES:
            return code
    except Exception:
        pass
    try:
        sys_loc = (locale.getlocale()[0] or "").lower()[:2]
        if sys_loc in LOCALES:
            return sys_loc
    except Exception:
        pass
    return "en"


def get_lang_pack(lang_code: str | None) -> dict[str, Any]:
    if lang_code and lang_code in LOCALES:
        return LOCALES[lang_code]
    return LOCALES.get("en", {})


def tr(lang_code: str | None, key: str, fallback: str = "") -> str:
    pack = get_lang_pack(lang_code)
    if key in pack:
        return str(pack[key])
    en_pack = LOCALES.get("en", {})
    return str(en_pack.get(key, fallback or key))


# ============================================================================
# Persistent Settings & Lyrics Cache
# ============================================================================

DEFAULT_SETTINGS: dict[str, Any] = {
    "language": detect_default_language(),
    "theme": "overcast",
    "showClock": True,
    "showSeconds": False,
    "use24Hour": True,
    "clockScale": 1.0,
    "showWhisper": False,
    "showSideFeed": True,
    "showSpotifyCard": True,
    "showDust": True,
    "reticleStyle": "crosshair",
    "nodeLifeSec": 13,
    "maxNodes": 12,
    "autoFadeDock": False,
    "compactDock": False,
    "videoBrightness": 0.72,
    "videoGrayscale": 100,
    "videoBlur": 0,
    "preferredSession": "auto",
    "offsets": {},
}


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.data["offsets"] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                offsets = raw.get("offsets", {})
                self.data.update({k: v for k, v in raw.items() if k != "offsets"})
                if isinstance(offsets, dict):
                    self.data["offsets"] = {
                        str(k): float(v)
                        for k, v in offsets.items()
                        if isinstance(v, (int, float))
                    }
        except Exception as exc:
            log.warning("Ayarlar okunamadı (%s), varsayılanlar kullanılıyor.", exc)

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except Exception as exc:
            log.warning("Ayarlar kaydedilemedi: %s", exc)

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        for k, v in patch.items():
            if k == "offsets" and isinstance(v, dict):
                self.data.setdefault("offsets", {}).update(
                    {str(ok): float(ov) for ok, ov in v.items() if isinstance(ov, (int, float))}
                )
            elif k in DEFAULT_SETTINGS:
                self.data[k] = v
        self.save()
        return self.data

    def set_offset(self, track_key: str, offset: float) -> None:
        if not track_key:
            return
        offsets = self.data.setdefault("offsets", {})
        if abs(offset) < 0.01:
            offsets.pop(track_key, None)
        else:
            offsets[track_key] = round(float(offset), 2)
        # Keep offset map bounded
        if len(offsets) > 500:
            oldest_key = next(iter(offsets))
            offsets.pop(oldest_key, None)
        self.save()


class LyricsCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, dict) and "saved_at" in v:
                        self._entries[k] = v
        except Exception as exc:
            log.warning("Söz önbelleği okunamadı: %s", exc)

    def save(self) -> None:
        try:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._entries, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except Exception as exc:
            log.warning("Söz önbelleği yazılamadı: %s", exc)

    def get(self, key: str) -> dict[str, Any] | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        age = time.time() - float(entry.get("saved_at", 0))
        ttl = POSITIVE_CACHE_TTL_SEC if entry.get("lyrics") else NEGATIVE_CACHE_TTL_SEC
        if age > ttl:
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return entry

    def put(self, key: str, lyrics: list[dict[str, Any]], mode: str) -> None:
        self._entries[key] = {
            "lyrics": lyrics,
            "mode": mode,
            "saved_at": time.time(),
        }
        self._entries.move_to_end(key)
        while len(self._entries) > MAX_CACHE_ENTRIES:
            self._entries.popitem(last=False)
        self.save()

    def clear(self) -> None:
        self._entries.clear()
        self.save()

    def __len__(self) -> int:
        return len(self._entries)


# ============================================================================
# LRC Parser & Smart Lyrics Fetcher
# ============================================================================

TIME_TAG_RE = re.compile(r"\[(\d+):(\d+(?:[\.:]\d+)?)\]")
INLINE_TAG_RE = re.compile(r"<(\d+):(\d+(?:[\.:]\d+)?)>")
OFFSET_TAG_RE = re.compile(r"\[offset:\s*([+-]?\d+)\s*\]", re.IGNORECASE)
INSTRUMENTAL_ONLY_RE = re.compile(r"^[\s♪♫♬♩•·.\-~–—*()\[\]]*$")


def _parse_ts(minutes: str, seconds: str) -> float:
    return int(minutes) * 60 + float(seconds.replace(":", "."))


def parse_lrc(lrc_text: str) -> list[dict[str, Any]]:
    """Parse standard and enhanced (<mm:ss.xx>) LRC text with [offset:] and blank-line end hints."""
    offset_sec = 0.0
    m_off = OFFSET_TAG_RE.search(lrc_text)
    if m_off:
        try:
            # Standard LRC: positive offset means lyrics appear earlier (subtract from timestamp)
            offset_sec = -int(m_off.group(1)) / 1000.0
        except ValueError:
            offset_sec = 0.0

    raw_events: list[dict[str, Any]] = []
    seen: set[tuple[float, str]] = set()

    for raw in lrc_text.splitlines():
        tags = TIME_TAG_RE.findall(raw)
        if not tags:
            continue
        body = TIME_TAG_RE.sub("", raw).strip()

        # Blank or instrumental-only timestamp marks the end of the previous line
        if not body or INSTRUMENTAL_ONLY_RE.match(body):
            for m, s in tags:
                sec = max(0.0, _parse_ts(m, s) + offset_sec)
                raw_events.append({"time": sec, "text": "", "words": None, "is_break": True})
            continue

        word_events: list[dict[str, Any]] | None = None
        if INLINE_TAG_RE.search(body):
            parts = INLINE_TAG_RE.split(body)
            word_events = []
            base_m, base_s = tags[0]
            base_sec = max(0.0, _parse_ts(base_m, base_s) + offset_sec)

            lead = parts[0].strip()
            if lead:
                for w in lead.split():
                    word_events.append({"time": round(base_sec, 3), "word": w})

            for i in range(1, len(parts), 3):
                wm, ws, seg = parts[i], parts[i + 1], parts[i + 2].strip()
                wsec = max(0.0, _parse_ts(wm, ws) + offset_sec)
                if seg:
                    for w in seg.split():
                        word_events.append({"time": round(wsec, 3), "word": w})

        clean_text = INLINE_TAG_RE.sub("", body).strip()
        clean_text = re.sub(r"\s+", " ", clean_text)
        if not clean_text or INSTRUMENTAL_ONLY_RE.match(clean_text):
            continue

        for m, s in tags:
            sec = max(0.0, _parse_ts(m, s) + offset_sec)
            key = (round(sec, 2), clean_text.lower())
            if key not in seen:
                seen.add(key)
                raw_events.append(
                    {
                        "time": round(sec, 3),
                        "text": clean_text,
                        "words": word_events if (word_events and len(tags) == 1) else None,
                        "is_break": False,
                    }
                )

    raw_events.sort(key=lambda item: (item["time"], 0 if item["is_break"] else 1))

    # Convert break markers into explicit `end` timestamps on the preceding lyric line
    lines: list[dict[str, Any]] = []
    for ev in raw_events:
        if ev["is_break"]:
            if lines and "end" not in lines[-1] and ev["time"] > lines[-1]["time"] + 0.15:
                lines[-1]["end"] = round(ev["time"], 3)
            continue
        lines.append(
            {
                "time": ev["time"],
                "text": ev["text"],
                "words": ev["words"],
            }
        )

    return lines


def build_estimated_lyrics(plain_text: str, duration: float) -> list[dict[str, Any]]:
    """Create softly-paced fallback timestamps from plain lyrics when no synced LRC exists."""
    raw_lines = [
        re.sub(r"\s+", " ", ln).strip()
        for ln in plain_text.splitlines()
        if ln.strip() and not re.match(r"^\[.*\]$", ln.strip())
    ]
    if not raw_lines:
        return []

    dur = duration if duration > 15.0 else max(60.0, len(raw_lines) * 3.2)
    intro = min(12.0, dur * 0.06)
    outro = min(10.0, dur * 0.05)
    usable = max(10.0, dur - intro - outro)

    # Weight lines by word count so denser lines get proportionally more time
    weights = [max(2.0, float(len(ln.split()))) for ln in raw_lines]
    total_w = sum(weights)

    result: list[dict[str, Any]] = []
    cursor = intro
    for ln, w in zip(raw_lines, weights):
        result.append({"time": round(cursor, 3), "text": ln, "words": None})
        cursor += (w / total_w) * usable
    return result


NOISE_PARENS_RE = re.compile(
    r"\s*[\(\[（【]"
    r"(?:feat\.?|ft\.?|featuring|with\s+|prod\.?|official\s*(?:music\s*)?(?:video|audio|lyric(?:s)?\s*video|visualizer|mv)|"
    r"lyrics?|remaster(?:ed|izado)?(?:\s*\d{4})?|audio|video|mv|hd|4k|hq|live|en\s+vivo|canlı|akustik|acoustic|"
    r"radio\s*edit|single\s*version|album\s*version|explicit|clean|slowed(?:\s*\+\s*reverb)?|sped\s*up|speed\s*up|"
    r"ver\.?|version|instrumental|from\s+)"
    r"[^\)\]）】]*[\)\]）】]",
    re.IGNORECASE,
)
NOISE_DASH_RE = re.compile(
    r"\s*[-–—]\s*(?:remaster(?:ed|izado)?|live|en\s+vivo|canlı|akustik|acoustic|radio\s*edit|single\s*version|"
    r"official.*|lyrics?.*|slowed.*|sped\s*up.*|from\s+.*|.*ver\.?$).*$",
    re.IGNORECASE,
)
ANY_BRACKETS_RE = re.compile(r"\s*(?:\([^\)]*\)|\[[^\]]*\]|（[^）]*）|【[^】]*】)")
NO_SPACE_SCRIPT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\u0e00-\u0e7f]")
CJK_CREDIT_RE = re.compile(
    r"^(?:(?:lyrics|music|written|composed|produced|arranged)\s*by\b|"
    r"(?:作[词詞曲]|编曲|編曲|制作|製作|演唱|詞|曲|編|作詞|作曲)\s*[:：]|"
    r".*\s*-\s*.*(?:作[词詞曲]|编曲))",
    re.IGNORECASE,
)
TRAILING_PUNCT_ONLY_RE = re.compile(r"^[\.,!?;:…、。！？，；：」』）\)\]\}\"'”’~～]+$")


def _fold_text(s: str) -> str:
    """Unicode-aware accent-insensitive comparison key across all scripts."""
    norm = unicodedata.normalize("NFKD", s or "")
    # Keep base letters/digits across all languages, drop combining diacritics (e.g. é->e, ü->u)
    stripped = "".join(ch for ch in norm if not unicodedata.combining(ch))
    # Handle Turkish dotless ı -> i for tolerant fuzzy matching
    return stripped.replace("ı", "i").replace("İ", "i").casefold().strip()


def _char_bigrams(s: str) -> set[str]:
    compact = re.sub(r"\s+", "", s)
    if len(compact) < 2:
        return {compact} if compact else set()
    return {compact[i : i + 2] for i in range(len(compact) - 1)}


def normalize_track_meta(title: str, artist: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Clean Spotify/YouTube/Browser metadata across all languages & scripts."""
    raw_title = unicodedata.normalize("NFC", (title or "").strip())
    raw_artist = unicodedata.normalize("NFC", (artist or "").strip())

    # Clean YouTube "- Topic" & VEVO noise on artist
    clean_artist = re.sub(r"\s*-\s*Topic$", "", raw_artist, flags=re.IGNORECASE).strip()
    clean_artist = re.sub(r"VEVO$", "", clean_artist).strip()

    # Main artist before collaboration separators (Spotify joins artists with ", ")
    main_artist = re.split(
        r"\s*(?:,|、|，|&|\bfeat\.?\b|\bft\.?\b|\bx\b|\bwith\b)\s*",
        clean_artist,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()

    clean_title = NOISE_PARENS_RE.sub("", raw_title).strip()
    clean_title = NOISE_DASH_RE.sub("", clean_title).strip()
    # Also clean trailing "feat. ..." without parentheses
    clean_title_no_feat = re.sub(r"\s+(?:feat\.?|ft\.?|featuring)\s+.*$", "", clean_title, flags=re.IGNORECASE).strip()
    # Strip any remaining Latin or CJK full-width bracketed suffixes
    stripped_title = ANY_BRACKETS_RE.sub("", clean_title_no_feat).strip() or clean_title_no_feat or clean_title

    candidates: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_candidate(t: str, a: str) -> None:
        t, a = t.strip(), a.strip()
        if not t:
            return
        k = (_fold_text(t), _fold_text(a))
        if k not in seen:
            seen.add(k)
            candidates.append((t, a))

    # YouTube pattern: title is "Artist - Song Title"
    if " - " in clean_title:
        left, right = clean_title.split(" - ", 1)
        left_s = ANY_BRACKETS_RE.sub("", left).strip()
        right_s = ANY_BRACKETS_RE.sub("", right).strip()
        if left_s and right_s:
            if not main_artist or _fold_text(main_artist) in _fold_text(left_s) or "youtube" in _fold_text(main_artist):
                add_candidate(right_s, left_s)
            add_candidate(stripped_title, main_artist)
            add_candidate(right_s, left_s)

    add_candidate(raw_title, main_artist)
    add_candidate(clean_title, main_artist)
    add_candidate(stripped_title, main_artist)
    if clean_artist and _fold_text(clean_artist) != _fold_text(main_artist):
        add_candidate(raw_title, clean_artist)
        add_candidate(stripped_title, clean_artist)

    return stripped_title or raw_title, main_artist or clean_artist, candidates


def _score_lrclib_result(item: dict[str, Any], target_title: str, target_artist: str, duration: float) -> float:
    score = 0.0
    r_title = _fold_text(item.get("trackName") or item.get("name") or "")
    r_artist = _fold_text(item.get("artistName") or "")
    t_low = _fold_text(target_title)
    a_low = _fold_text(target_artist)

    if r_title == t_low:
        score += 50.0
    elif t_low and (t_low in r_title or r_title in t_low):
        score += 28.0
    elif t_low and r_title:
        tb, rb = _char_bigrams(t_low), _char_bigrams(r_title)
        if tb and rb:
            score += (len(tb & rb) / max(len(tb | rb), 1)) * 34.0

    if a_low:
        if r_artist == a_low:
            score += 45.0
        elif a_low in r_artist or r_artist in a_low:
            score += 26.0
        else:
            a_tokens = set(re.findall(r"\w+", a_low, re.UNICODE))
            r_tokens = set(re.findall(r"\w+", r_artist, re.UNICODE))
            tok_overlap = (len(a_tokens & r_tokens) / max(len(a_tokens), 1)) if (a_tokens and r_tokens) else 0.0
            ab, rb = _char_bigrams(a_low), _char_bigrams(r_artist)
            bg_overlap = (len(ab & rb) / max(len(ab | rb), 1)) if (ab and rb) else 0.0
            score += max(tok_overlap, bg_overlap) * 24.0

    r_dur = item.get("duration")
    if duration >= 10 and isinstance(r_dur, (int, float)) and r_dur > 0:
        diff = abs(float(r_dur) - duration)
        if diff <= 2.0:
            score += 35.0
        elif diff <= 5.0:
            score += 22.0
        elif diff <= 12.0:
            score += 8.0
        else:
            score -= min(40.0, diff * 0.6)

    return score


LYRICSPLUS_BASES = [
    "https://lyricsplus.prjktla.my.id",
    "https://lyricsplus-seven.vercel.app",
]


def parse_lyricsplus(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Parse LyricsPlus v2 JSON (Apple Music / Musixmatch / Spotify / NetEase) across all scripts."""
    raw_lines = payload.get("lyrics") or payload.get("lines") or []
    if not isinstance(raw_lines, list) or not raw_lines:
        return [], "none"

    meta = payload.get("metadata") or {}
    songwriters = {_fold_text(str(w)) for w in (meta.get("songWriters") or []) if w}

    lines: list[dict[str, Any]] = []
    word_synced_lines = 0

    for item in raw_lines:
        if not isinstance(item, dict):
            continue
        text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", str(item.get("text") or "")).strip())
        if not text or INSTRUMENTAL_ONLY_RE.match(text):
            continue

        start_ms = float(item.get("time", item.get("startTime", 0)) or 0)
        dur_ms = float(item.get("duration", 0) or 0)
        end_ms = float(item.get("endTime", 0) or 0)

        start_sec = max(0.0, start_ms / 1000.0)
        if end_ms > start_ms:
            end_sec: float | None = round(end_ms / 1000.0, 3)
        elif dur_ms > 100:
            end_sec = round((start_ms + dur_ms) / 1000.0, 3)
        else:
            end_sec = None

        # Skip non-vocal composer/lyricist credit headers (English & CJK)
        if start_sec < 4.5 and (_fold_text(text) in songwriters or CJK_CREDIT_RE.match(text)):
            continue

        syllables = item.get("syllabus") or item.get("words") or []
        word_events: list[dict[str, Any]] | None = None

        if isinstance(syllables, list) and syllables:
            merged: list[dict[str, Any]] = []
            # Detect non-space-delimited scripts (Japanese / Chinese / Thai) where
            # syllabus tokens do not contain trailing spaces between words.
            non_bg = [s for s in syllables if isinstance(s, dict) and not s.get("isBackground")]
            has_any_space = any(any(ch.isspace() for ch in str(s.get("text") or "")) for s in non_bg)
            is_no_space_script = bool(NO_SPACE_SCRIPT_RE.search(text)) and not has_any_space

            if is_no_space_script:
                for syl in non_bg:
                    tok = unicodedata.normalize("NFC", str(syl.get("text") or "").strip())
                    if not tok:
                        continue
                    s_ms = float(syl.get("time", syl.get("startTime", start_ms)) or start_ms)
                    s_sec = max(0.0, s_ms / 1000.0)
                    # Attach standalone punctuation cleanly to the previous token
                    if TRAILING_PUNCT_ONLY_RE.match(tok) and merged:
                        merged[-1]["word"] += tok
                    else:
                        merged.append({"time": round(s_sec, 3), "word": tok})
            else:
                buf_text = ""
                buf_time: float | None = None
                for syl in non_bg:
                    raw_t = unicodedata.normalize("NFC", str(syl.get("text") or ""))
                    if not raw_t:
                        continue
                    s_ms = float(syl.get("time", syl.get("startTime", start_ms)) or start_ms)
                    s_sec = max(0.0, s_ms / 1000.0)

                    # Leading space flushes the previous word cleanly
                    if raw_t[0].isspace() and buf_text.strip():
                        for w in buf_text.strip().split():
                            merged.append({"time": round(buf_time if buf_time is not None else s_sec, 3), "word": w})
                        buf_text = ""
                        buf_time = None
                        raw_t = raw_t.lstrip()
                        if not raw_t:
                            continue

                    if buf_time is None and raw_t.strip():
                        buf_time = s_sec
                    buf_text += raw_t

                    if raw_t[-1].isspace():
                        for w in buf_text.strip().split():
                            merged.append({"time": round(buf_time if buf_time is not None else s_sec, 3), "word": w})
                        buf_text = ""
                        buf_time = None

                if buf_text.strip():
                    for w in buf_text.strip().split():
                        merged.append({"time": round(buf_time if buf_time is not None else start_sec, 3), "word": w})

            if merged:
                word_events = merged
                word_synced_lines += 1

        entry: dict[str, Any] = {
            "time": round(start_sec, 3),
            "text": text,
            "words": word_events,
        }
        if end_sec is not None and end_sec > start_sec + 0.15:
            entry["end"] = end_sec
        lines.append(entry)

    if not lines:
        return [], "none"

    lines.sort(key=lambda ln: ln["time"])
    mode = "word" if word_synced_lines >= max(1, len(lines) // 3) else "synced"
    return lines, mode


async def _fetch_lyricsplus(
    http_session: aiohttp.ClientSession,
    candidates: list[tuple[str, str]],
    album: str,
    duration: float,
    headers: dict[str, str],
) -> tuple[list[dict[str, Any]], str]:
    """Query LyricsPlus across global providers (Apple Music / Musixmatch / Spotify / NetEase)."""
    timeout = aiohttp.ClientTimeout(total=5.5)
    source_tiers = [
        "apple,musixmatch,spotify,lyricsplus",
        "netease,qq,musixmatch,spotify",
    ]
    for source_list in source_tiers:
        for cand_title, cand_artist in candidates[:2]:
            if not cand_title:
                continue
            params: dict[str, str] = {
                "title": cand_title,
                "artist": cand_artist,
                "source": source_list,
            }
            if album:
                params["album"] = album
            if duration >= 10:
                params["duration"] = str(round(duration))

            for base in LYRICSPLUS_BASES:
                try:
                    async with http_session.get(
                        f"{base}/v2/lyrics/get",
                        params=params,
                        headers=headers,
                        timeout=timeout,
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            if isinstance(data, dict):
                                parsed, mode = parse_lyricsplus(data)
                                if parsed:
                                    src = (data.get("metadata") or {}).get("source", "LyricsPlus")
                                    log.info("LyricsPlus [%s] eşleşti (%s, %d satır)", src, mode, len(parsed))
                                    return parsed, mode
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.debug("LyricsPlus (%s) hatası: %s", base, exc)
    return [], "none"


async def fetch_lyrics(
    http_session: aiohttp.ClientSession,
    title: str,
    artist: str,
    album: str,
    duration: float,
    cache: LyricsCache,
) -> tuple[list[dict[str, Any]], str]:
    """Fetch exact word-by-word (LyricsPlus/Apple/Musixmatch/NetEase) or strict line-synced (LRCLIB) lyrics.
    Returns: (lyrics_list, mode) where mode is 'word' | 'synced' | 'none'
    """
    norm_title, norm_artist, candidates = normalize_track_meta(title, artist)
    cache_key = f"v3::{_fold_text(norm_artist)}::{_fold_text(norm_title)}::{round(duration / 5) * 5}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached["lyrics"], cached["mode"]

    timeout = aiohttp.ClientTimeout(total=6.5)
    headers = {"User-Agent": USER_AGENT}
    fallback_line_synced: tuple[list[dict[str, Any]], str] | None = None

    # 1) Priority 1: True word-by-word synced lyrics via LyricsPlus (Apple Music / Musixmatch / Spotify)
    lp_lyrics, lp_mode = await _fetch_lyricsplus(http_session, candidates, album, duration, headers)
    if lp_lyrics and lp_mode == "word":
        cache.put(cache_key, lp_lyrics, "word")
        return lp_lyrics, "word"
    if lp_lyrics:
        fallback_line_synced = (lp_lyrics, lp_mode)

    # 2) Priority 2: Exact match via LRCLIB /api/get
    if duration >= 10 and norm_artist:
        for cand_title, cand_artist in candidates[:2]:
            params: dict[str, str] = {
                "track_name": cand_title,
                "artist_name": cand_artist,
                "duration": str(round(duration)),
            }
            if album:
                params["album_name"] = album
            try:
                async with http_session.get(
                    "https://lrclib.net/api/get",
                    params=params,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("syncedLyrics"):
                            parsed = parse_lrc(data["syncedLyrics"])
                            if parsed:
                                has_words = any(ln.get("words") for ln in parsed)
                                mode = "word" if has_words else "synced"
                                cache.put(cache_key, parsed, mode)
                                return parsed, mode
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.debug("LRCLIB /api/get hatası: %s", exc)

    # 3) Priority 3: Strict structured search via LRCLIB /api/search
    min_score = 45.0 if norm_artist else 25.0
    for cand_title, cand_artist in candidates[:3]:
        params = {"track_name": cand_title}
        if cand_artist:
            params["artist_name"] = cand_artist
        try:
            async with http_session.get(
                "https://lrclib.net/api/search",
                params=params,
                headers=headers,
                timeout=timeout,
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    if isinstance(results, list) and results:
                        synced = [r for r in results if r.get("syncedLyrics")]
                        if synced:
                            best = max(
                                synced,
                                key=lambda r: _score_lrclib_result(r, cand_title, cand_artist, duration),
                            )
                            if _score_lrclib_result(best, cand_title, cand_artist, duration) >= min_score:
                                parsed = parse_lrc(best["syncedLyrics"])
                                if parsed:
                                    has_words = any(ln.get("words") for ln in parsed)
                                    mode = "word" if has_words else "synced"
                                    cache.put(cache_key, parsed, mode)
                                    return parsed, mode
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.debug("LRCLIB /api/search hatası: %s", exc)

    # 4) Return line-synced LyricsPlus if we found one earlier
    if fallback_line_synced is not None:
        cache.put(cache_key, fallback_line_synced[0], fallback_line_synced[1])
        return fallback_line_synced

    # 5) Strict fuzzy LRCLIB fallback (only synced, high confidence so words never mismatch)
    query = f"{norm_title} {norm_artist}".strip()
    if query:
        try:
            async with http_session.get(
                "https://lrclib.net/api/search",
                params={"q": query},
                headers=headers,
                timeout=timeout,
            ) as resp:
                if resp.status == 200:
                    results = await resp.json()
                    if isinstance(results, list) and results:
                        synced = [r for r in results if r.get("syncedLyrics")]
                        if synced:
                            best = max(
                                synced,
                                key=lambda r: _score_lrclib_result(r, norm_title, norm_artist, duration),
                            )
                            if _score_lrclib_result(best, norm_title, norm_artist, duration) >= min_score:
                                parsed = parse_lrc(best["syncedLyrics"])
                                if parsed:
                                    has_words = any(ln.get("words") for ln in parsed)
                                    mode = "word" if has_words else "synced"
                                    cache.put(cache_key, parsed, mode)
                                    return parsed, mode
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.debug("LRCLIB fuzzy search hatası: %s", exc)

    cache.put(cache_key, [], "none")
    return [], "none"


# ============================================================================
# Thumbnail & Dominant Ambient Color Extraction
# ============================================================================

def _process_thumbnail_bytes(raw_bytes: bytes) -> tuple[str | None, str | None]:
    """Resize album cover to compact JPEG data-URI and pick a refined ambient accent color."""
    if not raw_bytes:
        return None, None

    if Image is None:
        b64 = base64.b64encode(raw_bytes).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", None

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            rgb = img.convert("RGB")

            # Compute subtle accent color from a small thumbnail
            small = rgb.resize((48, 48), Image.Resampling.BILINEAR)
            pixels = list(
                small.get_flattened_data()
                if hasattr(small, "get_flattened_data")
                else small.getdata()
            )
            best_rgb = (220, 228, 240)
            best_score = -1.0

            # Sample evenly to keep CPU negligible
            for r, g, b in pixels[::3]:
                h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
                if v < 0.22 or v > 0.96:
                    continue
                # Favor pleasant mid-to-rich saturation and clean brightness
                score = s * 1.4 + (1.0 - abs(v - 0.65)) * 0.6
                if score > best_score:
                    best_score = score
                    best_rgb = (r, g, b)

            # Soften & lift accent color so it always reads elegantly on dark clouds
            h, s, v = colorsys.rgb_to_hsv(best_rgb[0] / 255.0, best_rgb[1] / 255.0, best_rgb[2] / 255.0)
            s = min(0.58, max(0.18, s))
            v = min(0.92, max(0.72, v))
            ar, ag, ab = colorsys.hsv_to_rgb(h, s, v)
            accent_hex = f"#{int(ar * 255):02x}{int(ag * 255):02x}{int(ab * 255):02x}"

            # Resize cover art to crisp 384x384 JPEG for sharp Now-Playing showcase
            rgb.thumbnail((384, 384), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            rgb.save(out, format="JPEG", quality=86, optimize=True)
            b64 = base64.b64encode(out.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}", accent_hex
    except Exception as exc:
        log.debug("Kapak görseli işlenemedi: %s", exc)
        return None, None


async def extract_thumbnail(thumbnail_ref: Any) -> tuple[str | None, str | None]:
    if not thumbnail_ref or not WINRT_AVAILABLE:
        return None, None
    stream = None
    try:
        stream = await thumbnail_ref.open_read_async()
        size = int(stream.size)
        if size <= 0 or size > 8 * 1024 * 1024:
            return None, None
        buf = Buffer(size)
        res = await stream.read_async(buf, size, InputStreamOptions.READ_AHEAD)
        raw_bytes = bytes(res)
        return await asyncio.to_thread(_process_thumbnail_bytes, raw_bytes)
    except Exception as exc:
        log.debug("SMTC kapak görseli alınamadı: %s", exc)
        return None, None
    finally:
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass


# ============================================================================
# Windows Desktop Icons Visibility Helper (Preserves Exact Icon Layout)
# ============================================================================

def _find_shelldll_defview() -> int:
    """Locate SHELLDLL_DefView on Windows 10 & Windows 11 (including 24H2/25H2)."""
    try:
        u32 = ctypes.windll.user32
        progman = u32.FindWindowW("Progman", None)
        if progman:
            dv = u32.FindWindowExW(progman, 0, "SHELLDLL_DefView", None)
            if dv:
                return int(dv)
        desktop = u32.GetDesktopWindow()
        workerw = 0
        for _ in range(64):
            workerw = u32.FindWindowExW(desktop, workerw, "WorkerW", None)
            if not workerw:
                break
            dv = u32.FindWindowExW(workerw, 0, "SHELLDLL_DefView", None)
            if dv:
                return int(dv)
    except Exception:
        pass
    return 0


def get_desktop_icons_visible() -> bool:
    """Return True if Windows desktop icons (SysListView32) are currently visible."""
    try:
        u32 = ctypes.windll.user32
        dv = _find_shelldll_defview()
        if not dv:
            return True
        lv = u32.FindWindowExW(dv, 0, "SysListView32", None)
        if not lv:
            return True
        return bool(u32.IsWindowVisible(lv))
    except Exception:
        return True


def set_desktop_icons_visible(visible: bool | None = None) -> bool:
    """Toggle or set Windows desktop icons via Explorer's native WM_COMMAND 0x7402.
    Preserves 100% of icon positions without restarting explorer.exe.
    """
    try:
        u32 = ctypes.windll.user32
        dv = _find_shelldll_defview()
        if not dv:
            return True
        cur = get_desktop_icons_visible()
        if visible is None or bool(visible) != cur:
            # WM_COMMAND (0x0111), Explorer 'Show desktop icons' toggle ID (0x7402)
            u32.SendMessageW(dv, 0x0111, 0x7402, 0)
        return get_desktop_icons_visible()
    except Exception:
        return get_desktop_icons_visible()


# ============================================================================
# Friendly Source App Name Helper
# ============================================================================

def friendly_app_name(app_id: str | None) -> str:
    if not app_id:
        return "Media"
    low = app_id.lower()
    mapping = [
        ("spotify", "Spotify"),
        ("applemusic", "Apple Music"),
        ("itunes", "iTunes"),
        ("ytmdesktop", "YouTube Music"),
        ("youtube", "YouTube"),
        ("tidal", "TIDAL"),
        ("deezer", "Deezer"),
        ("soundcloud", "SoundCloud"),
        ("foobar", "foobar2000"),
        ("vlc", "VLC"),
        ("musicbee", "MusicBee"),
        ("aimp", "AIMP"),
        ("chrome", "Chrome"),
        ("msedge", "Edge"),
        ("firefox", "Firefox"),
        ("brave", "Brave"),
        ("opera", "Opera"),
        ("vivaldi", "Vivaldi"),
        ("zunemusic", "Media Player"),
        ("microsoft.media", "Media Player"),
    ]
    for needle, label in mapping:
        if needle in low:
            return label
    # Strip UWP package noise or .exe
    cleaned = app_id.split("!")[-1].replace(".exe", "").replace(".EXE", "")
    cleaned = cleaned.split("_")[0].split(".")[-1]
    return cleaned[:20] or "Media"


# ============================================================================
# Core Bridge Service
# ============================================================================

class LyricSkyBridge:
    def __init__(self) -> None:
        self.settings = SettingsStore(SETTINGS_FILE)
        self.cache = LyricsCache(CACHE_FILE)
        self.clients: set[web.WebSocketResponse] = set()
        self.http_session: aiohttp.ClientSession | None = None

        self.manager: Any = None
        self.active_session: Any = None
        self._active_session_id: str | None = None
        self._session_tokens: list[tuple[str, Any]] = []
        self._wake_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None

        self._lyrics_task: asyncio.Task[Any] | None = None
        self._thumb_cache: OrderedDict[str, tuple[str | None, str | None]] = OrderedDict()
        self._generation = 0

        self.clock: dict[str, Any] = {
            "active": False,
            "track_id": None,
            "title": "",
            "artist": "",
            "album": "",
            "source_id": "",
            "source_name": "",
            "cover": None,
            "accent": None,
            "duration": 0.0,
            "lyrics": [],
            "lyrics_status": "idle",  # idle | loading | ready | none
            "lyrics_mode": "none",    # synced | estimated | none
            "playing": False,
            "anchor_pos": 0.0,
            "anchor_mono": 0.0,
            "last_raw_pos": -1.0,
            "last_updated": "",
        }
        self.available_sessions: list[dict[str, Any]] = []

    # --- Clock helpers ---
    def get_unclamped_pos(self) -> float:
        if self.clock["playing"]:
            return max(0.0, self.clock["anchor_pos"] + (time.monotonic() - self.clock["anchor_mono"]))
        return max(0.0, self.clock["anchor_pos"])

    def get_clock_pos(self) -> float:
        pos = self.get_unclamped_pos()
        if self.clock["duration"] > 1.0:
            return min(self.clock["duration"], pos)
        return pos

    @staticmethod
    def compute_timeline_pos(
        timeline: Any,
        playing: bool,
        duration: float,
        is_new_track: bool = False,
        is_initial_sync: bool = False,
    ) -> tuple[float, float, str]:
        """Compute accurate playback position using SMTC timeline.position + last_updated_time."""
        raw_pos = max(0.0, timeline.position.total_seconds())
        last_upd = getattr(timeline, "last_updated_time", None)
        upd_str = str(last_upd or "")

        # Guard against stale end-of-previous-song timeline right on track switch
        if is_new_track and not is_initial_sync and duration > 5.0 and raw_pos > duration - 2.5:
            return 0.0, raw_pos, upd_str

        est = raw_pos
        if playing and isinstance(last_upd, datetime) and 2000 < last_upd.year < 3000:
            now_utc = datetime.now(timezone.utc) if last_upd.tzinfo is not None else datetime.utcnow()
            elapsed = (now_utc - last_upd).total_seconds()
            # On track switch, if last_updated_time is older than ~2s (and not initial startup),
            # it may still carry the previous song's timestamp.
            if is_new_track and not is_initial_sync and elapsed > 2.5:
                elapsed = 0.0
            if 0.0 <= elapsed <= max(duration + 5.0, 7200.0):
                est = raw_pos + elapsed

        if duration > 1.0:
            if is_new_track and not is_initial_sync and est > duration - 1.5:
                est = 0.0
            else:
                est = min(duration, est)

        return max(0.0, est), raw_pos, upd_str

    # --- Payloads & Broadcasting ---
    def build_track_payload(self) -> dict[str, Any]:
        return {
            "type": "track",
            "track_id": self.clock["track_id"],
            "title": self.clock["title"],
            "artist": self.clock["artist"],
            "album": self.clock["album"],
            "source_id": self.clock["source_id"],
            "source_name": self.clock["source_name"],
            "cover": self.clock["cover"],
            "accent": self.clock["accent"],
            "duration": self.clock["duration"] if self.clock["duration"] > 1.0 else 1.0,
            "position": round(self.get_clock_pos(), 3),
            "playing": self.clock["playing"],
            "lyrics": self.clock["lyrics"],
            "lyrics_status": self.clock["lyrics_status"],
            "lyrics_mode": self.clock["lyrics_mode"],
            "sessions": self.available_sessions,
        }

    def build_init_payload(self) -> dict[str, Any]:
        return {
            "type": "init",
            "settings": self.settings.data,
            "sessions": self.available_sessions,
            "desktop_icons": get_desktop_icons_visible(),
            "winrt": WINRT_AVAILABLE,
        }

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self.clients:
            return
        raw = json.dumps(message, ensure_ascii=False)
        dead: list[web.WebSocketResponse] = []
        for ws in list(self.clients):
            if ws.closed:
                dead.append(ws)
                continue
            try:
                await ws.send_str(raw)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.discard(ws)

    # --- SMTC Event Subscription ---
    def _signal_wake(self, *_args: Any) -> None:
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._wake_event.set)

    def _detach_session_listeners(self) -> None:
        if self.active_session is None:
            self._session_tokens.clear()
            return
        for kind, token in self._session_tokens:
            try:
                if kind == "media":
                    self.active_session.remove_media_properties_changed(token)
                elif kind == "playback":
                    self.active_session.remove_playback_info_changed(token)
                elif kind == "timeline":
                    self.active_session.remove_timeline_properties_changed(token)
            except Exception:
                pass
        self._session_tokens.clear()

    def _attach_session_listeners(self, session: Any) -> None:
        self._detach_session_listeners()
        self.active_session = session
        if session is None:
            self._active_session_id = None
            return
        self._active_session_id = session.source_app_user_model_id or ""
        try:
            self._session_tokens.append(("media", session.add_media_properties_changed(self._signal_wake)))
            self._session_tokens.append(("playback", session.add_playback_info_changed(self._signal_wake)))
            self._session_tokens.append(("timeline", session.add_timeline_properties_changed(self._signal_wake)))
        except Exception as exc:
            log.debug("Oturum dinleyicileri eklenemedi: %s", exc)

    def _list_and_pick_session(self) -> Any:
        if not self.manager:
            return None
        sessions = list(self.manager.get_sessions())
        preferred = self.settings.data.get("preferredSession", "auto")

        session_info: list[dict[str, Any]] = []
        playing_sessions: list[Any] = []
        preferred_match = None

        for s in sessions:
            sid = s.source_app_user_model_id or ""
            is_playing = False
            try:
                pb = s.get_playback_info()
                is_playing = pb.playback_status == PlaybackStatus.PLAYING
            except Exception:
                pass
            if is_playing:
                playing_sessions.append(s)
            if preferred != "auto" and sid == preferred:
                preferred_match = s
            session_info.append(
                {
                    "id": sid,
                    "name": friendly_app_name(sid),
                    "playing": is_playing,
                }
            )

        # Deduplicate session list by id
        seen_ids: set[str] = set()
        deduped = []
        for item in session_info:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                deduped.append(item)
        self.available_sessions = deduped

        if preferred_match is not None:
            return preferred_match

        # Smart auto selection: Playing Spotify > Any playing > Paused Spotify > System current
        for s in playing_sessions:
            if "spotify" in (s.source_app_user_model_id or "").lower():
                return s
        if playing_sessions:
            return playing_sessions[0]
        for s in sessions:
            if "spotify" in (s.source_app_user_model_id or "").lower():
                return s
        return self.manager.get_current_session()

    # --- Background Lyrics Task ---
    def _spawn_lyrics_fetch(
        self,
        gen: int,
        track_id: str,
        title: str,
        artist: str,
        album: str,
        duration: float,
    ) -> None:
        if self._lyrics_task and not self._lyrics_task.done():
            self._lyrics_task.cancel()

        async def _worker() -> None:
            assert self.http_session is not None
            try:
                lyrics, mode = await fetch_lyrics(
                    self.http_session, title, artist, album, duration, self.cache
                )
                if gen != self._generation or self.clock["track_id"] != track_id:
                    return
                self.clock["lyrics"] = lyrics
                self.clock["lyrics_mode"] = mode
                self.clock["lyrics_status"] = "ready" if lyrics else "none"
                log.info(
                    "Sözler hazır: %s — %d satır (%s)",
                    track_id,
                    len(lyrics),
                    mode,
                )
                await self.broadcast(
                    {
                        "type": "lyrics",
                        "track_id": track_id,
                        "lyrics": lyrics,
                        "lyrics_status": self.clock["lyrics_status"],
                        "lyrics_mode": mode,
                        "position": round(self.get_clock_pos(), 3),
                    }
                )
            except asyncio.CancelledError:
                return
            except Exception as exc:
                log.warning("Söz çekme hatası (%s): %s", track_id, exc)
                if gen == self._generation and self.clock["track_id"] == track_id:
                    self.clock["lyrics_status"] = "none"
                    self.clock["lyrics_mode"] = "none"
                    await self.broadcast(
                        {
                            "type": "lyrics",
                            "track_id": track_id,
                            "lyrics": [],
                            "lyrics_status": "none",
                            "lyrics_mode": "none",
                            "position": round(self.get_clock_pos(), 3),
                        }
                    )

        self._lyrics_task = asyncio.create_task(_worker())

    # --- Client Commands ---
    async def handle_client_command(
        self, data: dict[str, Any], ws: web.WebSocketResponse | None = None
    ) -> None:
        cmd = data.get("cmd")

        if cmd == "sync":
            payload = (
                self.build_track_payload()
                if (self.clock["active"] and self.clock["track_id"])
                else {"type": "idle", "sessions": self.available_sessions}
            )
            if ws is not None and not ws.closed:
                await ws.send_str(json.dumps(payload, ensure_ascii=False))
            else:
                await self.broadcast(payload)
            return

        if cmd == "update_settings":
            patch = data.get("settings")
            if isinstance(patch, dict):
                updated = self.settings.update(patch)
                await self.broadcast({"type": "settings", "settings": updated})
                self._wake_event.set()
            return

        if cmd in ("set_desktop_icons", "toggle_desktop_icons"):
            desired = None if cmd == "toggle_desktop_icons" else bool(data.get("visible", True))
            new_state = set_desktop_icons_visible(desired)
            lang = self.settings.data.get("language", "en")
            await self.broadcast({"type": "desktop_icons", "visible": new_state})
            await self.broadcast(
                {
                    "type": "notice",
                    "text": tr(lang, "iconsShown" if new_state else "iconsHidden"),
                }
            )
            return

        if cmd == "set_offset":
            track_key = str(data.get("track_key") or self.clock["track_id"] or "")
            offset = float(data.get("offset", 0.0))
            self.settings.set_offset(track_key, offset)
            await self.broadcast({"type": "settings", "settings": self.settings.data})
            return

        if cmd == "select_session":
            sid = str(data.get("session_id") or "auto")
            self.settings.update({"preferredSession": sid})
            await self.broadcast({"type": "settings", "settings": self.settings.data})
            self._wake_event.set()
            return

        if cmd == "refetch_lyrics":
            if self.clock["active"] and self.clock["track_id"]:
                self.cache.clear()
                self._generation += 1
                self.clock["lyrics"] = []
                self.clock["lyrics_status"] = "loading"
                self.clock["lyrics_mode"] = "none"
                await self.broadcast(self.build_track_payload())
                self._spawn_lyrics_fetch(
                    self._generation,
                    self.clock["track_id"],
                    self.clock["title"],
                    self.clock["artist"],
                    self.clock["album"],
                    self.clock["duration"],
                )
            return

        session = self.active_session
        if not session:
            lang = self.settings.data.get("language", "en")
            await self.broadcast({"type": "notice", "text": tr(lang, "noPlayerNotice")})
            return

        try:
            if cmd == "toggle":
                await session.try_toggle_play_pause_async()
                self._wake_event.set()

            elif cmd == "next":
                await session.try_skip_next_async()
                self._wake_event.set()

            elif cmd == "prev":
                cur_pos = self.get_clock_pos()
                if cur_pos > 3.5:
                    ok = await session.try_change_playback_position_async(0)
                    if ok:
                        now_mono = time.monotonic()
                        self.clock["anchor_pos"] = 0.0
                        self.clock["anchor_mono"] = now_mono
                        self.clock["last_raw_pos"] = 0.0
                        await self.broadcast(
                            {"type": "seek", "position": 0.0, "playing": self.clock["playing"]}
                        )
                        return
                await session.try_skip_previous_async()
                self._wake_event.set()

            elif cmd in ("seek", "seek_rel"):
                dur = self.clock["duration"] if self.clock["duration"] > 1.0 else 0.0
                if cmd == "seek":
                    target = float(data.get("position", 0.0))
                else:
                    target = self.get_clock_pos() + float(data.get("delta", 0.0))

                target = max(0.0, min(dur, target)) if dur > 0 else max(0.0, target)
                ticks = int(target * 10_000_000)
                ok = await session.try_change_playback_position_async(ticks)
                if ok:
                    now_mono = time.monotonic()
                    self.clock["anchor_pos"] = target
                    self.clock["anchor_mono"] = now_mono
                    self.clock["last_raw_pos"] = target
                    await self.broadcast(
                        {
                            "type": "seek",
                            "position": round(target, 3),
                            "playing": self.clock["playing"],
                        }
                    )
                else:
                    lang = self.settings.data.get("language", "en")
                    await self.broadcast(
                        {"type": "notice", "text": tr(lang, "seekUnsupported")}
                    )
        except Exception as exc:
            log.debug("Medya komutu başarısız (%s): %s", cmd, exc)

    # --- Main SMTC Media Loop ---
    async def media_loop(self) -> None:
        self._loop = asyncio.get_running_loop()
        if not WINRT_AVAILABLE:
            log.warning("winrt kütüphanesi bulunamadı — yalnızca sunucu & demo modu aktif.")
            while True:
                await asyncio.sleep(5.0)

        try:
            self.manager = await MediaManager.request_async()
            self.manager.add_sessions_changed(self._signal_wake)
            self.manager.add_current_session_changed(self._signal_wake)
        except Exception as exc:
            log.error("Windows SMTC başlatılamadı: %s", exc)
            while True:
                await asyncio.sleep(5.0)

        last_heartbeat = 0.0
        last_sessions_sig = ""
        is_initial_sync = True

        while True:
            try:
                session = self._list_and_pick_session()
                new_sid = (session.source_app_user_model_id or "") if session else None
                if new_sid != self._active_session_id or (session is None) != (self.active_session is None):
                    self._attach_session_listeners(session)

                sessions_sig = json.dumps(self.available_sessions, sort_keys=True)
                if sessions_sig != last_sessions_sig:
                    last_sessions_sig = sessions_sig
                    await self.broadcast({"type": "sessions", "sessions": self.available_sessions})

                if not session:
                    if self.clock["active"]:
                        self._generation += 1
                        if self._lyrics_task and not self._lyrics_task.done():
                            self._lyrics_task.cancel()
                        self.clock.update(
                            {
                                "active": False,
                                "track_id": None,
                                "title": "",
                                "artist": "",
                                "album": "",
                                "source_id": "",
                                "source_name": "",
                                "cover": None,
                                "accent": None,
                                "duration": 0.0,
                                "lyrics": [],
                                "lyrics_status": "idle",
                                "lyrics_mode": "none",
                                "playing": False,
                                "anchor_pos": 0.0,
                            }
                        )
                        await self.broadcast({"type": "idle", "sessions": self.available_sessions})
                    is_initial_sync = False
                else:
                    props = await session.try_get_media_properties_async()
                    title = (props.title or "").strip() if props else ""
                    artist = (props.artist or "").strip() if props else ""
                    album = (props.album_title or "").strip() if props else ""
                    source_id = session.source_app_user_model_id or ""
                    source_name = friendly_app_name(source_id)

                    if title:
                        track_id = f"{artist} - {title}" if artist else title
                        timeline = session.get_timeline_properties()
                        playback = session.get_playback_info()
                        now_mono = time.monotonic()

                        duration = max(0.0, timeline.end_time.total_seconds())
                        playing = playback.playback_status == PlaybackStatus.PLAYING

                        # === NEW TRACK ===
                        if track_id != self.clock["track_id"] or not self.clock["active"]:
                            est_pos, raw_pos, upd_str = self.compute_timeline_pos(
                                timeline,
                                playing,
                                duration,
                                is_new_track=True,
                                is_initial_sync=is_initial_sync,
                            )
                            is_initial_sync = False

                            # Extract or load cached album cover + accent color
                            if track_id in self._thumb_cache:
                                cover, accent = self._thumb_cache[track_id]
                                self._thumb_cache.move_to_end(track_id)
                            else:
                                cover, accent = await extract_thumbnail(props.thumbnail)
                                self._thumb_cache[track_id] = (cover, accent)
                                if len(self._thumb_cache) > 50:
                                    self._thumb_cache.popitem(last=False)

                            self._generation += 1
                            self.clock.update(
                                {
                                    "active": True,
                                    "track_id": track_id,
                                    "title": title,
                                    "artist": artist,
                                    "album": album,
                                    "source_id": source_id,
                                    "source_name": source_name,
                                    "cover": cover,
                                    "accent": accent,
                                    "duration": duration,
                                    "playing": playing,
                                    "anchor_pos": est_pos,
                                    "anchor_mono": now_mono,
                                    "last_raw_pos": raw_pos,
                                    "last_updated": upd_str,
                                    "lyrics": [],
                                    "lyrics_status": "loading",
                                    "lyrics_mode": "none",
                                }
                            )

                            log.info("Yeni şarkı [%s]: %s (%ds)", source_name, track_id, int(duration))
                            # Broadcast immediately so UI updates instantly (0ms lag!)
                            await self.broadcast(self.build_track_payload())
                            last_heartbeat = now_mono

                            # Fetch lyrics asynchronously in background
                            self._spawn_lyrics_fetch(
                                self._generation, track_id, title, artist, album, duration
                            )

                        # === SAME TRACK CONTINUING ===
                        else:
                            is_initial_sync = False
                            if duration > 5.0 and abs(duration - self.clock["duration"]) > 1.0:
                                self.clock["duration"] = duration

                            est_pos, raw_pos, upd_str = self.compute_timeline_pos(
                                timeline, playing, self.clock["duration"]
                            )
                            raw_changed = abs(raw_pos - self.clock["last_raw_pos"]) > 0.12
                            upd_changed = upd_str != self.clock["last_updated"]
                            if upd_changed:
                                self.clock["last_updated"] = upd_str

                            cur = self.get_clock_pos()

                            # 1) Play / Pause state transition
                            if playing != self.clock["playing"]:
                                if raw_changed or upd_changed:
                                    cur = est_pos
                                    self.clock["last_raw_pos"] = raw_pos
                                self.clock["anchor_pos"] = cur
                                self.clock["anchor_mono"] = now_mono
                                self.clock["playing"] = playing
                                await self.broadcast(
                                    {
                                        "type": "playstate",
                                        "playing": playing,
                                        "position": round(cur, 3),
                                    }
                                )

                            # 2) Loop / Repeat restart detection
                            elif upd_changed and raw_pos < 2.5 and cur > 8.0:
                                self.clock["anchor_pos"] = est_pos
                                self.clock["anchor_mono"] = now_mono
                                self.clock["last_raw_pos"] = raw_pos
                                await self.broadcast(
                                    {
                                        "type": "seek",
                                        "position": round(est_pos, 3),
                                        "playing": playing,
                                    }
                                )

                            # 3) External seek or timeline drift correction
                            elif raw_changed or upd_changed:
                                self.clock["last_raw_pos"] = raw_pos
                                diff = est_pos - cur
                                if abs(diff) > 1.6:
                                    self.clock["anchor_pos"] = est_pos
                                    self.clock["anchor_mono"] = now_mono
                                    await self.broadcast(
                                        {
                                            "type": "seek",
                                            "position": round(est_pos, 3),
                                            "playing": playing,
                                        }
                                    )
                                elif abs(diff) > 0.35:
                                    self.clock["anchor_pos"] = cur + diff * 0.5
                                    self.clock["anchor_mono"] = now_mono

                            # 4) 1-second heartbeat broadcast
                            if now_mono - last_heartbeat >= 1.0:
                                last_heartbeat = now_mono
                                pos = self.get_clock_pos()
                                await self.broadcast(
                                    {
                                        "type": "heartbeat",
                                        "position": round(pos, 3),
                                        "playing": self.clock["playing"],
                                        "duration": (
                                            self.clock["duration"]
                                            if self.clock["duration"] > 1.0
                                            else 1.0
                                        ),
                                    }
                                )

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.debug("Medya döngüsü hatası: %s", exc)

            # Event-driven wait with gentle fallback poll
            wait_sec = 0.4 if self.clock["playing"] else 0.85
            self._wake_event.clear()
            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=wait_sec)
            except asyncio.TimeoutError:
                pass

    # --- HTTP & WebSocket Handlers ---
    async def handle_websocket(self, request: web.Request, ws: web.WebSocketResponse) -> web.WebSocketResponse:
        await ws.prepare(request)
        self.clients.add(ws)
        log.info("İstemci bağlandı (toplam: %d)", len(self.clients))
        try:
            await ws.send_str(json.dumps(self.build_init_payload(), ensure_ascii=False))
            if self.clock["active"] and self.clock["track_id"]:
                await ws.send_str(json.dumps(self.build_track_payload(), ensure_ascii=False))
            else:
                await ws.send_str(
                    json.dumps({"type": "idle", "sessions": self.available_sessions}, ensure_ascii=False)
                )

            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if isinstance(data, dict) and "cmd" in data:
                            await self.handle_client_command(data, ws)
                    except Exception as exc:
                        log.debug("WS mesaj ayrıştırma hatası: %s", exc)
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            self.clients.discard(ws)
            log.info("İstemci ayrıldı (kalan: %d)", len(self.clients))
        return ws

    async def handle_root(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=25.0)
        if ws.can_prepare(request).ok:
            return await self.handle_websocket(request, ws)
        index_path = BASE_DIR / "index.html"
        if not index_path.exists():
            return web.Response(status=404, text="index.html bulunamadı")
        return web.FileResponse(index_path)

    async def handle_ws_route(self, request: web.Request) -> web.StreamResponse:
        ws = web.WebSocketResponse(heartbeat=25.0)
        if ws.can_prepare(request).ok:
            return await self.handle_websocket(request, ws)
        return web.Response(status=400, text="WebSocket bağlantısı gerekli")

    async def handle_static(self, request: web.Request) -> web.StreamResponse:
        rel = request.match_info.get("filename", "")
        # Prevent path traversal
        candidate = (BASE_DIR / rel).resolve()
        if BASE_DIR not in candidate.parents or not candidate.is_file():
            return web.Response(status=404, text="Dosya bulunamadı")
        # Never expose python source or private data files over HTTP
        if candidate.suffix.lower() in {".py", ".vbs", ".bat"} or DATA_DIR in candidate.parents:
            return web.Response(status=403, text="Erişim engellendi")
        return web.FileResponse(candidate)

    async def handle_status(self, _request: web.Request) -> web.Response:
        return web.json_response(
            {
                "ok": True,
                "version": "2.0",
                "winrt": WINRT_AVAILABLE,
                "clients": len(self.clients),
                "cache_entries": len(self.cache),
                "active": self.clock["active"],
                "track": self.clock["track_id"],
                "source": self.clock["source_name"],
                "playing": self.clock["playing"],
                "position": round(self.get_clock_pos(), 2),
                "duration": round(self.clock["duration"], 2),
                "lyrics_status": self.clock["lyrics_status"],
                "lyrics_mode": self.clock["lyrics_mode"],
                "lyrics_count": len(self.clock["lyrics"]),
                "sessions": self.available_sessions,
            }
        )

    async def handle_get_settings(self, _request: web.Request) -> web.Response:
        return web.json_response(self.settings.data)

    async def handle_post_settings(self, request: web.Request) -> web.Response:
        try:
            patch = await request.json()
        except Exception:
            return web.json_response({"error": "Geçersiz JSON"}, status=400)
        if not isinstance(patch, dict):
            return web.json_response({"error": "Nesne bekleniyor"}, status=400)
        updated = self.settings.update(patch)
        await self.broadcast({"type": "settings", "settings": updated})
        return web.json_response(updated)

    @web.middleware
    async def cors_middleware(self, request: web.Request, handler: Any) -> web.StreamResponse:
        if request.method == "OPTIONS":
            resp: web.StreamResponse = web.Response(status=204)
        else:
            resp = await handler(request)
        if not isinstance(resp, web.WebSocketResponse):
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
            # Prevent stale browser/WebView2 cache on HTML, CSS, JS, and API responses
            if not request.path.lower().endswith((".mp4", ".webm", ".jpg", ".png", ".webp")):
                resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        return resp

    async def handle_get_locales(self, _request: web.Request) -> web.Response:
        return web.json_response(LOCALES)

    def create_app(self) -> web.Application:
        app = web.Application(middlewares=[self.cors_middleware])
        app.router.add_get("/", self.handle_root)
        app.router.add_get("/ws", self.handle_ws_route)
        app.router.add_get("/api/status", self.handle_status)
        app.router.add_get("/api/settings", self.handle_get_settings)
        app.router.add_post("/api/settings", self.handle_post_settings)
        app.router.add_get("/api/locales", self.handle_get_locales)
        app.router.add_get("/{filename:.+}", self.handle_static)
        app.on_startup.append(self._on_startup)
        app.on_cleanup.append(self._on_cleanup)
        return app

    def dispatch_command_threadsafe(self, data: dict[str, Any]) -> None:
        """Safely invoke a bridge command from another thread (e.g., native desktop tray)."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.handle_client_command(data), self._loop)

    def broadcast_threadsafe(self, message: dict[str, Any]) -> None:
        """Safely broadcast a JSON message to connected WebSocket clients from another thread."""
        if self._loop and not self._loop.is_closed() and self.clients:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)

    async def _on_startup(self, app: web.Application) -> None:
        self._loop = asyncio.get_running_loop()
        self.http_session = aiohttp.ClientSession()
        app["media_task"] = asyncio.create_task(self.media_loop())

    async def _on_cleanup(self, app: web.Application) -> None:
        task = app.get("media_task")
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if self._lyrics_task and not self._lyrics_task.done():
            self._lyrics_task.cancel()
        self._detach_session_listeners()
        for ws in list(self.clients):
            await ws.close()
        if self.http_session:
            await self.http_session.close()


SweaterBridge = LyricSkyBridge  # Backward-compatible alias


def main() -> None:
    svc = LyricSkyBridge()
    app = svc.create_app()
    log.info("LyricSky Bridge v2.0 starting...")
    log.info("  Wallpaper / Preview : http://%s:%d", HOST, PORT)
    log.info("  WebSocket Bridge    : ws://%s:%d", HOST, PORT)
    log.info("  Status API          : http://%s:%d/api/status", HOST, PORT)
    web.run_app(app, host=HOST, port=PORT, print=None)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("LyricSky Bridge stopped.")
