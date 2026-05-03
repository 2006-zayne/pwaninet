# PwaniNet PWA Splash Screen

## Overview

The splash screen provides a Facebook-style loading experience when launching the PWA from the app drawer/home screen. It is **connection-aware** and handles offline scenarios gracefully.

## Architecture

### Files

| File | Purpose |
|------|---------|
| `/static/js/startup-v2.js` | Startup manager (IIFE, no class, no loops) |
| `/static/css/splash.css` | Splash screen animations and styles |
| `/templates/base.html` | Inline critical CSS + splash HTML markup |

### Flow

```
App Launch
    │
    ▼
Is Fresh PWA Launch? ──NO──▶ Hide splash, show app immediately
    │
   YES
    │
    ▼
Show splash screen (visible by default via CSS)
    │
    ▼
Progressive Internet Check (3 attempts)
    │
    ├── Connected ──▶ "Connected!" ──▶ Fade to app
    │
    ├── Slow ──▶ "Connection slow, retrying..." ──▶ Retry
    │
    └── Failed ──▶ "No internet connection" ──▶ /offline/
```

## Launch Detection

The splash screen **only** appears on the absolute initial PWA launch. It is skipped for:

- Page refresh (F5, Ctrl+R)
- Internal navigation (clicking links within the app)
- Back/forward browser navigation
- Any subsequent page load in the same session

### Detection Criteria

A fresh launch requires **all** of these:

1. **PWA standalone mode** — `display-mode: standalone` or `navigator.standalone` (iOS)
2. **No session flag** — `sessionStorage.getItem('pwaninet_launched')` is null
3. **First navigation** — `performance.getEntriesByType('navigation')[0].type === 'navigate'`

Once detected, `sessionStorage.setItem('pwaninet_launched', 'true')` prevents the splash from showing again until the browser session ends.

## Connection-Aware Behavior

### Progressive Connection Attempts

| Attempt | Timeout | Status Text | Animation Speed |
|---------|---------|-------------|-----------------|
| 1st | 4s | "Connecting to server..." | Normal (1.4s) |
| 2nd | 6s | "Connection slow, retrying..." | Slow (2s) |
| 3rd | 8s | "Still trying to connect..." | Very slow (3s) |

**Maximum total wait: ~18 seconds** before offline fallback.

### Status Messages

| Condition | Message | Next Action |
|-----------|---------|-------------|
| First attempt | "Connecting to server..." | Wait up to 4s |
| First attempt succeeds | "Connected!" | Transition to app |
| First attempt fails | "Connection slow, retrying..." | Retry with 6s timeout |
| Second attempt succeeds | "Connection restored!" | Transition to app |
| Second attempt fails | "Still trying to connect..." | Final retry with 8s timeout |
| Third attempt succeeds | "Connection restored!" | Transition to app |
| All attempts fail | "No internet connection" | Redirect to `/offline/` |

### Visual Feedback

- **Text updates** reflect real-time connection status
- **Dot animation slows down** as connection struggles (1.4s → 2s → 3s)
- **Offline icon** 📵 replaces loading dots when all attempts fail
- **Progress bar hidden** when going to offline page

## CSS Strategy

The splash screen is **visible by default** via CSS to prevent the app content from flashing before JavaScript runs:

```css
#startup-splash {
    opacity: 1;  /* Visible immediately - no JS needed */
    display: flex;
    z-index: 999999;
}

#app {
    opacity: 0;  /* Hidden until JS reveals it */
}
```

JavaScript only needs to:
1. **Hide splash** for non-fresh launches (`display: none`)
2. **Fade out splash** after successful connection check
3. **Show app** with `opacity: 1`

## Theme Support

All splash screen colors use CSS variables that match the base app:

| Element | Variable | Light | Dark |
|---------|----------|-------|------|
| Background | `--background` | `#f8fafc` | `#18191f` |
| Brand text | `--text-dark` | `#0f172a` | `#e4e6eb` |
| Status text | `--text-secondary` | `#64748b` | `#e4e6eb` |
| Logo card | `--card-bg` | `#ffffff` | `#242526` |
| Logo border | `--border` | `#e2e8f0` | `#3a3b3c` |
| Progress bar | `--primary` | `#2563eb` | `#6366f1` |
| Loading dots | `--primary` | `#2563eb` | `#6366f1` |

