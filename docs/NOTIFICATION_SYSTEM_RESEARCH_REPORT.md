# Notification System Research Report

**Date:** 2025-01-09  
**Purpose:** Deep analysis of notification architecture, creation paths, rendering flow, and inconsistencies.

## Executive Summary

PwaniNet uses a **hybrid notification system**:
- **Primary:** Event-driven (PlatformEvent → RulesEngine → NotificationObject)
- **Secondary:** Direct creation (NotificationObject.objects.create/bulk_create)

**Finding:** The event-driven system is actively used for most notifications. Direct creation only exists in one location (post sharing). Both paths converge on the same rendering pipeline.

## 1. Architecture Overview

### Core Models
- **PlatformEvent:** Immutable event facts (what happened)
- **NotificationObject:** Mutable user notifications (what to display)
- **NotificationAction:** First-class notification actions

### Event-Driven Pipeline
```
User Action → Signal → publish_event() → PlatformEvent 
→ post_save → RulesEngine → NotificationObject → PreferenceEngine 
→ AggregationEngine → DeliveryEngine
```

### Rendering Pipeline
```
NotificationObject → NotificationObjectAdapter → NotificationPayload 
→ ProfileDrivenRenderer → ProfileResolver → MessageEngine 
→ ComponentVisibilityResolver → PreviewResolver → ActionResolver 
→ render_to_string() → HTML
```

## 2. Notification Creation Paths

### 2.1 Event-Driven (Primary)

**Location:** `notifications/signals.py`

| Notification | Signal | Event Type | Metadata |
|-------------|--------|------------|----------|
| Like | create_like_notification | posts.post.liked | thumbnail_url, resource_type |
| Comment | create_comment_notification | posts.comment.created | thumbnail_url, resource_type |
| Comment Reply | create_comment_notification | posts.comment.replied | thumbnail_url, resource_type |
| Comment Like | create_comment_like_notification | posts.comment.liked | comment_content |
| Follow | create_follow_notification | users.user.followed | follower_username |
| Pinch | create_pinch_notification | users.user.pinched | pinch_username |
| Group Request | create_membership_notification | groups.member.requested | group_name |
| Group Approved | create_membership_notification | groups.member.approved | group_name |
| Group Rejected | create_membership_notification | groups.member.rejected | group_name |
| Document Uploaded | document_uploaded_or_published | documents.document.uploaded | thumbnail_url, resource_type |
| Document Published | document_uploaded_or_published | documents.document.published | thumbnail_url, resource_type |

**Document signals location:** `documents/signals.py`

### 2.2 Direct Creation (Legacy)

**Location:** `posts/serializers.py` (lines 398-415)

- **Only use case:** Post sharing to specific users
- **Method:** `NotificationObject.objects.bulk_create()`
- **Reason:** Custom recipient logic not supported by event system rules
- **Metadata includes:** thumbnail_url, resource_type, target_type, target_id

### 2.3 Test Creation

Various test files use direct `NotificationObject.objects.create()` for testing only.

## 3. Rendering System

### 3.1 Entry Points

1. **Template Tag:** `notifications/templatetags/notifications_rendering.py`
   - Filter: `{{ notification|render_notification }}`
   - Used in: notification_list_items.html, notification_list_grouped.html

2. **Service Function:** `notifications/rendering/service.py`
   - Function: `render_notification()`
   - Used in: views.py (imported but not actively used)

3. **API Endpoint:** `notifications/rendering/api_views.py`
   - URL: `/notifications/api/rendering/render/`
   - Purpose: Testing

### 3.2 Key Components

**NotificationObjectAdapter** (`notifications/rendering/adapters.py`)
- Converts NotificationObject to NotificationPayload
- `_resolve_resource()`: Prioritizes thumbnail_url from metadata
- `_get_post_image_url()`: Fallback to post images, video poster, document preview

**ProfileDrivenRenderer** (`notifications/rendering/profile_driven_renderer.py`)
- Orchestrates rendering pipeline
- Uses Rendering Profiles for type-specific behavior

**RenderingProfileRegistry** (`notifications/rendering/profile_registry.py`)
- Central registry of notification type profiles
- LIKE profile: `preview=True`, `preview_type="POST"`

**Template** (`notifications/templates/notifications/components/notification_card_profile_driven.html`)
- Lines 298-341: Preview rendering section
- Condition: `payload.resource.image_url` must be present

## 4. Data Flow: Like Notification Example

```
1. User likes post → Like model saved
2. Signal: create_like_notification (notifications/signals.py:10)
3. Determine thumbnail_url (post.thumbnail → images → video poster → document)
4. publish_event() with metadata including thumbnail_url
5. PlatformEvent.objects.create()
6. post_save signal → RulesEngine.process_event()
7. POST_LIKE_RULE matched → recipient: post owner
8. NotificationObject.objects.create() with metadata
9. User views notifications → notifications_list view
10. build_notifications_context() → get_notifications_for_user()
11. Template: notification_list_items.html
12. Filter: {{ notification|render_notification }}
13. NotificationObjectAdapter.to_standard_payload()
14. _resolve_resource() → thumbnail_url from metadata
15. ProfileDrivenRenderer.render()
16. Template: notification_card_profile_driven.html
17. Preview displayed if payload.resource.image_url exists
```

## 5. Inconsistencies and Issues

### 5.1 Dual Creation Paths
- **Issue:** Two different ways to create notifications
- **Impact:** Inconsistent metadata propagation
- **Status:** Direct creation only in post sharing (minimal impact)

### 5.2 Missing Rules
- **Issue:** Comment like notifications have signal but no rule
- **Location:** `create_comment_like_notification` exists but no corresponding rule in rules.py
- **Impact:** Comment likes may not create notifications

### 5.3 Deprecated Services
- **Issue:** `groups/services/group_notification_service.py` exists but marked as deprecated
- **Impact:** Potential confusion, redundant code

### 5.4 Metadata Inconsistency
- **Issue:** Direct creation includes target_type/target_id, event-driven may not
- **Impact:** Resource resolution may fail for some notifications

### 5.5 Preview Display Logic
- **Issue:** Template checks `payload.resource.image_url` but adapter may not always populate it
- **Impact:** Previews may not display even when metadata has thumbnail_url

## 6. Recommendations

1. **Migrate post sharing to event system:** Create custom recipient resolution for post sharing
2. **Add missing rule:** Create rule for comment like notifications
3. **Remove deprecated code:** Delete or update group_notification_service.py
4. **Standardize metadata:** Ensure all event-driven paths include target_type/target_id
5. **Improve preview logic:** Ensure adapter always populates resource.image_url from metadata

## 7. Conclusion

The notification system is **primarily event-driven** with one legacy direct creation path. The rendering system is **unified and well-architected** using profile-driven rendering. The main issue is the **dual creation paths** causing inconsistent metadata propagation, which affects preview display.

**Root cause of missing previews:** The adapter's `_resolve_resource()` method prioritizes metadata thumbnail_url, but if the metadata structure varies between creation paths, the preview may not display correctly.
