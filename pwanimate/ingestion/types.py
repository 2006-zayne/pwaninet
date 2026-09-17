"""
Intermediate Representation for Pwanimate Structural Document Extraction.

Provides a format-agnostic, structure-preserving data contract representing
extracted document elements (headings, paragraphs, tables, slides, notes)
and their spatial/document locations (page number, slide number, section heading).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ElementType(str, Enum):
    """Semantic types of extracted document elements."""
    DOCUMENT = "document"
    PAGE = "page"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    SLIDE = "slide"
    NOTES = "notes"
    CODE = "code"
    TEXT = "text"


@dataclass
class LocationMetadata:
    """Location and spatial context of an extracted element within a document."""
    page_number: Optional[int] = None
    page_end: Optional[int] = None
    slide_number: Optional[int] = None
    section_heading: Optional[str] = None
    block_index: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.page_number is not None:
            result['page_number'] = self.page_number
        if self.page_end is not None:
            result['page_end'] = self.page_end
        if self.slide_number is not None:
            result['slide_number'] = self.slide_number
        if self.section_heading:
            result['section_heading'] = self.section_heading
        if self.block_index is not None:
            result['block_index'] = self.block_index
        if self.extra:
            result['extra'] = self.extra
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LocationMetadata":
        return cls(
            page_number=data.get('page_number'),
            page_end=data.get('page_end'),
            slide_number=data.get('slide_number'),
            section_heading=data.get('section_heading'),
            block_index=data.get('block_index'),
            extra=data.get('extra', {}),
        )


@dataclass
class ExtractedElement:
    """An individual structural unit of a document (e.g. paragraph, heading, table, slide)."""
    element_type: str
    text: str
    location: LocationMetadata = field(default_factory=LocationMetadata)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_type": self.element_type,
            "text": self.text,
            "location": self.location.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedElement":
        loc_data = data.get("location", {})
        location = LocationMetadata.from_dict(loc_data) if isinstance(loc_data, dict) else LocationMetadata()
        return cls(
            element_type=data.get("element_type", ElementType.TEXT),
            text=data.get("text", ""),
            location=location,
            metadata=data.get("metadata", {}),
        )


@dataclass
class ExtractedDocument:
    """Complete structure-preserving extraction result for a document file."""
    source_filename: str
    format: str
    elements: List[ExtractedElement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_filename": self.source_filename,
            "format": self.format,
            "elements": [elem.to_dict() for elem in self.elements],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedDocument":
        raw_elements = data.get("elements", [])
        elements = [ExtractedElement.from_dict(e) for e in raw_elements]
        return cls(
            source_filename=data.get("source_filename", ""),
            format=data.get("format", ""),
            elements=elements,
            metadata=data.get("metadata", {}),
        )

    @property
    def total_pages(self) -> int:
        """Total pages in document if known, or derived from elements."""
        if "total_pages" in self.metadata:
            return self.metadata["total_pages"]
        pages = {e.location.page_number for e in self.elements if e.location.page_number is not None}
        return len(pages) if pages else 0

    @property
    def total_slides(self) -> int:
        """Total slides in presentation if known, or derived from elements."""
        if "total_slides" in self.metadata:
            return self.metadata["total_slides"]
        slides = {e.location.slide_number for e in self.elements if e.location.slide_number is not None}
        return len(slides) if slides else 0

    def get_full_text(self, separator: str = "\n\n") -> str:
        """Return combined text of all elements."""
        return separator.join(elem.text for elem in self.elements if elem.text.strip())

    def get_elements_by_type(self, element_type: str) -> List[ExtractedElement]:
        """Filter elements by their semantic type."""
        return [elem for elem in self.elements if elem.element_type == element_type]

    def get_elements_by_page(self, page_number: int) -> List[ExtractedElement]:
        """Filter elements residing on a specific 1-indexed page."""
        return [elem for elem in self.elements if elem.location.page_number == page_number]

    def get_elements_by_slide(self, slide_number: int) -> List[ExtractedElement]:
        """Filter elements residing on a specific 1-indexed slide."""
        return [elem for elem in self.elements if elem.location.slide_number == slide_number]

    @property
    def total_characters(self) -> int:
        """Total character count across all extracted elements."""
        return sum(len(elem.text) for elem in self.elements)

    @property
    def element_count(self) -> int:
        """Total number of structural elements."""
        return len(self.elements)
