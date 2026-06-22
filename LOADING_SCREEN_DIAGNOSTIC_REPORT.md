# PWANINET MVP Loading Screen Diagnostic Report

**Date:** 2025-01-XX  
**Investigation Scope:** Loading screen lifecycle, startup timeline, blank screen occurrences, loading screen flashing, service worker behavior, network activity, JavaScript runtime errors, and state dependencies

---

## Executive Summary

The PWANINET MVP has **multiple competing loading systems** that operate independently without coordination, leading to:
- **Blank screens** when no loading system successfully shows the app
- **Loading screen flashing** when systems conflict over visibility control
- **Inconsistent behavior** across different launch scenarios
- **Race conditions** between multiple initialization scripts

**Root Cause:** The codebase contains 5 different startup script variants, 2 inline loading screens in base.html, and multiple independent systems that all control the same DOM elements without synchronization.

---

## 1. Loading Screen Lifecycle Analysis

### 1.1 Multiple Loading Systems Identified

| System | Location | Purpose | Status |
|--------|----------|---------|--------|
| **Page Skeleton** | `templates/base.html` | Initial page load placeholder | Active |
| **Startup Splash** | `templates/base.html` | PWA launch splash screen | Active |
| **startup-v2.js** | `static/js/startup-v2.js` | Main startup manager | Active |
| **startup.js** | `static/js/startup.js` | Legacy startup manager | Unused |
| **startup-fixed.js** | `static/js/startup-fixed.js` | Fixed version with strict launch detection | Unused |
| **startup-safe.js** | `static/js/startup-safe.js` | Safe version with timeout safeguards | Unused |
| **startup-final.js** | `static/js/startup-final.js` | Final version with connectivity check | Unused |
| **splash-screen.js** | `static/js/splash-screen.js` | Alternative splash manager | Unused |
| **skeleton-loader.js** | `static/js/skeleton-loader.js` | HTMX content loading | Active |

### 1.2 Page Skeleton Lifecycle

**Location:** `templates/base.html` lines 1733-1804

**Initial State:**
```css
#page-skeleton {
    display: block !important;  /* Always visible initially */
}
#page-skeleton.hidden {
    display: none !important;  /* Hidden via class */
}
```

**Hide Triggers:**
1. **Immediate hide for fresh PWA launches** (line 1767-1770)
   - Condition: `html.fresh-launch` class present
   - Action: Adds `.hidden` class immediately

2. **DOMContentLoaded event** (line 1781-1789)
   - Condition: Not a fresh PWA launch
   - Delay: 100ms
   - Action: Calls `hidePageSkeleton()`

3. **window.load event** (line 1773-1778)
   - Condition: Not a fresh PWA launch
   - Action: Calls `hidePageSkeleton()`

4. **HTMX afterRequest event** (line 1792-1797)
   - Condition: Not a fresh PWA launch
   - Action: Calls `hidePageSkeleton()`

5. **Failsafe timeout** (line 1800-1803)
   - Delay: 3000ms
   - Action: Calls `hidePageSkeleton()` unconditionally

**App Visibility Control:**
```javascript
function hidePageSkeleton() {
    if (pageSkeleton && !pageSkeleton.classList.contains('hidden')) {
        pageSkeleton.classList.add('hidden');
        if (app) {
            app.classList.add('loaded');  // Sets opacity: 1 !important
            app.style.opacity = '1';
            app.style.pointerEvents = 'auto';
        }
    }
}
```

### 1.3 Startup Splash Lifecycle

**Location:** `templates/base.html` lines 196-320

**Initial State:**
```css
#startup-splash {
    opacity: 0;  /* Hidden by default */
    pointer-events: none;
}
html.fresh-launch #startup-splash,
#startup-splash.show-splash {
    opacity: 1;  /* Visible via class */
    pointer-events: auto;
}
#startup-splash.fade-out {
    opacity: 0;  /* Hidden via class */
    pointer-events: none;
}
```

