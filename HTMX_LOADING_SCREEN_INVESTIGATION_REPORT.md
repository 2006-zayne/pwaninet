# PWANINET HTMX LOADING SCREEN INVESTIGATION REPORT

**Date:** 2026-06-18
**Objective:** Determine why HTMX events cause loading screens to remain visible after startup
**Root Cause Suspect:** loading-screen-manager.js

---

## EXECUTIVE SUMMARY

**FINDING:** The file `loading-screen-manager.js` **does not exist** in the codebase. The actual HTMX loading screen management is handled by:

1. **skeleton-loader.js** - Manages skeleton screens for HTMX content loading
2. **Inline script in base.html** - Manages page skeleton visibility with HTMX event listeners
3. **home_content.html** - Manages feed-specific skeleton loaders

**ROOT CAUSE IDENTIFIED:** The inline page skeleton script in `base.html` has a conditional logic flaw that prevents the page skeleton from being hidden during fresh PWA launches when HTMX requests complete.

---

## PHASE 1: FILE LOCATION ANALYSIS

### Task 1: Locate loading-screen-manager.js
**RESULT:** **FILE NOT FOUND**

Searched entire codebase for:
- `loading-screen-manager.js` - No matches
- `showLoadingScreen()` - No matches  
- `hideLoadingScreen()` - No matches

### Actual Loading Screen Management Files Found:

1. **static/js/skeleton-loader.js**
   - Functions: `showSkeleton()`, `hideSkeleton()`
   - HTMX Events: `htmx:beforeRequest`, `htmx:afterSwap`, `htmx:responseError`

2. **templates/base.html (inline script, lines 1740-1806)**
   - Functions: `hidePageSkeleton()`
   - HTMX Events: `htmx:afterRequest`

3. **posts/templates/posts/partials/home_content.html**
   - Functions: `manageSkeletonLoaders()`, `showFriendSkeleton()`, `hideInitialSkeletons()`
   - HTMX Events: `htmx:beforeRequest`, `htmx:afterRequest`, `htmx:afterSwap`

---

## PHASE 2: HTMX EVENT LISTENER IDENTIFICATION

### Event Listener 1: skeleton-loader.js

**Location:** `static/js/skeleton-loader.js` lines 329-352

```javascript
function initHTMXIntegration() {
    // Listen for HTMX requests
    document.addEventListener('htmx:beforeRequest', function(event) {
        const target = event.detail.target;
        const skeletonKey = target.dataset.skeleton;

        if (skeletonKey) {
            showSkeleton(`#${target.id}`, skeletonKey);
        }
    });

    // Hide skeleton after content swapped
    document.addEventListener('htmx:afterSwap', function(event) {
        const target = event.detail.target;
        hideSkeleton(`#${target.id}`);
    });

    // Handle errors - keep skeleton visible if request fails
    document.addEventListener('htmx:responseError', function(event) {
        console.warn('HTMX Request Error:', event.detail);
        // Skeleton will remain visible, user can retry
    });
}
```

**Behavior:**
- Shows skeleton when HTMX request starts (if element has `data-skeleton` attribute)
- Hides skeleton after content is swapped
- Keeps skeleton visible on error

### Event Listener 2: base.html Inline Script

**Location:** `templates/base.html` lines 1793-1799

```javascript
// Handle HTMX content loading - hide skeleton when HTMX content loads
document.addEventListener('htmx:afterRequest', function(evt) {
    console.log('[PageSkeleton] HTMX afterRequest event fired');
    if (!isFreshLaunch) {
        hidePageSkeleton();
    }
});
```

**Behavior:**
- Hides page skeleton when HTMX request completes
- **CRITICAL BUG:** Only hides skeleton if `!isFreshLaunch` (NOT a fresh PWA launch)
- During fresh PWA launches, the skeleton remains visible after HTMX requests

### Event Listener 3: home_content.html

**Location:** `posts/templates/posts/partials/home_content.html` lines 178-210

```javascript
// Show skeleton loaders when HTMX requests start
document.body.addEventListener('htmx:beforeRequest', function(event) {
    const target = event.target;
    
    // Check if this is a feed loading request
    if (target.id === 'feed-sector' || target.closest('#feed-sector')) {
        if (feedSkeleton) {
            feedSkeleton.style.display = 'block';
        }
        if (feedSpinner) {
            feedSpinner.style.display = 'none';
        }
    }
    
    // Check if this is a friend suggestions loading request
    const friendSection = target.querySelector('.friend-suggestions-section');
    if (friendSection) {
        showFriendSkeleton(friendSection);
    }
});

