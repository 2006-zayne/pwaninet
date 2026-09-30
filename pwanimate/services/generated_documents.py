"""Render Pwanimate answers as DOCX/PDF resources in a student's library."""

import hashlib
import io
import os
import re

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from documents.documents.models import Category, Document, DocumentFile, DocumentVersion
from documents.private_storage import get_private_resource_storage


MAX_RESOURCE_CHARACTERS = 180_000


def _clean_inline(text):
    text = re.sub(r"!?\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*|(?<!_)_([^_]+)_", lambda m: m.group(1) or m.group(2), text)
    return text.strip()


def _content_blocks(markdown):
    blocks = []
    paragraph = []
    in_code = False
    code_lines = []

    def flush_paragraph():
        if paragraph:
            blocks.append(("paragraph", _clean_inline(" ".join(paragraph))))
            paragraph.clear()

    for raw_line in (markdown or "").splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            flush_paragraph()
            if in_code:
                blocks.append(("code", "\n".join(code_lines)))
                code_lines.clear()
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            blocks.append(("heading", _clean_inline(heading.group(2)), len(heading.group(1))))
            continue
        bullet = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            blocks.append(("bullet", _clean_inline(bullet.group(1))))
            continue
        numbered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if numbered:
            flush_paragraph()
            blocks.append(("numbered", _clean_inline(line.strip())))
            continue
        if line.startswith("> "):
            flush_paragraph()
            blocks.append(("quote", _clean_inline(line[2:])))
            continue
        paragraph.append(line.strip())

    flush_paragraph()
    if in_code and code_lines:
        blocks.append(("code", "\n".join(code_lines)))
    return blocks


def _source_labels(message):
    labels = []
    for source in message.sources if isinstance(message.sources, list) else []:
        if isinstance(source, str):
            label = source.strip()
        elif isinstance(source, dict):
            label = source.get("title") or source.get("citation") or source.get("url") or ""
        else:
            label = ""
        if label and label not in labels:
            labels.append(label)
    for citation in message.citations if isinstance(message.citations, list) else []:
        label = citation if isinstance(citation, str) else ""
        if label and label not in labels:
            labels.append(label)
    return labels


def _render_docx(title, message):
    from docx import Document as WordDocument
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = WordDocument()
    section = doc.sections[0]
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.72)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(40, 48, 60)
    normal.paragraph_format.space_after = Pt(7)
    for style_name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)):
        style = doc.styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(25, 74, 137)

    brand = section.header.paragraphs[0]
    brand.text = "PWANINET  •  PWANIMATE"
    brand.style = "Caption"
    brand.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    title_paragraph = doc.add_paragraph(style="Title")
    title_paragraph.add_run(title)
    subtitle = doc.add_paragraph("Prepared with Pwanimate")
    subtitle.style = "Subtitle"

    for block in _content_blocks(message.content):
        kind, text, *extra = block
        if kind == "heading":
            doc.add_paragraph(text, style=f"Heading {min(extra[0], 3)}")
        elif kind == "bullet":
            doc.add_paragraph(text, style="List Bullet")
        elif kind == "numbered":
            doc.add_paragraph(text)
        elif kind == "quote":
            paragraph = doc.add_paragraph(text, style="Quote")
            paragraph.paragraph_format.left_indent = Inches(0.25)
        elif kind == "code":
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(text)
            run.font.name = "Consolas"
            run.font.size = Pt(9)
        elif text:
            doc.add_paragraph(text)

    sources = _source_labels(message)
    if sources:
        doc.add_heading("Sources", level=1)
        for source in sources:
            doc.add_paragraph(source, style="List Bullet")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("My Resources  •  ")
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _render_pdf(title, message):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        KeepTogether,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
    )
    from xml.sax.saxutils import escape

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=23 * mm,
        bottomMargin=22 * mm,
        title=title,
        author="Pwanimate",
    )

    font_path = getattr(settings, "PWANIMATE_DOCUMENT_FONT", "") or "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font_bold_path = getattr(settings, "PWANIMATE_DOCUMENT_BOLD_FONT", "") or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_name, bold_name = "Helvetica", "Helvetica-Bold"
    if os.path.exists(font_path) and os.path.exists(font_bold_path):
        try:
            pdfmetrics.registerFont(TTFont("PwanimateSans", font_path))
            pdfmetrics.registerFont(TTFont("PwanimateSans-Bold", font_bold_path))
            font_name, bold_name = "PwanimateSans", "PwanimateSans-Bold"
        except Exception:
            pass

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ResourceTitle", parent=styles["Title"], fontName=bold_name, fontSize=22, leading=28, textColor=colors.HexColor("#194a89"), alignment=TA_LEFT, spaceAfter=5))
    styles.add(ParagraphStyle(name="ResourceSubtitle", parent=styles["Normal"], fontName=font_name, fontSize=9, leading=13, textColor=colors.HexColor("#64748b"), spaceAfter=18))
    styles.add(ParagraphStyle(name="ResourceBody", parent=styles["BodyText"], fontName=font_name, fontSize=10, leading=15, textColor=colors.HexColor("#28303c"), spaceAfter=8, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="ResourceH1", parent=styles["Heading1"], fontName=bold_name, fontSize=16, leading=21, textColor=colors.HexColor("#194a89"), spaceBefore=12, spaceAfter=7, keepWithNext=True))
    styles.add(ParagraphStyle(name="ResourceH2", parent=styles["Heading2"], fontName=bold_name, fontSize=13, leading=17, textColor=colors.HexColor("#194a89"), spaceBefore=10, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name="ResourceH3", parent=styles["Heading3"], fontName=bold_name, fontSize=11, leading=15, textColor=colors.HexColor("#334155"), spaceBefore=8, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="ResourceQuote", parent=styles["ResourceBody"], leftIndent=14, borderColor=colors.HexColor("#cbd5e1"), borderWidth=1, borderPadding=7, backColor=colors.HexColor("#f8fafc")))
    styles.add(ParagraphStyle(name="ResourceCode", parent=styles["Code"], fontName="Courier", fontSize=8.5, leading=11, backColor=colors.HexColor("#f1f5f9"), borderPadding=6, spaceAfter=8))

    story = [Paragraph(escape(title), styles["ResourceTitle"]), Paragraph("Prepared with Pwanimate", styles["ResourceSubtitle"])]
    for block in _content_blocks(message.content):
        kind, text, *extra = block
        if kind == "heading":
            story.append(Paragraph(escape(text), styles[f"ResourceH{min(extra[0], 3)}"]))
        elif kind == "bullet":
            story.append(Paragraph(f"&#8226;&nbsp;&nbsp;{escape(text)}", styles["ResourceBody"]))
        elif kind == "numbered":
            story.append(Paragraph(escape(text), styles["ResourceBody"]))
        elif kind == "quote":
            story.append(Paragraph(escape(text), styles["ResourceQuote"]))
        elif kind == "code":
            story.append(Preformatted(text, styles["ResourceCode"], maxLineLength=95))
        elif text:
            story.append(Paragraph(escape(text), styles["ResourceBody"]))

    sources = _source_labels(message)
    if sources:
        story.append(Paragraph("Sources", styles["ResourceH1"]))
        for source in sources:
            story.append(KeepTogether([Paragraph(f"&#8226;&nbsp;&nbsp;{escape(source)}", styles["ResourceBody"])]))

    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(doc.leftMargin, 15 * mm, A4[0] - doc.rightMargin, 15 * mm)
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 10 * mm, "PwaniNet  •  My Resources")
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"{doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()


