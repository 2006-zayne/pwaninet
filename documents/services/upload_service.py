"""Upload service for handling document uploads.

This service encapsulates the business logic for uploading documents,
keeping it out of the views and models.
"""

import logging
from typing import List, Optional
from django.db import transaction
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from ..documents.models import (
    Document,
    DocumentVersion,
    DocumentFile,
    DocumentAuthor,
    DocumentAcademicUnit,
    DocumentTag,
)
from ..academic.models import AcademicUnit, Semester, AcademicYear
from ..storage.models import FileChecksum
from ..events.base import DocumentUploadedEvent
from ..events.dispatcher import event_dispatcher

logger = logging.getLogger(__name__)


class UploadService:
    """Service for handling document uploads."""
    
    def __init__(self):
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.allowed_extensions = ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'zip', 'rar']
    
    def validate_file(self, file: UploadedFile) -> tuple[bool, str]:
        """Validate an uploaded file."""
        if not file or not getattr(file, 'name', None):
            return False, "Invalid file"

        # Check empty file
        if getattr(file, 'size', 0) == 0:
            return False, "File is empty"

        # Check file size
        if file.size > self.max_file_size:
            max_mb = int(self.max_file_size / (1024 * 1024))
            return False, f"File size exceeds maximum of {max_mb}MB"
        
        # Check file extension
        extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
        if not extension or extension not in self.allowed_extensions:
            return False, f"File type '{extension}' is not allowed. Supported formats: {', '.join(self.allowed_extensions).upper()}"
        
        return True, ""
    
    def compute_checksum(self, file: UploadedFile) -> str:
        """Compute SHA-256 checksum for a file."""
        return FileChecksum.compute_checksum(file, algorithm='sha256')
    
    def check_duplicate(self, checksum: str) -> Optional['DocumentFile']:
        """Check if a file with this checksum already exists."""
        try:
            checksum_obj = FileChecksum.objects.get(checksum=checksum)
            # Get the most recent file with this checksum
            recent_file = DocumentFile.objects.filter(
                checksum=checksum
            ).order_by('-uploaded_at').first()
            return recent_file
        except FileChecksum.DoesNotExist:
            return None
    
    @transaction.atomic
    def create_document(
        self,
        title: str,
        description: str,
        category_id: int,
        uploaded_by,
        academic_unit_ids: List[int],
        semester_id: int,
        academic_year_id: int,
        tags: List[str] = None,
        authors: List[dict] = None,
        visibility: str = 'public',
    ) -> Document:
        """Create a new document with metadata."""
        document = Document.objects.create(
            title=title,
            description=description,
            category_id=category_id,
            uploaded_by=uploaded_by,
            visibility=visibility,
            status='draft',
            language='en',
        )
        
        # Add academic unit mappings
        for unit_id in academic_unit_ids:
            DocumentAcademicUnit.objects.create(
                document=document,
                academic_unit_id=unit_id,
                semester_id=semester_id,
                academic_year_id=academic_year_id,
                is_primary=(unit_id == academic_unit_ids[0]),
            )
        
        # Add tags
        if tags:
            from ..documents.models import Tag
            for tag_name in tags:
                tag, _ = Tag.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': tag_name.lower().replace(' ', '-')}
                )
                DocumentTag.objects.create(document=document, tag=tag)
        
        # Add authors
        if authors:
            for author_data in authors:
                DocumentAuthor.objects.create(
                    document=document,
                    user=author_data.get('user_id'),
                    name=author_data.get('name'),
                    author_type=author_data.get('author_type', 'uploader'),
                )
        
        logger.info(f"Created document {document.id}")
        return document
    
    @transaction.atomic
    def create_version(
        self,
        document: Document,
        files: List[UploadedFile],
        uploaded_by,
        change_notes: str = "",
    ) -> DocumentVersion:
        """Create a new version of a document with files."""
        # Get next version number
        last_version = document.versions.order_by('-version_number').first()
        version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create version
        version = DocumentVersion.objects.create(
            document=document,
            version_number=version_number,
            change_notes=change_notes,
            created_by=uploaded_by,
            is_latest=True,
        )
        
        # Mark previous versions as not latest
        document.versions.exclude(id=version.id).update(is_latest=False)
        
        # Add files to version
        for file in files:
            self._add_file_to_version(version, file, uploaded_by)
        
        logger.info(f"Created version {version_number} for document {document.id}")
        return version
    
    def _add_file_to_version(
        self,
        version: DocumentVersion,
        file: UploadedFile,
        uploaded_by,
    ) -> DocumentFile:
        """Add a file to a document version."""
        # Compute checksum
        checksum = self.compute_checksum(file)
        
        # Check for duplicate
        duplicate = self.check_duplicate(checksum)
        if duplicate:
            logger.warning(f"Duplicate file detected: {file.name}")
            # Could raise an exception here or handle differently
        
        # Create or update checksum record
        checksum_obj, _ = FileChecksum.objects.get_or_create(
            checksum=checksum,
            defaults={'algorithm': 'sha256'}
        )
        checksum_obj.increment_count()
        
        # Store file (this would use the storage service)
        # For now, we'll just record the metadata
        extension = file.name.split('.')[-1].lower()
        mime_type = self._get_mime_type(extension)
        
        document_file = DocumentFile.objects.create(
            document_version=version,
            original_filename=file.name,
            storage_path=f"documents/{version.document.id}/{version.id}/{file.name}",
            mime_type=mime_type,
            extension=extension,
            size_bytes=file.size,
            checksum=checksum,
            storage_provider='local',
            processing_status='pending',
            uploaded_by=uploaded_by,
        )
        
        logger.info(f"Added file {file.name} to version {version.id}")
        return document_file
    
    def _get_mime_type(self, extension: str) -> str:
        """Get MIME type for a file extension."""
        mime_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'ppt': 'application/vnd.ms-powerpoint',
            'zip': 'application/zip',
            'rar': 'application/vnd.rar',
        }
        return mime_types.get(extension, 'application/octet-stream')
    
    @transaction.atomic
    def complete_upload(self, document: Document) -> Document:
        """Mark document upload as complete and queue processing."""
        document.status = 'processing'
        document.save(update_fields=['status'])
        
        logger.info(f"Completed upload for document {document.id}, queued processing")
        return document

    @transaction.atomic
    def create_document_version(
        self,
        document: Document,
        file: UploadedFile,
        user,
        change_notes: str = ''
    ) -> DocumentVersion:
        """Create a new version for an existing document with the provided file."""
        is_valid, err = self.validate_file(file)
        if not is_valid:
            raise ValueError(err)

        next_version_num = document.versions.count() + 1
        
        # Unmark previous latest versions
        document.versions.filter(is_latest=True).update(is_latest=False)

        version = DocumentVersion.objects.create(
            document=document,
            version_number=next_version_num,
            change_notes=change_notes,
            created_by=user,
            is_latest=True
        )

        extension = file.name.split('.')[-1].lower() if '.' in file.name else ''
        mime_type = getattr(file, 'content_type', None) or self._get_mime_type(extension)

        DocumentFile.objects.create(
            document_version=version,
            file=file,
            original_filename=file.name,
            storage_path=f"documents/{document.id}/{version.id}/{file.name}",
            mime_type=mime_type,
            extension=extension,
            size_bytes=file.size,
            storage_provider='local',
            processing_status='pending',
            uploaded_by=user,
        )

        # Update document status to processing
        document.status = 'processing'
        document.save(update_fields=['status'])

        # Trigger Celery processing
        from ..tasks.processing import process_document
        process_document.delay(document.id)

        logger.info(
            f"Created version {next_version_num} for document {document.id}, queued processing"
        )
        return version

