from notifications.models import Notifications
from notifications.services.notification_service import create_notification, invalidate_unread_count_cache
from groups.models import Membership, MembershipRole, MembershipStatus


def send_group_join_request_notification(requesting_user, group):
    """
    Send GROUP_REQUEST notifications to all admins when a user requests to join.
    """
    for admin_membership in group.memberships.filter(
        role=MembershipRole.ADMIN,
        status=MembershipStatus.APPROVED
    ):
        create_notification(
            recipient=admin_membership.user,
            sender=requesting_user,
            notification_type=Notifications.GROUP_REQUEST,
            msg=f'{requesting_user.username} requested to join {group.name}',
            group=group
        )
        invalidate_unread_count_cache(admin_membership.user.id)


def send_group_approved_notification(approved_user, group, admin_user):
    """
    Send GROUP_APPROVED notification to a user when their join request is approved.
    """
    create_notification(
        recipient=approved_user,
        sender=admin_user,
        notification_type=Notifications.GROUP_APPROVED,
        msg=f'Welcome to {group.name}! You can now contribute to the group.',
        group=group
    )
    invalidate_unread_count_cache(approved_user.id)


def send_group_rejected_notification(rejected_user, group, admin_user):
    """
    Send GROUP_REJECTED notification to a user when their join request is rejected.
    """
    create_notification(
        recipient=rejected_user,
        sender=admin_user,
        notification_type=Notifications.GROUP_REJECTED,
        msg=f'Your request to join {group.name} was not approved',
        group=group
    )
    invalidate_unread_count_cache(rejected_user.id)


def send_group_welcome_notification(user, group):
    """
    Send GROUP_APPROVED notification when a user joins an open group.
    """
    create_notification(
        recipient=user,
        sender=user,
        notification_type=Notifications.GROUP_APPROVED,
        msg=f'Welcome to {group.name}! You can now contribute to the group.',
        group=group
    )
    invalidate_unread_count_cache(user.id)


def send_group_invite_notification(recipient_user, sender_user, group):
    """
    Send INVITE notification when a user is invited to a group.
    """
    create_notification(
        recipient=recipient_user,
        sender=sender_user,
        notification_type=Notifications.INVITE,
        msg=f'invited you to join {group.name}.',
        group=group
    )
    invalidate_unread_count_cache(recipient_user.id)
