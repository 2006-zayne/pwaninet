# Phase 0 Audit Report - Current Notification System

**Date:** August 3, 2026
**Purpose:** Complete audit of existing notification subsystem before implementing Notification Engine v2
**Status:** Complete

---

## Executive Summary

The current notification system is a tightly-coupled, signal-driven implementation that creates notifications directly from Django signals and service calls. It lacks event-driven architecture, has no separation between notification creation and delivery, and contains business logic scattered across signals, services, and views.

**Key Findings:**
- 2 notification models (Notifications, PushSubscription)
- 5 Django signal handlers creating notifications
- 8+ service-level notification creation points
- No event infrastructure
- No rules engine
- No aggregation engine
- No preference engine (only basic user flags)
- Direct WebSocket broadcasting from service layer
- Caching implemented for performance

---

## 1. Current Notification Models

### 1.1 Notifications Model
**Location:** `/home/zayne/projects/pwaninet/notifications/models.py`

**Fields:**
- `recipient` - ForeignKey to User (who receives notification)
- `sender` - ForeignKey to User (who triggered notification)
- `group` - ForeignKey to Group (nullable, for group-related notifications)
- `post` - ForeignKey to Post (nullable, for post-related notifications)
- `notification_type` - CharField with 11 choices
- `msg` - CharField (notification message)
- `timestamp` - DateTimeField (auto_now_add)
- `is_read` - BooleanField (default=False)

**Notification Types:**
- `INVITE` - Group invite
- `ALERTE` - General alert
- `LIKE` - Post like
- `FOLLOW` - New follower
- `GROUP_REQUEST` - Group join request
- `GROUP_APPROVED` - Group join approved
- `GROUP_REJECTED` - Group join rejected
- `POST_SHARED` - Post shared to user
- `POST_SHARED_TO_GROUP` - Post shared to group
- `PINCH` - Profile pinch
- `COMMENT_REPLY` - Comment reply

**Indexes:**
- recipient, sender, group, post, notification_type, timestamp, is_read

### 1.2 PushSubscription Model
**Location:** `/home/zayne/projects/pwaninet/notifications/models.py`

**Purpose:** Web push notification subscriptions (FCM/Web Push)

**Fields:**
- `user` - ForeignKey to User
- `endpoint` - TextField (unique)
- `p256dh` - TextField (VAPID key)
- `auth` - TextField (VAPID key)
- `user_agent` - TextField (blank)
- `is_active` - BooleanField (default=True)
- `created_at` - DateTimeField (auto_now_add)
- `updated_at` - DateTimeField (auto_now)

**Indexes:**
- user, is_active

---

## 2. Notification Creation Points

### 2.1 Django Signal Handlers
**Location:** `/home/zayne/projects/pwaninet/notifications/signals.py`

| Signal | Model | Notification Type | Recipient Logic |
|--------|-------|-------------------|----------------|
| post_save | Like | LIKE | Post author (if liker ≠ author) |
| post_save | Comment | ALERTE | Post author (if commenter ≠ author) |
| post_save | CommentLike | ALERTE | Comment author (if liker ≠ author) |
| post_save | Follow | FOLLOW | Followed user |
| post_save | Pinch | PINCH | Pinched user |

**Issues:**
- Business logic embedded in signals
- No event abstraction
- Direct notification creation from signals
- No validation layer beyond basic checks

### 2.2 Service-Level Creation Points

#### Group Notifications
**Location:** `/home/zayne/projects/pwaninet/groups/services/group_notification_service.py`

- `send_group_join_request_notification()` - GROUP_REQUEST to all admins
- `send_group_approved_notification()` - GROUP_APPROVED to approved user
- `send_group_rejected_notification()` - GROUP_REJECTED to rejected user
- `send_group_welcome_notification()` - GROUP_APPROVED for open groups
- `send_group_invite_notification()` - INVITE to invited user

#### Post Notifications
**Location:** `/home/zayne/projects/pwaninet/posts/services/comment_service.py`

- Comment reply notifications (COMMENT_REPLY)

**Location:** `/home/zayne/projects/pwaninet/posts/services/share_service.py`

- Post shared to user (POST_SHARED)
- Post shared to group (POST_SHARED_TO_GROUP)

