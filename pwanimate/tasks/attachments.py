"""Private, page-aware processing for Pwanimate chat attachments."""

import logging
import os
import tempfile
from typing import Any, Dict, List

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from pwanimate.ai.gateway import AIGateway, ChatMessage, LLMRequest
from pwanimate.ai.gateway.types import AttachmentData
from pwanimate.ingestion.chunker import chunk_document
from pwanimate.ingestion.exceptions import EmptyDocumentError
from pwanimate.ingestion.extractors.factory import extract_document
from pwanimate.ingestion.types import (
    ElementType,
    ExtractedDocument,
    ExtractedElement,
    LocationMetadata,
)
from pwanimate.models import PwanimateAttachment, PwanimateAttachmentChunk

logger = logging.getLogger(__name__)


def _copy_attachment_to_temp(attachment: PwanimateAttachment) -> str:
    suffix = os.path.splitext(attachment.file_name)[1]
    handle = tempfile.NamedTemporaryFile(prefix="pwanimate-attachment-", suffix=suffix, delete=False)
    try:
        attachment.file.open("rb")
        try:
            for block in attachment.file.chunks():
                handle.write(block)
        finally:
            attachment.file.close()
        handle.flush()
        return handle.name
    except Exception:
        handle.close()
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise
    finally:
        if not handle.closed:
            handle.close()


def _transcribe_pdf_page(page, attachment: PwanimateAttachment, page_number: int) -> tuple[str, str, str]:
    """Use the image-capable route for one scanned or image-heavy PDF page."""
    from django.conf import settings
    import fitz

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    page_bytes = pixmap.tobytes("png")
    page_image = AttachmentData(
        id=f"{attachment.id}-page-{page_number}",
        name=f"{attachment.file_name} page {page_number}",
        mime_type="image/png",
        attachment_type="image",
        data_bytes=page_bytes,
    )
    model = getattr(settings, "PWANIMATE_VISION_MODEL", "gemini-3.6-flash")
    result = AIGateway().generate(LLMRequest(
        task="attachment_vision_extraction",
        messages=[ChatMessage(
            role="user",
            content=(
                f"Transcribe the meaningful text on page {page_number} faithfully. "
                "Preserve equations, labels, table structure, and reading order. "
                "Briefly describe any diagram or chart that contains useful information. "
                "Do not guess text that is unreadable; say when a region is unclear."
            ),
            attachments=[page_image],
        )],
        provider="gemini",
        model=model,
        temperature=0.1,
        max_tokens=1600,
        attachments=[page_image],
        metadata={"required_capability": "image"},
    ))
    return result.content.strip(), result.provider, result.model


@shared_task(name="pwanimate.tasks.attachments.process_pwanimate_attachment")
def process_pwanimate_attachment(attachment_id: str) -> Dict[str, Any]:
    """Extract, OCR when needed, chunk, and persist a private chat upload."""
    attachment = PwanimateAttachment.objects.filter(id=attachment_id).first()
    if attachment is None:
        return {"status": "missing", "attachment_id": str(attachment_id)}
    if attachment.attachment_type != "document":
        attachment.processing_status = "not_required"
        attachment.save(update_fields=["processing_status"])
        return {"status": "not_required", "attachment_id": str(attachment.id)}
    if (
        attachment.processing_status == "ready"
        and not attachment.processing_error
        and attachment.chunks.exists()
    ):
        return {
            "status": "ready",
            "attachment_id": str(attachment.id),
            "chunk_count": attachment.chunks.count(),
        }

    attachment.processing_status = "processing"
    attachment.processing_error = ""
    attachment.save(update_fields=["processing_status", "processing_error"])
    temp_path = None
    try:
        temp_path = _copy_attachment_to_temp(attachment)
        try:
            extracted = extract_document(
                temp_path,
                filename=attachment.file_name,
                mime_type=attachment.mime_type,
            )
        except EmptyDocumentError:
            if attachment.extension != ".pdf":
                raise
            import fitz
            with fitz.open(temp_path) as pdf:
                extracted = ExtractedDocument(
                    source_filename=attachment.file_name,
                    format="pdf",
                    metadata={"total_pages": len(pdf), "parsed_pages": len(pdf), "element_count": 0},
                )

        warnings: List[str] = []
        if attachment.extension == ".pdf":
            import fitz
            max_vision_pages = max(0, int(getattr(settings, "PWANIMATE_ATTACHMENT_VISION_MAX_PAGES", 20)))
            existing_text_by_page = {}
            for element in extracted.elements:
                page_no = element.location.page_number
                if page_no:
                    existing_text_by_page[page_no] = existing_text_by_page.get(page_no, 0) + len(element.text.strip())

            vision_count = 0
            with fitz.open(temp_path) as pdf:
                total_pages = len(pdf)
                extracted.metadata["total_pages"] = total_pages
                for page_index, page in enumerate(pdf):
                    page_number = page_index + 1
                    text_chars = existing_text_by_page.get(page_number, 0)
                    has_images = bool(page.get_images(full=True))
                    has_visual_content = has_images or bool(page.get_drawings())
                    if text_chars >= 80 and not has_images and not has_visual_content:
                        continue
                    if text_chars < 80 and not has_visual_content:
                        continue
                    if vision_count >= max_vision_pages:
                        warnings.append(f"Visual extraction limit reached after {max_vision_pages} pages")
                        break
                    vision_count += 1
                    try:
                        text, provider, model = _transcribe_pdf_page(page, attachment, page_number)
                        if text:
                            extracted.elements.append(ExtractedElement(
                                element_type=ElementType.PARAGRAPH,
                                text=text,
                                location=LocationMetadata(page_number=page_number),
                                metadata={
                                    "extraction_method": "vision",
                                    "vision_provider": provider,
                                    "vision_model": model,
                                },
                            ))
                    except Exception as exc:
                        logger.warning(
                            "Vision extraction failed for attachment %s page %s: %s",
                            attachment.id,
                            page_number,
                            exc,
                        )
                        warnings.append(f"Page {page_number} could not be visually processed")

        chunks = chunk_document(extracted)
        if not chunks:
            raise ValueError("No readable text could be extracted from this file.")

        with transaction.atomic():
            PwanimateAttachmentChunk.objects.filter(attachment=attachment).delete()
            PwanimateAttachmentChunk.objects.bulk_create([
                PwanimateAttachmentChunk(
                    attachment=attachment,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    page_number=chunk.page_number,
                    page_end=chunk.page_end,
                    chunk_type=chunk.chunk_type,
                    metadata=chunk.metadata,
                )
                for chunk in chunks
            ])
            attachment.processing_status = "ready"
            attachment.processing_error = "; ".join(warnings)[:2000]
            attachment.processed_at = timezone.now()
            attachment.save(update_fields=["processing_status", "processing_error", "processed_at"])

        return {
            "status": "ready",
            "attachment_id": str(attachment.id),
            "chunk_count": len(chunks),
            "vision_pages": vision_count if attachment.extension == ".pdf" else 0,
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception("Attachment processing failed for %s", attachment.id)
        attachment.processing_status = "failed"
        attachment.processing_error = str(exc)[:2000]
        attachment.processed_at = timezone.now()
        attachment.save(update_fields=["processing_status", "processing_error", "processed_at"])
        return {"status": "failed", "attachment_id": str(attachment.id), "error": str(exc)[:500]}
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Could not delete temporary attachment copy: %s", temp_path)
