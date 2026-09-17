"""
Order-preserving DOCX structural extractor using python-docx.
Preserves true document sequence across headings, paragraphs, and tables.
"""

import os
import logging
from typing import Optional
from .base import BaseDocumentExtractor
from ..types import ExtractedDocument, ExtractedElement, ElementType, LocationMetadata
from ..exceptions import CorruptFileError, EmptyDocumentError, ExtractionError

logger = logging.getLogger(__name__)


class DocxExtractor(BaseDocumentExtractor):
    """
    Extracts structured elements from DOCX files in their exact spatial sequence,
    interleaving headings, body paragraphs, and tables as they appear in the original document.
    """

    def extract(self, file_path: str, filename: Optional[str] = None, **kwargs) -> ExtractedDocument:
        if not file_path or not os.path.isfile(file_path):
            raise CorruptFileError(f"DOCX file not found: {file_path}", source_filename=filename or file_path, format="docx")

        display_name = filename or os.path.basename(file_path)

        try:
            import docx
            from docx.oxml.text.paragraph import CT_P
            from docx.oxml.table import CT_Tbl
            from docx.text.paragraph import Paragraph
            from docx.table import Table
        except ImportError as e:
            raise ExtractionError("python-docx library is not installed", source_filename=display_name, format="docx") from e

        try:
            doc = docx.Document(file_path)
        except Exception as e:
            raise CorruptFileError(f"Cannot open DOCX document: {e}", source_filename=display_name, format="docx") from e

        elements = []
        current_section = None
        block_counter = 0

        # Traverse body child elements in natural document order
        for child in doc.element.body.iterchildren():
            if isinstance(child, CT_P):
                p = Paragraph(child, doc)
                text = p.text.replace('\x00', '').strip()
                if not text:
                    continue

                style_name = p.style.name if p.style else "Normal"
                style_lower = style_name.lower()

                # Determine element type
                if "heading" in style_lower or style_lower.startswith("title"):
                    elem_type = ElementType.HEADING
                    current_section = text[:120]
                    heading_level = None
                    for part in style_name.split():
                        if part.isdigit():
                            heading_level = int(part)
                            break
                    meta = {"style": style_name, "level": heading_level}
                elif "list" in style_lower or "bullet" in style_lower:
                    elem_type = ElementType.PARAGRAPH
                    meta = {"style": style_name, "is_list_item": True}
                elif "code" in style_lower:
                    elem_type = ElementType.CODE
                    meta = {"style": style_name}
                else:
                    elem_type = ElementType.PARAGRAPH
                    meta = {"style": style_name}

                elements.append(
                    ExtractedElement(
                        element_type=elem_type,
                        text=text,
                        location=LocationMetadata(
                            block_index=block_counter,
                            section_heading=current_section,
                        ),
                        metadata=meta,
                    )
                )
                block_counter += 1

            elif isinstance(child, CT_Tbl):
                t = Table(child, doc)
                rows_data = []
                for row in t.rows:
                    cells = [c.text.replace('\x00', '').strip() for c in row.cells]
                    if any(cells):
                        rows_data.append(cells)

                if not rows_data:
                    continue

                # Format table as clean pipe-delimited text/markdown
                table_lines = []
                for row_idx, row in enumerate(rows_data):
                    table_lines.append(" | ".join(row))
                    if row_idx == 0 and len(rows_data) > 1:
                        table_lines.append(" | ".join(["---"] * len(row)))

                formatted_table_text = "\n".join(table_lines)

                elements.append(
                    ExtractedElement(
                        element_type=ElementType.TABLE,
                        text=formatted_table_text,
                        location=LocationMetadata(
                            block_index=block_counter,
                            section_heading=current_section,
                        ),
                        metadata={
                            "row_count": len(rows_data),
                            "col_count": len(rows_data[0]) if rows_data else 0,
                        },
                    )
                )
                block_counter += 1

        if not elements:
            raise EmptyDocumentError(f"No extractable text found in DOCX: {display_name}", source_filename=display_name, format="docx")

        return ExtractedDocument(
            source_filename=display_name,
            format="docx",
            elements=elements,
            metadata={
                "element_count": len(elements),
                "total_paragraphs_and_tables": block_counter,
            }
        )