#### User Notifications
**Location:** `/home/zayne/projects/pwaninet/users/views.py`

- Direct calls to `create_notification()` for user-related events

---

## 3. Django Signals

**Location:** `/home/zayne/projects/pwaninet/notifications/signals.py`

**Active Signals:**
1. `create_like_notification` - Like.post_save
2. `create_comment_notification` - Comment.post_save
3. `create_comment_like_notification` - CommentLike.post_save
4. `create_follow_notification` - Follow.post_save
5. `create_pinch_notification` - Pinch.post_save

**Characteristics:**
- All use `post_save` signal
- All call `create_notification()` directly
- No signal-based event publishing
- Tightly coupled to notification creation

---

## 4. Views and HTMX Endpoints

**Location:** `/home/zayne/projects/pwaninet/notifications/views.py`

### Web Views (HTMX)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/notifications/` | GET | List notifications with grouping options |
| `/notifications/unread-count/` | GET | Return HTML badge with unread count |
| `/notifications/mark-as-read/` | POST | Mark all notifications as read |
| `/notifications/read/<id>/` | POST | Mark single notification as read |
| `/notifications/delete/<id>/` | POST | Delete single notification |
| `/notifications/delete-all/` | POST | Delete all notifications |
| `/notifications/delete-read/` | POST | Delete read notifications |

**Features:**
- Multiple grouping strategies (by type, sender, time, hybrid)
- HTMX partial updates
- Pagination support
- Filtering by type and read status

### API ViewSets
| ViewSet | Purpose |
|---------|---------|
| `NotificationViewSet` | CRUD operations for notifications |
| `VapidPublicKeyView` Expose VAPID public key |
| `SubscribeView` | Push subscription endpoint |
| `UnsubscribeView` | Push unsubscribe endpoint |

**API Actions:**
- `unread_count` - GET unread count
- `mark_all_read` - POST mark all as read
- `mark_read` - POST mark single as read
- `mark_unread` - POST mark single as unread
- `delete_all` - POST delete all
- `delete_read` - POST delete read
- `bulk_action` - POST bulk operations

---

## 5. WebSocket Consumers

**Location:** `/home/zayne/projects/pwaninet/realtime/consumers.py`

### NotificationConsumer
**Purpose:** Real-time notification delivery

**Features:**
- User-specific channel: `notifications_{user_id}`
- Broadcasts unread count updates
- Broadcasts notification events
- Echoes client messages

**Event Handlers:**
- `notification()` - Send notification to client
- `unread_count_update()` - Send updated unread count
- `user_status()` - Send user online status

**Issues:**
- Direct WebSocket calls from service layer
- No event-based architecture
- Tight coupling between service and consumer

---

## 6. Notification Templates

**Location:** `/home/zayne/projects/pwaninet/notifications/templates/notifications/`

### Main Templates
- `notifications.html` - Main notification page

### Partial Templates
- `notification_badge.html` - Badge counter display
- `notification_list.html` - Standard list view
- `notification_list_grouped.html` - Grouped by activity
- `notification_list_hybrid.html` - Hybrid grouping
- `notification_list_items.html` - Individual items
- `notification_list_sender_grouped.html` - Grouped by sender
- `notification_list_time_grouped.html` - Grouped by time

**Grouping Strategies:**
1. Activity grouping (type + post + group)
2. Sender grouping (by user)
3. Time grouping (just now, today, yesterday, earlier)
4. Hybrid grouping (adaptive based on sender count)

---

## 7. Badge Counter Logic

**Location:** `/home/zayne/projects/pwaninet/notifications/services/notification_service.py`

**Implementation:**
- Cache key: `notif:unread_count:user:{user_id}`
- Cache timeout: 30 seconds
- Invalidation on notification create/read/delete
- WebSocket broadcast on count change

**Functions:**
- `get_cached_unread_count()` - Get count with caching
- `invalidate_unread_count_cache()` - Clear cache
- `build_unread_notification_html()` - Generate badge HTML

**Context Processor:**
**Location:** `/home/zayne/projects/pwaninet/notifications/context_processors.py`
- Provides `unread_notifications_count` globally

---

