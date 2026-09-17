"""
Exceptions for Pwanimate Document Ingestion and Extraction.
"""


class ExtractionError(Exception):
    """Base exception for all document extraction failures."""
    def __init__(self, message: str, source_filename: str = "", format: str = ""):
        super().__init__(message)
        self.source_filename = source_filename
        self.format = format


class UnsupportedFormatError(ExtractionError):
    """Raised when an uploaded document file extension or MIME type is unsupported."""
    pass


class CorruptFileError(ExtractionError):
    """Raised when a file cannot be parsed due to corruption, invalid headers, or syntax errors."""
    pass


class EmptyDocumentError(ExtractionError):
    """Raised when a file contains zero extractable text or content."""
    pass
