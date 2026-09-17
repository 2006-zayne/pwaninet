"""
Centralized extraction factory and entry point for Pwanimate.
"""

import os
from pathlib import Path
from typing import Union, Optional, Any
from ..types import ExtractedDocument
from ..exceptions import UnsupportedFormatError, ExtractionError
from .pdf import PDFExtractor
from .docx import DocxExtractor
from .pptx import PPTXExtractor
from .text import TextExtractor

# Format registry mapping lowercased extensions to extractor instances
EXTRACTORS = {
    'pdf': PDFExtractor(),
    'docx': DocxExtractor(),
    'doc': DocxExtractor(),
    'pptx': PPTXExtractor(),
    'ppt': PPTXExtractor(),
    'txt': TextExtractor(),
    'md': TextExtractor(),
    'csv': TextExtractor(),
    'json': TextExtractor(),
    'py': TextExtractor(),
    'js': TextExtractor(),
    'java': TextExtractor(),
    'c': TextExtractor(),
    'cpp': TextExtractor(),
    'html': TextExtractor(),
    'xml': TextExtractor(),
    'sql': TextExtractor(),
}

MIME_TYPE_MAP = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/vnd.ms-powerpoint': 'ppt',
    'text/plain': 'txt',
    'text/markdown': 'md',
    'text/csv': 'csv',
    'text/html': 'html',
    'application/json': 'json',
}


def resolve_format(filename: str = "", mime_type: str = "", extension: str = "") -> str:
    """Resolve a normalized format extension string from metadata."""
    if extension:
        ext = extension.lower().lstrip('.')
        if ext in EXTRACTORS:
            return ext

    if filename:
        ext = os.path.splitext(filename)[1].lower().lstrip('.')
        if ext in EXTRACTORS:
            return ext

    if mime_type:
        mime = mime_type.lower().split(';')[0].strip()
        if mime in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[mime]
        if mime.startswith('text/'):
            return 'txt'

    return ""


def extract_document(
    file_input: Union[str, Path, Any],
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    extension: Optional[str] = None,
    **kwargs
) -> ExtractedDocument:
    """
    Central, format-agnostic structural extraction entry point.

    Args:
        file_input: Local path string/Path, OR a PwaniNet DocumentFile model instance.
        filename: Optional original or display filename.
        mime_type: Optional MIME type hint.
        extension: Optional extension hint (e.g. 'pdf').
        **kwargs: Additional parameters passed to format extractors.

    Returns:
        ExtractedDocument containing structured, location-aware elements.

    Raises:
        UnsupportedFormatError: If the document format is not supported.
        CorruptFileError: If the document cannot be parsed or read.
        EmptyDocumentError: If the document contains zero text elements.
        ExtractionError: For generic extraction failures.
    """
    # Check if file_input is a PwaniNet DocumentFile model instance
    if hasattr(file_input, 'file') and hasattr(file_input, 'original_filename'):
        doc_file = file_input
        eff_filename = filename or getattr(doc_file, 'original_filename', '') or os.path.basename(doc_file.file.name)
        eff_mime = mime_type or getattr(doc_file, 'mime_type', '')
        eff_ext = extension or getattr(doc_file, 'extension', '')

        # Use PwaniNet's storage context manager to handle local vs remote R2 storage
        try:
            from documents.tasks.processing import get_local_filepath
        except ImportError:
            get_local_filepath = None

        if get_local_filepath:
            with get_local_filepath(doc_file) as local_path:
                if not local_path:
                    raise ExtractionError(f"Could not resolve local file for DocumentFile {doc_file.id}", source_filename=eff_filename)
                return _extract_from_local_path(
                    file_path=local_path,
                    filename=eff_filename,
                    mime_type=eff_mime,
                    extension=eff_ext,
                    **kwargs
                )
        else:
            # Fallback to direct file path
            return _extract_from_local_path(
                file_path=doc_file.file.path,
                filename=eff_filename,
                mime_type=eff_mime,
                extension=eff_ext,
                **kwargs
            )

    # Standard local path string or Path object
    file_path = str(file_input)
    eff_filename = filename or os.path.basename(file_path)
    return _extract_from_local_path(
        file_path=file_path,
        filename=eff_filename,
        mime_type=mime_type or "",
        extension=extension or "",
        **kwargs
    )


def _extract_from_local_path(
    file_path: str,
    filename: str,
    mime_type: str,
    extension: str,
    **kwargs
) -> ExtractedDocument:
    """Internal router dispatching to format-specific extractor."""
    resolved_ext = resolve_format(filename=filename, mime_type=mime_type, extension=extension)

    if not resolved_ext or resolved_ext not in EXTRACTORS:
        raise UnsupportedFormatError(
            f"Unsupported document format: '{extension or os.path.splitext(filename)[1]}' (MIME: '{mime_type}')",
            source_filename=filename,
            format=resolved_ext
        )

    extractor = EXTRACTORS[resolved_ext]
    return extractor.extract(file_path=file_path, filename=filename, **kwargs)
