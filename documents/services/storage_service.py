"""Storage service for abstracting file storage operations.

This service provides a storage-agnostic interface for file operations,
allowing migration between different storage backends without changing business logic.
"""

import logging
from typing import Optional
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from ..storage.models import StorageBackend, StorageMigration

logger = logging.getLogger(__name__)


class StorageService:
    """Service for handling file storage operations."""
    
    def __init__(self):
        self.default_backend = self._get_default_backend()
    
    def _get_default_backend(self) -> StorageBackend:
        """Get the default storage backend."""
        try:
            return StorageBackend.objects.get(is_default=True, is_active=True)
        except StorageBackend.DoesNotExist:
            # Fallback to first active backend
            return StorageBackend.objects.filter(is_active=True).first()
    
    def store_file(
        self,
        file,
        path: str,
        backend: Optional[StorageBackend] = None,
    ) -> str:
        """Store a file using the specified or default backend."""
        backend = backend or self.default_backend
        
        if backend.backend_type == 'local':
            return self._store_local(file, path)
        elif backend.backend_type == 's3':
            return self._store_s3(file, path, backend.config)
        elif backend.backend_type == 'r2':
            return self._store_r2(file, path, backend.config)
        else:
            raise ValueError(f"Unsupported backend type: {backend.backend_type}")
    
    def _store_local(self, file, path: str) -> str:
        """Store file using local Django storage."""
        # Save file to local storage
        name = default_storage.save(path, file)
        logger.info(f"Stored file locally at {name}")
        return name
    
    def _store_s3(self, file, path: str, config: dict) -> str:
        """Store file using Amazon S3."""
        # This would use boto3 for S3 storage
        # For now, fallback to local storage
        logger.warning("S3 storage not implemented, falling back to local")
        return self._store_local(file, path)
    
    def _store_r2(self, file, path: str, config: dict) -> str:
        """Store file using Cloudflare R2."""
        # This would use appropriate R2 SDK
        # For now, fallback to local storage
        logger.warning("R2 storage not implemented, falling back to local")
        return self._store_local(file, path)
    
    def retrieve_file(self, path: str, backend: Optional[StorageBackend] = None):
        """Retrieve a file from storage."""
        backend = backend or self.default_backend
        
        if backend.backend_type == 'local':
            return self._retrieve_local(path)
        else:
            # Implement other backends
            return self._retrieve_local(path)
    
    def _retrieve_local(self, path: str):
        """Retrieve file from local storage."""
        if default_storage.exists(path):
            return default_storage.open(path, 'rb')
        raise FileNotFoundError(f"File not found: {path}")
    
    def delete_file(self, path: str, backend: Optional[StorageBackend] = None) -> bool:
        """Delete a file from storage."""
        backend = backend or self.default_backend
        
        if backend.backend_type == 'local':
            return self._delete_local(path)
        else:
            return self._delete_local(path)
    
    def _delete_local(self, path: str) -> bool:
        """Delete file from local storage."""
        if default_storage.exists(path):
            default_storage.delete(path)
            logger.info(f"Deleted file from local storage: {path}")
            return True
        return False
    
    def file_exists(self, path: str, backend: Optional[StorageBackend] = None) -> bool:
        """Check if a file exists in storage."""
        backend = backend or self.default_backend
        
        if backend.backend_type == 'local':
            return default_storage.exists(path)
        else:
            return default_storage.exists(path)
    
    def get_file_url(self, path: str, backend: Optional[StorageBackend] = None) -> str:
        """Get the public URL for a file."""
        backend = backend or self.default_backend
        
        if backend.backend_type == 'local':
            return default_storage.url(path)
        else:
            return default_storage.url(path)
    
    def initiate_migration(
        self,
        source_backend_id: int,
        target_backend_id: int,
        initiated_by,
    ) -> StorageMigration:
        """Initiate a storage migration between backends."""
        source = StorageBackend.objects.get(id=source_backend_id)
        target = StorageBackend.objects.get(id=target_backend_id)
        
        # Count files to migrate
        from ..documents.models import DocumentFile
        total_files = DocumentFile.objects.filter(
            storage_provider=source.backend_type
        ).count()
        
        migration = StorageMigration.objects.create(
            source_backend=source,
            target_backend=target,
            status='pending',
            total_files=total_files,
            created_by=initiated_by,
        )
        
        logger.info(f"Initiated storage migration {migration.id}")
        return migration
