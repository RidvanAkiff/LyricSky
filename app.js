/* ==========================================================================
   LyricSky v2.0 — Live Constellation Lyrics Engine & Media Dock Controller
   ========================================================================== */

(() => {
  "use strict";

  // --------------------------------------------------------------------------
  // DOM References
  // --------------------------------------------------------------------------
  const $ = (id) => document.getElementById(id);

  const bgVideoA = $("bg-video-a");
  const bgVideoB = $("bg-video-b");
  const canvas = $("constellation");
  const ctx = canvas.getContext("2d");

  const clockWrap = $("clock-wrap");
  const dateEl = $("date");
  const timeMainEl = $("time-main");
  const timeSecEl = $("time-sec");

  const playerDock = $("player-dock");
  const coverImg = $("cover-img");
  const coverPlaceholder = $("cover-placeholder");
  const trackTitleEl = $("track-title");
  const trackArtistEl = $("track-artist");
  const statusDotEl = $("status-dot");
  const statusTextEl = $("status-text");
  const offsetBadgeEl = $("offset-badge");

  const progressHit = $("progress-hit");
  const progressFill = $("progress-fill");
  const progressThumb = $("progress-thumb");
  const compactProgressFill = $("compact-progress-fill");
  const scrubTooltip = $("scrub-tooltip");
  const timeElapsedEl = $("time-elapsed");
  const timeTotalEl = $("time-total");

  const btnPrev = $("btn-prev");
  const btnNext = $("btn-next");
  const btnToggle = $("btn-toggle");
  const btnBack10 = $("btn-back10");
  const btnFwd10 = $("btn-fwd10");
  const iconPlay = $("icon-play");
  const iconPause = $("icon-pause");

  const btnDemoQuick = $("btn-demo-quick");
  const btnDemoPanel = $("btn-demo-panel");
  const demoCtaLabel = $("demo-cta-label");
  const btnSettings = $("btn-settings");
  const btnCloseSettings = $("btn-close-settings");
  const settingsPanel = $("settings-panel");
  const settingsConnLabel = $("settings-conn-label");
  const btnOffsetReset = $("btn-offset-reset");
  const btnRefetch = $("btn-refetch");
  const langSelect = $("lang-select");
  const sessionSelect = $("session-select");

  const optSpotifyCard = $("opt-spotifycard");
  const optSideFeed = $("opt-sidefeed");
  const optWhisper = $("opt-whisper");
  const optDust = $("opt-dust");
  const optClock = $("opt-clock");
  const optSeconds = $("opt-seconds");
  const optAutofade = $("opt-autofade");
  const optCompact = $("opt-compact");
  const optIcons = $("opt-icons");
  const optLife = $("opt-life");
  const optBrightness = $("opt-brightness");
  const optGrayscale = $("opt-grayscale");
  const valLife = $("val-life");
  const valBrightness = $("val-brightness");
  const valGrayscale = $("val-grayscale");

  const spotifyStageEl = $("spotify-stage");
  const spAmbientBgEl = $("sp-ambient-bg");
  const spBrandTextEl = $("sp-brand-text");
  const spStateLabelEl = $("sp-state-label");
  const spCoverImgEl = $("sp-cover-img");
  const spArtPlaceholderEl = $("sp-art-placeholder");
  const spTitleEl = $("sp-title");
  const spArtistEl = $("sp-artist");
  const spAlbumEl = $("sp-album");
  const spProgressFillEl = $("sp-progress-fill");
  const spTimeCurEl = $("sp-time-cur");
  const spTimeDurEl = $("sp-time-dur");

  const lyricFeedEl = $("lyric-feed");
  const lyricFeedListEl = $("lyric-feed-list");
  const whisperEl = $("lyric-whisper");
  const noticeEl = $("notice");

  // --------------------------------------------------------------------------
  // State & Settings
  // --------------------------------------------------------------------------
  const DEFAULT_SETTINGS = {
    language: "en",
    theme: "overcast",
    showClock: true,
    showSeconds: false,
    use24Hour: true,
    clockScale: 1.0,
    showWhisper: false,
    showSideFeed: true,
    showSpotifyCard: true,
    showDust: true,
    reticleStyle: "crosshair",
    nodeLifeSec: 13,
    maxNodes: 12,
    autoFadeDock: false,
    compactDock: false,
    videoBrightness: 0.72,
    videoGrayscale: 100,
    videoBlur: 0,
    preferredSession: "auto",
    offsets: {},
  };

  // Built-in English fallback dictionary; full 12-language pack is loaded from /api/locales
  const FALLBACK_EN = {
    name: "English",
    locale: "en-US",
    rtl: false,
    appTitle: "LyricSky — Live Lyrics Desktop",
    settingsTitle: "Appearance & Settings",
    connWaiting: "Waiting for LyricSky bridge...",
    connConnected: "Bridge connected (localhost:8765)",
    connDemo: "Preview mode active",
    connBridgeDemo: "Bridge connected (Preview active)",
    close: "Close",
    languageLabel: "Language",
    themeLabel: "Atmosphere Theme",
    sourceAuto: "Automatic (Spotify priority)",
    sourcePlayingTag: "Playing",
    demoStart: "Start Animation Preview",
    demoStop: "Stop Animation Preview",
    demoStarted: "Animation preview started",
    demoBuiltInNotice: "Using built-in preview lyrics",
    demoStatus: "Preview · Synced demo",
    demoTrackTitle: "Cloudline (Preview)",
    demoTrackArtist: "LyricSky Studio",
    demoTrackAlbum: "Live Constellation Demo",
    idleTitle: "No music playing",
    idleSubtitle: "Play a song on Spotify or any media app",
    waitingBridgeTitle: "Waiting for connection...",
    waitingBridgeSubtitle: "Syncs automatically when a song starts",
    statusOffline: "Bridge offline",
    statusWaitingMedia: "Connected · Waiting for media",
    statusSearchingLyrics: "Searching lyrics...",
    statusWordSync: "Word-by-word sync",
    statusLineSync: "Line-synced lyrics",
    statusSynced: "Synced lyrics",
    statusNoLyrics: "No synced lyrics found",
    spotifyCardBrand: "Spotify",
    spotifyPlayingOn: "Playing on Spotify",
    nowPlayingOn: "{source} · Now Playing",
    stateReady: "Ready",
    statePlaying: "Playing",
    statePaused: "Paused",
    spotifyIdleTitle: "Waiting for Spotify",
    spotifyIdleSubtitle: "Your current track will appear here",
    unknownTrack: "Unknown Track",
    unknownArtist: "Unknown Artist",
    sourceNotice: "Source: {name}",
    refetchNotice: "Searching lyrics again...",
    bridgeOfflineNotice: "Bridge is not connected",
  };

  let localesMap = { en: FALLBACK_EN };
  let lastSessionsList = [];

  function getLangPack() {
    const code = settings.language || "en";
    return localesMap[code] || localesMap.en || FALLBACK_EN;
  }

  function t(key, vars = null) {
    const pack = getLangPack();
    let str = pack[key] !== undefined ? pack[key] : (FALLBACK_EN[key] !== undefined ? FALLBACK_EN[key] : key);
    if (vars && typeof str === "string") {
      for (const [k, v] of Object.entries(vars)) {
        str = str.replaceAll(`{${k}}`, String(v));
      }
    }
    return str;
  }

  function populateLanguageSelect() {
    if (!langSelect) return;
    const codes = Object.keys(localesMap);
    langSelect.innerHTML = "";
    for (const code of codes) {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = localesMap[code].name || code.toUpperCase();
      langSelect.appendChild(opt);
    }
    if (localesMap[settings.language]) {
      langSelect.value = settings.language;
    }
  }

  function applyLanguageToDOM() {
    const pack = getLangPack();
    const langCode = settings.language || "en";
    document.documentElement.lang = langCode;
    document.title = t("appTitle");
    document.body.classList.toggle("is-rtl", !!pack.rtl);

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.getAttribute("data-i18n-title");
      if (key) el.title = t(key);
    });

    demoCtaLabel.textContent = isDemoMode ? t("demoStop") : t("demoStart");
    if (langSelect && localesMap[langCode]) {
      langSelect.value = langCode;
    }

    updateClock();
    updateSessionsDropdown(lastSessionsList);
    updateSpotifyStageState();
    updateStatusUI();
    if (!hasActiveTrack && !isDemoMode) {
      trackTitleEl.textContent = wsConnected ? t("idleTitle") : t("waitingBridgeTitle");
      trackArtistEl.textContent = wsConnected ? t("idleSubtitle") : t("waitingBridgeSubtitle");
      updateSpotifyTrackMeta(t("spotifyIdleTitle"), t("spotifyIdleSubtitle"), "");
    }
  }

  async function loadLocalesPack() {
    const urls =
      window.location.protocol === "http:" || window.location.protocol === "https:"
        ? ["/api/locales", "locales.json"]
        : ["locales.json"];
    for (const u of urls) {
      try {
        const resp = await fetch(u, { cache: "no-store" });
        if (resp.ok) {
          const data = await resp.json();
          if (data && typeof data === "object" && data.en) {
            localesMap = data;
            populateLanguageSelect();
            applyLanguageToDOM();
            return;
          }
        }
      } catch {}
    }
    populateLanguageSelect();
    applyLanguageToDOM();
  }

  let settings = loadLocalSettings();

  let wsSocket = null;
  let wsConnected = false;
  let reconnectDelay = 1200;
  let reconnectTimer = null;

  let isDemoMode = false;
  let isPlaying = false;
  let showRemainingTime = false;
  let hasActiveTrack = false;
  let currentTrackKey = "";
  let currentSourceName = "";
  let currentLyricsStatus = "idle"; // idle | loading | ready | none
  let currentLyricsMode = "none";   // synced | estimated | none
  let manualOffsetSec = 0.0;

  let trackDuration = 1.0;
  let baseTrackTime = 0.0;
  let basePerfTime = performance.now();

  let rawLines = [];
  let wordQueue = [];
  let nextWordIdx = 0;
  let currentWhisperText = "";

  // Scrubber drag state
  let isScrubbing = false;
  let scrubRatio = 0;

  // Dynamic theme accent RGB for canvas rendering
  let accentRGB = [255, 255, 255];
  let albumAccentHex = "#d8e4f5";
  let albumAccentRGB = [216, 228, 245];

  // Auto-fade timer
  let idleFadeTimer = null;

  // --------------------------------------------------------------------------
  // Built-in Demo Preview Track (Always available offline or online)
  // --------------------------------------------------------------------------
  const DEMO_COVER_SVG =
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 240">
        <defs>
          <radialGradient id="g" cx="45%" cy="35%" r="70%">
            <stop offset="0%" stop-color="#8b96a8"/>
            <stop offset="55%" stop-color="#2c323d"/>
            <stop offset="100%" stop-color="#0d1016"/>
          </radialGradient>
        </defs>
        <rect width="240" height="240" fill="url(#g)"/>
        <g stroke="#ffffff" stroke-opacity="0.45" stroke-width="1.2" fill="none">
          <path d="M55 150 L98 102 L144 124 L182 76"/>
          <circle cx="182" cy="76" r="14" stroke-opacity="0.8"/>
          <line x1="173" y1="76" x2="191" y2="76" stroke-opacity="0.7"/>
          <line x1="182" y1="67" x2="182" y2="85" stroke-opacity="0.7"/>
        </g>
        <g fill="#ffffff">
          <circle cx="55" cy="150" r="3" opacity="0.7"/>
          <circle cx="98" cy="102" r="3.5" opacity="0.85"/>
          <circle cx="144" cy="124" r="3" opacity="0.75"/>
          <circle cx="182" cy="76" r="4"/>
        </g>
      </svg>`
    );

  const DEMO_TRACK = {
    track_id: "LyricSky Studio - Cloudline (Demo)",
    title: "Cloudline (Preview)",
    artist: "LyricSky Studio",
    source_name: "Demo",
    cover: DEMO_COVER_SVG,
    accent: "#b9d4f8",
    duration: 42.0,
    lyrics: [
      { time: 0.4, end: 4.1, text: "Grey clouds drifting slow across the midnight glass" },
      { time: 4.5, end: 8.6, text: "Every quiet syllable turns into silver starlight" },
      { time: 9.1, end: 13.4, text: "Cold air on the window while the city fades away" },
      { time: 13.9, end: 18.2, text: "Tracing constellations in the static of the sky" },
      { time: 19.6, end: 23.8, text: "Bulutların arasından süzülen sessiz bir gece" },
      { time: 24.3, end: 28.6, text: "Her kelime gökyüzünde ince bir yıldıza dönüşür" },
      { time: 29.2, end: 33.6, text: "Hold the moment steady before the winter wind arrives" },
      { time: 34.2, end: 39.4, text: "We are only shadows drawn in light across the dark" },
    ],
  };

  // --------------------------------------------------------------------------
  // Utility Helpers
  // --------------------------------------------------------------------------
  function hexToRgb(hex) {
    if (!hex || typeof hex !== "string") return [216, 228, 245];
    const clean = hex.replace("#", "").trim();
    if (clean.length !== 6) return [216, 228, 245];
    const n = parseInt(clean, 16);
    if (Number.isNaN(n)) return [216, 228, 245];
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function clamp(v, lo, hi) {
    return Math.min(hi, Math.max(lo, v));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function easeOutCubic(t) {
    const k = 1 - clamp(t, 0, 1);
    return 1 - k * k * k;
  }

  function easeOutBack(t) {
    const x = clamp(t, 0, 1);
    const c1 = 1.45;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
  }

  function fmtTime(sec) {
    const s = Math.max(0, Math.floor(sec));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  }

  function loadLocalSettings() {
    try {
      const raw = localStorage.getItem("lyricsky_settings_v2");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === "object") {
          return {
            ...DEFAULT_SETTINGS,
            ...parsed,
            offsets: { ...(parsed.offsets || {}) },
          };
        }
      }
    } catch {}
    return { ...DEFAULT_SETTINGS, offsets: {} };
  }

  function saveLocalSettings() {
    try {
      localStorage.setItem("lyricsky_settings_v2", JSON.stringify(settings));
    } catch {}
  }

  // --------------------------------------------------------------------------
  // Notice Toast
  // --------------------------------------------------------------------------
  let noticeTimer = null;
  function showNotice(text, ms = 2500) {
    if (!text) return;
    noticeEl.textContent = text;
    noticeEl.classList.add("visible");
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => {
      noticeEl.classList.remove("visible");
    }, ms);
  }

  // --------------------------------------------------------------------------
  // Seamless Dual-Deck Crossfade Video Looper (Zero Black Frames Forever)
  // --------------------------------------------------------------------------
  const videoLooper = {
    active: bgVideoA,
    standby: bgVideoB,
    crossfading: false,
    trimStart: 1.15, // Skips baked-in black fade-in (0.00s..1.00s) of clouds.mp4
    trimEnd: 14.35,  // Ends BEFORE baked-in black fade-out (14.58s..15.41s)
    crossfadeSec: 2.35,
    initialized: false,
    failed: false,
  };

  function configureVideoBounds(dur) {
    if (!Number.isFinite(dur) || dur < 2.5) return;
    if (dur > 10.0) {
      videoLooper.trimStart = Math.min(1.15, dur * 0.08);
      videoLooper.trimEnd = Math.max(videoLooper.trimStart + 3.5, dur - 1.08);
    } else {
      videoLooper.trimStart = Math.min(0.35, dur * 0.06);
      videoLooper.trimEnd = Math.max(videoLooper.trimStart + 1.4, dur - 0.45);
    }
    videoLooper.crossfadeSec = Math.min(2.35, (videoLooper.trimEnd - videoLooper.trimStart) * 0.24);
  }

  function initVideoLooper() {
    if (videoLooper.initialized || videoLooper.failed) return;
    if (!bgVideoA || !bgVideoB) return;
    if (bgVideoA.readyState < 1) return;

    configureVideoBounds(bgVideoA.duration);
    videoLooper.initialized = true;

    const a = videoLooper.active;
    const b = videoLooper.standby;

    try { a.currentTime = videoLooper.trimStart; } catch {}
    a.style.zIndex = "0";
    a.style.opacity = "1";
    a.play().catch(() => {});

    b.pause();
    try { b.currentTime = videoLooper.trimStart; } catch {}
    b.style.zIndex = "0";
    b.style.opacity = "0";
  }

  function tickVideoCrossfade() {
    if (videoLooper.failed) return;
    if (!videoLooper.initialized) {
      initVideoLooper();
      return;
    }

    const active = videoLooper.active;
    const standby = videoLooper.standby;

    if (active.paused && !videoLooper.crossfading) {
      active.play().catch(() => {});
    }

    // Never allow active deck to display dark head frames
    if (active.currentTime < videoLooper.trimStart - 0.2 && !videoLooper.crossfading) {
      try { active.currentTime = videoLooper.trimStart; } catch {}
    }

    const handoffStart = videoLooper.trimEnd - videoLooper.crossfadeSec;

    if (!videoLooper.crossfading && active.currentTime >= handoffStart) {
      videoLooper.crossfading = true;
      if (Math.abs(standby.currentTime - videoLooper.trimStart) > 0.25) {
        try { standby.currentTime = videoLooper.trimStart; } catch {}
      }
      standby.style.zIndex = "1";
      standby.style.opacity = "0";
      active.style.zIndex = "0";
      active.style.opacity = "1";
      standby.play().catch(() => {});
    }

    if (videoLooper.crossfading) {
      // Track smooth progress using both active deck and incoming deck for resilience
      const progActive = (active.currentTime - handoffStart) / Math.max(0.2, videoLooper.crossfadeSec);
      const progStandby = (standby.currentTime - videoLooper.trimStart) / Math.max(0.2, videoLooper.crossfadeSec);
      const rawT = clamp(Math.max(progActive, progStandby), 0, 1);
      // Smoothstep S-curve: incoming fades 0->1 OVER fully opaque active (zero brightness dip!)
      const t = rawT * rawT * (3 - 2 * rawT);
      standby.style.opacity = t.toFixed(4);

      if (rawT >= 1.0 || active.ended || active.currentTime >= videoLooper.trimEnd) {
        standby.style.opacity = "1";
        standby.style.zIndex = "0";

        // Hide and pre-cue old deck silently behind the now-active deck
        active.pause();
        active.style.opacity = "0";
        active.style.zIndex = "0";
        try { active.currentTime = videoLooper.trimStart; } catch {}

        videoLooper.active = standby;
        videoLooper.standby = active;
        videoLooper.crossfading = false;
      }
    }
  }

  bgVideoA.addEventListener("loadedmetadata", initVideoLooper);
  bgVideoA.addEventListener("canplay", initVideoLooper);
  bgVideoB.addEventListener("loadedmetadata", () => {
    if (videoLooper.initialized && !videoLooper.crossfading && videoLooper.standby === bgVideoB) {
      try { bgVideoB.currentTime = videoLooper.trimStart; } catch {}
    }
  });
  bgVideoA.addEventListener("error", () => {
    videoLooper.failed = true;
    bgVideoA.style.opacity = "0";
    bgVideoB.style.opacity = "0";
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && videoLooper.initialized) {
      const a = videoLooper.active;
      if (a.currentTime >= videoLooper.trimEnd - 0.1 || a.currentTime < videoLooper.trimStart) {
        try { a.currentTime = videoLooper.trimStart; } catch {}
      }
      a.play().catch(() => {});
    }
  });

  // --------------------------------------------------------------------------
  // Top Lockscreen Clock
  // --------------------------------------------------------------------------
  function updateClock() {
    const now = new Date();
    let h = now.getHours();
    let suffix = "";
    if (!settings.use24Hour) {
      suffix = h >= 12 ? " PM" : " AM";
      h = h % 12 || 12;
    }
    const hh = String(h).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");

    timeMainEl.textContent = `${hh}:${mm}`;
    timeSecEl.textContent = settings.showSeconds ? `:${ss}${suffix}` : suffix;

    const dateLocale = getLangPack().locale || "en-US";
    try {
      dateEl.textContent = now.toLocaleDateString(dateLocale, {
        day: "numeric",
        month: "long",
        weekday: "long",
      });
    } catch {
      dateEl.textContent = now.toLocaleDateString("en-US", {
        day: "numeric",
        month: "long",
        weekday: "long",
      });
    }
  }
  setInterval(updateClock, 1000);
  updateClock();

  // --------------------------------------------------------------------------
  // Apply Settings to DOM & CSS Variables
  // --------------------------------------------------------------------------
  function syncAccentRGB() {
    const theme = settings.theme || "overcast";
    if (theme === "midnight") {
      accentRGB = [197, 222, 255];
    } else if (theme === "dusk") {
      accentRGB = [247, 223, 194];
    } else if (theme === "ambient") {
      accentRGB = albumAccentRGB;
    } else {
      accentRGB = [255, 255, 255];
    }
  }

  function applyAlbumAccent(hex) {
    albumAccentHex = hex || "#d8e4f5";
    albumAccentRGB = hexToRgb(albumAccentHex);
    const root = document.documentElement.style;
    root.setProperty("--album-accent", albumAccentHex);
    root.setProperty("--album-accent-rgb", albumAccentRGB.join(", "));
    syncAccentRGB();
  }

  function applySettingsToUI() {
    const root = document.documentElement.style;
    document.body.dataset.theme = settings.theme || "overcast";
    document.body.classList.toggle("hide-clock", !settings.showClock);
    document.body.classList.toggle("hide-whisper", !settings.showWhisper);
    document.body.classList.toggle("hide-sidefeed", !settings.showSideFeed);
    document.body.classList.toggle("hide-spotifycard", !settings.showSpotifyCard);
    document.body.classList.toggle("compact-dock", !!settings.compactDock);

    root.setProperty("--vid-brightness", String(settings.videoBrightness));
    root.setProperty("--vid-grayscale", `${settings.videoGrayscale}%`);
    root.setProperty("--vid-blur", `${settings.videoBlur || 0}px`);
    root.setProperty("--clock-scale", String(settings.clockScale || 1));

    syncAccentRGB();
    applyLanguageToDOM();

    // Sync Settings Popover controls
    document.querySelectorAll("#theme-grid .theme-chip").forEach((el) => {
      el.classList.toggle("active", el.dataset.themeVal === settings.theme);
    });
    document.querySelectorAll("#reticle-group .seg-btn").forEach((el) => {
      el.classList.toggle("active", el.dataset.reticle === settings.reticleStyle);
    });

    if (optSpotifyCard) optSpotifyCard.checked = !!settings.showSpotifyCard;
    optSideFeed.checked = !!settings.showSideFeed;
    optWhisper.checked = !!settings.showWhisper;
    optDust.checked = !!settings.showDust;
    optClock.checked = !!settings.showClock;
    optSeconds.checked = !!settings.showSeconds;
    optAutofade.checked = !!settings.autoFadeDock;
    optCompact.checked = !!settings.compactDock;

    optLife.value = String(settings.nodeLifeSec);
    valLife.textContent = `${settings.nodeLifeSec}s`;

    optBrightness.value = String(settings.videoBrightness);
    valBrightness.textContent = `${Math.round(settings.videoBrightness * 100)}%`;

    optGrayscale.value = String(settings.videoGrayscale);
    valGrayscale.textContent = `${Math.round(settings.videoGrayscale)}%`;

    if (sessionSelect.querySelector(`option[value="${CSS.escape(settings.preferredSession)}"]`)) {
      sessionSelect.value = settings.preferredSession;
    }

    if (!settings.autoFadeDock) {
      document.body.classList.remove("dock-faded");
      clearTimeout(idleFadeTimer);
    } else {
      resetIdleFade();
    }
  }

  function updateSettings(patch, pushToBridge = true) {
    settings = { ...settings, ...patch };
    saveLocalSettings();
    applySettingsToUI();
    if (pushToBridge && wsConnected) {
      sendCmd({ cmd: "update_settings", settings: patch });
    }
  }

  // Auto-fade dock after pointer inactivity
  function resetIdleFade() {
    document.body.classList.remove("dock-faded");
    clearTimeout(idleFadeTimer);
    if (!settings.autoFadeDock) return;
    idleFadeTimer = setTimeout(() => {
      if (!document.body.classList.contains("settings-open")) {
        document.body.classList.add("dock-faded");
      }
    }, 4200);
  }

  window.addEventListener("pointermove", resetIdleFade, { passive: true });
  window.addEventListener("pointerdown", resetIdleFade, { passive: true });

  // --------------------------------------------------------------------------
  // Canvas Setup & Ambient Stardust
  // --------------------------------------------------------------------------
  let viewW = window.innerWidth;
  let viewH = window.innerHeight;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);

  const dustParticles = [];
  const DUST_COUNT = 44;

  function initDust() {
    dustParticles.length = 0;
    for (let i = 0; i < DUST_COUNT; i++) {
      dustParticles.push({
        x: Math.random() * viewW,
        y: Math.random() * viewH,
        r: 0.7 + Math.random() * 1.5,
        vx: (Math.random() - 0.5) * 7.5,
        vy: -2.0 - Math.random() * 6.5,
        phase: Math.random() * Math.PI * 2,
        speed: 0.6 + Math.random() * 1.3,
        baseAlpha: 0.1 + Math.random() * 0.28,
      });
    }
  }

  function resizeCanvas() {
    viewW = window.innerWidth;
    viewH = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(viewW * dpr);
    canvas.height = Math.round(viewH * dpr);
    canvas.style.width = `${viewW}px`;
    canvas.style.height = `${viewH}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (dustParticles.length === 0) initDust();
  }
  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();

  // --------------------------------------------------------------------------
  // Constellation Node Engine (Non-overlapping, Delta-Time, Smooth Reticle)
  // --------------------------------------------------------------------------
  const nodes = [];
  let nodeIdSeq = 0;

  const reticle = {
    x: viewW * 0.5,
    y: viewH * 0.48,
    vx: 0,
    vy: 0,
    alpha: 0,
    rot: 0,
    pulse: 0,
    initialized: false,
  };

  function getSafeBounds() {
    const padX = clamp(viewW * 0.11, 76, 180);
    let topY = viewH * 0.25;
    if (settings.showClock && clockWrap) {
      const cr = clockWrap.getBoundingClientRect();
      topY = Math.max(topY, cr.bottom + 52);
    } else {
      topY = clamp(viewH * 0.13, 68, 124);
    }

    // Reserve enough vertical space below star anchor for active 32px text (+60px)
    // plus orbital drift (+9px) and whisper lyric bar (~48px above dock)
    let botY = viewH * 0.65;
    if (playerDock) {
      const dr = playerDock.getBoundingClientRect();
      const whisperMargin = settings.showWhisper ? 132 : 96;
      botY = Math.min(botY, dr.top - whisperMargin);
    }

    if (botY - topY < 140) {
      topY = viewH * 0.22;
      botY = Math.max(topY + 140, viewH * 0.62);
    }
    return {
      minX: padX,
      maxX: Math.max(padX + 100, viewW - padX),
      minY: topY,
      maxY: botY,
    };
  }

  function measureWordBox(word) {
    ctx.save();
    ctx.font = `600 32px ${getComputedStyle(document.body).fontFamily}`;
    const w = ctx.measureText(word).width;
    ctx.restore();
    return { halfW: Math.max(36, w * 0.54 + 14), halfH: 30 };
  }

  function boxesOverlap(ax, ay, aBox, bx, by, bBox) {
    return (
      Math.abs(ax - bx) < aBox.halfW + bBox.halfW &&
      Math.abs(ay - by) < aBox.halfH + bBox.halfH
    );
  }

  function spawnWord(word, isLineStart = false) {
    const bounds = getSafeBounds();
    const box = measureWordBox(word);
    const minX = clamp(bounds.minX + box.halfW * 0.55, 50, viewW * 0.45);
    const maxX = clamp(bounds.maxX - box.halfW * 0.55, viewW * 0.55, viewW - 50);
    const minY = bounds.minY;
    const maxY = bounds.maxY;
    const centerX = (minX + maxX) * 0.5;
    const centerY = (minY + maxY) * 0.5;

    const activeNodes = nodes.filter((n) => !n.retiring);
    const prev = activeNodes.length > 0 ? activeNodes[activeNodes.length - 1] : null;
    const visibleForAvoid = nodes.filter((n) => n.currentAlpha > 0.14 || !n.retiring);

    let x, y;
    if (!prev) {
      x = centerX + (Math.random() - 0.5) * Math.min(180, (maxX - minX) * 0.3);
      y = centerY + (Math.random() - 0.5) * Math.min(90, (maxY - minY) * 0.3);
    } else {
      let best = null;
      let bestScore = -Infinity;
      const minDistPref = isLineStart ? 135 : 115;
      const maxDistPref = isLineStart ? 275 : 230;
      const prev2 = activeNodes.length > 1 ? activeNodes[activeNodes.length - 2] : null;
      const prevAngle = prev2 ? Math.atan2(prev.y - prev2.y, prev.x - prev2.x) : null;

      for (let i = 0; i < 44; i++) {
        const angle = Math.random() * Math.PI * 2;
        const dist = minDistPref + Math.random() * (maxDistPref - minDistPref);
        const cx = clamp(prev.x + Math.cos(angle) * dist, minX, maxX);
        const cy = clamp(prev.y + Math.sin(angle) * dist, minY, maxY);

        let score = 0;
        let minCenterDist = Infinity;
        let overlaps = 0;

        for (let j = 0; j < visibleForAvoid.length; j++) {
          const n = visibleForAvoid[j];
          const d = Math.hypot(cx - n.x, cy - n.y);
          if (d < minCenterDist) minCenterDist = d;

          const recency = (j + 1) / Math.max(1, visibleForAvoid.length);
          const alphaWeight = n.retiring ? Math.max(0.25, n.currentAlpha) : 1.0;
          if (boxesOverlap(cx, cy + 16, box, n.x, n.y + 14, n.box)) {
            overlaps += (1 + recency * 2) * alphaWeight;
          }
        }

        // Strongly penalize text overlap and cramped spacing
        score -= overlaps * 340;
        score += Math.min(minCenterDist, 230) * 1.15;

        // Softly avoid the bottom-left Spotify Now-Playing card & bottom-right lyric feed
        if (settings.showSpotifyCard && spotifyStageEl && viewW > 960) {
          const sr = spotifyStageEl.getBoundingClientRect();
          if (sr.width > 0 && cx - box.halfW < sr.right + 24 && cy + 62 > sr.top - 16) {
            score -= 480;
          }
        }
        if (settings.showSideFeed && lyricFeedEl && viewW > 820) {
          const fr = lyricFeedEl.getBoundingClientRect();
          if (fr.width > 0 && cx + box.halfW > fr.left - 24 && cy + 62 > fr.top - 16) {
            score -= 480;
          }
        }

        // Gentle pull back toward center if getting near viewport borders
        const distFromCenter = Math.hypot(
          (cx - centerX) / Math.max(1, (maxX - minX) * 0.5),
          (cy - centerY) / Math.max(1, (maxY - minY) * 0.5)
        );
        score -= distFromCenter * 42;

        // Prefer natural forward flow rather than sharp 180° U-turn directly onto prev2
        if (prevAngle !== null) {
          const candAngle = Math.atan2(cy - prev.y, cx - prev.x);
          const diff = Math.abs(Math.atan2(Math.sin(candAngle - prevAngle), Math.cos(candAngle - prevAngle)));
          if (diff > 2.55) score -= 55;
        }

        if (score > bestScore) {
          bestScore = score;
          best = { x: cx, y: cy };
        }
      }

      x = best.x;
      y = best.y;
    }

    // Build clean celestial links:
    // 1 primary spine link to immediate previous active word + up to 1 faint harmonic neighbor
    const links = [];
    if (prev) {
      links.push({
        target: prev,
        primary: true,
        softBridge: isLineStart,
        progress: 0,
      });
    }
    if (activeNodes.length >= 2) {
      let nearest = null;
      let nearestDist = 275;
      for (let i = Math.max(0, activeNodes.length - 6); i < activeNodes.length - 1; i++) {
        const cand = activeNodes[i];
        const d = Math.hypot(x - cand.x, y - cand.y);
        if (d > 85 && d < nearestDist) {
          nearestDist = d;
          nearest = cand;
        }
      }
      if (nearest) {
        links.push({
          target: nearest,
          primary: false,
          softBridge: false,
          progress: 0,
        });
      }
    }

    const node = {
      id: ++nodeIdSeq,
      word,
      x,
      y,
      originX: x,
      originY: y,
      box,
      links,
      age: 0,
      prominence: 1.0,
      spawnProgress: 0.0,
      retiring: false,
      retireAge: 0,
      retireDur: 3.4,
      retireStartAlpha: 1.0,
      currentAlpha: 0.0,
      driftPhaseX: Math.random() * Math.PI * 2,
      driftPhaseY: Math.random() * Math.PI * 2,
      driftSpeedX: 0.35 + Math.random() * 0.35,
      driftSpeedY: 0.3 + Math.random() * 0.32,
      driftAmpX: 4 + Math.random() * 6,
      driftAmpY: 3.5 + Math.random() * 5,
    };

    nodes.push(node);

    // NEVER hard-delete oldest node! Gracefully retire oldest active nodes so they fade slowly.
    const maxAllowed = clamp(Number(settings.maxNodes) || 12, 6, 20);
    let activeCount = activeNodes.length + 1;
    if (activeCount > maxAllowed) {
      for (const n of nodes) {
        if (!n.retiring && n !== node) {
          n.retiring = true;
          n.retireAge = 0;
          n.retireDur = 3.4;
          n.retireStartAlpha = Math.max(0.01, n.currentAlpha || 0.72);
          activeCount--;
          if (activeCount <= maxAllowed) break;
        }
      }
    }

    // Pure memory safety guard (only drops invisible/oldest if extreme burst > 56)
    while (nodes.length > 56) {
      nodes.shift();
    }

    if (!reticle.initialized) {
      reticle.x = x;
      reticle.y = y;
      reticle.vx = 0;
      reticle.vy = 0;
      reticle.initialized = true;
    }
    reticle.pulse = 1.0;
  }

  function clearConstellation(immediate = false) {
    if (immediate) {
      nodes.length = 0;
      reticle.initialized = false;
      reticle.alpha = 0;
    } else {
      // Softly melt existing words into the clouds instead of snapping them away
      for (const n of nodes) {
        if (!n.retiring) {
          n.retiring = true;
          n.retireAge = 0;
          n.retireDur = 1.35;
          n.retireStartAlpha = Math.max(0.01, n.currentAlpha || 0.6);
        } else {
          n.retireDur = Math.min(n.retireDur, n.retireAge + 1.1);
        }
      }
    }
    setWhisper("");
  }

  // --------------------------------------------------------------------------
  // Reticle Renderers (Crosshair / Orbital / Starburst)
  // --------------------------------------------------------------------------
  function drawReticle(x, y, alpha, rot, pulse) {
    if (alpha <= 0.01) return;
    const [r, g, b] = accentRGB;
    const style = settings.reticleStyle || "crosshair";
    const breathe = 1 + pulse * 0.22;

    ctx.save();
    ctx.translate(x, y);

    // Ambient soft radial glow behind the active star
    const halo = ctx.createRadialGradient(0, 0, 1, 0, 0, 28 * breathe);
    halo.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha * 0.34})`);
    halo.addColorStop(0.45, `rgba(${r}, ${g}, ${b}, ${alpha * 0.1})`);
    halo.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(0, 0, 28 * breathe, 0, Math.PI * 2);
    ctx.fill();

    if (style === "orbital") {
      // Minimalist dual orbital rings + tiny satellite
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.72})`;
      ctx.lineWidth = 1.15;
      ctx.beginPath();
      ctx.arc(0, 0, 13.5 * breathe, 0, Math.PI * 2);
      ctx.stroke();

      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.28})`;
      ctx.lineWidth = 0.9;
      ctx.beginPath();
      ctx.arc(0, 0, 20 * breathe, rot, rot + Math.PI * 1.4);
      ctx.stroke();

      const sx = Math.cos(rot * 1.7) * 13.5 * breathe;
      const sy = Math.sin(rot * 1.7) * 13.5 * breathe;
      ctx.fillStyle = `rgba(255, 255, 255, ${alpha * 0.95})`;
      ctx.beginPath();
      ctx.arc(sx, sy, 2.0, 0, Math.PI * 2);
      ctx.fill();
    } else if (style === "starburst") {
      // 4-point celestial diamond star
      ctx.rotate(rot * 0.25);
      const outer = 16 * breathe;
      const inner = 3.2;
      ctx.beginPath();
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4;
        const rad = i % 2 === 0 ? outer : inner;
        const px = Math.cos(a) * rad;
        const py = Math.sin(a) * rad;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.24})`;
      ctx.fill();
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.84})`;
      ctx.lineWidth = 1.1;
      ctx.stroke();
    } else {
      // Classic Sweater Weather Precision Astronomical Crosshair
      const radius = 13.5 * breathe;
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.8})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.stroke();

      // Precision ticks with subtle center aperture
      const innerGap = 4.6;
      const outerTick = radius + 4.2;
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.68})`;
      ctx.lineWidth = 1.1;
      ctx.beginPath();
      ctx.moveTo(-outerTick, 0); ctx.lineTo(-innerGap, 0);
      ctx.moveTo(innerGap, 0); ctx.lineTo(outerTick, 0);
      ctx.moveTo(0, -outerTick); ctx.lineTo(0, -innerGap);
      ctx.moveTo(0, innerGap); ctx.lineTo(0, outerTick);
      ctx.stroke();
    }

    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // Main 60-240Hz Render Loop
  // --------------------------------------------------------------------------
  let lastFrameNow = performance.now();

  function render(now) {
    const dt = clamp((now - lastFrameNow) / 1000, 0.001, 0.05);
    lastFrameNow = now;

    ctx.clearRect(0, 0, viewW, viewH);

    const [ar, ag, ab] = accentRGB;
    const lifeSec = clamp(Number(settings.nodeLifeSec) || 13, 6, 28);

    // 0) Advance zero-black-frame dual-deck video crossfade
    tickVideoCrossfade();

    // 1) Ambient Sky Stardust
    if (settings.showDust) {
      for (const p of dustParticles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.phase += p.speed * dt;
        if (p.y < -10) {
          p.y = viewH + 10;
          p.x = Math.random() * viewW;
        }
        if (p.x < -10) p.x = viewW + 10;
        if (p.x > viewW + 10) p.x = -10;

        const twinkle = 0.55 + 0.45 * Math.sin(p.phase);
        const a = p.baseAlpha * twinkle;
        ctx.fillStyle = `rgba(${ar}, ${ag}, ${ab}, ${a})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 2) Update Nodes (Delta-Time orbital drift, prominence, velvety slow fade-out)
    const timeSec = now / 1000;
    let latestActive = null;
    for (let i = nodes.length - 1; i >= 0; i--) {
      if (!nodes[i].retiring) {
        latestActive = nodes[i];
        break;
      }
    }

    const liveNodes = [];
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const isLatest = n === latestActive;

      // Freeze normal aging when paused so lyrics stay suspended cleanly in the clouds
      if (isPlaying) {
        n.age += dt;
      }
      n.spawnProgress = Math.min(1, n.spawnProgress + dt / 0.34);

      // Smoothly interpolate prominence (1 for latest word, softly settling to 0)
      const targetProm = isLatest ? 1.0 : 0.0;
      const decayRate = isLatest ? 11.0 : 4.2;
      n.prominence += (targetProm - n.prominence) * (1 - Math.exp(-dt * decayRate));

      // Gentle weightless orbital float anchored to origin
      n.x = n.originX + Math.sin(timeSec * n.driftSpeedX + n.driftPhaseX) * n.driftAmpX;
      n.y = n.originY + Math.cos(timeSec * n.driftSpeedY + n.driftPhaseY) * n.driftAmpY;

      for (const link of n.links) {
        link.progress = Math.min(1, link.progress + dt / 0.28);
      }

      // Compute velvety smooth opacity envelope
      const fadeIn = easeOutCubic(n.spawnProgress);
      const softStart = lifeSec * 0.32;
      const ageSpan = Math.max(1.0, lifeSec - softStart);
      const ageT = clamp((n.age - softStart) / ageSpan, 0, 1);
      // Gentle cosine-like softening across the node's entire lifespan
      const naturalFade = Math.pow(1 - ageT, 1.85);

      if (!n.retiring && n.age >= lifeSec) {
        n.retiring = true;
        n.retireAge = 0;
        n.retireDur = 2.6;
        n.retireStartAlpha = Math.max(0.01, n.currentAlpha || fadeIn * naturalFade);
      }

      if (n.retiring) {
        n.retireAge += dt;
        const rt = clamp(n.retireAge / Math.max(0.4, n.retireDur), 0, 1);
        // Velvety slow ease-out tail so text dissolves seamlessly into zero
        const dissolve = Math.pow(1 - rt, 2.35);
        n.currentAlpha = n.retireStartAlpha * dissolve;
      } else {
        n.currentAlpha = fadeIn * naturalFade;
      }

      // Keep node alive until it has completely melted into invisibility
      if (!n.retiring || n.currentAlpha > 0.002) {
        liveNodes.push(n);
      }
    }
    if (liveNodes.length !== nodes.length) {
      nodes.length = 0;
      nodes.push(...liveNodes);
    }

    const aliveSet = new Set(nodes);

    // 3) Draw Constellation Threads (Anchor-to-Anchor, Dissolving in Lockstep with Nodes)
    for (const n of nodes) {
      if (n.currentAlpha <= 0.003) continue;

      for (const link of n.links) {
        const target = link.target;
        if (!aliveSet.has(target) || target.currentAlpha <= 0.003) continue;
        const edgeAlpha = Math.min(n.currentAlpha, target.currentAlpha);
        if (edgeAlpha <= 0.003) continue;

        const prog = easeOutCubic(link.progress);
        const ex = lerp(target.x, n.x, prog);
        const ey = lerp(target.y, n.y, prog);

        const baseOp = link.primary ? (link.softBridge ? 0.22 : 0.42) : 0.14;
        const lineAlpha = edgeAlpha * baseOp;

        ctx.save();
        if (link.primary) {
          const grad = ctx.createLinearGradient(target.x, target.y, ex, ey);
          grad.addColorStop(0, `rgba(${ar}, ${ag}, ${ab}, ${lineAlpha * 0.55})`);
          grad.addColorStop(1, `rgba(${ar}, ${ag}, ${ab}, ${lineAlpha})`);
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.05;
        } else {
          ctx.strokeStyle = `rgba(${ar}, ${ag}, ${ab}, ${lineAlpha})`;
          ctx.lineWidth = 0.75;
        }
        ctx.beginPath();
        ctx.moveTo(target.x, target.y);
        ctx.lineTo(ex, ey);
        ctx.stroke();
        ctx.restore();
      }
    }

    // 4) Update & Draw Gliding Precision Reticle
    if (latestActive) {
      const stiffness = 135;
      const damping = 18.5;
      const ax = (latestActive.x - reticle.x) * stiffness - reticle.vx * damping;
      const ay = (latestActive.y - reticle.y) * stiffness - reticle.vy * damping;
      reticle.vx += ax * dt;
      reticle.vy += ay * dt;
      reticle.x += reticle.vx * dt;
      reticle.y += reticle.vy * dt;

      reticle.alpha += (latestActive.currentAlpha * 0.92 - reticle.alpha) * (1 - Math.exp(-dt * 8));
      reticle.rot += dt * 0.55;
      reticle.pulse = Math.max(0, reticle.pulse - dt * 2.4);

      drawReticle(reticle.x, reticle.y, reticle.alpha, reticle.rot, reticle.pulse);
    } else if (reticle.alpha > 0.003) {
      // Smoothly dissolve reticle when no active word remains
      reticle.alpha *= Math.exp(-dt * 2.2);
      drawReticle(reticle.x, reticle.y, reticle.alpha, reticle.rot, 0);
    }

    // 5) Draw Star Anchors & Smoothly Scaled Typography
    const fontFamily = getComputedStyle(document.body).fontFamily;

    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i];
      const alpha = n.currentAlpha;
      if (alpha <= 0.003) continue;

      const prom = n.prominence;
      const starRadius = lerp(2.2, 3.4, prom);

      // Star core dot right at constellation vertex (n.x, n.y)
      ctx.save();
      ctx.fillStyle = `rgba(${lerp(ar, 255, prom)}, ${lerp(ag, 255, prom)}, ${lerp(ab, 255, prom)}, ${alpha * lerp(0.68, 1.0, prom)})`;
      ctx.shadowColor = `rgba(${ar}, ${ag}, ${ab}, ${alpha * lerp(0.35, 0.85, prom)})`;
      ctx.shadowBlur = lerp(4, 14, prom);
      ctx.beginPath();
      ctx.arc(n.x, n.y, starRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // Word label smoothly positioned below anchor — zero overlap with constellation lines!
      const popScale = lerp(0.86, 1.0, easeOutBack(n.spawnProgress));
      const scale = lerp(0.46, 1.0, prom) * popScale;
      const textY = n.y + lerp(16, 28, prom);
      const textAlpha = alpha * lerp(0.55, 0.98, prom);

      ctx.save();
      ctx.translate(n.x, textY);
      ctx.scale(scale, scale);
      ctx.font = `600 32px ${fontFamily}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.shadowColor = `rgba(0, 0, 0, ${0.68 * alpha})`;
      ctx.shadowBlur = lerp(6, 20, prom);
      ctx.shadowOffsetY = 2;
      ctx.fillStyle = `rgba(${lerp(ar, 255, prom * 0.8)}, ${lerp(ag, 255, prom * 0.8)}, ${lerp(ab, 255, prom * 0.8)}, ${textAlpha})`;
      ctx.fillText(n.word, 0, 0);
      ctx.restore();
    }

    // 6) Advance synced lyrics, side sentence feed & playback UI
    tickPlaybackAndLyrics(now, dt);

    requestAnimationFrame(render);
  }

  // --------------------------------------------------------------------------
  // Universal All-Language Word Segmentation & Syllable-Weighted Timeline
  // --------------------------------------------------------------------------
  const NO_SPACE_SCRIPT_RE = /[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\u0e00-\u0e7f]/;
  const TRAILING_PUNCT_RE = /^[\.,!?;:…、。！？，；：」』）\)\]\}\"'”’~～]+$/;
  const wordSegmenter =
    typeof Intl !== "undefined" && typeof Intl.Segmenter === "function"
      ? new Intl.Segmenter(undefined, { granularity: "word" })
      : null;

  function segmentLineIntoWords(lineText) {
    const clean = (lineText || "").trim();
    if (!clean) return [];
    // Space-delimited languages (Turkish, English, Korean, Spanish, French, Russian, Arabic, etc.)
    if (!NO_SPACE_SCRIPT_RE.test(clean) || /\s/.test(clean)) {
      const spaceTokens = clean.split(/\s+/).filter(Boolean);
      // If mixed text still has long CJK chunk without spaces, segment that chunk cleanly
      const out = [];
      for (const tok of spaceTokens) {
        if (NO_SPACE_SCRIPT_RE.test(tok) && tok.length > 4 && wordSegmenter) {
          for (const seg of wordSegmenter.segment(tok)) {
            const s = seg.segment.trim();
            if (!s) continue;
            if (TRAILING_PUNCT_RE.test(s) && out.length > 0) out[out.length - 1] += s;
            else out.push(s);
          }
        } else {
          out.push(tok);
        }
      }
      return out;
    }

    // Pure CJK / Thai without spaces: use native Intl.Segmenter word boundaries
    if (wordSegmenter) {
      const tokens = [];
      for (const seg of wordSegmenter.segment(clean)) {
        const s = seg.segment.trim();
        if (!s) continue;
        if (TRAILING_PUNCT_RE.test(s) && tokens.length > 0) {
          tokens[tokens.length - 1] += s;
        } else {
          tokens.push(s);
        }
      }
      if (tokens.length > 0) return tokens;
    }

    // Fallback: group into short 2-3 char phrases
    return clean.match(/.{1,3}/g) || [clean];
  }

  function syllableWeight(word) {
    const raw = (word || "").trim();
    if (!raw) return 1;

    // 1) Korean Hangul: every Hangul block is exactly 1 syllable
    const hangul = raw.match(/[\uAC00-\uD7A3]/g);
    // 2) Japanese Kana & CJK Hanzi/Kanji: each character ~0.85-1.0 vocal beat
    const cjk = raw.match(/[\u3040-\u30FF\u3400-\u9FFF]/g);
    // 3) Cyrillic, Greek, Arabic, Hebrew, Devanagari, Thai scripts
    const cyrGreekVowels = raw.toLowerCase().match(/[аеёиоуыэюяαεηιουωάέήίόύώ]+/g);
    const rtlIndic = raw.match(/[\u0600-\u06FF\u0590-\u05FF\u0900-\u097F\u0E00-\u0E7F]/g);

    // 4) Latin + Turkish + European accented scripts via NFD decomposition
    const latinBase = raw
      .toLocaleLowerCase("tr-TR")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z\u0131]/g, "");
    const latinVowels = latinBase.match(/[aeiouy\u0131]+/g);

    let syl = 0;
    if (hangul) syl += hangul.length;
    if (cjk) syl += cjk.length * 0.9;
    if (cyrGreekVowels) syl += cyrGreekVowels.length;
    if (rtlIndic) syl += Math.max(1, rtlIndic.length * 0.45);
    if (latinVowels) syl += latinVowels.length;
    if (syl < 1) syl = Math.max(1, raw.length * 0.35);

    let pauseBonus = 0;
    if (/[.!?…。！？؟]$/.test(raw)) pauseBonus = 0.8;
    else if (/[,;:、，；：،]$/.test(raw)) pauseBonus = 0.5;
    return Math.max(1, syl) + pauseBonus;
  }

  function buildWordTimeline(lines) {
    rawLines = Array.isArray(lines) ? lines : [];
    wordQueue = [];
    resetSideFeed(false);
    let minTime = 0;

    for (let i = 0; i < rawLines.length; i++) {
      const line = rawLines[i];
      const lineText = (line.text || "").trim();

      // True word-level timestamps (Apple Music / Musixmatch / Enhanced LRC)
      if (Array.isArray(line.words) && line.words.length > 0) {
        line.words.forEach((w, wIdx) => {
          const t = Math.max(minTime, Number(w.time) || 0);
          wordQueue.push({
            time: t,
            word: w.word,
            lineIdx: i,
            isLineStart: wIdx === 0,
          });
          minTime = t + 0.035;
        });
        continue;
      }

      const start = Math.max(minTime, Number(line.time) || 0);
      const nextLineTime = i + 1 < rawLines.length ? Number(rawLines[i + 1].time) : start + 4.0;
      const explicitEnd = typeof line.end === "number" && line.end > start + 0.25 ? line.end : null;
      const effectiveEnd = explicitEnd ? Math.min(explicitEnd, nextLineTime) : nextLineTime;

      const words = segmentLineIntoWords(lineText);
      if (words.length === 0) continue;

      const gap = Math.max(0.35, effectiveEnd - start);
      const weights = words.map(syllableWeight);
      const totalW = weights.reduce((a, b) => a + b, 0);

      // Natural vocal pacing: don't stretch words across long instrumental solos
      const naturalSpan = totalW * 0.24;
      const span = Math.min(gap * 0.88, Math.max(0.45, naturalSpan));

      let cursor = start;
      words.forEach((w, idx) => {
        wordQueue.push({
          time: cursor,
          word: w,
          lineIdx: i,
          isLineStart: idx === 0,
        });
        cursor += (weights[idx] / totalW) * span;
      });

      minTime = Math.min(cursor, nextLineTime - 0.04);
    }

    nextWordIdx = 0;
  }

  function getRawTrackSec(now) {
    if (!isPlaying) return baseTrackTime;
    return baseTrackTime + (now - basePerfTime) / 1000;
  }

  function getLyricSec(now) {
    return getRawTrackSec(now) + manualOffsetSec;
  }

  function setPointerTo(sec) {
    const idx = wordQueue.findIndex((item) => item.time >= sec);
    nextWordIdx = idx === -1 ? wordQueue.length : idx;
  }

  function setWhisper(text) {
    if (text === currentWhisperText) return;
    currentWhisperText = text;
    if (text) {
      whisperEl.textContent = text;
      whisperEl.classList.add("visible");
    } else {
      whisperEl.classList.remove("visible");
    }
  }

  function updateWhisperForTime(lyricSec) {
    if (!settings.showWhisper || rawLines.length === 0 || !hasActiveTrack) {
      setWhisper("");
      return;
    }
    let activeIdx = -1;
    for (let i = rawLines.length - 1; i >= 0; i--) {
      if (rawLines[i].time <= lyricSec + 0.05) {
        activeIdx = i;
        break;
      }
    }
    if (activeIdx === -1) {
      setWhisper("");
      return;
    }
    const line = rawLines[activeIdx];
    const nextTime = activeIdx + 1 < rawLines.length ? rawLines[activeIdx + 1].time : line.time + 6.0;
    const endLimit = typeof line.end === "number" ? line.end + 1.4 : Math.min(nextTime, line.time + 7.5);
    if (lyricSec > endLimit) {
      setWhisper("");
    } else {
      setWhisper(line.text || "");
    }
  }

  // --------------------------------------------------------------------------
  // Bottom-Right Spotify-Style Scrolling Sentence Feed (Gradual Time Fade-Out)
  // --------------------------------------------------------------------------
  const sideFeedItems = new Map(); // key ("epoch:lineIdx") -> { key, epoch, lineIdx, el, opacity, retiring }
  let sideFeedEpoch = 1;
  const FEED_PAST_MAX = 4;
  const FEED_FADE_SEC = 11.5;

  function resetSideFeed(immediate = false) {
    sideFeedEpoch++;
    if (immediate) {
      sideFeedItems.clear();
      if (lyricFeedListEl) lyricFeedListEl.innerHTML = "";
      return;
    }
    for (const item of sideFeedItems.values()) {
      item.retiring = true;
    }
  }

  function getLineEndSec(idx) {
    const ln = rawLines[idx];
    if (!ln) return 0;
    const nextStart = idx + 1 < rawLines.length ? Number(rawLines[idx + 1].time) : Number(ln.time) + 5.5;
    if (typeof ln.end === "number" && ln.end > ln.time + 0.2) {
      return Math.min(ln.end, nextStart);
    }
    return Math.min(nextStart, Number(ln.time) + 6.5);
  }

  function ensureFeedLineEl(lineIdx) {
    const key = `${sideFeedEpoch}:${lineIdx}`;
    let item = sideFeedItems.get(key);
    if (item) {
      item.retiring = false;
      return item;
    }
    const ln = rawLines[lineIdx];
    const el = document.createElement("div");
    el.className = "feed-line";
    el.dir = "auto";
    el.textContent = ln.text || "";
    el.style.opacity = "0";
    el.dataset.sort = String(sideFeedEpoch * 100000 + lineIdx);
    el.addEventListener("click", (e) => {
      e.stopPropagation();
      handleSeekTo(Number(ln.time) || 0);
    });

    item = {
      key,
      epoch: sideFeedEpoch,
      lineIdx,
      el,
      opacity: 0,
      retiring: false,
      lineTime: Number(ln.time) || 0,
      lineEnd: getLineEndSec(lineIdx),
    };
    sideFeedItems.set(key, item);

    // Keep DOM order strictly ascending by epoch & lineIdx so new lines flow smoothly upward
    const mySort = sideFeedEpoch * 100000 + lineIdx;
    let inserted = false;
    for (const child of lyricFeedListEl.children) {
      const cSort = parseInt(child.dataset.sort || "0", 10);
      if (cSort > mySort) {
        lyricFeedListEl.insertBefore(el, child);
        inserted = true;
        break;
      }
    }
    if (!inserted) lyricFeedListEl.appendChild(el);
    return item;
  }

  function tickSideFeed(dt, lyricSec) {
    if (!lyricFeedListEl) return;

    const show = !!settings.showSideFeed && hasActiveTrack && rawLines.length > 0;
    const desiredTargets = new Map(); // key -> { role, targetOpacity }

    if (show) {
      let activeIdx = -1;
      for (let i = rawLines.length - 1; i >= 0; i--) {
        if (rawLines[i].time <= lyricSec + 0.06) {
          activeIdx = i;
          break;
        }
      }

      // Past lines (up to 4 above active) that gradually fade away over time
      if (activeIdx >= 0) {
        const startPast = Math.max(0, activeIdx - FEED_PAST_MAX);
        for (let i = startPast; i < activeIdx; i++) {
          const rank = activeIdx - i; // 1 = immediately previous, 4 = oldest
          const rankFactor = [1, 0.56, 0.36, 0.21, 0.11][rank] || 0.08;
          const endSec = getLineEndSec(i);
          const sinceEnd = Math.max(0, lyricSec - endSec);
          const timeFade = Math.pow(1 - clamp(sinceEnd / FEED_FADE_SEC, 0, 1), 1.85);
          const op = rankFactor * timeFade;
          if (op > 0.015) {
            desiredTargets.set(`${sideFeedEpoch}:${i}`, { lineIdx: i, role: "is-past", targetOpacity: op });
          }
        }

        // Active line (softens gently if song enters a long instrumental break)
        const actEnd = getLineEndSec(activeIdx);
        const pastActEnd = Math.max(0, lyricSec - (actEnd + 1.8));
        const actFade = pastActEnd > 0 ? Math.pow(1 - clamp(pastActEnd / 5.5, 0, 1), 1.8) : 1.0;
        if (actFade > 0.015) {
          desiredTargets.set(`${sideFeedEpoch}:${activeIdx}`, {
            lineIdx: activeIdx,
            role: "is-active",
            targetOpacity: 0.96 * actFade,
          });
        }
      }

      // Subtle upcoming sentence preview right underneath active line (like Spotify!)
      const nextIdx = activeIdx + 1;
      if (nextIdx >= 0 && nextIdx < rawLines.length) {
        const untilNext = rawLines[nextIdx].time - lyricSec;
        if (untilNext <= 5.5 && untilNext > -0.1) {
          const introFade = clamp((5.5 - untilNext) / 1.4, 0, 1);
          desiredTargets.set(`${sideFeedEpoch}:${nextIdx}`, {
            lineIdx: nextIdx,
            role: "is-upcoming",
            targetOpacity: 0.32 * introFade,
          });
        }
      }

      for (const spec of desiredTargets.values()) {
        ensureFeedLineEl(spec.lineIdx);
      }
    }

    // Smoothly animate every item's opacity & prune completely invisible lines
    const fadeSpeed = 4.2;
    const step = 1 - Math.exp(-dt * fadeSpeed);
    const toRemove = [];

    for (const [key, item] of sideFeedItems.entries()) {
      const spec = desiredTargets.get(key);
      let targetOp = 0;

      if (spec && !item.retiring) {
        targetOp = spec.targetOpacity;
        item.el.classList.toggle("is-active", spec.role === "is-active");
        item.el.classList.toggle("is-past", spec.role === "is-past");
        item.el.classList.toggle("is-upcoming", spec.role === "is-upcoming");
      } else {
        item.retiring = true;
        item.el.classList.remove("is-active", "is-upcoming");
        item.el.classList.add("is-past");
      }

      if (isPlaying || !show || item.retiring) {
        item.opacity += (targetOp - item.opacity) * step;
      } else if (spec) {
        item.opacity += (targetOp - item.opacity) * step;
      }

      item.el.style.opacity = item.opacity.toFixed(4);
      if (item.retiring && item.opacity <= 0.004) {
        toRemove.push(key);
      }
    }

    for (const key of toRemove) {
      const item = sideFeedItems.get(key);
      if (item && item.el.parentNode) item.el.parentNode.removeChild(item.el);
      sideFeedItems.delete(key);
    }
  }

  function tickPlaybackAndLyrics(now, dt) {
    if (!hasActiveTrack) {
      tickSideFeed(dt, 0);
      return;
    }

    let rawSec = clamp(getRawTrackSec(now), 0, trackDuration);

    // Loop demo seamlessly at track end
    if (isDemoMode && isPlaying && getRawTrackSec(now) >= trackDuration) {
      baseTrackTime = 0;
      basePerfTime = now;
      rawSec = 0;
      clearConstellation();
      resetSideFeed(false);
      setPointerTo(0);
    }

    const displayRatio = isScrubbing ? scrubRatio : clamp(rawSec / Math.max(trackDuration, 0.01), 0, 1);
    const displaySec = isScrubbing ? scrubRatio * trackDuration : rawSec;
    const pct = `${(displayRatio * 100).toFixed(3)}%`;

    progressFill.style.width = pct;
    progressThumb.style.left = pct;
    compactProgressFill.style.width = pct;
    progressHit.setAttribute("aria-valuenow", String(Math.round(displayRatio * 100)));

    timeElapsedEl.textContent = fmtTime(displaySec);
    if (showRemainingTime && trackDuration > 1) {
      timeTotalEl.textContent = `-${fmtTime(Math.max(0, trackDuration - displaySec))}`;
    } else {
      timeTotalEl.textContent = fmtTime(trackDuration);
    }

    if (spProgressFillEl) {
      spProgressFillEl.style.width = pct;
      spTimeCurEl.textContent = fmtTimeShort(displaySec);
      spTimeDurEl.textContent = fmtTimeShort(trackDuration);
    }

    const lyricSec = rawSec + manualOffsetSec;
    tickSideFeed(dt, lyricSec);

    if (!isPlaying || wordQueue.length === 0) return;

    updateWhisperForTime(lyricSec);

    // Guard against tab-sleep bursts: fast-forward smoothly if behind by > 1.8s
    if (nextWordIdx < wordQueue.length && lyricSec - wordQueue[nextWordIdx].time > 1.8) {
      setPointerTo(lyricSec - 0.15);
    }

    // Spawn due words (cap to max 2 per frame for silky cadence)
    let spawnedThisFrame = 0;
    while (
      nextWordIdx < wordQueue.length &&
      wordQueue[nextWordIdx].time <= lyricSec &&
      spawnedThisFrame < 2
    ) {
      const item = wordQueue[nextWordIdx];
      spawnWord(item.word, item.isLineStart);
      nextWordIdx++;
      spawnedThisFrame++;
    }
  }

  // --------------------------------------------------------------------------
  // UI State Helpers
  // --------------------------------------------------------------------------
  function fmtTimeShort(sec) {
    const s = Math.max(0, Math.floor(sec));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, "0")}`;
  }

  function updateSpotifyStageState() {
    if (!spotifyStageEl) return;
    const active = hasActiveTrack;
    spotifyStageEl.classList.toggle("is-idle", !active);

    if (!active) {
      spBrandTextEl.textContent = t("spotifyCardBrand");
      spStateLabelEl.textContent = t("stateReady");
      return;
    }

    const src = currentSourceName || "Spotify";
    const isSpotify = src.toLowerCase().includes("spotify");
    spBrandTextEl.textContent = isSpotify ? t("spotifyPlayingOn") : t("nowPlayingOn", { source: src });
    spStateLabelEl.textContent = isPlaying ? t("statePlaying") : t("statePaused");
  }

  function updatePlayButtonUI() {
    const activePlaying = isPlaying && hasActiveTrack;
    document.body.classList.toggle("is-playing", activePlaying);
    iconPlay.toggleAttribute("hidden", activePlaying);
    iconPause.toggleAttribute("hidden", !activePlaying);
    updateSpotifyStageState();
  }

  function updateCoverUI(coverDataUri) {
    if (coverDataUri) {
      coverImg.src = coverDataUri;
      coverImg.hidden = false;
      coverPlaceholder.hidden = true;
      if (spCoverImgEl) {
        spCoverImgEl.src = coverDataUri;
        spCoverImgEl.hidden = false;
        spArtPlaceholderEl.hidden = true;
        spAmbientBgEl.style.backgroundImage = `url("${coverDataUri}")`;
        spotifyStageEl.classList.add("has-cover");
      }
    } else {
      coverImg.hidden = true;
      coverImg.removeAttribute("src");
      coverPlaceholder.hidden = false;
      if (spCoverImgEl) {
        spCoverImgEl.hidden = true;
        spCoverImgEl.removeAttribute("src");
        spArtPlaceholderEl.hidden = false;
        spAmbientBgEl.style.backgroundImage = "none";
        spotifyStageEl.classList.remove("has-cover");
      }
    }
  }

  function updateSpotifyTrackMeta(title, artist, album) {
    if (!spTitleEl) return;
    spTitleEl.textContent = title || t("spotifyIdleTitle");
    spArtistEl.textContent = artist || t("spotifyIdleSubtitle");
    if (album && album.trim()) {
      spAlbumEl.textContent = album.trim();
      spAlbumEl.hidden = false;
    } else {
      spAlbumEl.textContent = "";
      spAlbumEl.hidden = true;
    }
  }

  function updateStatusUI() {
    statusDotEl.className = "status-dot";

    if (isDemoMode) {
      statusDotEl.classList.add("demo");
      statusTextEl.textContent = t("demoStatus");
      settingsConnLabel.textContent = wsConnected ? t("connBridgeDemo") : t("connDemo");
      return;
    }

    if (!wsConnected) {
      statusDotEl.classList.add("offline");
      statusTextEl.textContent = t("statusOffline");
      settingsConnLabel.textContent = t("connWaiting");
      return;
    }

    settingsConnLabel.textContent = t("connConnected");

    if (!hasActiveTrack) {
      statusDotEl.classList.add("online");
      statusTextEl.textContent = t("statusWaitingMedia");
      return;
    }

    const src = currentSourceName || "Media";
    if (currentLyricsStatus === "loading") {
      statusDotEl.classList.add("loading");
      statusTextEl.textContent = `${src} · ${t("statusSearchingLyrics")}`;
    } else if (currentLyricsStatus === "ready") {
      statusDotEl.classList.add("online");
      const modeLabel =
        currentLyricsMode === "word"
          ? t("statusWordSync")
          : currentLyricsMode === "synced"
          ? t("statusLineSync")
          : t("statusSynced");
      statusTextEl.textContent = `${src} · ${modeLabel}`;
    } else {
      statusDotEl.classList.add("online");
      statusTextEl.textContent = `${src} · ${t("statusNoLyrics")}`;
    }
  }

  function updateOffsetUI() {
    const label = `${manualOffsetSec >= 0 ? "+" : ""}${manualOffsetSec.toFixed(1)}s`;
    btnOffsetReset.textContent = label;
    offsetBadgeEl.textContent = label;
    offsetBadgeEl.hidden = Math.abs(manualOffsetSec) < 0.05;
  }

  function loadOffsetForTrack(trackKey) {
    const fromStore = settings.offsets && typeof settings.offsets[trackKey] === "number"
      ? settings.offsets[trackKey]
      : null;
    if (fromStore !== null) {
      manualOffsetSec = fromStore;
    } else {
      try {
        const legacy = localStorage.getItem("lyric_offset_" + trackKey);
        manualOffsetSec = legacy !== null ? parseFloat(legacy) || 0.0 : 0.0;
      } catch {
        manualOffsetSec = 0.0;
      }
    }
    updateOffsetUI();
  }

  function setTrackOffset(newVal) {
    manualOffsetSec = Math.round(clamp(newVal, -15, 15) * 10) / 10;
    if (currentTrackKey) {
      settings.offsets = settings.offsets || {};
      if (Math.abs(manualOffsetSec) < 0.01) {
        delete settings.offsets[currentTrackKey];
      } else {
        settings.offsets[currentTrackKey] = manualOffsetSec;
      }
      saveLocalSettings();
      if (wsConnected && !isDemoMode) {
        sendCmd({ cmd: "set_offset", track_key: currentTrackKey, offset: manualOffsetSec });
      }
    }
    updateOffsetUI();
    setPointerTo(getLyricSec(performance.now()));
  }

  function updateSessionsDropdown(sessions) {
    if (!Array.isArray(sessions)) return;
    lastSessionsList = sessions;
    const prevVal = settings.preferredSession || "auto";
    sessionSelect.innerHTML = "";
    const autoOpt = document.createElement("option");
    autoOpt.value = "auto";
    autoOpt.textContent = t("sourceAuto");
    sessionSelect.appendChild(autoOpt);
    for (const s of sessions) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = `${s.name}${s.playing ? ` (${t("sourcePlayingTag")})` : ""}`;
      sessionSelect.appendChild(opt);
    }
    if (sessionSelect.querySelector(`option[value="${CSS.escape(prevVal)}"]`)) {
      sessionSelect.value = prevVal;
    }
  }

  function enterIdleState() {
    if (isDemoMode) return;
    hasActiveTrack = false;
    isPlaying = false;
    currentTrackKey = "";
    currentSourceName = "";
    currentLyricsStatus = "idle";
    currentLyricsMode = "none";
    rawLines = [];
    wordQueue = [];
    clearConstellation();
    resetSideFeed(false);

    trackTitleEl.textContent = wsConnected ? t("idleTitle") : t("waitingBridgeTitle");
    trackArtistEl.textContent = wsConnected ? t("idleSubtitle") : t("waitingBridgeSubtitle");
    updateSpotifyTrackMeta(t("spotifyIdleTitle"), t("spotifyIdleSubtitle"), "");
    updateCoverUI(null);
    applyAlbumAccent(null);
    progressFill.style.width = "0%";
    progressThumb.style.left = "0%";
    compactProgressFill.style.width = "0%";
    if (spProgressFillEl) {
      spProgressFillEl.style.width = "0%";
      spTimeCurEl.textContent = "0:00";
      spTimeDurEl.textContent = "0:00";
    }
    timeElapsedEl.textContent = "00:00";
    timeTotalEl.textContent = "00:00";
    offsetBadgeEl.hidden = true;
    updatePlayButtonUI();
    updateStatusUI();
  }

  // --------------------------------------------------------------------------
  // Demo Mode Controls
  // --------------------------------------------------------------------------
  function startDemo() {
    isDemoMode = true;
    hasActiveTrack = true;
    isPlaying = true;
    currentTrackKey = DEMO_TRACK.track_id;
    currentSourceName = DEMO_TRACK.source_name;
    currentLyricsStatus = "ready";
    currentLyricsMode = "synced";
    trackDuration = DEMO_TRACK.duration;
    baseTrackTime = 0;
    basePerfTime = performance.now();
    manualOffsetSec = 0;

    clearConstellation();
    const demoTitle = t("demoTrackTitle");
    const demoArtist = t("demoTrackArtist");
    const demoAlbum = t("demoTrackAlbum");
    trackTitleEl.textContent = demoTitle;
    trackArtistEl.textContent = demoArtist;
    updateSpotifyTrackMeta(demoTitle, demoArtist, demoAlbum);
    updateCoverUI(DEMO_TRACK.cover);
    applyAlbumAccent(DEMO_TRACK.accent);
    buildWordTimeline(DEMO_TRACK.lyrics);
    setPointerTo(0);

    btnDemoQuick.classList.add("active");
    btnDemoPanel.classList.add("running");
    demoCtaLabel.textContent = t("demoStop");

    updateOffsetUI();
    updatePlayButtonUI();
    updateStatusUI();
    showNotice(t("demoStarted"));
  }

  function stopDemo() {
    if (!isDemoMode) return;
    isDemoMode = false;
    btnDemoQuick.classList.remove("active");
    btnDemoPanel.classList.remove("running");
    demoCtaLabel.textContent = t("demoStart");
    clearConstellation();
    enterIdleState();
    // Seamlessly request current live state without dropping the WebSocket
    if (wsConnected) {
      sendCmd({ cmd: "sync" });
    }
  }

  function toggleDemo() {
    if (isDemoMode) stopDemo();
    else startDemo();
  }

  // --------------------------------------------------------------------------
  // WebSocket Communication
  // --------------------------------------------------------------------------
  function sendCmd(payload) {
    if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
      wsSocket.send(JSON.stringify(payload));
    }
  }

  function getWsUrl() {
    if (window.location.protocol === "http:" || window.location.protocol === "https:") {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${window.location.host}/ws`;
    }
    return "ws://127.0.0.1:8765/ws";
  }

  function connectWS() {
    clearTimeout(reconnectTimer);
    try {
      const ws = new WebSocket(getWsUrl());
      wsSocket = ws;

      ws.onopen = () => {
        wsConnected = true;
        reconnectDelay = 1200;
        updateStatusUI();
      };

      ws.onclose = () => {
        wsConnected = false;
        if (!isDemoMode) {
          // Freeze timer instead of falsely marching progress while disconnected
          baseTrackTime = clamp(getRawTrackSec(performance.now()), 0, trackDuration);
          basePerfTime = performance.now();
          isPlaying = false;
          updatePlayButtonUI();
        }
        updateStatusUI();
        reconnectTimer = setTimeout(connectWS, reconnectDelay);
        reconnectDelay = Math.min(5000, Math.round(reconnectDelay * 1.35));
      };

      ws.onerror = () => {
        // onclose will trigger clean backoff reconnect
      };

      ws.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        handleBridgeMessage(data);
      };
    } catch {
      reconnectTimer = setTimeout(connectWS, reconnectDelay);
    }
  }

  function handleBridgeMessage(data) {
    const now = performance.now();

    if (data.type === "notice") {
      showNotice(data.text || "");
      return;
    }

    if (data.type === "toggle_settings") {
      if (document.body.classList.contains("wallpaper-mode")) {
        setSettingsOpen(settingsPanel.hidden);
      }
      return;
    }

    if (data.type === "desktop_pointer") {
      if (document.body.classList.contains("wallpaper-mode")) {
        handleDesktopPointer(data);
      }
      return;
    }

    if (data.type === "desktop_icons") {
      if (optIcons && typeof data.visible === "boolean") {
        optIcons.checked = data.visible;
      }
      return;
    }

    if (data.type === "init" || data.type === "settings") {
      if (optIcons && typeof data.desktop_icons === "boolean") {
        optIcons.checked = data.desktop_icons;
      }
      if (data.settings && typeof data.settings === "object") {
        settings = {
          ...DEFAULT_SETTINGS,
          ...settings,
          ...data.settings,
          offsets: { ...(settings.offsets || {}), ...(data.settings.offsets || {}) },
        };
        saveLocalSettings();
        applySettingsToUI();
        if (currentTrackKey && !isDemoMode) {
          loadOffsetForTrack(currentTrackKey);
        }
      }
      if (data.sessions) updateSessionsDropdown(data.sessions);
      updateStatusUI();
      return;
    }

    if (data.type === "sessions") {
      updateSessionsDropdown(data.sessions);
      return;
    }

    // While Demo mode is explicitly active, ignore live playback packets until Demo stops
    if (isDemoMode) return;

    if (data.type === "idle") {
      if (data.sessions) updateSessionsDropdown(data.sessions);
      enterIdleState();
      return;
    }

    if (data.type === "track") {
      clearConstellation();
      hasActiveTrack = true;

      const title = data.title || t("unknownTrack");
      const artist = data.artist || "";
      currentTrackKey = data.track_id || `${artist} - ${title}`;
      currentSourceName = data.source_name || "";
      currentLyricsStatus = data.lyrics_status || (data.lyrics?.length ? "ready" : "none");
      currentLyricsMode = data.lyrics_mode || "none";

      trackTitleEl.textContent = title;
      trackArtistEl.textContent = artist || (data.album || t("unknownArtist"));
      updateSpotifyTrackMeta(title, artist || t("unknownArtist"), data.album || "");
      updateCoverUI(data.cover || null);
      applyAlbumAccent(data.accent || null);
      if (data.sessions) updateSessionsDropdown(data.sessions);

      loadOffsetForTrack(currentTrackKey);

      trackDuration = data.duration > 1 ? data.duration : 1;
      buildWordTimeline(data.lyrics || []);

      baseTrackTime = clamp(data.position || 0, 0, trackDuration);
      basePerfTime = now;
      isPlaying = !!data.playing;

      setPointerTo(getLyricSec(now) - 0.15);
      updatePlayButtonUI();
      updateStatusUI();
      return;
    }

    if (data.type === "lyrics") {
      if (data.track_id && data.track_id !== currentTrackKey) return;
      currentLyricsStatus = data.lyrics_status || (data.lyrics?.length ? "ready" : "none");
      currentLyricsMode = data.lyrics_mode || "none";
      buildWordTimeline(data.lyrics || []);
      setPointerTo(getLyricSec(now) - 0.12);
      updateStatusUI();
      return;
    }

    if (data.type === "playstate") {
      baseTrackTime = clamp(data.position || 0, 0, trackDuration);
      basePerfTime = now;
      isPlaying = !!data.playing;
      updatePlayButtonUI();
      return;
    }

    if (data.type === "seek") {
      clearConstellation();
      baseTrackTime = clamp(data.position || 0, 0, trackDuration);
      basePerfTime = now;
      isPlaying = !!data.playing;
      setPointerTo(getLyricSec(now));
      updatePlayButtonUI();
      return;
    }

    if (data.type === "heartbeat") {
      if (data.duration > 1) trackDuration = data.duration;
      const localSec = getRawTrackSec(now);
      const diff = (data.position || 0) - localSec;
      if (Math.abs(diff) > 2.6) {
        clearConstellation();
        baseTrackTime = clamp(data.position || 0, 0, trackDuration);
        basePerfTime = now;
        setPointerTo(getLyricSec(now));
      } else if (Math.abs(diff) > 0.25) {
        baseTrackTime = clamp(localSec + diff * 0.28, 0, trackDuration);
        basePerfTime = now;
      }
      if (isPlaying !== !!data.playing) {
        isPlaying = !!data.playing;
        updatePlayButtonUI();
      }
    }
  }

  // --------------------------------------------------------------------------
  // Interactive Controls & Scrubbing
  // --------------------------------------------------------------------------
  function handlePlayPause() {
    if (isDemoMode) {
      const now = performance.now();
      baseTrackTime = clamp(getRawTrackSec(now), 0, trackDuration);
      basePerfTime = now;
      isPlaying = !isPlaying;
      updatePlayButtonUI();
      return;
    }
    sendCmd({ cmd: "toggle" });
  }

  function handleSeekTo(targetSec) {
    const target = clamp(targetSec, 0, trackDuration);
    if (isDemoMode) {
      const now = performance.now();
      clearConstellation();
      baseTrackTime = target;
      basePerfTime = now;
      setPointerTo(target + manualOffsetSec);
      return;
    }
    sendCmd({ cmd: "seek", position: target });
  }

  function handleSeekRel(delta) {
    if (isDemoMode) {
      handleSeekTo(getRawTrackSec(performance.now()) + delta);
      return;
    }
    sendCmd({ cmd: "seek_rel", delta });
  }

  btnToggle.addEventListener("click", handlePlayPause);
  btnPrev.addEventListener("click", () => {
    if (isDemoMode) handleSeekTo(0);
    else sendCmd({ cmd: "prev" });
  });
  btnNext.addEventListener("click", () => {
    if (isDemoMode) handleSeekTo(0);
    else sendCmd({ cmd: "next" });
  });
  btnBack10.addEventListener("click", () => handleSeekRel(-10));
  btnFwd10.addEventListener("click", () => handleSeekRel(10));

  timeTotalEl.addEventListener("click", () => {
    showRemainingTime = !showRemainingTime;
  });

  // Pointer drag scrubbing with hover time tooltip
  function ratioFromPointer(e) {
    const rect = progressHit.getBoundingClientRect();
    return clamp((e.clientX - rect.left) / Math.max(1, rect.width), 0, 1);
  }

  function updateTooltip(ratio) {
    const pct = `${(ratio * 100).toFixed(2)}%`;
    scrubTooltip.style.left = pct;
    scrubTooltip.textContent = fmtTime(ratio * trackDuration);
  }

  progressHit.addEventListener("pointermove", (e) => {
    if (!hasActiveTrack || trackDuration <= 1) return;
    const r = ratioFromPointer(e);
    updateTooltip(r);
    if (isScrubbing) {
      scrubRatio = r;
    }
  });

  progressHit.addEventListener("pointerdown", (e) => {
    if (!hasActiveTrack || trackDuration <= 1) return;
    isScrubbing = true;
    scrubRatio = ratioFromPointer(e);
    progressHit.classList.add("dragging");
    progressHit.setPointerCapture(e.pointerId);
    updateTooltip(scrubRatio);
  });

  progressHit.addEventListener("pointerup", (e) => {
    if (!isScrubbing) return;
    isScrubbing = false;
    progressHit.classList.remove("dragging");
    try { progressHit.releasePointerCapture(e.pointerId); } catch {}
    handleSeekTo(scrubRatio * trackDuration);
  });

  progressHit.addEventListener("pointercancel", () => {
    isScrubbing = false;
    progressHit.classList.remove("dragging");
  });

  // Settings Panel Open / Close
  function setSettingsOpen(open) {
    settingsPanel.hidden = !open;
    document.body.classList.toggle("settings-open", open);
    btnSettings.classList.toggle("active", open);
    if (open) {
      document.body.classList.remove("dock-faded");
    } else {
      resetIdleFade();
    }
  }

  btnSettings.addEventListener("click", (e) => {
    e.stopPropagation();
    setSettingsOpen(settingsPanel.hidden);
  });
  offsetBadgeEl.addEventListener("click", (e) => {
    e.stopPropagation();
    setSettingsOpen(true);
  });
  btnCloseSettings.addEventListener("click", () => setSettingsOpen(false));

  document.addEventListener("click", (e) => {
    if (!settingsPanel.hidden && !settingsPanel.contains(e.target) && !playerDock.contains(e.target)) {
      setSettingsOpen(false);
    }
  });

  // Theme Chips
  document.querySelectorAll("#theme-grid .theme-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      updateSettings({ theme: btn.dataset.themeVal });
    });
  });

  // Reticle Style
  document.querySelectorAll("#reticle-group .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      updateSettings({ reticleStyle: btn.dataset.reticle });
    });
  });

  // Offset buttons
  document.querySelectorAll(".sync-row [data-offset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const delta = parseFloat(btn.dataset.offset);
      setTrackOffset(manualOffsetSec + delta);
    });
  });
  btnOffsetReset.addEventListener("click", () => setTrackOffset(0));
  btnRefetch.addEventListener("click", () => {
    if (isDemoMode) {
      showNotice(t("demoBuiltInNotice"));
      return;
    }
    sendCmd({ cmd: "refetch_lyrics" });
    showNotice(t("refetchNotice"));
  });

  // Language Selector
  if (langSelect) {
    langSelect.addEventListener("change", () => {
      updateSettings({ language: langSelect.value });
    });
  }

  // Session Selector
  sessionSelect.addEventListener("change", () => {
    const val = sessionSelect.value;
    settings.preferredSession = val;
    saveLocalSettings();
    if (wsConnected) {
      sendCmd({ cmd: "select_session", session_id: val });
    }
  });

  // Toggles & Sliders
  if (optSpotifyCard) {
    optSpotifyCard.addEventListener("change", () =>
      updateSettings({ showSpotifyCard: optSpotifyCard.checked })
    );
  }
  optSideFeed.addEventListener("change", () => updateSettings({ showSideFeed: optSideFeed.checked }));
  optWhisper.addEventListener("change", () => updateSettings({ showWhisper: optWhisper.checked }));
  optDust.addEventListener("change", () => updateSettings({ showDust: optDust.checked }));
  optClock.addEventListener("change", () => updateSettings({ showClock: optClock.checked }));
  optSeconds.addEventListener("change", () => updateSettings({ showSeconds: optSeconds.checked }));
  optAutofade.addEventListener("change", () => updateSettings({ autoFadeDock: optAutofade.checked }));
  optCompact.addEventListener("change", () => updateSettings({ compactDock: optCompact.checked }));
  if (optIcons) {
    optIcons.addEventListener("change", () => {
      if (!wsConnected) {
        showNotice(t("bridgeOfflineNotice"));
        optIcons.checked = !optIcons.checked;
        return;
      }
      sendCmd({ cmd: "set_desktop_icons", visible: optIcons.checked });
    });
  }

  optLife.addEventListener("input", () => {
    updateSettings({ nodeLifeSec: parseInt(optLife.value, 10) }, false);
  });
  optLife.addEventListener("change", () => {
    updateSettings({ nodeLifeSec: parseInt(optLife.value, 10) }, true);
  });

  optBrightness.addEventListener("input", () => {
    updateSettings({ videoBrightness: parseFloat(optBrightness.value) }, false);
  });
  optBrightness.addEventListener("change", () => {
    updateSettings({ videoBrightness: parseFloat(optBrightness.value) }, true);
  });

  optGrayscale.addEventListener("input", () => {
    updateSettings({ videoGrayscale: parseInt(optGrayscale.value, 10) }, false);
  });
  optGrayscale.addEventListener("change", () => {
    updateSettings({ videoGrayscale: parseInt(optGrayscale.value, 10) }, true);
  });

  // Demo Buttons
  btnDemoQuick.addEventListener("click", toggleDemo);
  btnDemoPanel.addEventListener("click", toggleDemo);

  // Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;

    if (e.code === "Space") {
      e.preventDefault();
      handlePlayPause();
    } else if (e.code === "ArrowLeft") {
      e.preventDefault();
      handleSeekRel(-5);
    } else if (e.code === "ArrowRight") {
      e.preventDefault();
      handleSeekRel(5);
    } else if (e.key === "[") {
      setTrackOffset(manualOffsetSec - 0.1);
    } else if (e.key === "]") {
      setTrackOffset(manualOffsetSec + 0.1);
    } else if (e.key === "d" || e.key === "D") {
      toggleDemo();
    } else if (e.key === "s" || e.key === "S") {
      setSettingsOpen(settingsPanel.hidden);
    } else if (e.key === "Escape") {
      setSettingsOpen(false);
    }
  });

  // --------------------------------------------------------------------------
  // Lively Wallpaper Native Properties Hook
  // --------------------------------------------------------------------------
  window.livelyPropertyListener = function (name, val) {
    const themes = ["overcast", "midnight", "ambient", "dusk"];
    const reticles = ["crosshair", "orbital", "starburst"];

    switch (name) {
      case "theme":
        updateSettings({ theme: themes[val] || String(val) }, false);
        break;
      case "reticleStyle":
        updateSettings({ reticleStyle: reticles[val] || String(val) }, false);
        break;
      case "showClock":
        updateSettings({ showClock: !!val }, false);
        break;
      case "showSeconds":
        updateSettings({ showSeconds: !!val }, false);
        break;
      case "showWhisper":
        updateSettings({ showWhisper: !!val }, false);
        break;
      case "showDust":
        updateSettings({ showDust: !!val }, false);
        break;
      case "autoFadeDock":
        updateSettings({ autoFadeDock: !!val }, false);
        break;
      case "compactDock":
        updateSettings({ compactDock: !!val }, false);
        break;
      case "videoBrightness":
        updateSettings({ videoBrightness: clamp(Number(val) / 100, 0.35, 1.15) }, false);
        break;
      case "videoGrayscale":
        updateSettings({ videoGrayscale: clamp(Number(val), 0, 100) }, false);
        break;
      case "nodeLifeSec":
        updateSettings({ nodeLifeSec: clamp(Number(val), 6, 24) }, false);
        break;
      default:
        break;
    }
  };

  // Expose minimal debug / preview helper on window
  window.LyricSky = {
    startDemo,
    stopDemo,
    toggleDemo,
    setTheme: (th) => updateSettings({ theme: th }),
    setLanguage: (lang) => updateSettings({ language: lang }),
  };

  // --------------------------------------------------------------------------
  // Native Desktop Wallpaper Pointer Bridge (0ms WebSocket Click, Hover & Drag)
  // --------------------------------------------------------------------------
  let desktopHoveredEl = null;
  let desktopDragRange = null;
  let desktopScrubbing = false;
  let desktopDownPt = null;

  function setDesktopHover(el) {
    if (desktopHoveredEl === el) return;
    if (desktopHoveredEl) desktopHoveredEl.classList.remove("desktop-hover");
    desktopHoveredEl = el || null;
    if (desktopHoveredEl) desktopHoveredEl.classList.add("desktop-hover");
  }

  function updateRangeFromClientX(rangeEl, clientX) {
    const rect = rangeEl.getBoundingClientRect();
    if (rect.width <= 0) return;
    const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
    const min = parseFloat(rangeEl.min || "0");
    const max = parseFloat(rangeEl.max || "100");
    const step = parseFloat(rangeEl.step || "1");
    const raw = min + ratio * (max - min);
    const snapped = Math.round((raw - min) / step) * step + min;
    rangeEl.value = String(clamp(Number(snapped.toFixed(4)), min, max));
    rangeEl.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function handleDesktopPointer(evt) {
    const action = evt.action;

    if (action === "leave") {
      setDesktopHover(null);
      progressHit.classList.remove("desktop-hover");
      playerDock.classList.remove("desktop-hover");
      if (desktopScrubbing) {
        desktopScrubbing = false;
        isScrubbing = false;
        progressHit.classList.remove("dragging");
      }
      if (desktopDragRange) {
        desktopDragRange.dispatchEvent(new Event("change", { bubbles: true }));
        desktopDragRange = null;
      }
      desktopDownPt = null;
      return;
    }

    const x = clamp(Number(evt.nx) || 0, 0, 1) * window.innerWidth;
    const y = clamp(Number(evt.ny) || 0, 0, 1) * window.innerHeight;
    const el = document.elementFromPoint(x, y);

    const inDock = !!(el && playerDock.contains(el));
    const inSettings = !!(!settingsPanel.hidden && el && settingsPanel.contains(el));
    const inFeed = !!(el && lyricFeedEl && lyricFeedEl.contains(el));

    if (action === "move") {
      if (inDock || inSettings) {
        resetIdleFade();
      }
      playerDock.classList.toggle("desktop-hover", inDock || inSettings);

      if (desktopScrubbing) {
        const rect = progressHit.getBoundingClientRect();
        scrubRatio = clamp((x - rect.left) / Math.max(1, rect.width), 0, 1);
        updateTooltip(scrubRatio);
        return;
      }

      if (desktopDragRange) {
        updateRangeFromClientX(desktopDragRange, x);
        return;
      }

      // Hover progress bar preview
      const onProg = !!(el && progressHit.contains(el) && hasActiveTrack && trackDuration > 1);
      progressHit.classList.toggle("desktop-hover", onProg);
      if (onProg) {
        const rect = progressHit.getBoundingClientRect();
        updateTooltip(clamp((x - rect.left) / Math.max(1, rect.width), 0, 1));
      }

      const hoverTarget =
        inDock || inSettings || inFeed
          ? el.closest("button, label.toggle-item, select, .feed-line, .time-toggle")
          : null;
      setDesktopHover(hoverTarget);
      return;
    }

    if (action === "down") {
      desktopDownPt = { x, y };
      if (inDock || inSettings) resetIdleFade();

      // Drag-scrub song progress bar directly from desktop
      if (el && progressHit.contains(el) && hasActiveTrack && trackDuration > 1) {
        desktopScrubbing = true;
        isScrubbing = true;
        progressHit.classList.add("dragging");
        const rect = progressHit.getBoundingClientRect();
        scrubRatio = clamp((x - rect.left) / Math.max(1, rect.width), 0, 1);
        updateTooltip(scrubRatio);
        return;
      }

      // Drag any range slider in Settings directly from desktop
      if (inSettings && el && el.tagName === "INPUT" && el.type === "range") {
        desktopDragRange = el;
        updateRangeFromClientX(el, x);
        return;
      }
      return;
    }

    if (action === "up") {
      if (desktopScrubbing) {
        desktopScrubbing = false;
        isScrubbing = false;
        progressHit.classList.remove("dragging");
        handleSeekTo(scrubRatio * trackDuration);
        desktopDownPt = null;
        return;
      }

      if (desktopDragRange) {
        desktopDragRange.dispatchEvent(new Event("change", { bubbles: true }));
        desktopDragRange = null;
        desktopDownPt = null;
        return;
      }

      // Ignore long drags (such as desktop icon marquee selection)
      const movedDist = desktopDownPt ? Math.hypot(x - desktopDownPt.x, y - desktopDownPt.y) : 0;
      desktopDownPt = null;
      if (movedDist > 20) return;

      if (inDock || inSettings || inFeed) {
        if (el.tagName === "SELECT" && el.options.length > 0) {
          el.selectedIndex = (el.selectedIndex + 1) % el.options.length;
          el.dispatchEvent(new Event("change", { bubbles: true }));
          const chosen = el.options[el.selectedIndex].textContent;
          showNotice(el.id === "lang-select" ? chosen : t("sourceNotice", { name: chosen }));
          return;
        }
        const clickable = el.closest("button, label.toggle-item, .feed-line, .time-toggle");
        if (clickable) {
          clickable.click();
          return;
        }
      } else if (!settingsPanel.hidden) {
        // Clicking empty desktop sky closes the open Settings popover
        setSettingsOpen(false);
      }
    }
  }

  // --------------------------------------------------------------------------
  // Boot
  // --------------------------------------------------------------------------
  if (new URLSearchParams(window.location.search).get("mode") === "wallpaper") {
    document.body.classList.add("wallpaper-mode");
  }
  applySettingsToUI();
  enterIdleState();
  loadLocalesPack();
  connectWS();
  requestAnimationFrame(render);
})();