## 8. Read/Unread Logic

**Location:** `/home/zayne/projects/pwaninet/notifications/queries/notification_queries.py`

**Functions:**
- `get_unread_count()` - Count unread notifications
- `get_unread_count_by_type()` - Count by type
- `get_unread_count_by_group()` - Count by group
- `get_unread_counts_for_groups()` - Batch count for multiple groups
- `mark_user_notifications_as_read()` - Mark all as read

**Service Functions:**
- `mark_single_notification_as_read()` - Mark single, invalidate cache, broadcast
- Direct database updates in views for bulk operations

**Characteristics:**
- Simple boolean field (`is_read`)
- No read timestamps
- No seen vs read distinction
- Cache invalidation on state changes

---

## 9. Notification Utilities

### Query Layer
**Location:** `/home/zayne/projects/pwaninet/notifications/queries/notification_queries.py`

**Functions:**
- `get_notifications_for_user()` - Basic query with filters
- `get_notifications_by_time_periods()` - Time-based grouping
- `get_grouped_notifications()` - Activity grouping
- `get_notifications_grouped_by_sender()` - Sender grouping
- `get_notifications_hybrid_grouped()` - Adaptive grouping
- `get_notification_for_user()` - Single notification lookup
- `delete_notification()` - Delete single
- `delete_all_notifications()` - Delete all
- `delete_read_notifications()` - Delete read

### Service Layer
**Location:** `/home/zayne/projects/pwaninet/notifications/services/notification_service.py`

**Functions:**
- `create_notification()` - Create with preference checks
- `mark_single_notification_as_read()` - Mark read with cache invalidation
- `delete_single_notification()` - Delete with cache invalidation
- `delete_all_user_notifications()` - Delete all with cache invalidation
- `delete_user_read_notifications()` - Delete read with cache invalidation
- `build_notifications_context()` - Build context for templates
- `build_unread_notification_html()` - Generate badge HTML
- `get_group_unread_counts()` - Batch group counts with caching
- `invalidate_group_unread_cache()` - Clear group cache

### Subscription Service
**Location:** `/home/zayne/projects/pwaninet/notifications/services/subscription_service.py`

**Class:** `SubscriptionService`

**Methods:**
- `subscribe()` - Create/update push subscription with deduplication
- `unsubscribe()` - Soft delete by setting is_active=False

### Filters
**Location:** `/home/zayne/projects/pwaninet/notifications/filters.py`

**Class:** `NotificationFilter`

**Filters:**
- recipient, sender, group, post
- notification_type, is_read
- timestamp_after, timestamp_before

### Serializers
**Location:** `/home/zayne/projects/pwaninet/notifications/serializers.py`

**Serializers:**
- `NotificationSerializer` - Read with nested relations
- `NotificationCreateSerializer` - Create with validation
- `NotificationUpdateSerializer` - Update is_read
- `NotificationBulkActionSerializer` - Bulk operations
- `SubscriptionSerializer` - Push subscription data
- `UnsubscribeSerializer` - Unsubscribe request

---

## 10. User Notification Preferences

**Location:** `/home/zayne/projects/pwaninet/users/models.py`

**Fields on User Model:**
- `notify_on_like` - BooleanField (default=True)
- `notify_on_follow` - BooleanField (default=True)
- `notify_on_invite` - BooleanField (default=True)
- `notify_on_group_request` - BooleanField (default=True)
- `notify_on_group_approved` - BooleanField (default=True)
- `notify_on_pinch` - BooleanField (default=True)
- `notify_on_comment_reply` - BooleanField (default=True)
- `email_notifications` - BooleanField (default=False)

**Preference Checking:**
**Location:** `/home/zayne/projects/pwaninet/notifications/services/notification_service.py`

In `create_notification()`:
```python
if notification_type == Notifications.LIKE and not recipient.notify_on_like:
    return None
# Similar checks for all types...
```

**Issues:**
- Preferences checked at creation time
- No category-based preferences
- No context-based preferences
- No quiet hours
- No channel-specific preferences

---

## 11. Technical Debt Identified

