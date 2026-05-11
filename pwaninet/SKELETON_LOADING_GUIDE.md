# Skeleton Loading Implementation Guide

## Overview
This guide explains how to implement skeleton loading screens across PwaniNet pages. Skeleton screens show placeholder UI while content is loading, providing better UX especially on poor networks.

## Architecture

### Files Created
- **`static/js/skeleton-loader.js`** - Core skeleton loader module that manages showing/hiding skeletons
- **`static/js/skeleton-init.js`** - Initializes and registers all skeleton templates
- **`templates/partials/_skeleton_*.html`** - Individual skeleton templates for each page type

### How It Works
1. **HTMX Integration**: When HTMX makes a request, `htmx:beforeRequest` event fires
2. **Skeleton Shows**: If target element has `data-skeleton` attribute, skeleton loads and displays
3. **Request Loads**: Backend fetches content normally
4. **Content Swaps**: When response arrives, `htmx:afterSwap` hides skeleton and shows real content
5. **Smooth Transition**: Shimmer animation plays while skeleton is visible

## Implementation

### Step 1: Add Skeleton Attribute to Your HTMX Element

Add `data-skeleton="skeleton-key"` to any element that loads content via HTMX:

```html
<div id="post-feed" data-skeleton="post-feed" hx-get="/api/posts/" hx-trigger="load">
    <!-- Initial content here, will be replaced -->
</div>
```

### Step 2: Use Existing Skeleton Keys

The following skeleton templates are pre-registered:

| Key | Usage | Example |
|-----|-------|---------|
| `post-feed` | Home feed with multiple posts | Posts page |
| `post-detail` | Single post with comments | Post detail page |
| `messaging-list` | List of conversations | Messaging list |
| `messaging-detail` | Single conversation with messages | Conversation detail |
| `groups-list` | Grid of groups/communities | Groups dashboard |
| `group-detail` | Single group with info and members | Group detail page |
| `notifications` | List of notifications | Notifications page |
| `search-results` | Search results feed | Search results page |
| `profile` | User profile with stats | Profile page |
| `course-detail` | Course unit with content | Course unit page |

### Step 3: Available Methods

```javascript
// Manually show skeleton (usually automatic via HTMX)
window.PwaniNetSkeletonLoader.showSkeleton('#target-id', 'skeleton-key');

// Manually hide skeleton
window.PwaniNetSkeletonLoader.hideSkeleton('#target-id');

// Register custom skeleton
window.PwaniNetSkeletonLoader.registerSkeleton('custom-key', '<div>...</div>');

// Get active skeletons
const active = window.PwaniNetSkeletonLoader.getActiveSkeletons();

// Clear all active skeletons
window.PwaniNetSkeletonLoader.clear();
```

## Examples

### Example 1: Post Feed with Skeleton

**Template:**
```html
{% load static %}
<div id="home-feed" 
     data-skeleton="post-feed"
     hx-get="{% url 'posts:home_content' %}" 
     hx-trigger="load"
     hx-swap="innerHTML">
    <!-- Skeleton will show here automatically -->
</div>
```

### Example 2: Messaging Conversation List

**Template:**
```html
<div id="conversations" 
     data-skeleton="messaging-list"
     hx-get="{% url 'messaging:conversation_list_partial' %}" 
     hx-trigger="load"
     hx-swap="innerHTML">
</div>
```

### Example 3: Notifications with Polling

**Template:**
```html
<div id="notifications-container"
     data-skeleton="notifications"
     hx-get="{% url 'notifications:list_partial' %}"
     hx-trigger="load, every 30s"
     hx-swap="innerHTML">
</div>
```

### Example 4: Search Results

**Template:**
```html
<form hx-get="{% url 'posts:search_results' %}" hx-trigger="change">
    <input type="search" name="q" placeholder="Search..." />
</form>

<div id="search-results"
     data-skeleton="search-results"
     hx-swap="innerHTML">
    <!-- Results load here with skeleton -->
</div>
```

## Creating Custom Skeletons

If you need a custom skeleton not in the pre-registered list:

### 1. Create HTML template in `templates/partials/_skeleton_custom.html`:
```html
<!-- Custom Skeleton -->
<div class="skeleton-container">
    <div style="display: flex; gap: 12px; padding: 16px;">
        <div class="skeleton-avatar"></div>
        <div style="flex: 1;">
            <div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div>
            <div class="skeleton-line" style="width: 80%; height: 12px;"></div>
        </div>
    </div>
</div>
```