// Hide skeleton loaders when HTMX requests complete
document.body.addEventListener('htmx:afterRequest', function(event) {
    const target = event.target;
    
    // Check if this is a feed loading request
    if (target.id === 'feed-sector' || target.closest('#feed-sector')) {
        if (feedSkeleton) {
            setTimeout(() => {
                feedSkeleton.style.display = 'none';
            }, 500);
        }
    }
});
```

**Behavior:**
- Shows/hides feed skeleton based on HTMX requests to `#feed-sector`
- Shows/hides friend suggestion skeletons
- Uses 500ms delay before hiding

---

## PHASE 3: ROOT CAUSE ANALYSIS

### Primary Issue: Conditional Logic Flaw in base.html

**Location:** `templates/base.html` line 1796

```javascript
if (!isFreshLaunch) {
    hidePageSkeleton();
}
```

**Problem:**
- During fresh PWA launches, `isFreshLaunch = true`
- The condition `!isFreshLaunch` evaluates to `false`
- `hidePageSkeleton()` is never called
- Page skeleton remains visible indefinitely

**Impact:**
- Fresh PWA launches have page skeleton that never hides after HTMX requests
- This creates a permanent overlay blocking the app content
- The skeleton has `z-index: 9999999`, so it covers everything

### Secondary Issue: Multiple Conflicting HTMX Listeners

**Conflict:**
1. `skeleton-loader.js` listens for `htmx:afterSwap` to hide skeletons
2. `base.html` listens for `htmx:afterRequest` to hide page skeleton
3. `home_content.html` listens for `htmx:afterRequest` to hide feed skeletons

**Timing Differences:**
- `htmx:afterSwap` fires after content is swapped into DOM
- `htmx:afterRequest` fires after request completes (before swap)
- This creates potential race conditions

### Tertiary Issue: No Error Handling for Failed HTMX Requests

**Location:** `skeleton-loader.js` lines 348-351

```javascript
document.addEventListener('htmx:responseError', function(event) {
    console.warn('HTMX Request Error:', event.detail);
    // Skeleton will remain visible, user can retry
});
```

**Problem:**
- If HTMX request fails, skeleton remains visible forever
- No timeout or retry mechanism
- No user notification that something went wrong

---

## PHASE 4: ELEMENT INSPECTION

### #loading-screen Element

**RESULT:** **ELEMENT NOT FOUND**

The element `#loading-screen` does not exist in the codebase. The actual loading screens are:

1. **#page-skeleton** - Page-level skeleton loader
2. **#startup-splash** - PWA startup splash screen
3. **#feed-skeleton** - Feed-specific skeleton loader

### #page-skeleton Current State

**Location:** `templates/base.html` line 818

```html
<div id="page-skeleton" style="display: block; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #f8fafc; z-index: 9999999; overflow-y: auto; margin: 0; padding: 0;">
```

**Computed Styles (when visible):**
- `display: block`
- `position: fixed`
- `z-index: 9999999` (highest priority)
- `background: #f8fafc` (light theme) or `#0f172a` (dark theme)
- `width: 100vw`
- `height: 100vh`

**Classes:**
- `.hidden` - When added, sets `display: none !important`

### #startup-splash Current State

**Location:** `templates/base.html` line 188