**Control Script:** `static/js/startup-v2.js`

**Fresh Launch Detection:**
```javascript
const SESSION_KEY = 'pwaninet_launched';

function isFreshLaunch() {
    const alreadyLaunched = sessionStorage.getItem(SESSION_KEY);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    const isIOS = window.navigator.standalone === true;
    const isPWA = isStandalone || isIOS;
    
    const fresh = !alreadyLaunched;
    
    if (fresh) {
        sessionStorage.setItem(SESSION_KEY, 'true');
    }
    
    return fresh;
}
```

**Startup Flow (startup-v2.js):**
1. Check if auth page → skip splash
2. Check if `showLoginWelcome` session flag → skip splash
3. Check if fresh launch → if not, show app immediately
4. If fresh launch:
   - Add `.show-splash` class to startup splash
   - Add `.hide-for-splash` class to app
   - Set progress to 0%
   - Check internet connectivity (progressive attempts: 4000ms, 6000ms, 8000ms)
   - If offline → show offline skeleton after 1500ms
   - If online → set progress to 80%, show "Connected!"
   - Wait 500ms
   - Call `transitionToApp()`:
     - Set progress to 100%
     - Wait 400ms
     - Remove `.show-splash`, add `.fade-out`
     - Remove splash element after 400ms
     - Remove `.hide-for-splash` from app
     - Set app opacity to 1, pointer-events to auto

### 1.4 App Container Lifecycle

**Location:** `templates/base.html` lines 1157, 204-236

**Initial State:**
```css
#app {
    opacity: 0 !important;  /* Hidden by default */
}
#app.loaded {
    opacity: 1 !important;  /* Visible via class */
}
html.fresh-launch #app {
    opacity: 0;  /* Hidden on fresh launch */
}
#app.show {
    opacity: 1;  /* Visible via class */
}
#app.hide-for-splash {
    opacity: 0;  /* Hidden via class */
}
```

**Inline Style:**
```html
<div id="app" style="opacity: 0; /* Hidden until page loads */">
```

**Visibility Control Points:**
1. **Page skeleton script** (base.html line 1752-1754)
   - Adds `.loaded` class
   - Sets `opacity: 1`
   - Sets `pointer-events: auto`

2. **startup-v2.js** (line 181-184)
   - Removes `.hide-for-splash` class
   - Sets `opacity: 1`
   - Sets `pointer-events: auto`

3. **startup-v2.js showAppImmediately()** (line 39-52)
   - Removes `.show-splash` from splash
   - Sets splash display to none
   - Removes `.hide-for-splash` from app
   - Sets app opacity to 1
   - Sets app pointer-events to auto

---

## 2. Application Startup Timeline

### 2.1 Typical Page Load Sequence

```
1. HTML Parsing
   ├─ <head> meta tags, PWA manifest
   ├─ Inline CSS for #page-skeleton (display: block !important)
   ├─ Inline CSS for #startup-splash (opacity: 0)
   ├─ Inline CSS for #app (opacity: 0 !important)
   └─ Inline script: theme detection (localStorage)

2. DOM Construction
   ├─ #page-skeleton element created (visible)
   ├─ #startup-splash element created (hidden)
   ├─ #app element created (hidden)
   └─ Inline script: fresh launch detection
       └─ If fresh launch → add .fresh-launch to html

3. Script Loading
   ├─ /static/js/startup-v2.js
   ├─ /static/js/skeleton-loader.js
   ├─ /static/js/skeleton-init.js
   └─ Other scripts...

4. DOMContentLoaded Event
   ├─ Page skeleton script executes (100ms delay)
   ├─ startup-v2.js executes
   │   ├─ Check fresh launch
   │   ├─ If not fresh → showAppImmediately()
   │   └─ If fresh → start connectivity check
   └─ WebSocket connection (if authenticated)

5. window.load Event
   ├─ Page skeleton script executes
   └─ All resources loaded

6. HTMX Events (if applicable)
   └─ Page skeleton hides on htmx:afterRequest
```

