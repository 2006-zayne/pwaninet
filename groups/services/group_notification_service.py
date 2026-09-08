from notifications.events import publish_event, EventTypes, EventSources, EventActions


def send_group_join_request_notification(requesting_user, group):
    """
    Send GROUP_REQUEST notifications to all admins when a user requests to join.
    """
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_REQUESTED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.REQUESTED.value,
        actor=requesting_user,
        target_type='Group',
        target_id=str(group.id),
        context_type='GROUP',
        context_id=str(group.id),
        metadata={
            'group_name': group.name,
            'group_id': group.id,
            'user_id': requesting_user.id,
            'user_username': requesting_user.username
        }
    )


def send_group_approved_notification(approved_user, group, admin_user):
    """
    Send GROUP_APPROVED notification to a user when their join request is approved.
    """
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.APPROVED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=admin_user,
        context_type='GROUP',
        context_id=str(group.id),
        metadata={
            'group_name': group.name,
            'group_id': group.id,
            'recipient_id': approved_user.id,
            'user_id': approved_user.id,
            'user_username': approved_user.username
        }
    )


def send_group_rejected_notification(rejected_user, group, admin_user):
    """
    Send GROUP_REJECTED notification to a user when their join request is rejected.
    """
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_REJECTED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.REJECTED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=admin_user,
        context_type='GROUP',
        context_id=str(group.id),
        metadata={
            'group_name': group.name,
            'group_id': group.id,
            'recipient_id': rejected_user.id,
            'user_id': rejected_user.id,
            'user_username': rejected_user.username
        }
    )


def send_group_welcome_notification(user, group):
    """
    Send welcome/approved notification when a user joins an open group.
    """
    welcoming_actor = group.created_by if group.created_by else user
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.APPROVED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=welcoming_actor,
        context_type='GROUP',
        context_id=str(group.id),
        metadata={
            'group_name': group.name,
            'group_id': group.id,
            'recipient_id': user.id,
            'user_id': user.id,
            'user_username': user.username
        }
    )


def send_group_invite_notification(recipient_user, sender_user, group):
    """
    Send INVITE notification when a user is invited to a group.
    """
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_INVITED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.INVITED.value,
        actor=sender_user,
        target_type='Group',
        target_id=str(group.id),
        context_type='GROUP',
        context_id=str(group.id),
        metadata={
            'group_name': group.name,
            'group_id': group.id,
            'recipient_id': recipient_user.id,
            'user_id': recipient_user.id,
            'inviter_username': sender_user.username,
            'recipient_username': recipient_user.username
        }
    )

