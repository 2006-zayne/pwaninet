"""
Release signals for PwaniNet Release Center.

Provides audit trail for release operations.
Tracks status changes, publishing, and other important events.
"""
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Release, ReleaseItem

User = get_user_model()


def create_release_published_event(release):
    """
    Create a PlatformEvent when a release is published.
    Strictly enforced: ONLY sends ONCE per version across the application lifetime.
    """
    import logging
    logger = logging.getLogger(__name__)

    if not release or not release.published:
        return

    try:
        from notifications.models import PlatformEvent, NotificationObject
        from notifications.events.registry import EventTypes, EventSources, EventActions
        from django.db.models import Q
        from django.core.cache import cache

        version_str = str(release.version).lstrip('v').strip()
        cache_key = f"release_notification_dispatched:{version_str}"

        # 1. Check fast cache lock (prevents concurrency bursts)
        if cache.get(cache_key):
            logger.info(f"[Release Notification] Notification for version {version_str} recently dispatched (cache). Skipping duplicate.")
            return

        # 2. Check PlatformEvent table (ensure no duplicate platform event for this release or version)
        if PlatformEvent.objects.filter(event_type=EventTypes.RELEASES_RELEASE_PUBLISHED.value).filter(
            Q(target_id=str(release.id)) | Q(metadata__version=version_str) | Q(metadata__version=f"v{version_str}")
        ).exists():
            logger.info(f"[Release Notification] PlatformEvent for version {version_str} already exists. Skipping duplicate.")
            cache.set(cache_key, True, timeout=86400 * 30)
            return

        # 3. Check NotificationObject table (ensure notifications have not already been created for users)
        if NotificationObject.objects.filter(
            notification_type='RELEASE'
        ).filter(
            Q(metadata__version=version_str) | Q(title__icontains=version_str) | Q(summary__icontains=version_str)
        ).exists():
            logger.info(f"[Release Notification] NotificationObject for version {version_str} already exists. Skipping duplicate.")
            cache.set(cache_key, True, timeout=86400 * 30)
            return

        # Set cache key immediately to prevent duplicate race conditions
        cache.set(cache_key, True, timeout=86400 * 30)

        # Create platform event for release publication
        PlatformEvent.objects.create(
            event_type=EventTypes.RELEASES_RELEASE_PUBLISHED.value,
            actor=release.published_by or release.created_by,
            source=EventSources.RELEASES.value,
            action=EventActions.PUBLISHED.value,
            target_type='Release',
            target_id=str(release.id),
            audience='EVERYONE',  # Release notifications go to all users
            metadata={
                'target_id': str(release.id),
                'version': version_str,
                'build_number': release.build_number,
                'release_title': release.release_title,
                'release_summary': release.release_summary,
                'release_type': release.release_type,
                'release_channel': release.release_channel,
                'mandatory_update': release.mandatory_update,
                'minimum_supported_version': release.minimum_supported_version,
                'release_url': f'/system/releases/{release.id}/',
            }
        )
        logger.info(f"[Release Notification] Successfully created release published event for version {version_str}")
    except Exception as e:
        logger.error(f"Failed to create release published event: {e}")



@receiver(pre_save, sender=Release)
def track_release_status_change(sender, instance, **kwargs):
    """
    Track status changes before save.
    Stores the old status for comparison in post_save.
    """
    if instance.pk:
        try:
            old_instance = Release.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_published = old_instance.published
            instance._old_is_current = old_instance.is_current_release
        except Release.DoesNotExist:
            instance._old_status = None
            instance._old_published = None
            instance._old_is_current = None
    else:
        instance._old_status = None
        instance._old_published = None
        instance._old_is_current = None


@receiver(post_save, sender=Release)
def log_release_audit_trail(sender, instance, created, **kwargs):
    """
    Log audit trail for release operations.
    
    Tracks:
    - Creation
    - Status changes
    - Publishing
    - Archiving
    """
    from django.contrib.admin.models import LogEntry, CHANGE
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get a valid user ID for logging (fallback to first user if needed)
    def get_valid_user_id(user):
        if user and user.id:
            return user.id
        # Fallback to first available user
        first_user = User.objects.first()
        return first_user.id if first_user else None
    
    if created:
        # Log creation
        user_id = get_valid_user_id(instance.created_by)
        if user_id:
            LogEntry.objects.log_action(
                user_id=user_id,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=str(instance.pk),
                object_repr=str(instance),
                action_flag=1,  # ADDITION
                change_message=f'Created release {instance.version}'
            )
    else:
        # Log status changes
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            user_id = get_valid_user_id(instance.published_by or instance.created_by)
            if user_id:
                LogEntry.objects.log_action(
                    user_id=user_id,
                    content_type_id=ContentType.objects.get_for_model(instance).pk,
                    object_id=str(instance.pk),
                    object_repr=str(instance),
                    action_flag=2,  # CHANGE
                    change_message=f'Status changed from {instance._old_status} to {instance.status}'
                )
        
        # Log publishing and dispatch notification event (strictly once per version)
        if hasattr(instance, '_old_published') and not instance._old_published and instance.published:
            user_id = get_valid_user_id(instance.published_by)
            if user_id:
                LogEntry.objects.log_action(
                    user_id=user_id,
                    content_type_id=ContentType.objects.get_for_model(instance).pk,
                    object_id=str(instance.pk),
                    object_repr=str(instance),
                    action_flag=2,  # CHANGE
                    change_message=f'Published release {instance.version}'
                )
            create_release_published_event(instance)
        
        # Log when release is set as current (audit only, NO notification)
        if hasattr(instance, '_old_is_current') and not instance._old_is_current and instance.is_current_release:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Release {instance.version} set as current")
            
            user_id = get_valid_user_id(instance.published_by or instance.created_by)
            if user_id:
                LogEntry.objects.log_action(
                    user_id=user_id,
                    content_type_id=ContentType.objects.get_for_model(instance).pk,
                    object_id=str(instance.pk),
                    object_repr=str(instance),
                    action_flag=2,  # CHANGE
                    change_message=f'Set release {instance.version} as current'
                )


@receiver(pre_delete, sender=Release)
def log_release_deletion(sender, instance, **kwargs):
    """
    Log release deletion before it happens.
    """
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get a valid user ID for logging (fallback to first user if needed)
    def get_valid_user_id(user):
        if user and user.id:
            return user.id
        # Fallback to first available user
        first_user = User.objects.first()
        return first_user.id if first_user else None
    
    user_id = get_valid_user_id(instance.created_by)
    if user_id:
        LogEntry.objects.log_action(
            user_id=user_id,
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=str(instance.pk),
            object_repr=str(instance),
            action_flag=3,  # DELETION
            change_message=f'Deleted release {instance.version}'
        )


@receiver(post_save, sender=ReleaseItem)
def log_release_item_creation(sender, instance, created, **kwargs):
    """
    Log release item creation.
    """
    if created:
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Get a valid user ID for logging (fallback to first user if needed)
        def get_valid_user_id(user):
            if user and user.id:
                return user.id
            # Fallback to first available user
            first_user = User.objects.first()
            return first_user.id if first_user else None
        
        # Try to get user from the release
        user_id = get_valid_user_id(instance.release.created_by)
        if user_id:
            LogEntry.objects.log_action(
                user_id=user_id,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=str(instance.pk),
                object_repr=str(instance),
                action_flag=1,  # ADDITION
                change_message=f'Added release item: {instance.title}'
            )