### 2.2 Fresh PWA Launch Sequence

```
1. HTML Parsing
   └─ .fresh-launch class added to html element

2. DOM Construction
   ├─ #page-skeleton visible (display: block)
   ├─ #startup-splash hidden (opacity: 0)
   └─ #app hidden (opacity: 0)

3. Page Skeleton Script (Immediate)
   └─ Detects .fresh-launch → hides #page-skeleton immediately
       Result: Both skeleton and splash are hidden → BLANK SCREEN

4. startup-v2.js Execution
   ├─ Detects fresh launch (sessionStorage check)
   ├─ Adds .show-splash to #startup-splash
   ├─ Adds .hide-for-splash to #app
   └─ Starts connectivity check (4000ms timeout)

5. Connectivity Check
   ├─ Fetch /static/images/favicon.ico
   ├─ If success → progress to 80%
   ├─ Wait 500ms
   └─ transitionToApp()
       ├─ Progress to 100%
       ├─ Wait 400ms
       └─ Show app
```

**Critical Issue:** Step 3 hides the page skeleton BEFORE startup-v2.js shows the splash screen, creating a gap where both are hidden.

### 2.3 Subsequent Navigation Sequence

```
1. HTML Parsing
   └─ No .fresh-launch class (sessionStorage has pwaninet_launched)

2. DOM Construction
   ├─ #page-skeleton visible (display: block)
   ├─ #startup-splash hidden (opacity: 0)
   └─ #app hidden (opacity: 0)

3. Page Skeleton Script (DOMContentLoaded)
   └─ Detects NOT fresh launch → waits 100ms → hides skeleton

4. startup-v2.js Execution
   ├─ Detects NOT fresh launch
   └─ showAppImmediately()
       ├─ Hides splash
       └─ Shows app

5. window.load Event
   └─ Page skeleton script executes (already hidden)
```

**Potential Issue:** If startup-v2.js executes before page skeleton script, app might be shown before skeleton is hidden, causing flash.

---

## 3. Blank Screen Investigation

### 3.1 Root Causes

#### Cause 1: Race Condition Between Page Skeleton and Startup Splash

**Location:** `templates/base.html` lines 1767-1770 vs `static/js/startup-v2.js` line 237

**Issue:**
```javascript
// Page skeleton script (executes immediately when script is parsed)
if (isFreshLaunch && pageSkeleton) {
    pageSkeleton.classList.add('hidden');  // Hides immediately
}

// startup-v2.js (executes after script loads)
if (!splashAlreadyVisible && splash) splash.classList.add('show-splash');  // Shows later
```

**Result:** Gap of ~50-200ms where both skeleton and splash are hidden, and app is still hidden → **BLANK SCREEN**

#### Cause 2: App Never Gets Shown

**Location:** Multiple locations control `#app` visibility

**Issue:** If all systems fail to show the app:
- Page skeleton script fails to execute
- startup-v2.js encounters an error
- Network check times out and error handler fails

**Result:** App remains with `opacity: 0` → **BLANK SCREEN**

#### Cause 3: CSS Specificity Conflict

**Location:** `templates/base.html` lines 111, 214, 226, 234

**Issue:**
```css
#app {
    opacity: 0 !important;  /* Inline CSS, highest specificity */
}
#app.loaded {
    opacity: 1 !important;  /* Class-based, same specificity */
}
```

**Result:** If `.loaded` class is not added, inline style keeps app hidden → **BLANK SCREEN**

#### Cause 4: JavaScript Error Preventing Execution

**Location:** `static/js/startup-v2.js` lines 98-101 (favicon fetch)