def _document_title(message):
    first_line = next((line.strip() for line in (message.content or "").splitlines() if line.strip()), "")
    title = re.sub(r"^#{1,6}\s*", "", first_line).strip(" *#")
    if not title:
        previous = message.conversation.messages.filter(role="user").order_by("-created_at").first()
        title = previous.content if previous else "Pwanimate Resource"
    title = re.sub(r"\s+", " ", title)
    return title[:180] or "Pwanimate Resource"


@transaction.atomic
def create_generated_resource(message, user, file_format):
    if file_format not in {"pdf", "docx"}:
        raise ValueError("Choose PDF or Word format.")
    content = (message.content or "").strip()
    if not content:
        raise ValueError("There is no response content to save.")
    if len(content) > MAX_RESOURCE_CHARACTERS:
        raise ValueError("This response is too long to export as one document.")

    existing = Document.objects.filter(
        uploaded_by=user,
        is_ai_generated=True,
        generated_from_message_id=message.id,
        generated_format=file_format,
    ).select_related("category").first()
    if existing:
        return existing, existing.latest_version.files.first(), False

    title = _document_title(message)
    category, _ = Category.objects.get_or_create(
        code="ai_generated",
        defaults={"name": "AI Generated Resource", "icon": "bi-stars"},
    )
    base_slug = slugify(title)[:500] or "pwanimate-resource"
    slug = base_slug
    suffix = 2
    while Document.objects.filter(slug=slug).exists():
        slug = f"{base_slug[:480]}-{suffix}"
        suffix += 1

    document = Document.objects.create(
        title=title,
        slug=slug,
        description="A private resource generated from a Pwanimate response.",
        category=category,
        uploaded_by=user,
        visibility="private",
        status="processing",
        is_available=True,
        is_ai_generated=True,
        generated_from_message_id=message.id,
        generated_format=file_format,
    )
    version = DocumentVersion.objects.create(
        document=document,
        version_number=1,
        change_notes="Generated by Pwanimate",
        created_by=user,
        is_latest=True,
    )

    data = _render_pdf(title, message) if file_format == "pdf" else _render_docx(title, message)
    extension = "pdf" if file_format == "pdf" else "docx"
    mime_type = "application/pdf" if extension == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = f"{slug[:160]}.{extension}"
    private_storage = get_private_resource_storage()
    resource_file = DocumentFile.objects.create(
        document_version=version,
        original_filename=filename,
        storage_path="",
        mime_type=mime_type,
        extension=extension,
        size_bytes=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        storage_provider="r2" if private_storage.uses_s3 else "local",
        processing_status="pending",
        uploaded_by=user,
        storage_private=True,
    )
    resource_file.file.storage = private_storage
    resource_file.file.save(filename, ContentFile(data), save=False)
    resource_file.storage_path = resource_file.file.name
    resource_file.save(update_fields=["file", "storage_path"])

    def queue_processing():
        from documents.tasks.processing import process_document
        process_document.delay(document.id)

    transaction.on_commit(queue_processing)
    return document, resource_file, True