### Architectural Issues
1. **No Event Infrastructure** - Direct notification creation from signals
2. **No Separation of Concerns** - Business logic in signals, services, and views
3. **Tight Coupling** - Direct calls to `create_notification()` throughout codebase
4. **No Rules Engine** - Notification logic embedded in signal handlers
5. **No Aggregation Engine** - Grouping done at query time, not creation time
6. **No Preference Engine** - Basic boolean flags only
7. **No Delivery Engine** - Direct WebSocket calls from service layer

### Code Quality Issues
1. **Duplicate Logic** - Cache invalidation repeated in multiple functions
2. **Mixed Responsibilities** - Service layer handles WebSocket broadcasting
3. **No Validation Layer** - Preference checks scattered in service function
4. **No Event Logging** - No audit trail for notification decisions
5. **No Error Handling** - Minimal error handling in notification creation

### Scalability Issues
1. **Synchronous Creation** - Notifications created synchronously in request/response
2. **No Queue** - No background processing for notifications
3. **Cache Invalidation** - Manual cache invalidation prone to errors
4. **Query-Time Grouping** - Expensive grouping operations at read time

---

## 12. Reusable Components

### Components to Preserve
1. **Query Layer** - Well-structured query functions can be adapted
2. **Template Structure** - Template organization is good
3. **Badge Logic** - Caching strategy is sound
4. **WebSocket Infrastructure** - Consumer structure can be reused
5. **API Structure** - ViewSet structure is reasonable

### Components to Replace
1. **Signal Handlers** - Replace with event publishing
2. **Service Creation Logic** - Replace with rules engine
3. **Preference Checks** - Replace with preference engine
4. **Direct WebSocket Calls** - Replace with delivery engine
5. **Current Models** - Replace with new notification models

---

## 13. Code That Should Remain Untouched

### During Initial Phases
1. **User Preference Fields** - Keep existing fields during migration
2. **WebSocket Routing** - Keep routing structure
3. **Template Structure** - Keep template organization
4. **API Endpoints** - Keep endpoint structure initially
5. **Push Subscription Model** - Keep for future FCM integration

### Until Legacy Removal
1. **Legacy Signal Handlers** - Keep until event publishing complete
2. **Legacy Service Functions** - Keep until rules engine operational
3. **Legacy Views** - Keep until new delivery engine ready
4. **Legacy Models** - Keep until data migration complete

---

## 14. Migration Strategy Recommendations

### Phase 1: Event Infrastructure
- Create event models and publisher service
- Add event publishing to existing signal handlers (dual operation)
- Keep legacy notification creation active
- Validate event coverage

### Phase 2: Notification Models
- Create new notification models per specification
- Keep legacy models active
- Add migration path for existing data

### Phase 3: Rules Engine
- Implement rules engine
- Connect events to rules
- Generate new notification objects
- Compare with legacy output (validation mode)

### Phase 4: Aggregation Engine
- Implement aggregation engine
- Enable for specific notification types
- Gradual rollout with monitoring

### Phase 5: Preference Engine
- Implement preference engine
- Migrate existing user preferences
- Add new preference types

### Phase 6: Delivery Engine
- Implement delivery engine (In-App only)
- Replace direct WebSocket calls
- Keep legacy delivery as fallback

### Phase 7: Frontend Integration
- Update templates to use new models
- Update API endpoints
- Maintain backward compatibility

### Phase 8: Legacy Migration
- Switch to new notification creation
- Remove legacy signal handlers
- Remove legacy service functions
- Migrate existing notification data

### Phase 9: Performance Optimization
- Add Redis caching
- Add Celery for async processing
- Optimize queries

---

## 15. Risks and Considerations

### High Risk
1. **Data Loss** - Notification data migration must be flawless
2. **User Experience** - No disruption to notification delivery
3. **Performance** - New system must match or exceed current performance
4. **Preference Migration** - User settings must be preserved

### Medium Risk
1. **Feature Parity** - All current features must be maintained
2. **WebSocket Stability** - Real-time updates must remain reliable
3. **Cache Consistency** - Cache invalidation must be robust
4. **API Compatibility** - Existing API consumers must not break

### Low Risk
1. **Template Updates** - Can be done incrementally
2. **Admin Interface** - Can be updated at any time
3. **Push Subscriptions** - Can remain unchanged initially