**Issue:**
```javascript
fetch('/static/images/favicon.ico', {
    method: 'HEAD',
    cache: 'no-cache'
}).then(function(response) {
    // ... success handling
}).catch(function() {
    // ... error handling - continues to next attempt
});
```

**Result:** If an unhandled error occurs before app is shown, execution stops → **BLANK SCREEN**

### 3.2 Evidence from Code

**File:** `templates/base.html` line 1767-1770
```javascript
// IMMEDIATE ACTION: Hide skeleton for fresh PWA launches (they use startup splash)
if (isFreshLaunch && pageSkeleton) {
    pageSkeleton.classList.add('hidden');
    console.log('[PageSkeleton] Fresh PWA launch - skeleton hidden immediately');
}
```

**File:** `static/js/startup-v2.js` line 237
```javascript
if (!splashAlreadyVisible && splash) splash.classList.add('show-splash');
```

**Timing Gap:** The page skeleton script executes as soon as it's parsed (before DOMContentLoaded), while startup-v2.js must first be loaded from the server. This creates a timing gap.

---

## 4. Loading Screen Flash Investigation

### 4.1 Root Causes

#### Cause 1: Multiple Systems Showing/Hiding Simultaneously

**Issue:** Both page skeleton and startup-v2.js try to control app visibility at the same time.

**Scenario:**
1. Page skeleton shows app (adds `.loaded` class)
2. startup-v2.js shows app (sets `opacity: 1`)
3. Both execute within milliseconds of each other
4. Result: Brief flash as app transitions from hidden to visible twice

#### Cause 2: CSS Transition Conflicts

**Location:** `templates/base.html` lines 201, 215