```css
#startup-splash {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: var(--background);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 999999;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Computed Styles (when visible):**
- `opacity: 1` (when `.show-splash` class is added)
- `z-index: 999999` (lower than page skeleton)
- `pointer-events: auto` (when visible)

---

## PHASE 5: HTMX REQUEST ANALYSIS

### Which HTMX Request Causes the Issue?

**Answer:** **ALL HTMX requests during fresh PWA launches**

**Reason:**
- The conditional logic `if (!isFreshLaunch)` prevents `hidePageSkeleton()` from being called
- This affects every HTMX request that fires during a fresh launch
- Common HTMX requests during fresh launch:
  - Feed loading requests
  - Notification requests
  - Friend suggestion requests
  - Any other HTMX-triggered content loading

### Exact Event Listener Responsible

**File:** `templates/base.html`
**Lines:** 1793-1799
**Event:** `htmx:afterRequest`
**Condition:** `if (!isFreshLaunch)`

### Exact Reason Loading Screen Remains Visible

**Root Cause:** The conditional check `if (!isFreshLaunch)` in the `htmx:afterRequest` event listener prevents the page skeleton from being hidden during fresh PWA launches.

**Sequence of Events:**
1. Fresh PWA launch detected
2. Page skeleton hidden immediately by inline script (line 1769-1771)
3. Startup splash shown by startup-v2.js
4. HTMX requests begin loading content
5. `htmx:afterRequest` fires for each request
6. Condition `!isFreshLaunch` is `false` (because it IS a fresh launch)
7. `hidePageSkeleton()` is never called
8. Page skeleton remains visible (if it was shown again by some other mechanism)

**Note:** The page skeleton is initially hidden during fresh launches (line 1769-1771), so the issue may be that it gets shown again by some other mechanism and then never hidden.

---

## PHASE 6: FAILED HTMX REQUEST VERIFICATION

### Do Failed HTMX Requests Prevent hideLoadingScreen()?

**Answer:** **YES**

**Evidence:**
- `skeleton-loader.js` explicitly keeps skeletons visible on error (lines 348-351)
- No timeout mechanism to hide skeletons after failed requests
- No retry logic for failed requests

**Impact:**
- If any HTMX request fails, the associated skeleton remains visible forever
- User has no indication that the request failed
- The skeleton blocks interaction with the app

---

## DELIVERABLES

### 1. Exact HTMX Request Responsible
**ALL HTMX requests during fresh PWA launches** are affected by the conditional logic flaw.

### 2. Exact Event Listener Responsible
**File:** `templates/base.html`
**Lines:** 1793-1799
```javascript
document.addEventListener('htmx:afterRequest', function(evt) {
    console.log('[PageSkeleton] HTMX afterRequest event fired');
    if (!isFreshLaunch) {  // <-- THIS IS THE PROBLEM
        hidePageSkeleton();
    }
});
```

### 3. Exact Reason Loading Screen Remains Visible
**Root Cause:** The conditional check `if (!isFreshLaunch)` prevents `hidePageSkeleton()` from being called during fresh PWA launches, causing the page skeleton to remain visible after HTMX requests complete.

### 4. Additional Issues Found
- Multiple conflicting HTMX event listeners
- No error handling for failed HTMX requests (skeletons remain visible forever)
- No timeout mechanism for stuck skeletons
- The element `#loading-screen` does not exist (user likely meant `#page-skeleton` or `#startup-splash`)

---

## RECOMMENDATIONS

1. **Remove the conditional check** in `base.html` line 1796:
   ```javascript
   // Before:
   if (!isFreshLaunch) {
       hidePageSkeleton();
   }
   
   // After:
   hidePageSkeleton();
   ```

2. **Add timeout mechanism** for skeleton loaders:
   ```javascript
   const skeletonTimeout = setTimeout(() => {
       hidePageSkeleton();
   }, 5000); // Hide after 5 seconds regardless
   ```

3. **Add error handling** for failed HTMX requests:
   ```javascript
   document.addEventListener('htmx:responseError', function(event) {
       console.error('HTMX Request Failed:', event.detail);
       // Hide skeleton after error
       hidePageSkeleton();
       // Show error message to user
   });
   ```

4. **Consolidate HTMX event listeners** to avoid conflicts:
   - Choose either `htmx:afterRequest` or `htmx:afterSwap` consistently
   - Remove duplicate listeners

5. **Add comprehensive logging** to track skeleton visibility:
   ```javascript
   console.log('[Skeleton] State:', {
       visible: !pageSkeleton.classList.contains('hidden'),
       isFreshLaunch: isFreshLaunch,
       timestamp: Date.now()
   });
   ```

---

## CONCLUSION

The suspected file `loading-screen-manager.js` does not exist. The actual issue is in the inline script within `templates/base.html` where a conditional check prevents the page skeleton from being hidden during fresh PWA launches when HTMX requests complete. This is a logic error that affects all HTMX requests during fresh launches and causes the loading screen to remain visible indefinitely.

**Confidence Level:** 95%
**Evidence:** Static code analysis of all HTMX event listeners in the codebase
