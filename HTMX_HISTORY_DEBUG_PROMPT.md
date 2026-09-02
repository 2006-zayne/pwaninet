# HTMX Browser History Navigation Debug Prompt

## Context

We have successfully migrated the Profile page to use HTMX navigation following the Home page architecture. The implementation includes:

- Navigation partials for Home and Profile pages
- HTMX attributes on navigation links (hx-get, hx-target, hx-swap, hx-push-url, hx-history="true")
- Out-of-band swaps for floating actions
- Active state management via JavaScript

## Current Issue

Browser back and forward buttons are not working correctly. When users click back/forward, the page renders blank with scattered nav header content instead of properly restoring the cached content.

## What We've Tried

1. **Added htmx:historyNavigate handler** - to update active state on history navigation
2. **Added hx-history="true"** to all Home and Profile navigation links:
   - Desktop brand/logo Home link
   - Desktop Home nav chip
   - Mobile Home nav chip
   - Desktop Profile avatar link
   - Mobile Profile nav chip
3. **Changed to htmx:historyRestore handler** - to update active state after content restoration

## Expected Behavior

When using browser back/forward buttons:
- Content should be restored from HTMX history cache
- No blank pages or scattered content
- Active nav chip should reflect current page
- Floating actions should appear/disappear correctly

## Actual Behavior

- Pages render blank with scattered nav header content
- Content not properly restored from cache
- Navigation broken

## Files to Review

1. **`templates/base.html`** - Navigation links and active state management script
2. **`users/templates/users/partials/profile_navigation_partial.html`** - Profile navigation partial
3. **`posts/templates/posts/partials/home_navigation_partial.html`** - Home navigation partial
4. **`users/views.py`** - Profile view HTMX request detection

## Key Code Sections

### Navigation Links (base.html)
```html
<a href="{% url 'posts:home' %}"
   hx-get="{% url 'posts:home' %}"
   hx-target="#page-content-target"
   hx-swap="innerHTML"
   hx-push-url="true"
   hx-history="true">
```

### Active State Management (base.html)
```javascript
document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'page-content-target' && evt.detail.xhr.status === 200 && evt.detail.xhr.responseURL) {
        updateActiveState(evt.detail.xhr.responseURL);
    }
});

document.body.addEventListener('htmx:historyRestore', function(evt) {
    updateActiveState(window.location.pathname);
});
```

## Investigation Tasks

1. **Check HTMX history cache** - Is content being cached correctly?
2. **Verify hx-history attribute** - Is it being processed correctly?
3. **Test with hx-history="false"** - Does disabling history caching fix the issue (at the cost of no back/forward support)?
4. **Check for JavaScript errors** - Are there console errors during history navigation?
5. **Verify target element** - Is `#page-content-target` being correctly restored?
6. **Check for conflicting scripts** - Are other scripts interfering with HTMX history?

## Potential Solutions

1. **Disable HTMX history for Profile** - Use full page loads on back/forward
2. **Manual history restoration** - Implement custom history handling
3. **Fix HTMX configuration** - Ensure HTMX is properly configured for history
4. **Debug HTMX events** - Add logging to see which events fire and when

## Testing Steps

1. Navigate from Home to Profile
2. Click browser back button
3. Observe: Is content restored? Any console errors?
4. Click browser forward button
5. Observe: Is content restored? Any console errors?
6. Check browser DevTools Network tab - Are requests being made?
7. Check HTMX history cache in DevTools Application/Storage

## Success Criteria

- Browser back button returns to previous page with correct content
- Browser forward button returns to next page with correct content
- No blank pages or scattered content
- Active state updates correctly
- Floating actions appear/disappear correctly