**Issue:**
```css
#startup-splash {
    transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
#app {
    transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Result:** When both splash fades out and app fades in simultaneously, the 300ms transitions overlap, causing a visible flash.

#### Cause 3: Inline Style vs Class Conflict

**Location:** `templates/base.html` line 1157

**Issue:**
```html
<div id="app" style="opacity: 0; /* Hidden until page loads */">
```

**Result:** When JavaScript sets `style.opacity = '1'`, it conflicts with the inline style, causing the browser to re-render the opacity, creating a flash.

### 4.2 Evidence from Code

**File:** `templates/base.html` line 1752-1754
```javascript
if (app) {
    app.classList.add('loaded');
    app.style.opacity = '1';  // Direct style manipulation
    app.style.pointerEvents = 'auto';
}
```

**File:** `static/js/startup-v2.js` line 181-184
```javascript
if (app) {
    app.classList.remove('hide-for-splash');
    app.style.opacity = '1';  // Also direct style manipulation
    app.style.pointerEvents = 'auto';
}
```

**Conflict:** Both scripts manipulate `style.opacity` directly, potentially causing double transitions.

---

## 5. Service Worker and PWA Investigation

### 5.1 Service Worker Configuration

**Location:** `static/service-worker.js`

**Cache Strategy:**
- **Navigation requests:** Network-first, then cache, then offline fallback
- **Static assets:** Cache-first, then network, then offline fallback
- **API requests:** Network-first, then cache (GET only), then offline fallback

**Core Assets Cached on Install:**
```javascript
const CORE_ASSETS = [
    '/offline.html',
    '/static/css/bootstrap.min.css',
    '/static/css/custom.css',
    '/static/css/splash.css',
    '/static/js/bootstrap.bundle.min.js',
    '/static/js/htmx.min.js',
    '/static/js/splash-screen.js',  // Note: splash-screen.js is cached but not used
    '/static/images/favicon.ico',
    '/static/images/web-app-manifest-192x192.png',
    '/static/images/web-app-manifest-512x512.png'
];
```

**Issue:** `splash-screen.js` is cached but not referenced in base.html. The active script is `startup-v2.js`, which is NOT in the core assets cache.

### 5.2 PWA Manifest

**Location:** `static/manifest.webmanifest`

**Key Settings:**
```json
{
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0f172a",
    "theme_color": "#2563eb",
    "orientation": "portrait-primary"
}
```

**Splash Screens:** Manifest includes 7 splash screen images for different device sizes, but these are native OS splash screens, not the custom JavaScript splash screen.

### 5.3 Service Worker Impact on Loading

**Potential Issue:** Service worker may serve cached versions of startup scripts, causing version mismatches.

**Evidence:**
```javascript
// service-worker.js line 140-177
async function handleStaticAssetRequest(request) {
    try {
        const networkResponse = await fetch(request);
        // Cache the fresh response
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, networkResponse.clone());
        return networkResponse;
    } catch (error) {
        console.log('Service Worker: Network failed for static asset:', request.url);
        // Return offline asset if available
        return await getOfflineAsset(request);
    }
}
```

**Result:** If `startup-v2.js` is cached and the server version changes, the cached version may be used, potentially causing inconsistencies.

---

## 6. Network and Asset Investigation

### 6.1 Health Check Endpoint

**Location:** `pwaninet/urls.py` line 79, `templates/health_check.html`

**Endpoint:** `/api/health/`

**Usage:** Referenced in multiple startup scripts for connectivity checks:
- `startup.js` line 349
- `startup-fixed.js` line 349
- `startup-safe.js` line 390
- `startup-final.js` line 190

**Issue:** `startup-v2.js` (the active script) does NOT use `/api/health/`. Instead, it fetches `/static/images/favicon.ico` for connectivity check.

**Evidence:**
```javascript
// startup-v2.js line 98-101
fetch('/static/images/favicon.ico', {
    method: 'HEAD',
    cache: 'no-cache'
})
```

**Implication:** The health check endpoint exists but is not used by the active startup script.

### 6.2 Asset Loading Order

**base.html Script Loading Order:**
1. Inline theme script (immediate)
2. `/static/js/startup-v2.js`
3. `/static/js/skeleton-loader.js`
4. `/static/js/skeleton-init.js`
5. Other scripts...

**Critical Path:** `startup-v2.js` must load before the splash screen can be shown. If this script loads slowly, the blank screen gap increases.

### 6.3 Network Timeout Configuration

**startup-v2.js Timeouts:**
```javascript
var timeouts = [4000, 6000, 8000];  // Progressive timeouts for connectivity check
```

**Total Maximum Wait:** 4000 + 6000 + 8000 = 18000ms (18 seconds) before offline fallback

**Issue:** If network is slow but available, user waits up to 18 seconds before seeing the app.

---

## 7. JavaScript Runtime Audit

### 7.1 Error Handling

**startup-v2.js Error Handling:**
```javascript
fetch('/static/images/favicon.ico', {
    method: 'HEAD',
    cache: 'no-cache'
}).then(function(response) {
    clearTimeout(attemptTimeout);
    
    if (response.ok) {
        setProgress(80);
        resolve(true);
    } else {
        clearTimeout(attemptTimeout);
        if (attempts < maxAttempts) {
            tryConnect();
        } else {
            resolve(false);
        }
    }
}).catch(function() {
    clearTimeout(attemptTimeout);
    if (attempts < maxAttempts) {
        tryConnect();
    } else {
        resolve(false);
    }
});
```

**Issue:** Errors are caught and handled, but if an error occurs before the splash is shown, the app may never become visible.

### 7.2 Console Errors Found

**Service Worker Errors:**
- `static/service-worker.js` line 55: "Failed to cache core assets"
- `static/service-worker.js` line 119: "Request handling failed"
- `static/service-worker.js` line 537: "Failed to cache page"

**Messaging System Errors:**
- Multiple files in `static/js/messaging/` have error handlers for offline scenarios
- These are expected for offline functionality and not related to loading screen issues

### 7.3 Potential Unhandled Errors

**startup-v2.js:**
- No global try-catch around the main `startUp()` function
- If an error occurs in `checkInternetWithProgress()`, the promise rejects but is not caught
- If `setSplashText()` fails (element not found), it silently fails

**Evidence:**
```javascript
// startup-v2.js line 56-59
function setSplashText(text) {
    const el = document.querySelector('#startup-splash .splash-text');
    if (el) el.textContent = text;  // Silent fail if element not found
}
```

---

## 8. State Dependency Audit

### 8.1 Session Storage Keys

| Key | Purpose | Set By | Checked By |
|-----|---------|--------|------------|
| `pwaninet_launched` | Track if PWA launched in current session | startup-v2.js line 27 | startup-v2.js line 18 |
| `pwaninet_session_started` | Track if session started (unused scripts) | startup.js, startup-fixed.js, startup-safe.js, startup-final.js | Same scripts |
| `showLoginWelcome` | Show welcome modal after login | Login flow | startup-v2.js line 216 |
| `loginWelcomeName` | User name for welcome modal | Login flow | home.html line 369 |

### 8.2 Local Storage Keys

| Key | Purpose | Set By |
|-----|---------|--------|
| `theme` | User theme preference (light/dark) | Theme handler |
| `pwaInstalled` | Track if PWA is installed | native-pwa-install.js |
| `profileNudgeDismissed` | Track if profile nudge dismissed | home_content.html line 49 |

### 8.3 CSS Class Dependencies

| Class | Purpose | Added By | Removed By |
|-------|---------|---------|------------|
| `fresh-launch` | Indicates fresh PWA launch | Inline script base.html | Never removed |
| `show-splash` | Shows startup splash | startup-v2.js | startup-v2.js |
| `fade-out` | Fades out splash | startup-v2.js | Never removed (element removed) |
| `hide-for-splash` | Hides app during splash | startup-v2.js | startup-v2.js |
| `loaded` | Shows app (page skeleton) | base.html script | Never removed |
| `show` | Shows app (startup scripts) | startup-v2.js | Never removed |
| `hidden` | Hides page skeleton | base.html script | Never removed |

### 8.4 State Machine Conflicts

**Issue:** The `fresh-launch` class is added by an inline script in base.html but is never removed. This means:

1. On first load in a session, `fresh-launch` is added
2. Page skeleton sees `fresh-launch` and hides immediately
3. startup-v2.js checks sessionStorage, sees it's a fresh launch
4. startup-v2.js shows splash screen
5. After splash completes, app is shown
6. On subsequent page loads in the same session:
   - `fresh-launch` is still present (never removed)
   - Page skeleton sees `fresh-launch` and hides immediately
   - startup-v2.js checks sessionStorage, sees it's NOT a fresh launch
   - startup-v2.js shows app immediately
   - Result: Works correctly for subsequent loads

**However:** If sessionStorage is cleared (e.g., user closes and reopens browser), `fresh-launch` class is still present but sessionStorage is empty, causing:
- Page skeleton to hide (thinks it's fresh launch)
- startup-v2.js to show splash (thinks it's fresh launch)
- This is actually correct behavior, but the `fresh-launch` class should be removed after first use for clarity.

---

## 9. Root Cause Analysis

### 9.1 Primary Root Cause: Uncoordinated Multiple Loading Systems

**Evidence:**
- 5 different startup script variants exist
- 2 inline loading screens in base.html
- 3 different systems control `#app` visibility
- No single source of truth for loading state

