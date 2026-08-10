# Migration Safety Report
## Event-Driven Notification Engine Migration Status

**Date:** August 4, 2026  
**Purpose:** Assess readiness for migrating from legacy notification system to new event-driven notification engine

---

## Executive Summary

**Status:** ⚠️ **NOT SAFE TO MIGRATE** - Critical gaps exist

While the infrastructure is largely complete, there are critical implementation gaps that prevent safe migration. The new notification engine cannot function without these components.

---

## ✅ Completed Components

### 1. Event Emission - COMPLETE
All legacy notification types now emit corresponding events:

| Legacy Type | Event Type | Location | Status |
|-------------|------------|----------|--------|
| LIKE | POSTS_POST_LIKED | notifications/signals.py | ✅ |
| COMMENT | POSTS_COMMENT_CREATED | notifications/signals.py | ✅ |
| COMMENT_REPLY | POSTS_COMMENT_REPLIED | notifications/signals.py | ✅ |
| COMMENT_LIKED | POSTS_COMMENT_LIKED | notifications/signals.py | ✅ |
| FOLLOW | USERS_USER_FOLLOWED | notifications/signals.py | ✅ |
| PINCH | USERS_USER_PINCHED | notifications/signals.py | ✅ |
| GROUP_REQUEST | GROUPS_MEMBER_REQUESTED | notifications/signals.py | ✅ |
| GROUP_APPROVED | GROUPS_MEMBER_APPROVED | notifications/signals.py | ✅ |
| GROUP_REJECTED | GROUPS_MEMBER_REJECTED | notifications/signals.py | ✅ |
| GROUP_INVITE | GROUPS_MEMBER_INVITED | groups/services/group_notification_service.py | ✅ |
| POST_SHARED | POSTS_POST_SHARED | posts/services/share_service.py | ✅ |
| POST_SHARED_TO_GROUP | POSTS_POST_SHARED_TO_GROUP | posts/services/share_service.py | ✅ |
| DOCUMENT_UPLOADED | DOCUMENTS_DOCUMENT_UPLOADED | documents/signals.py | ✅ |
| DOCUMENT_PUBLISHED | DOCUMENTS_DOCUMENT_PUBLISHED | documents/signals.py | ✅ |
| DOCUMENT_DOWNLOADED | DOCUMENTS_DOCUMENT_DOWNLOADED | documents/signals.py | ✅ |
| DOCUMENT_BOOKMARKED | DOCUMENTS_DOCUMENT_BOOKMARKED | documents/signals.py | ✅ |
| DOCUMENT_RATED | DOCUMENTS_DOCUMENT_RATED | documents/signals.py | ✅ |
| COURSE_CREATED | COURSES_COURSE_CREATED | courses/signals.py | ✅ |
| UNIT_CREATED | COURSES_UNIT_CREATED | courses/signals.py | ✅ |
| MESSAGE_SENT | MESSAGING_MESSAGE_SENT | messaging.frozen/signals.py | ✅ |
| CONVERSATION_MEMBER_ADDED | MESSAGING_CONVERSATION_MEMBER_ADDED | messaging.frozen/signals.py | ✅ |

**Legacy Compatibility:** All signal handlers maintain legacy `create_notification()` calls alongside new event emission for smooth migration.

### 2. PlatformEvent Model - READY
- ✅ Model exists in `notifications/models.py`
- ✅ All required fields: event_id, event_type, actor, source, action, target_type, target_id, context_type, context_id, audience, metadata, timestamp, version, correlation_id
- ✅ EventArchive model for historical data
- ✅ EventTypes, EventSources, EventActions enums defined in `notifications/events/registry.py`
- ✅ EventPublisher and publish_event function implemented

### 3. NotificationObject Model - READY
- ✅ Model exists in `notifications/models.py`
- ✅ All required fields: notification_id, recipient, source_events, notification_type, category, priority, title, summary, context_type, context_id, status, delivery_policy, aggregation_key, event_count, first_event_time, latest_event_time, metadata, created_at, updated_at, expires_at
- ✅ NotificationAction model exists
- ✅ NotificationTypes, NotificationCategories, NotificationPriorities, NotificationStatuses, DeliveryPolicies enums defined

### 4. Rendering System - COMPLETE
- ✅ NotificationRenderer base class and registry implemented
- ✅ All legacy notification types have renderers:
  - LikeRenderer, FollowRenderer, InviteRenderer
  - CommentReplyRenderer, GroupRequestRenderer
  - GroupApprovedRenderer, GroupRejectedRenderer
  - PostSharedRenderer, PostSharedToGroupRenderer
  - PinchRenderer, AlertRenderer