---

## 16. Success Criteria for Phase 0

- ✅ All notification models documented
- ✅ All notification creation points identified
- ✅ All Django signals documented
- ✅ All views and endpoints documented
- ✅ WebSocket consumers documented
- ✅ Templates documented
- ✅ Badge counter logic documented
- ✅ Read/unread logic documented
- ✅ All utilities documented
- ✅ Technical debt identified
- ✅ Reusable components identified
- ✅ Migration strategy defined

---

## 17. Next Steps

**Phase 1: Event Infrastructure**
1. Create event model per specification
2. Create event publisher service
3. Create event registry
4. Create event validator
5. Add event publishing to existing signal handlers
6. Validate event coverage matrix

**Do Not Proceed Until:**
- Event infrastructure is complete
- All existing notification sources publish events
- Event coverage is 100%
- Events are being logged successfully

---

**Report Status:** COMPLETE (UPDATED)
**Prepared By:** Cascade AI Assistant
**Date:** August 3, 2026
**Updated:** August 4, 2026 - Frontend Implementation Audit

---

## 18. Frontend Implementation Audit (Updated)

### 18.1 CSS Structure
**Location:** `/home/zayne/projects/pwaninet/notifications/templates/notifications/notifications.html`

**Current State:**
- Inline CSS in main template (lines 4-853)
- Design tokens for light/dark mode
- Mobile-responsive breakpoints
- No separate CSS file

**Design Tokens:**
- Colors: brand, primary, success, danger, info
- Spacing: radius-sm, radius-md, radius-lg, radius-pill
- Shadows: shadow-card, shadow-hover
- Typography: Inter, Roboto, system-ui

**CSS Classes:**
- `.page-wrap` - Container
- `.page-header` - Header section
- `.card` - Card container
- `.notif-item` - Individual notification
- `.notif-avatar` - Avatar styling
- `.notif-content` - Content area
- `.notif-actions` - Action buttons
- `.avatar-stack` - Avatar grouping
- `.empty-state` - Empty state
- `.btn-*` - Button variants
- `.pagination` - Pagination controls

**Decision:** KEEP CSS structure, extract to separate file during Phase 1

### 18.2 JavaScript
**Location:** Inline in `notifications.html` (lines 981-1053)

**Current Functions:**
- `handleFilterChange()` - Filter dropdown handler
- `toggleOlderNotifications()` - Expand/collapse older notifications
- HTMX event listener for unread count updates

**External JavaScript:**
- HTMX library loaded from `/static/js/htmx.min.js`
- Bootstrap icons used throughout

**Decision:** KEEP HTMX integration, extract inline JS to module during Phase 1

### 18.3 Templates
**Location:** `/home/zayne/projects/pwaninet/notifications/templates/notifications/`

**Main Template:**
- `notifications.html` - Main page with inline CSS/JS

**Partial Templates:**
- `notification_badge.html` - Badge counter
- `notification_list.html` - Standard list
- `notification_list_grouped.html` - Activity grouping
- `notification_list_hybrid.html` - Hybrid grouping
- `notification_list_items.html` - Individual items
- `notification_list_sender_grouped.html` - Sender grouping
- `notification_list_time_grouped.html` - Time grouping

**Template Features:**
- Multiple grouping strategies
- Dark mode support via CSS variables
- Mobile-responsive layouts
- HTMX partial updates

**Decision:** KEEP template structure, refactor to component-based during Phase 1

### 18.4 Existing UI Components

#### Document Viewer
**Location:** `/home/zayne/projects/pwaninet/documents/static/documents/js/document-viewer.js`

**Features:**
- PDF rendering with PDF.js
- DOCX rendering with mammoth.js
- Markdown rendering with marked.js
- Preview generation

**Decision:** REUSE for document notification previews

#### Avatar Components
**Location:** User profile pics in User model

**Current Implementation:**
- `profile_pic` field on User model
- Avatar rendering in templates
- Fallback to initials

**Decision:** REUSE existing avatar rendering, create reusable component

#### Base Template
**Location:** `/home/zayne/projects/pwaninet/templates/base.html`

**Features:**
- Bootstrap integration
- Dark mode support
- Responsive layout
- Navigation structure