**Impact:**
- Race conditions between systems
- Blank screens when timing doesn't align
- Flashing when systems conflict
- Unpredictable behavior across different scenarios

### 9.2 Secondary Root Cause: Timing Gap in Fresh Launch

**Evidence:**
```javascript
// base.html line 1767-1770 (executes immediately)
if (isFreshLaunch && pageSkeleton) {
    pageSkeleton.classList.add('hidden');  // Hides skeleton
}

// startup-v2.js line 237 (executes after script loads)
if (!splashAlreadyVisible && splash) splash.classList.add('show-splash');  // Shows splash
```

**Impact:**
- Gap of 50-200ms where both skeleton and splash are hidden
- User sees blank screen during this gap
- Worse on slow connections where script loading takes longer

### 9.3 Tertiary Root Cause: CSS Specificity and Inline Styles

**Evidence:**
```html
<div id="app" style="opacity: 0; /* Hidden until page loads */">
```

```css
#app {
    opacity: 0 !important;
}
#app.loaded {
    opacity: 1 !important;
}
```

**Impact:**
- Inline style conflicts with class-based styles
- JavaScript must manipulate inline style directly
- Multiple style manipulations cause reflows and flashes

### 9.4 Contributing Factors

1. **Unused Scripts:** 4 startup script variants are present but not used, creating confusion
2. **Cached Script Not Used:** `splash-screen.js` is cached by service worker but not referenced
3. **Health Check Not Used:** `/api/health/` endpoint exists but active script uses favicon fetch instead
4. **No Global Error Handler:** startup-v2.js has no global try-catch to ensure app is shown even on error
5. **Session Storage Not Cleared:** `fresh-launch` class persists across session but should be cleared

