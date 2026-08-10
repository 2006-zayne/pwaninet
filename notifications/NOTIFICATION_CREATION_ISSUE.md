# Notification Creation Issue - Investigation and Fix

## Problem
Notifications were not being created when platform events occurred.

## Root Cause
The `RULES_REGISTRY` in `notifications/rules/rules.py` was incomplete. Several notification rules were defined but not registered in the registry, meaning the Rules Engine would not find matching rules for those event types.

## Missing Rules
The following rules were defined but not registered in RULES_REGISTRY:
- DOCUMENT_PUBLISHED_RULE
- DOCUMENT_DOWNLOADED_RULE  
- DOCUMENT_BOOKMARKED_RULE
- DOCUMENT_RATED_RULE
- COURSE_CREATED_RULE
- UNIT_CREATED_RULE
- MESSAGE_SENT_RULE
- CONVERSATION_MEMBER_ADDED_RULE

## Impact
When events with these triggers occurred:
- `documents.document.published`
- `documents.document.downloaded`
- `documents.document.bookmarked`
- `documents.document.rated`
- `courses.course.created`
- `courses.unit.created`
- `messaging.message.sent`
- `messaging.conversation.member_added`

The Rules Engine would return no matching rules, and no notifications would be created.

## Fix Applied
Updated `notifications/rules/rules.py` to include all defined rules in RULES_REGISTRY:

```python
RULES_REGISTRY = [
    POST_LIKE_RULE,
    POST_COMMENT_RULE,
    POST_COMMENT_REPLY_RULE,
    POST_SHARED_RULE,
    POST_SHARED_TO_GROUP_RULE,
    GROUP_INVITE_RULE,
    GROUP_REQUEST_RULE,
    GROUP_APPROVED_RULE,
    GROUP_REJECTED_RULE,
    USER_FOLLOW_RULE,
    USER_PINCH_RULE,
    DOCUMENT_UPLOADED_RULE,
    DOCUMENT_PUBLISHED_RULE,           # ADDED
    DOCUMENT_DOWNLOADED_RULE,         # ADDED
    DOCUMENT_BOOKMARKED_RULE,         # ADDED
    DOCUMENT_RATED_RULE,              # ADDED
    COURSE_CREATED_RULE,              # ADDED
    UNIT_CREATED_RULE,                # ADDED
    MESSAGE_SENT_RULE,                # ADDED
    CONVERSATION_MEMBER_ADDED_RULE,   # ADDED
    COURSE_ASSIGNMENT_PUBLISHED_RULE,
]
```

## Verification Steps
The notification creation flow is now complete:

1. **Platform Action** (e.g., user likes a post)
2. **Signal Handler** (posts/signals.py) calls `publish_event()`
3. **PlatformEvent Created** in database
4. **post_save Signal** triggers `process_platform_event()` in event_processor.py
5. **Rules Engine** processes event and finds matching rule
6. **NotificationObject Created** in database
7. **Preference Engine** evaluates user preferences
8. **Aggregation Engine** combines related notifications (if applicable)
9. **Delivery Engine** delivers notification through channels

## Additional Findings

### Signal Connection Status
- ✅ PlatformEvent post_save signal is connected to event_processor
- ✅ Posts app signals are connected and call publish_event
- ✅ Event publisher creates PlatformEvent correctly

### Rules Engine Status
- ✅ Rules Engine correctly processes events
- ✅ Recipient resolution functions are implemented
- ✅ Condition functions are implemented
- ✅ Aggregation logic is implemented

### Known Working Rules
The following rules were already registered and should have been working:
- POST_LIKE_RULE (trigger: posts.post.liked)
- POST_COMMENT_RULE (trigger: posts.comment.created)
- POST_COMMENT_REPLY_RULE (trigger: posts.comment.replied)
- POST_SHARED_RULE (trigger: posts.post.shared)
- POST_SHARED_TO_GROUP_RULE (trigger: posts.post.shared_to_group)
- GROUP_INVITE_RULE (trigger: groups.member.invited)
- GROUP_REQUEST_RULE (trigger: groups.member.requested)
- GROUP_APPROVED_RULE (trigger: groups.member.approved)
- GROUP_REJECTED_RULE (trigger: groups.member.rejected)
- USER_FOLLOW_RULE (trigger: users.user.followed)
- USER_PINCH_RULE (trigger: users.user.pinched)
- DOCUMENT_UPLOADED_RULE (trigger: documents.document.uploaded)
- COURSE_ASSIGNMENT_PUBLISHED_RULE (trigger: courses.assignment.published)

## Recommendations

1. **Test the fix**: Create test events for the previously broken event types to verify notifications are now created.

2. **Add validation**: Consider adding a test that verifies all defined rules are registered in RULES_REGISTRY to prevent this issue in the future.

3. **Monitor logs**: Check application logs for "No rules found for event type" messages to catch any missing rules.

4. **Document rule additions**: When adding new notification rules, ensure they are added to RULES_REGISTRY.

## Testing Commands

To test notification creation:

```python
# Test document published notification
from notifications.events import publish_event, EventTypes, EventSources, EventActions
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

publish_event(
    event_type='documents.document.published',
    source='DOCUMENTS',
    action='published',
    actor=user,
    target_type='Document',
    target_id=1,
    context_type='DocumentRepository',
    context_id=1,
    metadata={'document_title': 'Test Document'}
)
```

Then check if a NotificationObject was created in the database.
