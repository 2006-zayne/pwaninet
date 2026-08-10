"""
Document domain signals for event emission.
Emits events for the new notification engine.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from documents.documents.models import Document
from documents.engagement.models import DocumentDownload, DocumentBookmark, DocumentRating
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(post_save, sender=Document)
def document_uploaded_or_published(sender, instance, created, **kwargs):
    """Emit event when document is uploaded or published."""
    if created:
        # Get primary academic unit for context
        primary_academic_unit = instance.academic_units.filter(is_primary=True).first()
        
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        try:
            if instance.latest_version:
                first_file = instance.latest_version.files.first()
                if first_file and first_file.preview_path:
                    thumbnail_url = f"/media/{first_file.preview_path}"
        except:
            pass
        
        # Document uploaded
        publish_event(
            event_type=EventTypes.DOCUMENTS_DOCUMENT_UPLOADED.value,
            source=EventSources.DOCUMENTS.value,
            action=EventActions.UPLOADED.value,
            actor=instance.uploaded_by,
            target_type='Document',
            target_id=str(instance.id),
            context_type='ACADEMIC_UNIT',
            context_id=str(primary_academic_unit.academic_unit.id) if primary_academic_unit else None,
            metadata={
                'document_title': instance.title,
                'category': instance.category.code,
                'uploader_username': instance.uploaded_by.username if instance.uploaded_by else None,
                'academic_unit_id': str(primary_academic_unit.academic_unit.id) if primary_academic_unit else None,
                'academic_unit_code': primary_academic_unit.academic_unit.code if primary_academic_unit else None,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'DOCUMENT',
            }
        )
    else:
        # Check if document was just published
        if hasattr(instance, 'is_published') and instance.is_published:
            # Get thumbnail URL for notification preview
            thumbnail_url = None
            try:
                if instance.latest_version:
                    first_file = instance.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
            
            publish_event(
                event_type=EventTypes.DOCUMENTS_DOCUMENT_PUBLISHED.value,
                source=EventSources.DOCUMENTS.value,
                action=EventActions.PUBLISHED.value,
                actor=instance.uploaded_by,
                target_type='Document',
                target_id=str(instance.id),
                metadata={
                    'document_title': instance.title,
                    'category': instance.category.code,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'DOCUMENT',
                }
            )


@receiver(post_save, sender=DocumentDownload)
def document_downloaded(sender, instance, created, **kwargs):
    """Emit event when document is downloaded."""
    if created:
        publish_event(
            event_type=EventTypes.DOCUMENTS_DOCUMENT_DOWNLOADED.value,
            source=EventSources.DOCUMENTS.value,
            action=EventActions.DOWNLOADED.value,
            actor=instance.user,
            target_type='Document',
            target_id=str(instance.document.id),
            metadata={
                'document_title': instance.document.title,
                'downloader_username': instance.user.username
            }
        )


@receiver(post_save, sender=DocumentBookmark)
def document_bookmarked(sender, instance, created, **kwargs):
    """Emit event when document is bookmarked."""
    if created:
        publish_event(
            event_type=EventTypes.DOCUMENTS_DOCUMENT_BOOKMARKED.value,
            source=EventSources.DOCUMENTS.value,
            action=EventActions.BOOKMARKED.value,
            actor=instance.user,
            target_type='Document',
            target_id=str(instance.document.id),
            metadata={
                'document_title': instance.document.title,
                'bookmarker_username': instance.user.username
            }
        )


@receiver(post_save, sender=DocumentRating)
def document_rated(sender, instance, created, **kwargs):
    """Emit event when document is rated."""
    if created:
        publish_event(
            event_type=EventTypes.DOCUMENTS_DOCUMENT_RATED.value,
            source=EventSources.DOCUMENTS.value,
            action=EventActions.RATED.value,
            actor=instance.user,
            target_type='Document',
            target_id=str(instance.document.id),
            metadata={
                'document_title': instance.document.title,
                'rating': instance.rating,
                'rater_username': instance.user.username
            }
        )