**Decision:** KEEP base template structure

### 18.5 WebSocket Integration
**Location:** `/home/zayne/projects/pwaninet/realtime/consumers.py`

**Current Implementation:**
- `NotificationConsumer` for real-time updates
- Channel: `notifications_{user_id}`
- Event types: notification, unread_count_update

**Decision:** KEEP WebSocket infrastructure, integrate with new delivery engine

### 18.6 Dark Mode Implementation
**Location:** CSS variables in `notifications.html`

**Current Implementation:**
- `[data-theme="light"]` and `[data-theme="dark"]` selectors
- CSS variable overrides for dark mode
- Manual theme switching

**Decision:** KEEP dark mode implementation, extend to new components

### 18.7 Mobile Layouts
**Location:** CSS media queries in `notifications.html`

**Breakpoints:**
- 767px - Mobile full screen
- 768px - Tablet adjustments
- 480px - Small phone adjustments

**Mobile Features:**
- Full-width containers
- Adjusted font sizes
- Stacked layouts
- Touch-friendly buttons

**Decision:** KEEP mobile layouts, extend to new components

### 18.8 Existing Utilities

#### Badge Counter
**Location:** `notification_service.py`

**Features:**
- Cached unread counts
- WebSocket broadcast
- HTML generation

**Decision:** KEEP and extend for new notification system

#### Query Layer
**Location:** `notification_queries.py`

**Features:**
- Multiple grouping strategies
- Time-based grouping
- Sender grouping
- Hybrid grouping

**Decision:** ADAPT for new NotificationObject model

#### Pagination
**Location:** Django Paginator in views

**Features:**
- Standard Django pagination
- HTMX-compatible

**Decision:** KEEP pagination, adapt for cursor-based pagination

---

## 19. Component Decision Matrix

### KEEP (No Changes)
1. **Base template structure** - `/templates/base.html`
2. **WebSocket infrastructure** - `/realtime/consumers.py`
3. **Document viewer** - `/documents/static/documents/js/document-viewer.js`
4. **Design tokens** - CSS variables
5. **Dark mode implementation** - CSS variable overrides
6. **Mobile breakpoints** - Media queries
7. **Badge counter caching** - Cache strategy
8. **HTMX library** - `/static/js/htmx.min.js`

### REFACTOR (Modify for New System)
1. **Main template** - Extract inline CSS/JS, componentize
2. **Partial templates** - Convert to reusable components
3. **Query layer** - Adapt for NotificationObject model
4. **Service layer** - Adapt for new notification engine
5. **Views** - Add new endpoints for NotificationObject
6. **Serializers** - Add serializers for NotificationObject
7. **URLs** - Add routes for new notification system

### REPLACE (New Implementation)
1. **NotificationCard component** - New reusable component
2. **NotificationToolbar component** - New toolbar component
3. **NotificationList component** - New list component
4. **ContextHeader component** - New context component
5. **ActorStack component** - New avatar stack component
6. **ResourcePreview component** - New preview component
7. **ActionBar component** - New action component
8. **NotificationDrawer component** - New drawer component
9. **Renderer registry** - New notification type registry
10. **Payload adapters** - New payload normalization layer

### REMOVE (Legacy Code)
1. **Legacy signal handlers** - After migration complete
2. **Legacy notification creation** - After migration complete
3. **Legacy Notifications model** - After data migration
4. **Legacy grouping queries** - After migration complete

---

## 20. Frontend Implementation Strategy

### Phase 1: Foundation Components
1. Extract inline CSS to separate file
2. Extract inline JS to module
3. Create base component structure
4. Set up component registry

### Phase 2: Reusable Components
1. Create NotificationCard component
2. Create ContextHeader component
3. Create ActorStack component
4. Create ResourcePreview component
5. Create ActionBar component
6. Create MetadataRow component

### Phase 3: Renderer Registry
1. Create notification type registry
2. Create payload adapter layer
3. Implement renderer interface
4. Register existing notification types

### Phase 4: Rendering Profiles
1. Implement Social renderer
2. Implement Academic renderer
3. Implement Document renderer
4. Implement Group renderer
5. Implement Workspace renderer
6. Implement Security renderer
7. Implement System renderer

