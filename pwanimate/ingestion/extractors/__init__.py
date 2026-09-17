"""
Pwanimate Structural Extractors.
"""

from .base import BaseDocumentExtractor
from .pdf import PDFExtractor
from .docx import DocxExtractor
from .pptx import PPTXExtractor
from .text import TextExtractor
from .factory import extract_document, resolve_format

__all__ = [
    'BaseDocumentExtractor',
    'PDFExtractor',
    'DocxExtractor',
    'PPTXExtractor',
    'TextExtractor',
    'extract_document',
    'resolve_format',
]