- ✅ Rendering profiles registered (social, group, system)
- ✅ NotificationRenderingService implemented
- ✅ Payload adapters implemented
- ✅ Templates exist

### 5. Preference System - READY
- ✅ NotificationPreference model exists (simplified version)
- ✅ NotificationPreferenceService implemented
- ✅ Methods: get_or_create_preferences, should_deliver_notification, update_global_preferences, update_type_preferences, update_quiet_hours, set_do_not_disturb, clear_do_not_disturb
- ✅ Settings page updated with new UI (delivery channels, notification types, quiet hours, do not disturb)
- ✅ Migration 0017_update_notification_preference_model applied
- ✅ PreferenceEngine implemented (for new engine)

### 6. Delivery System - READY (Placeholder)
- ✅ DeliveryEngine implemented
- ✅ DeliveryAttempt model exists
- ✅ Delivery adapters implemented:
  - InAppAdapter (marks as delivered, TODO: WebSocket)
  - EmailAdapter (TODO: actual email sending)
  - PushAdapter (TODO: FCM integration)
  - SMSAdapter (TODO: SMS gateway)
- ✅ Adapter registry exists

### 7. Aggregation Engine - READY
- ✅ AggregationEngine implemented
- ✅ Aggregation windows defined for each notification type
- ✅ Grouping and merging logic implemented

### 8. Rules Engine - IMPLEMENTED (Non-Functional)
- ✅ RulesEngine class implemented
- ✅ NotificationRule dataclass defined
- ✅ Rules defined for all event types (POST_LIKE_RULE, POST_COMMENT_RULE, etc.)
- ⚠️ **CRITICAL GAP:** Recipient functions are placeholders

---

## ❌ Critical Gaps (Blocking Migration)

### 1. Recipient Resolution Functions - NOT IMPLEMENTED
**Location:** `notifications/rules/rules.py`

The recipient functions that determine who should receive notifications are currently placeholders:

```python
def _post_owner_recipient(event_data: Dict[str, Any]) -> List[int]:
    """Recipient: Post owner."""
    # Extract post owner from event metadata
    # This will be implemented when we have the actual post model access
    return event_data.get('recipient_user_ids', [])  # Returns empty list!
```

**Impact:** Rules Engine cannot determine notification recipients, so no notifications will be created.

**Required Implementation:**
- `_post_owner_recipient` - Query Post model to get author
- `_group_admins_recipient` - Query Membership model for admins
- `_group_member_recipient` - Query Membership model for specific user
- `_followed_user_recipient` - Extract from event metadata
- `_pinched_user_recipient` - Extract from event metadata

### 2. Event Processing Pipeline - NOT WIRED
**Issue:** PlatformEvents are being published but not consumed by the Rules Engine.

**Current Flow:**
```
Signal Handler → publish_event() → PlatformEvent created → (STOP)
```

**Required Flow:**
```
Signal Handler → publish_event() → PlatformEvent created → RulesEngine.process_event() → NotificationObject created → PreferenceEngine → AggregationEngine → DeliveryEngine
```

**Required Implementation:**
- Event consumer/listener that triggers RulesEngine.process_event()
- Could be Django signal on PlatformEvent post_save
- Could be Celery task for async processing
- Could be WebSocket-based real-time processing

### 3. Delivery Adapter Implementations - PLACEHOLDERS
**Location:** `notifications/delivery/adapters.py`

All delivery adapters are placeholders with TODO comments:

```python
class InAppAdapter:
    def deliver(self, notification, attempt):
        # TODO: Send via WebSocket to user's notification center
        return True  # Always returns True
```

**Impact:** Notifications will be marked as "delivered" but users won't actually receive them.

**Required Implementation:**
- WebSocket integration for real-time in-app delivery
- Email backend integration with templates
- Firebase Cloud Messaging (FCM) for push notifications
- SMS gateway integration

### 4. NotificationObject Creation - NOT TESTED
**Issue:** Rules Engine has never been tested with actual PlatformEvents.

**Required:**
- Integration tests for RulesEngine.process_event()
- Verify NotificationObject creation from events
- Verify metadata extraction from events
- Verify action generation

---

## ⚠️ Medium Priority Gaps

### 1. Event Metadata Structure
**Issue:** Event metadata structure may not match what Rules Engine expects.

**Current Event Metadata:**
```python
metadata={
    'post_content': post.content[:100],
    'liker_username': liker.username
}
```

**Rules Engine Expects:**
```python
event_data.get('recipient_user_ids', [])
event_data.get('actor_id')
event_data.get('post_author_id')
```

**Required:** Align event metadata structure with Rules Engine expectations.

### 2. NotificationAction Creation
**Issue:** NotificationAction creation in Rules Engine may not work with current model.