### Phase 5: Interactions
1. Implement search functionality
2. Implement filters
3. Implement bulk actions
4. Implement selection mode
5. Implement drawer navigation
6. Implement timeline grouping
7. Implement live updates

### Phase 6: Animations
1. Implement arrival animations
2. Implement dismissal animations
3. Implement aggregation animations
4. Implement live update animations
5. Implement drawer animations

### Phase 7: Performance
1. Implement lazy loading
2. Implement virtual scrolling
3. Implement DOM reuse
4. Implement performance profiling
5. Implement accessibility audit

---

## 21. Payload Adapter Requirements

### Legacy Notification → Standard Payload
**Source:** Legacy `Notifications` model
**Target:** Standard notification payload

**Mapping Required:**
```python
{
    "id": notification.id,
    "type": notification.notification_type,
    "created_at": notification.timestamp,
    "read": notification.is_read,
    "priority": "NORMAL",  # Default for legacy
    
    "actor": {
        "id": notification.sender.id,
        "name": notification.sender.get_full_name(),
        "username": notification.sender.username,
        "avatar": notification.sender.profile_pic.url if notification.sender.profile_pic else None,
        "verified": False  # Not in legacy model
    },
    
    "context": {
        "id": notification.group.id if notification.group else None,
        "type": "GROUP" if notification.group else None,
        "name": notification.group.name if notification.group else None,
        "avatar": notification.group.avatar.url if notification.group and notification.group.avatar else None,
        "badge": None
    },
    
    "resource": {
        "id": notification.post.id if notification.post else None,
        "type": "POST" if notification.post else None,
        "title": notification.post.content[:50] if notification.post else None,
        "preview": None,
        "url": f"/posts/{notification.post.id}" if notification.post else None
    },
    
    "content": {
        "title": notification.msg,
        "body": "",
        "highlight": []
    },
    
    "metadata": {
        "timestamp": notification.timestamp,
        "unread": not notification.is_read,
        "aggregated": False,
        "count": 1
    },
    
    "actions": [],  # Legacy has no actions
    "status": {
        "state": "READ" if notification.is_read else "CREATED",
        "offline": False,
        "pending": False,
        "failed": False
    },
    
    "rendering_hints": {
        "show_preview": True,
        "show_actor": True,
        "show_context": True,
        "compact": False
    }
}
```

### NotificationObject → Standard Payload
**Source:** New `NotificationObject` model
**Target:** Standard notification payload

**Mapping Required:**
- Direct field mapping for most fields
- Resolve actor from source_events
- Resolve context from context_type/context_id
- Resolve resource from metadata
- Resolve actions from NotificationAction model

---

## 22. Implementation Blockers

### No Critical Blockers Identified

The existing codebase provides:
- ✅ Solid CSS foundation with design tokens
- ✅ Dark mode implementation
- ✅ Mobile-responsive layouts
- ✅ WebSocket infrastructure
- ✅ Document viewer for previews
- ✅ HTMX integration
- ✅ Template structure
- ✅ Caching infrastructure

### Potential Challenges
1. **Legacy Coexistence** - Need to run both systems during migration
2. **Payload Normalization** - Need adapters for legacy notifications
3. **Component Migration** - Need gradual replacement of templates
4. **Performance** - Need to maintain current performance levels

---

## 23. Updated Success Criteria

### Phase 0 Success Criteria (Updated)
- ✅ All notification models documented
- ✅ All notification services documented
- ✅ Event generation documented
- ✅ HTMX endpoints documented
- ✅ Templates documented
- ✅ JavaScript documented
- ✅ CSS structure documented
- ✅ Existing UI components documented
- ✅ Document viewer identified
- ✅ Avatar components identified
- ✅ Dark mode implementation documented
- ✅ Mobile layouts documented
- ✅ Existing utilities documented
- ✅ Component decision matrix created
- ✅ Frontend implementation strategy defined
- ✅ Payload adapter requirements defined
- ✅ Implementation blockers identified

---

**Report Status:** COMPLETE (UPDATED)
**Prepared By:** Cascade AI Assistant
**Date:** August 3, 2026
**Updated:** August 4, 2026
