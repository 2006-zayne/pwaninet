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
    This event will be consumed by the notification engine to deliver notifications.
    """
    try:
        from notifications.models import PlatformEvent
        from notifications.events.registry import EventTypes, EventSources, EventActions
        
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
                'version': release.version,
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
    except Exception as e:
        # Log error but don't break the publishing process
        import logging
        logger = logging.getLogger(__name__)
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
        
        # Log publishing
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
        
        # Log and create notification when release is set as current
        if hasattr(instance, '_old_is_current') and not instance._old_is_current and instance.is_current_release:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Release {instance.version} set as current, creating notification event")
            
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
            
            # Create notification event when release is set as current
            create_release_published_event(instance)


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
