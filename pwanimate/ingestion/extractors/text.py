"""
Plain text and source code structural extractor.
"""

import os
import re
import logging
from typing import Optional
from .base import BaseDocumentExtractor
from ..types import ExtractedDocument, ExtractedElement, ElementType, LocationMetadata
from ..exceptions import CorruptFileError, EmptyDocumentError

logger = logging.getLogger(__name__)


class TextExtractor(BaseDocumentExtractor):
    """
    Extracts structured elements from plain text, markdown, and source code files,
    partitioning content on logical paragraph or section boundaries.
    """

    def extract(self, file_path: str, filename: Optional[str] = None, **kwargs) -> ExtractedDocument:
        if not file_path or not os.path.isfile(file_path):
            raise CorruptFileError(f"Text file not found: {file_path}", source_filename=filename or file_path, format="txt")

        display_name = filename or os.path.basename(file_path)
        ext = os.path.splitext(display_name)[1].lower().lstrip('.')

        raw_content = ""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="latin-1", errors="replace") as f:
                    raw_content = f.read()
            except Exception as e:
                raise CorruptFileError(f"Failed to decode text file: {e}", source_filename=display_name, format=ext) from e

        cleaned = raw_content.replace('\x00', '').strip()
        if not cleaned:
            raise EmptyDocumentError(f"Text file is empty: {display_name}", source_filename=display_name, format=ext)

        elements = []
        current_heading = None

        # Split on double newlines to form logical paragraphs/blocks
        blocks = re.split(r'\n{2,}', cleaned)

        for block_idx, block in enumerate(blocks):
            text = block.strip()
            if not text:
                continue

            elem_type = ElementType.PARAGRAPH
            if re.match(r'^#{1,6}\s+', text):
                elem_type = ElementType.HEADING
                current_heading = text.lstrip('#').strip().split('\n')[0][:120]
            elif text.startswith('```') or ext in ('py', 'js', 'java', 'c', 'cpp', 'html', 'json', 'xml', 'sql'):
                elem_type = ElementType.CODE

            elements.append(
                ExtractedElement(
                    element_type=elem_type,
                    text=text,
                    location=LocationMetadata(
                        block_index=block_idx,
                        section_heading=current_heading,
                    ),
                    metadata={"source_extension": ext},
                )
            )

        if not elements:
            raise EmptyDocumentError(f"No extractable text in file: {display_name}", source_filename=display_name, format=ext)

        return ExtractedDocument(
            source_filename=display_name,
            format=ext or "txt",
            elements=elements,
            metadata={
                "element_count": len(elements),
                "total_characters": len(cleaned),
            }
        )