**Current Model:** Two foreign keys (notification and legacy_notification)
**Rules Engine:** Uses NotificationObject.notification_id

**Required:** Verify NotificationAction creation works correctly.

### 3. Legacy Notification Cleanup
**Issue:** Legacy Notifications model will still exist after migration.

**Required:** Plan for:
- Gradual phase-out of legacy notifications
- Migration of existing legacy notifications to NotificationObject
- Timeline for removing legacy code

---

## 📋 Migration Readiness Checklist

| Component | Status | Notes |
|-----------|--------|-------|
| Event Emission | ✅ Complete | All legacy types emit events |
| PlatformEvent Model | ✅ Ready | Model and registry complete |
| NotificationObject Model | ✅ Ready | Model and enums complete |
| Rendering System | ✅ Complete | All renderers implemented |
| Preference System | ✅ Ready | Model, service, UI complete |
| Delivery System | ⚠️ Partial | Adapters are placeholders |
| Aggregation Engine | ✅ Ready | Engine implemented |
| Rules Engine | ⚠️ Partial | Engine exists, recipients not implemented |
| Recipient Resolution | ❌ Missing | Functions return empty lists |
| Event Processing Pipeline | ❌ Missing | Events not consumed |
| Delivery Implementation | ❌ Missing | WebSocket, email, push not implemented |
| Integration Tests | ❌ Missing | No end-to-end tests |
| Metadata Alignment | ⚠️ Needs Review | Structure may not match |

---

## 🔧 Required Work Before Migration

### High Priority (Blocking)

1. **Implement Recipient Resolution Functions**
   - File: `notifications/rules/rules.py`
   - Functions: `_post_owner_recipient`, `_group_admins_recipient`, etc.
   - Effort: 2-3 hours

2. **Wire Event Processing Pipeline**
   - Create PlatformEvent post_save signal handler
   - Trigger RulesEngine.process_event()
   - Add error handling and logging
   - Effort: 1-2 hours

3. **Implement In-App Delivery**
   - WebSocket integration for real-time delivery
   - Update InAppAdapter.deliver()
   - Effort: 4-6 hours

### Medium Priority

4. **Implement Email Delivery**
   - Create email templates
   - Configure Django email backend
   - Update EmailAdapter.deliver()
   - Effort: 3-4 hours

5. **Implement Push Notifications**
   - Configure FCM
   - Update PushAdapter.deliver()
   - Effort: 3-4 hours

6. **Align Event Metadata**
   - Review event metadata structure
   - Update publish_event calls if needed
   - Update Rules Engine expectations
   - Effort: 2-3 hours

### Low Priority

7. **Add Integration Tests**
   - Test RulesEngine with actual events
   - Test full pipeline end-to-end
   - Effort: 4-6 hours

8. **Plan Legacy Cleanup**
   - Define migration timeline
   - Plan legacy notification migration
   - Effort: 2-3 hours

---

## 🎯 Recommended Migration Strategy

### Phase 1: Complete Critical Infrastructure (1-2 weeks)
- Implement recipient resolution functions
- Wire event processing pipeline
- Implement in-app delivery (WebSocket)
- Add integration tests

### Phase 2: Implement Additional Channels (1-2 weeks)
- Implement email delivery
- Implement push notifications
- Align event metadata structure

### Phase 3: Gradual Rollout (2-4 weeks)
- Enable new engine for specific notification types
- Monitor performance and errors
- Gradually enable more types
- Keep legacy system as fallback

### Phase 4: Full Migration (1-2 weeks)
- Enable new engine for all notification types
- Migrate existing legacy notifications
- Remove legacy code
- Clean up old models

---

## 📊 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Recipient resolution fails | High | Critical | Implement and test thoroughly |
| Event pipeline not wired | High | Critical | Add signal handler with logging |
| Delivery not working | High | High | Implement at least in-app first |
| Metadata mismatch | Medium | Medium | Review and align structures |
| Performance issues | Low | Medium | Add monitoring and caching |
| Data loss | Low | Critical | Keep legacy system as fallback |

---

## ✅ Conclusion

**NOT SAFE TO MIGRATE**

The notification engine infrastructure is well-designed and largely complete, but critical gaps in recipient resolution and event processing prevent safe migration. The system cannot create or deliver notifications in its current state.

**Estimated Time to Safe Migration:** 2-4 weeks of focused development

 **Recommended Next Steps:**
1. Implement recipient resolution functions (highest priority)
2. Wire event processing pipeline
3. Implement in-app delivery
4. Add integration tests
5. Gradual rollout with legacy fallback

---

**Report Generated:** August 4, 2026  
**Generated By:** Cascade AI Assistant  
**Version:** 1.0