---

## 10. Recommended Fixes

### 10.1 Immediate Fix: Eliminate Timing Gap

**Problem:** Page skeleton hides before startup splash is shown on fresh launches.

**Solution:** Remove the immediate hide logic for fresh launches from page skeleton script. Let startup-v2.js control the entire fresh launch flow.

**File:** `templates/base.html` lines 1766-1770

**Change:** Remove or comment out:
```javascript
// IMMEDIATE ACTION: Hide skeleton for fresh PWA launches (they use startup splash)
if (isFreshLaunch && pageSkeleton) {
    pageSkeleton.classList.add('hidden');
    console.log('[PageSkeleton] Fresh PWA launch - skeleton hidden immediately');
}
```

**Rationale:** The startup-v2.js script will handle showing the splash screen. The page skeleton should only hide after the app is ready to be shown.

### 10.2 Secondary Fix: Consolidate Loading Systems

**Problem:** Multiple competing loading systems cause conflicts.

**Solution:** Choose one loading system and remove the others.

**Recommendation:** Keep startup-v2.js as the primary loading system. Remove:
- Page skeleton logic from base.html (or make it a fallback only)
- Unused startup scripts (startup.js, startup-fixed.js, startup-safe.js, startup-final.js)
- splash-screen.js (if not used)

**Rationale:** Single source of truth eliminates race conditions and conflicts.

### 10.3 Tertiary Fix: Remove Inline Styles

**Problem:** Inline styles on `#app` cause conflicts and flashes.

**Solution:** Remove inline style and rely solely on CSS classes.

**File:** `templates/base.html` line 1157

**Change:** Remove `style="opacity: 0;"` from:
```html
<div id="app" style="opacity: 0; /* Hidden until page loads */">
```

**Rationale:** CSS classes provide better control and avoid style manipulation conflicts.

### 10.4 Additional Improvements

1. **Add Global Error Handler:** Wrap startup-v2.js main function in try-catch to ensure app is shown even on error
2. **Use Health Check Endpoint:** Change startup-v2.js to use `/api/health/` instead of favicon fetch
3. **Clear fresh-launch Class:** Remove `fresh-launch` class after first use for clarity
4. **Add Loading State Indicator:** Add a visual indicator during the transition between loading systems
5. **Remove Unused Scripts:** Delete or move unused startup scripts to a backup directory
6. **Update Service Worker Cache:** Add `startup-v2.js` to core assets cache
7. **Add Failsafe Timeout:** Ensure app is shown after maximum timeout even if all else fails

---

## 11. Testing Recommendations

### 11.1 Test Scenarios

1. **Fresh PWA Launch (Online)**
   - Clear all data (cache, storage, cookies)
   - Launch PWA from home screen
   - Expected: Splash screen shows, then app appears
   - Current Issue: Blank screen gap

