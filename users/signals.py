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
    # Try to get device ID from headers first (HTMX requests)
    device_id = request.headers.get('X-Device-ID')
    
    # Fallback to POST data (regular form submissions)
    if not device_id:
        device_id = request.POST.get('device_id')
    
    if device_id:
        # Hash the device ID before storing
        hashed_device_id = hash_device_id(device_id)
        
        # Create or update the DeviceAccount record
        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': request.session.session_key
            }
        )
    else:
        # If no device ID, generate one and store it
        from .services.device_service import generate_device_id
        device_id = generate_device_id()
        hashed_device_id = hash_device_id(device_id)
        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': request.session.session_key
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
    Automatically enrolls new users in official academic groups based on their course and year.

    This function now uses an asynchronous Celery task to prevent blocking the main thread
    and causing timeouts during user signup. The task runs in the background and handles
    both the service-based approach (database flags) and the fallback naming convention.
    """
    # Only execute for NEW users who have completed their profile intel
    if created and instance.course and instance.year:
        # Dispatch the async task to prevent blocking
        from groups.tasks import auto_join_course_group_task
        auto_join_course_group_task.delay(instance.id)


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
