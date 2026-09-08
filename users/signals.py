from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DeviceAccount, User, Follow, Pinch
from .services.device_service import get_or_create_device_id, hash_device_id
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(user_logged_in)
def track_device_on_login(sender, request, user, **kwargs):
    """
    Automatically create or update DeviceAccount when a user logs in.
    This tracks which accounts have been used on which devices.
    """
    if not request or not user:
        return

    device_id = get_or_create_device_id(request)
    if device_id:
        hashed_device_id = hash_device_id(device_id)
        session_key = getattr(request.session, 'session_key', None) if hasattr(request, 'session') else None

        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': session_key
            }
        )



@receiver(user_logged_out)
def clear_session_on_logout(sender, request, user, **kwargs):
    """
    Clear the session key from DeviceAccount when user logs out.
    """
    device_id = get_or_create_device_id(request)
    
    if device_id and user:
        hashed_device_id = hash_device_id(device_id)
        DeviceAccount.objects.filter(
            user=user,
            device_id=hashed_device_id
        ).update(session_key=None)


@receiver(post_save, sender=User)
def auto_join_course_group(sender, instance, created, **kwargs):
    """
    Automatically enrolls users in official academic groups based on their
    programme & academic_level (modern) or course & year (legacy).
    """
    has_academic_info = bool(
        (instance.programme and instance.academic_level) or
        (instance.course and instance.year)
    )
    if has_academic_info:
        from groups.tasks import auto_join_course_group_task
        from django.db import transaction
        transaction.on_commit(lambda: auto_join_course_group_task.delay(instance.id))



@receiver(post_save, sender=Follow)
def follow_created(sender, instance, created, **kwargs):
    """Emit event when a user follows another user."""
    if created:
        publish_event(
            event_type=EventTypes.USERS_USER_FOLLOWED.value,
            source=EventSources.USERS.value,
            action=EventActions.FOLLOWED.value,
            actor=instance.follower,
            target_type='User',
            target_id=instance.followed.id,
            context_type='User',
            context_id=instance.followed.id,
            metadata={
                'follower_id': instance.follower.id,
                'follower_username': instance.follower.username,
                'followed_id': instance.followed.id,
                'followed_username': instance.followed.username,
            }
        )


@receiver(post_save, sender=Pinch)
def pinch_created(sender, instance, created, **kwargs):
    """Emit event when a user pinches another user."""
    if created:
        publish_event(
            event_type=EventTypes.USERS_USER_PINCHED.value,
            source=EventSources.USERS.value,
            action=EventActions.PINCHED.value,
            actor=instance.pinch_user,
            target_type='User',
            target_id=instance.pinched_user.id,
            context_type='User',
            context_id=instance.pinched_user.id,
            metadata={
                'pinch_user_id': instance.pinch_user.id,
                'pinch_user_username': instance.pinch_user.username,
                'pinched_user_id': instance.pinched_user.id,
                'pinched_user_username': instance.pinched_user.username,
            }
        )
