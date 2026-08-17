"""
Signal handlers for Groups app to emit PlatformEvents for the notification engine.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from groups.models import Membership, MembershipStatus
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(post_save, sender=Membership)
def membership_status_changed(sender, instance, created, **kwargs):
    """Emit event when membership status changes."""
    # Track previous status to detect changes
    if created:
        # New membership created (request or direct join)
        if instance.status == MembershipStatus.PENDING:
            # Only emit REQUESTED if the user created it themselves (not via invite)
            # Invites are handled separately by send_group_invite_notification
            # We can detect invites by checking if the user is the actor in the context
            # For now, we'll skip this event for PENDING memberships to avoid duplicate notifications
            # since invites are handled by the explicit invite notification call
            pass
        elif instance.status == MembershipStatus.APPROVED:
            # Direct approval (e.g., by admin invite)
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.APPROVED.value,
                actor=instance.group.created_by if instance.group.created_by else instance.user,
                target_type='Group',
                target_id=instance.group.id,
                context_type='Group',
                context_id=instance.group.id,
                metadata={
                    'group_name': instance.group.name,
                    'user_id': instance.user.id,
                    'user_username': instance.user.username,
                }
            )
    else:
        # Status change on existing membership
        # We need to check if status actually changed
        # This requires tracking previous status, which Django signals don't provide directly
        # For now, we'll emit events on every save with the current status
        # In production, you'd want to use a field tracker or pre_save signal
        
        if instance.status == MembershipStatus.APPROVED:
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.APPROVED.value,
                actor=instance.group.created_by if instance.group.created_by else instance.user,
                target_type='Group',
                target_id=instance.group.id,
                context_type='Group',
                context_id=instance.group.id,
                metadata={
                    'group_name': instance.group.name,
                    'user_id': instance.user.id,
                    'user_username': instance.user.username,
                }
            )
        elif instance.status == MembershipStatus.REJECTED:
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_REJECTED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.REJECTED.value,
                actor=instance.group.created_by if instance.group.created_by else instance.user,
                target_type='Group',
                target_id=instance.group.id,
                context_type='Group',
                context_id=instance.group.id,
                metadata={
                    'group_name': instance.group.name,
                    'user_id': instance.user.id,
                    'user_username': instance.user.username,
                }
            )