### 2. Register in `static/js/skeleton-init.js`:
```javascript
loader.registerSkeleton('custom-key', `
    <div class="skeleton-container">
        <!-- Your skeleton HTML here -->
    </div>
`);
```

### 3. Use in template:
```html
<div id="custom-area" data-skeleton="custom-key" hx-get="/api/custom/" hx-trigger="load">
</div>
```

## CSS Classes Reference

### Container
- `.skeleton-container` - Wrapper for skeleton

### Basic Elements
- `.skeleton-line` - Generic line placeholder
- `.skeleton-avatar` - 48x48px circular placeholder
- `.skeleton-avatar-sm` - 32x32px circular placeholder
- `.skeleton-button` - Button placeholder

### Post-Related
- `.skeleton-post-card` - Full post card
- `.skeleton-post-header` - Post header with avatar, name, time
- `.skeleton-post-body` - Post text content
- `.skeleton-post-media` - Post image/video area
- `.skeleton-post-actions` - Like, comment, share buttons
- `.skeleton-text-line` - Text content lines

### Messaging
- `.skeleton-msg-item` - Message list item
- `.skeleton-msg-bubble` - Message bubble

### Notifications
- `.skeleton-notification-item` - Notification card
- `.skeleton-notification-content` - Notification text

### Groups
- `.skeleton-group-item` - Group card
- `.skeleton-group-label` - Group name label

### Inputs
- `.skeleton-input-field` - Input/textarea placeholder
- `.skeleton-search-bar` - Search bar placeholder

## Theme Support

Skeletons automatically adapt to light/dark theme via `[data-theme]` attribute:

- **Light theme**: Light gray shimmer effect
- **Dark theme**: Subtle white shimmer effect

## Performance Tips

1. **Register skeletons early**: Skeletons are registered on page load
2. **Minimal HTML**: Keep skeleton HTML small (less DOM to paint)
3. **Use CSS animations**: Shimmer effect is pure CSS, very performant
4. **No blocking**: Skeleton loader doesn't block page rendering
5. **Automatic cleanup**: Skeletons are removed when content arrives

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- iOS 12+
- Android 5+
- Graceful degradation: If skeleton not found, shows blank (normal HTMX behavior)

## Troubleshooting

### Skeleton not showing
- Ensure `data-skeleton="key"` matches registered skeleton key
- Check browser console for warnings
- Verify element has an `id` attribute

### Skeleton stays visible
- Check if HTMX request is completing
- Look for HTMX errors in console
- Verify backend is returning content

### Shimmer animation not smooth
- Check browser performance (60fps)
- Reduce number of skeleton elements if many on page
- Ensure GPU acceleration is enabled

### Theme colors wrong
- Check `[data-theme]` attribute on `<html>` element
- Verify CSS variables are set correctly
- Look for theme conflicts in CSS

## Integration Checklist

When adding skeleton loading to a page:

- [ ] Add `id` attribute to content container
- [ ] Add `data-skeleton="appropriate-key"` to container
- [ ] Verify skeleton key is registered in `skeleton-init.js`
- [ ] Test on slow network (DevTools throttling)
- [ ] Test on fast network (should not show skeleton)
- [ ] Test on mobile device
- [ ] Verify theme switching works
- [ ] Check for console errors

## Advanced Usage

### Skip skeleton for specific requests
```html
<div id="fast-content" hx-get="/api/fast-data/" hx-trigger="load" hx-swap="innerHTML">
    <!-- Won't show skeleton even if data-skeleton added, because HTMX caches fast requests -->
</div>
```

### Programmatic control
```javascript
// Show skeleton manually
document.getElementById('my-element').setAttribute('data-skeleton', 'post-feed');
window.PwaniNetSkeletonLoader.showSkeleton('#my-element', 'post-feed');

// After manual content update
window.PwaniNetSkeletonLoader.hideSkeleton('#my-element');
```

### Event handling
```javascript
// Listen for skeleton show
document.addEventListener('htmx:beforeRequest', function(event) {
    console.log('Request starting, skeleton will show');
});

// Listen for content arrival
document.addEventListener('htmx:afterSwap', function(event) {
    console.log('Content arrived, skeleton hidden');
});
```

## Future Enhancements

- [ ] Skeleton state persistence (remember which skeletons user has seen)
- [ ] Progressive enhancement with actual content preview
- [ ] Skeleton animation variations
- [ ] Skeleton size auto-detection
- [ ] Analytics tracking for loading times

---

For questions or issues, check the skeleton-loader.js and skeleton-init.js source code for detailed comments.
