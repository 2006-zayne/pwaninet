# Parked: Reels Player UX Enhancements (queued 2026-10-18)

>Reminder file — pick these up when returning to the reels-UX chat/thread.
>Everything below builds on the already-shipped desktop fullscreen player.

## Currently shipped (baseline)
- Floating comment rail (16px radius / 12px gutter), card language shared
- Doze/idle dimming, first-run immersive rail tip
- Keyboard: Space play/pause, ↑/↓ browse, M mute, C cinema mode, Esc close
- First-run keyboard coach card + persistent "?" shortcuts panel (Shift+/)
- Double-tap like + heart burst, progress line/scrubber, wheel wake
- Comment prefetch (LRU cache) + skeleton shimmer + 200ms card crossfade

## Parked enhancement shortlist (from the option survey)
1. **Keyboard seek suite** — ←/→ seek ±5s, J/L ±10s (YouTube-style),
   0–9 jump to percentage, on-screen seek feedback bubble; update coach
   card + ? panel to match.
2. **Scroll-wheel volume** — hover video, wheel adjusts volume with OSD.
3. **Autoplay & loop toggle** — `A` key, small status pill for current mode.
4. **Mini-player (PiP)** — scroll away and the reel shrinks into a corner
   mini-player that keeps playing (TikTok/YouTube continuity).
5. **Live comment stream** — WebSocket push into the floating rail; badge
   pulse + soft ping, comments pop in real time.

## Environment notes（if resuming later）
- SW cache flow: bump `CACHE_BUILD` in `static/service-worker.js` for any
  JS/CSS change; template edits need a Django process restart.
- User's canonical origin for testing: `127.0.0.1:8000` (NOT localhost —
  separate SW origin, has its own fossil caches).
- Reset browser caches/SW snippet:
  `navigator.serviceWorker.getRegistrations().then(rs=>rs.forEach(r=>r.unregister()));caches.keys().then(ks=>Promise.all(ks.map(caches.delete))).then(()=>location.reload())`
