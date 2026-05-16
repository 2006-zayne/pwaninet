# Pwaninet v0.99.06 - Changelog

**Release Date:** May 11, 2026

---

## 🎯 Overview

This release focuses on mobile UI improvements, WebSocket stability fixes, and connection safety enhancements to prevent crashes and false disconnections.

---

## 📱 Mobile Post Card Layout Improvements

### Problem
Post cards in the home feed had padding that prevented them from touching the device walls on mobile devices.

### Solution
Modified mobile-specific CSS to ensure edge-to-edge display while maintaining internal content padding.

### Files Changed
- `posts/templates/posts/partials/post_card.html`
- `posts/templates/posts/home.html`

### Changes
**post_card.html:**
- Removed border-radius override (restored original rounded corners)
- Set horizontal padding to 0 for direct child elements on mobile
- Ensured `width: 100%`, `margin-left: 0`, `margin-right: 0` on mobile

**home.html:**
- Added specific rule to remove padding from `main.container` on mobile
- Existing media query already removed padding from `.container` and `.container-fluid`

### Result
Post cards now touch device walls on mobile with no gaps, while maintaining internal content padding for readability.

---

## 🔧 WebSocket Consumer Disconnect Safety Refactor

### Problem
The `ChatConsumer.disconnect()` method had several safety issues:
- Unsafe attribute access (`self.user`, `self.room_group_name`)
- Potential crashes on disconnect
- Unstable connection count logic
- Race conditions causing incorrect online/offline state

### Solution
Refactored `disconnect()` to be crash-safe and race-condition safe.

### Files Changed
- `messaging/consumers.py`

### Changes
1. **Safe guard at function start** - Store `user_id` using `getattr()` and return early if None
2. **Safe heartbeat cleanup** - Use `getattr(self, "heartbeat_task", None)` instead of direct access
3. **Safe group cleanup** - Store `room_group_name` using `getattr()` and check before calling `group_discard`
4. **Safe tracker unregister** - Always call `unregister_connection()` with stored `user_id`
5. **Connection count clamping** - Clamp to 0 if `connection_count <= 0` to prevent negative values
6. **Debug logging** - Added print statement showing connection count after disconnect
7. **Safe username access** - Use `getattr(self.user, "username", "")` instead of direct access
8. **Offline toggle safety** - Only mark offline when `connection_count == 0`

### Result
- No AttributeError on disconnect
- No duplicate offline toggles
- Connection count never negative or inconsistent
- Logs show stable lifecycle transitions

---

## 🔄 WebSocket Client-Side Heartbeat Fix

### Problem
Client-side WebSocket logic used silence-based detection that caused false disconnections:
- Assumed socket was dead if no messages arrived within 60-90 seconds
- Triggered unnecessary reconnect loops
- Caused duplicate connections on server
- Broke online/offline presence logic

### Solution
Replaced silence-based detection with proper heartbeat-based connection health system.

### Files Changed
- `static/js/chat/core/websocket.js`

### Changes
1. **Removed silence-based disconnect logic** - Deleted 60-90 second timeout
2. **Added ping/pong handler** - Server pings responded with pongs, updates `lastHeartbeatTime`
3. **Implemented heartbeat-based health check** - 3-minute timeout (180000ms) monitors heartbeat age
4. **Added reconnect guard** - `reconnectInProgress` flag prevents duplicate reconnection attempts
5. **Removed message-based assumptions** - Connection health now depends solely on ping/pong heartbeat

### Result
- WebSocket stays open even if idle for 10+ minutes
- Reconnects only on real socket close or heartbeat failure
- No duplicate connections on server
- Stable online/offline presence

---

## 📊 Summary

**Total Files Modified:** 3
- `posts/templates/posts/partials/post_card.html`
- `posts/templates/posts/home.html`
- `messaging/consumers.py`
- `static/js/chat/core/websocket.js`

**Key Improvements:**
- ✅ Mobile post cards touch device walls
- ✅ WebSocket disconnect is crash-safe
- ✅ No false disconnections from silence detection
- ✅ Stable connection counting
- ✅ Proper online/offline presence

---

## 🔍 Technical Details

### WebSocket Connection Flow
1. Client connects to `/ws/chat/{conversationId}/`
2. Server heartbeat sends ping every 30 seconds
3. Client responds with pong, updates `lastHeartbeatTime`
4. Client monitors heartbeat age (10-second interval)
5. If heartbeat age > 3 minutes, client reconnects
6. Server tracks connections in Redis with 10-minute timeout
7. Max 50 connections per user (force-clear if exceeded)

### Mobile CSS Media Query
```css
@media (max-width: 767px) {
  .post-card {
    width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }
}
```

---

## 🚀 Next Steps
- Monitor WebSocket connection stability in production
- Consider adjusting heartbeat timeout based on real-world usage
- Evaluate if 50 connection limit needs adjustment

---

**Version:** v0.99.06
**Status:** Released
