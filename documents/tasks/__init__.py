"""Celery async tasks."""

from .processing import (
    process_document,
    process_file,
    generate_thumbnail,
    generate_preview,
    extract_metadata,
    check_duplicate,
    perform_ocr,
    virus_scan,
    update_search_index,
    remove_from_search_index,
    reindex_all_documents,
    get_local_filepath,
)

__all__ = [
    'process_document',
    'process_file',
    'generate_thumbnail',
    'generate_preview',
    'extract_metadata',
    'check_duplicate',
    'perform_ocr',
    'virus_scan',
    'update_search_index',
    'remove_from_search_index',
    'reindex_all_documents',
    'get_local_filepath',
]
