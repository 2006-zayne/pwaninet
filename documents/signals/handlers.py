"""Django signal handlers for the document repository.

These handlers respond to Django model signals and emit domain events,
keeping the repository decoupled from other PwaniNet modules.
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.conf import settings

from ..events.base import (
    DocumentUploadedEvent,
    DocumentPublishedEvent,
    DocumentDownloadedEvent,
    DocumentReportedEvent,
    RequestFulfilledEvent,
    ModerationStatusChangedEvent,
)
from ..events.dispatcher import event_dispatcher

logger = logging.getLogger(__name__)


@receiver(post_save, sender='documents.Document')
def document_post_save(sender, instance, created, **kwargs):
    """Handle document post-save signals."""
    if created:
        # Emit document uploaded event
        event = DocumentUploadedEvent(
            document_id=instance.id,
            document_title=instance.title,
            user_id=instance.uploaded_by.id,
            category=instance.category.code,
            academic_units=[
                au.academic_unit.code for au in instance.academic_units.all()
            ],
        )
        event_dispatcher.emit(event)
        logger.info(f"Emitted DocumentUploadedEvent for document {instance.id}")
    
    elif instance.status == 'ready' and not instance.published_at:
        # Document was published
        instance.published_at = instance.created_at
        instance.save(update_fields=['published_at'])
        
        event = DocumentPublishedEvent(
            document_id=instance.id,
            document_title=instance.title,
            user_id=instance.uploaded_by.id,
        )
        event_dispatcher.emit(event)
        logger.info(f"Emitted DocumentPublishedEvent for document {instance.id}")


@receiver(post_save, sender='documents.DocumentDownload')
def document_download_post_save(sender, instance, created, **kwargs):
    """Handle document download signals."""
    if created:
        event = DocumentDownloadedEvent(
            document_id=instance.document.id,
            document_title=instance.document.title,
            user_id=instance.user.id if instance.user else None,
            file_name=instance.document_file.original_filename,
        )
        event_dispatcher.emit(event)
        logger.info(f"Emitted DocumentDownloadedEvent for document {instance.document.id}")
        
        # Update analytics immediately
        from ..engagement.models import DocumentAnalytics
        analytics, created = DocumentAnalytics.objects.get_or_create(
            document=instance.document
        )
        analytics.download_count = instance.document.downloads.count()
        analytics.save(update_fields=['download_count'])
        logger.info(f"Updated download_count to {analytics.download_count} for document {instance.document.id}")


@receiver(post_save, sender='documents.DocumentReport')
def document_report_post_save(sender, instance, created, **kwargs):
    """Handle document report signals."""
    if created:
        event = DocumentReportedEvent(
            document_id=instance.document.id,
            document_title=instance.document.title,
            user_id=instance.user.id if instance.user else None,
            reason=instance.reason,
        )
        event_dispatcher.emit(event)
        logger.info(f"Emitted DocumentReportedEvent for document {instance.document.id}")


@receiver(post_save, sender='documents.DocumentRequest')
def document_request_post_save(sender, instance, created, **kwargs):
    """Handle document request signals."""
    if not created and instance.status == 'fulfilled' and instance.fulfilled_document:
        event = RequestFulfilledEvent(
            request_id=instance.id,
            request_title=instance.title,
            document_id=instance.fulfilled_document.id,
            fulfilled_by_user_id=instance.fulfilled_by.id if instance.fulfilled_by else None,
            requested_by_user_id=instance.requested_by.id,
        )
        event_dispatcher.emit(event)
        logger.info(f"Emitted RequestFulfilledEvent for request {instance.id}")


@receiver(pre_save, sender='documents.DocumentModeration')
def document_moderation_pre_save(sender, instance, **kwargs):
    """Handle document moderation status changes."""
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        old_status = old_instance.status.code
        new_status = instance.status.code
        
        if old_status != new_status:
            # Store old status for post_save handler
            instance._old_status = old_status
    else:
        instance._old_status = None


@receiver(post_save, sender='documents.DocumentModeration')
def document_moderation_post_save(sender, instance, created, **kwargs):
    """Handle document moderation post-save signals."""
    if not created and hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status.code
        
        if old_status != new_status:
            event = ModerationStatusChangedEvent(
                document_id=instance.document.id,
                document_title=instance.document.title,
                old_status=old_status,
                new_status=new_status,
                moderated_by_user_id=instance.moderated_by.id if instance.moderated_by else None,
            )
            event_dispatcher.emit(event)
            logger.info(
                f"Emitted ModerationStatusChangedEvent for document {instance.document.id}: "
                f"{old_status} -> {new_status}"
            )