## Logo

The splash screen uses the **actual PWA icon** from the manifest:

```html
<img src="/static/images/web-app-manifest-192x192.png" alt="PwaniNet">
```

This matches the icon shown on the home screen/app drawer.

## Offline Handling

When all connection attempts fail:

1. Status text changes to "No internet connection"
2. Loading dots replaced with 📵 icon
3. Progress bar hidden
4. After 2 seconds, redirects to `/offline/`

The service worker (`/static/service-worker.js`) also handles offline navigation fallback by serving a cached offline page for failed navigation requests.

## Health Check Endpoint

The connection check uses `/static/images/favicon.ico` (a static file) instead of an API endpoint. This avoids:

- **Auth redirects** — API endpoints may return 302 to login
- **Server-side rendering delays** — Static files are served directly
- **Loop risks** — No redirect chains that could cause infinite loops

## Debugging

| URL | Purpose |
|-----|---------|
| `/debug/startup/` | Monitor startup progress, force show app, test network |
| `/clear-cache/` | Clear service worker, caches, and session flags |
| `/offline/` | Test offline page directly |

### Console Logs

```
🚀 Fresh PWA launch - showing splash       # Initial launch detected
📱 Not a fresh launch - skipping splash      # Subsequent navigation
🌐 Checking internet connectivity...          # Connection check started
✅ Internet connectivity confirmed            # Connection successful
❌ Connectivity check error: ...             # Connection failed
✅ App ready                                  # Transition complete
```

## Offline Skeleton Overlays

When the internet connection is lost, instead of redirecting to `/offline/`, the app shows a **Facebook-style skeleton overlay** matching the current page layout.

### Page-Aware Skeletons

| Page | Skeleton Layout | Notes |
|------|----------------|-------|
| Home/Feed | Search header + groups row + 3 post cards | Default fallback |
| Profile | Cover photo + avatar + name + bio + stats + tabs + 2 posts | Matches profile card layout |
| Groups | 6 group cards in grid | Matches groups dashboard grid |
| Notifications | 5 notification items (avatar + text + time) | Matches notification list |
| Messages | **No skeleton** | Available offline for reading cached messages |

### Route Detection

The skeleton manager detects the current page from `window.location.pathname`:

- `/messages/` or `/messaging/` → **skipped** (offline available)
- `/profile/` or `/users/{username}/` → profile skeleton
- `/groups/` (not `/groups/create`) → groups skeleton
- `/notifications/` → notifications skeleton
- `/` or `/home/` or `/posts/` → home feed skeleton
- Everything else → home feed skeleton (fallback)

### Features

- **Red offline banner** with "Retrying..." pulse animation
- **Shimmer animation** on all skeleton elements
- **Theme-aware** — uses CSS variables for light/dark mode
- **Auto-recovery** — listens for `online` event, verifies with fetch, hides skeleton
- **No redirect** — stays on current page, overlays skeleton on top
- **Mobile responsive** — adapts skeleton sizes for small screens

### Files

| File | Purpose |
|------|---------|
| `/static/js/offline-skeleton-v2.js` | Page-aware skeleton manager |
| `/static/js/offline-skeleton.js` | Original skeleton (deprecated) |

## Design Decisions

### Why IIFE instead of Class?

Previous class-based implementations had syntax errors from multiple edits that caused infinite loops. The IIFE pattern:

- Runs once, cannot recurse
- No `this` binding issues
- No method name typos
- Simpler control flow

### Why Static File for Health Check?

API endpoints (`/api/health/`) were causing 302 redirects to login for unauthenticated users, which made `fetch()` hang or loop. Static files bypass authentication entirely.

### Why CSS-First Visibility?

Making the splash visible via CSS (not JS) ensures:

- Zero flash of app content before splash
- Splash appears on first paint, before JavaScript loads
- Works even if JavaScript fails to load
