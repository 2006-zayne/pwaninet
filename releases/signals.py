"""
Release signals for PwaniNet Release Center.

Provides audit trail for release operations.
Tracks status changes, publishing, and other important events.
"""
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Release, ReleaseItem


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
        except Release.DoesNotExist:
            instance._old_status = None
            instance._old_published = None
    else:
        instance._old_status = None
        instance._old_published = None


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
    
    if created:
        # Log creation
        LogEntry.objects.log_action(
            user_id=instance.created_by.id if instance.created_by else 1,
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=str(instance.pk),
            object_repr=str(instance),
            action_flag=1,  # ADDITION
            change_message=f'Created release {instance.version}'
        )
    else:
        # Log status changes
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            LogEntry.objects.log_action(
                user_id=instance.published_by.id if instance.published_by else instance.created_by.id if instance.created_by else 1,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=str(instance.pk),
                object_repr=str(instance),
                action_flag=2,  # CHANGE
                change_message=f'Status changed from {instance._old_status} to {instance.status}'
            )
        
        # Log publishing
        if hasattr(instance, '_old_published') and not instance._old_published and instance.published:
            LogEntry.objects.log_action(
                user_id=instance.published_by.id if instance.published_by else 1,
                content_type_id=ContentType.objects.get_for_model(instance).pk,
                object_id=str(instance.pk),
                object_repr=str(instance),
                action_flag=2,  # CHANGE
                change_message=f'Published release {instance.version}'
            )


@receiver(pre_delete, sender=Release)
def log_release_deletion(sender, instance, **kwargs):
    """
    Log release deletion before it happens.
    """
    from django.contrib.admin.models import LogEntry
    from django.contrib.contenttypes.models import ContentType
    
    LogEntry.objects.log_action(
        user_id=1,  # System user since we don't have request context here
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
        
        LogEntry.objects.log_action(
            user_id=1,  # System user
            content_type_id=ContentType.objects.get_for_model(instance).pk,
            object_id=str(instance.pk),
            object_repr=str(instance),
            action_flag=1,  # ADDITION
            change_message=f'Added release item: {instance.title}'
        )
