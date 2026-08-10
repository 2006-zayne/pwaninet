from notifications.events import publish_event, EventTypes, EventSources, EventActions


def send_group_join_request_notification(requesting_user, group):
    """
    Send GROUP_REQUEST notifications to all admins when a user requests to join.
    Notifications are now handled by the event system in signals.py.
    """
    # Emit event for new notification engine
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_REQUESTED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.REQUESTED.value,
        actor=requesting_user,
        target_type='Group',
        target_id=str(group.id),
        metadata={
            'group_name': group.name,
            'user_username': requesting_user.username
        }
    )


def send_group_approved_notification(approved_user, group, admin_user):
    """
    Send GROUP_APPROVED notification to a user when their join request is approved.
    Notifications are now handled by the event system in signals.py.
    """
    # Emit event for new notification engine
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.APPROVED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=admin_user,
        context_type='User',
        context_id=str(approved_user.id),
        metadata={
            'group_name': group.name,
            'user_username': approved_user.username
        }
    )


def send_group_rejected_notification(rejected_user, group, admin_user):
    """
    Send GROUP_REJECTED notification to a user when their join request is rejected.
    Notifications are now handled by the event system in signals.py.
    """
    # Emit event for new notification engine
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_REJECTED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.REJECTED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=admin_user,
        context_type='User',
        context_id=str(rejected_user.id),
        metadata={
            'group_name': group.name,
            'user_username': rejected_user.username
        }
    )


def send_group_welcome_notification(user, group):
    """
    Send GROUP_APPROVED notification when a user joins an open group.
    Notifications are now handled by the event system in signals.py.
    """
    # Emit event for new notification engine
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.APPROVED.value,
        target_type='Group',
        target_id=str(group.id),
        actor=user,
        context_type='User',
        context_id=str(user.id),
        metadata={
            'group_name': group.name,
            'user_username': user.username
        }
    )


def send_group_invite_notification(recipient_user, sender_user, group):
    """
    Send INVITE notification when a user is invited to a group.
    Notifications are now handled by the event system.
    """
    # Emit event for new notification engine
    publish_event(
        event_type=EventTypes.GROUPS_MEMBER_INVITED.value,
        source=EventSources.GROUPS.value,
        action=EventActions.INVITED.value,
        actor=sender_user,
        target_type='Group',
        target_id=str(group.id),
        context_type='USER',
        context_id=str(recipient_user.id),
        metadata={
            'group_name': group.name,
            'inviter_username': sender_user.username,
            'recipient_username': recipient_user.username
        }
    )
