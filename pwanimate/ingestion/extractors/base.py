"""
Base extractor interface for Pwanimate document extraction.
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..types import ExtractedDocument


class BaseDocumentExtractor(ABC):
    """Abstract base class for format-specific structural document extractors."""

    @abstractmethod
    def extract(self, file_path: str, filename: Optional[str] = None, **kwargs) -> ExtractedDocument:
        """
        Extract structured elements from a file.

        Args:
            file_path: Local filesystem path to the file.
            filename: Optional display or original filename.
            **kwargs: Extractor-specific options.

        Returns:
            ExtractedDocument containing ordered structural elements with location metadata.

        Raises:
            CorruptFileError: If the file is unreadable or malformed.
            EmptyDocumentError: If the file contains no text content.
            ExtractionError: For generic extractor failures.
        """
        pass
