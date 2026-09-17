"""
Page-aware PDF structural extractor using PyMuPDF (fitz).
"""

import os
import re
import logging
from typing import Optional
from .base import BaseDocumentExtractor
from ..types import ExtractedDocument, ExtractedElement, ElementType, LocationMetadata
from ..exceptions import CorruptFileError, EmptyDocumentError, ExtractionError

logger = logging.getLogger(__name__)

# Heuristic patterns for academic and document headings
HEADING_REGEX = re.compile(
    r'^(?:chapter\s+\d+|section\s+\d+|unit\s+\d+|part\s+[a-z0-9]+|question\s+\d+|q\d+[\.:])',
    re.IGNORECASE
)


class PDFExtractor(BaseDocumentExtractor):
    """
    Extracts structured elements from PDF files page-by-page,
    preserving page numbers, reading order blocks, and section headings.
    """

    def __init__(self, max_pages: Optional[int] = None):
        self.max_pages = max_pages

    def extract(self, file_path: str, filename: Optional[str] = None, **kwargs) -> ExtractedDocument:
        if not file_path or not os.path.isfile(file_path):
            raise CorruptFileError(f"PDF file not found: {file_path}", source_filename=filename or file_path, format="pdf")

        display_name = filename or os.path.basename(file_path)

        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ExtractionError("PyMuPDF (fitz) library is not installed", source_filename=display_name, format="pdf") from e

        doc = None
        elements = []
        current_section = None

        try:
            try:
                doc = fitz.open(file_path)
            except Exception as e:
                raise CorruptFileError(f"Cannot open PDF document: {e}", source_filename=display_name, format="pdf") from e

            total_pages = len(doc)
            if total_pages == 0:
                raise EmptyDocumentError(f"PDF document contains 0 pages: {display_name}", source_filename=display_name, format="pdf")

            limit = min(total_pages, self.max_pages) if self.max_pages else total_pages

            for page_idx in range(limit):
                page_num = page_idx + 1
                page = doc[page_idx]
                blocks = page.get_text("blocks")

                for block_idx, block in enumerate(blocks):
                    # block format: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(block) >= 7 and block[6] != 0:
                        continue  # Skip image/non-text blocks

                    raw_text = block[4] if len(block) > 4 else ""
                    text = raw_text.replace('\x00', '').strip()
                    if not text:
                        continue

                    # Heuristic heading detection
                    is_heading = False
                    first_line = text.split('\n')[0].strip()
                    if (
                        HEADING_REGEX.match(first_line) or
                        (len(text) < 100 and (text.isupper() or text.istitle()) and not text.endswith('.'))
                    ):
                        is_heading = True
                        current_section = first_line[:120]

                    elem_type = ElementType.HEADING if is_heading else ElementType.PARAGRAPH
                    location = LocationMetadata(
                        page_number=page_num,
                        block_index=block_idx,
                        section_heading=current_section,
                        extra={
                            "bbox": [round(coord, 2) for coord in block[:4]] if len(block) >= 4 else []
                        }
                    )

                    elements.append(
                        ExtractedElement(
                            element_type=elem_type,
                            text=text,
                            location=location,
                            metadata={"char_count": len(text)}
                        )
                    )

        finally:
            if doc is not None:
                doc.close()

        if not elements:
            raise EmptyDocumentError(f"No extractable text found in PDF: {display_name}", source_filename=display_name, format="pdf")

        return ExtractedDocument(
            source_filename=display_name,
            format="pdf",
            elements=elements,
            metadata={
                "total_pages": total_pages,
                "parsed_pages": limit,
                "element_count": len(elements)
            }
        )
