# Group Membership System Refactoring

## Overview

Refactored the group membership system to support flexible join policies (open, approval, invite-only), proper admin notifications, and clear user feedback. This change replaces the binary `is_official` logic with a more scalable `join_policy` system.

## Migration Files

- `groups/migrations/0004_group_join_policy.py` - Adds `join_policy` field to Group model
- `notifications/migrations/0005_alter_notifications_notification_type.py` - Adds `GROUP_REJECTED` notification type

## Model Changes

### Group Model (`groups/models.py`)

**Added:**
```python
class JoinPolicy(models.TextChoices):
    OPEN = "open", "Open"
    APPROVAL = "approval", "Requires Approval"
    INVITE_ONLY = "invite", "Invite Only"

join_policy = models.CharField(
    max_length=20,
    choices=JoinPolicy.choices,
    default=JoinPolicy.OPEN
)
```

**Preserved for backward compatibility:**
- `is_official` field (still used for course/year restrictions, not join logic)

### Notifications Model (`notifications/models.py`)

**Added:**
```python
GROUP_REJECTED = 'GROUP_REJECTED'
```

## Serializer Changes

### Group Serializers (`groups/serializers.py`)

**Updated fields to include `join_policy`:**
- `GroupSerializer` - Added `join_policy` to fields list
- `GroupCreateSerializer` - Added `join_policy` to fields list

### MembershipCreateSerializer (`groups/serializers.py`)

**Refactored `create()` method:**
```python
def create(self, validated_data):
    # Determine status based on join policy
    if group.join_policy == JoinPolicy.OPEN:
        status = MembershipStatus.APPROVED
    elif group.join_policy == JoinPolicy.APPROVAL:
        status = MembershipStatus.PENDING
    elif group.join_policy == JoinPolicy.INVITE_ONLY:
        raise serializers.ValidationError("This group is invite-only.")
    else:
        status = MembershipStatus.PENDING
```

## View Changes

### API Views (`groups/views.py`)

#### Join Action
- Replaced `is_official` logic with `join_policy` logic
- Added admin notifications for pending requests
- Returns structured response with status and message

```python
# Determine status based on join policy
if group.join_policy == JoinPolicy.OPEN:
    membership_status = MembershipStatus.APPROVED
elif group.join_policy == JoinPolicy.APPROVAL:
    membership_status = MembershipStatus.PENDING
elif group.join_policy == JoinPolicy.INVITE_ONLY:
    return Response({'detail': 'This group is invite-only.'}, status=403)

# Send admin notifications for pending requests
if membership_status == MembershipStatus.PENDING:
    for admin_membership in group.memberships.filter(
        role=MembershipRole.ADMIN,
        status=MembershipStatus.APPROVED
    ):
        create_notification(
            recipient=admin_membership.user,
            sender=request.user,
            notification_type=Notifications.GROUP_REQUEST,
            msg=f'{request.user.username} requested to join {group.name}',
            group=group
        )
```

#### Reject Action
- Added user notification for rejection

```python
membership.status = MembershipStatus.REJECTED
membership.save()

# Send rejection notification to the user
create_notification(
    recipient=membership.user,
    sender=request.user,
    notification_type=Notifications.GROUP_REJECTED,
    msg=f'Your request to join {group.name} was not approved',
    group=group
)
```

### Web Views (`groups/views.py`)

#### toggle_group_membership
- Replaced `is_official` logic with `join_policy` logic
- Added admin notifications for pending requests
- Maintained course/year restrictions for official groups

## Service Changes

### Group Service (`groups/services/group_service.py`)

**Added `is_rejected` state:**
```python
is_rejected = user_membership and user_membership.status == MembershipStatus.REJECTED
```

## Form Changes

### GroupForm (`groups/forms.py`)

**Added `join_policy` field:**
```python
fields = ['name', 'description', 'group_pic', 'cover_photo', 'join_policy']
```

## Template Changes

### Create Group Template (`groups/templates/groups/create_group.html`)

**Added join policy dropdown:**
```html
<div class="mb-4">
  <label class="field-label">Join Policy</label>
  <select name="join_policy" class="form-field">
    <option value="open">Open - Anyone can join</option>
    <option value="approval">Requires Approval - Admin must approve requests</option>
    <option value="invite">Invite Only - Only invited users can join</option>
  </select>
</div>
```

### Group Detail Template (`groups/templates/groups/groups_detail.html`)

**Updated button states:**
- APPROVED → "Joined ✅"
- PENDING → "Request Sent ⏳"
- REJECTED → "Request Again" (new state)
- NONE → "Join Group"

### Groups Dashboard Template (`groups/templates/groups/groups_dashboard.html`)

**Updated status badges:**
- "Joined" → "Joined ✅"
- "Pending" → "Request Sent ⏳"

## Join Policy Behavior

| Policy      | Join Behavior                          | Initial Status |
|------------|----------------------------------------|----------------|
| OPEN       | Anyone can join instantly              | APPROVED       |
| APPROVAL   | Requires admin approval               | PENDING        |
| INVITE_ONLY| Only invited users can join            | Blocked (403)  |

## Notification Flow

### Join Request (APPROVAL policy)
1. User requests to join
2. Membership created with PENDING status
3. **All group admins** receive notification: "{username} requested to join {group}"
4. User receives confirmation: "Your request to join {group} has been sent"

### Approval
1. Admin approves request
2. Membership status changed to APPROVED
3. User receives notification: "Welcome to {group}! You can now contribute to the group."

### Rejection
1. Admin rejects request
2. Membership status changed to REJECTED
3. User receives notification: "Your request to join {group} was not approved"

## UI State Mapping

| Backend Status | UI Label           | Action                  |
|----------------|--------------------|-------------------------|
| APPROVED       | Joined ✅          | Leave Group             |
| PENDING        | Request Sent ⏳     | Cancel Request          |
| REJECTED       | Request Again      | Request Again           |
| NONE           | Join Group         | Join Group              |

## Backward Compatibility

- `is_official` field is **NOT** deleted
- `is_official` is still used for course/year restrictions
- Existing groups default to `join_policy = OPEN`
- No data loss or breaking changes

## Testing Scenarios

1. **Open group** → User joins instantly (APPROVED status)
2. **Approval group** → User joins (PENDING status), all admins notified
3. **Invite-only group** → User blocked with 403 error
4. **Admin approves** → User notified of approval
5. **Admin rejects** → User notified of rejection
6. **Duplicate join** → Blocked with error message
7. **Rejected user re-requests** → Can request again

## Future Enhancements

This refactoring enables:
- Premium/paid groups (invite-only with payment)
- Private communities (approval-based)
- Public communities (open)
- Custom join workflows per group type