2. **Fresh PWA Launch (Offline)**
   - Clear all data
   - Enable airplane mode
   - Launch PWA from home screen
   - Expected: Offline skeleton shows
   - Current Issue: May show blank screen

3. **Subsequent Navigation (Same Session)**
   - Navigate to different page within PWA
   - Expected: App shows immediately without splash
   - Current Issue: May flash

4. **Browser Refresh**
   - Refresh page while in PWA
   - Expected: App shows immediately without splash
   - Current Issue: May show splash or flash

5. **Slow Network**
   - Throttle network to 3G
   - Launch PWA
   - Expected: Splash shows, app loads when ready
   - Current Issue: Long blank screen gap

### 11.2 Diagnostic Logging

Add console logging to track:
- When each loading system shows/hides
- When app visibility changes
- Timestamp of each event
- Current state of all loading systems

**Example:**
```javascript
console.log('[LoadingSystem] timestamp:', Date.now(), 'event:', 'splashShown', 'state': {
    skeletonVisible: !pageSkeleton.classList.contains('hidden'),
    splashVisible: splash.classList.contains('show-splash'),
    appVisible: app.style.opacity === '1'
});
```

---

## 12. Conclusion

The PWANINET MVP loading screen issues are caused by **multiple uncoordinated loading systems** that operate independently without synchronization. The primary issue is a **timing gap** between the page skeleton hiding and the startup splash showing on fresh PWA launches, resulting in blank screens.

**Key Findings:**
- 5 startup script variants exist, but only startup-v2.js is active
- 2 inline loading screens in base.html compete for control
- 3 different systems control `#app` visibility
- No single source of truth for loading state
- Race conditions cause blank screens and flashing

**Recommended Action:**
1. Remove immediate hide logic for fresh launches from page skeleton script
2. Consolidate to a single loading system (startup-v2.js)
3. Remove inline styles and rely on CSS classes
4. Add global error handling and failsafe timeouts

**Expected Outcome:**
- Eliminate blank screen gap on fresh launches
- Eliminate flashing during transitions
- Provide predictable loading behavior across all scenarios
- Simplify codebase by removing unused systems

---

## Appendix A: File Inventory

### Loading System Files
- `templates/base.html` - Main template with inline loading screens
- `templates/startup_base.html` - Alternative startup template
- `static/js/startup-v2.js` - Active startup manager
- `static/js/startup.js` - Legacy startup manager (unused)
- `static/js/startup-fixed.js` - Fixed version (unused)
- `static/js/startup-safe.js` - Safe version (unused)
- `static/js/startup-final.js` - Final version (unused)
- `static/js/splash-screen.js` - Alternative splash manager (unused)
- `static/js/skeleton-loader.js` - HTMX skeleton loader
- `static/js/skeleton-init.js` - Skeleton template registration
- `static/js/offline-skeleton.js` - Offline skeleton handler

### PWA Files
- `static/service-worker.js` - Service worker
- `static/manifest.webmanifest` - PWA manifest
- `templates/health_check.html` - Health check template

### Documentation
- `SKELETON_LOADING_GUIDE.md` - Skeleton loading documentation

---

## Appendix B: CSS Class Reference

### Page Skeleton
- `#page-skeleton` - Skeleton element
- `.hidden` - Hides skeleton (display: none !important)

### Startup Splash
- `#startup-splash` - Splash element
- `.show-splash` - Shows splash (opacity: 1)
- `.fade-out` - Hides splash (opacity: 0)

### App Container
- `#app` - Main app container
- `.loaded` - Shows app (opacity: 1 !important)
- `.show` - Shows app (opacity: 1)
- `.hide-for-splash` - Hides app (opacity: 0)

### HTML Element
- `.fresh-launch` - Added to html on fresh PWA launch

---

**Report End**
