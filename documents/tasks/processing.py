"""Celery tasks for document processing pipeline.

These tasks handle asynchronous processing of uploaded documents,
including thumbnail generation, preview creation, metadata extraction,
OCR text extraction, and search indexing. Each stage is independently retryable.

OCR Pipeline Architecture:
- Extension points are provided for future OCR implementation
- OCR text will be stored in DocumentSearchIndex.ocr_text
- OCR text will be indexed with weight D (lower priority)
- The pipeline supports multiple OCR engines (Tesseract, Google Vision, etc.)
"""

import logging
from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.utils import timezone

from ..documents.models import Document, DocumentFile, DocumentVersion
from ..services.storage_service import StorageService
from ..services.search_service import SearchService

logger = logging.getLogger(__name__)


# OCR Extension Points
# These functions provide clear extension points for future OCR implementation
# without requiring architectural changes

def extract_ocr_text(file: DocumentFile) -> str:
    """Extract text from document using OCR.
    
    This is an extension point for future OCR implementation.
    Currently returns empty string.
    
    Future implementations could use:
    - Tesseract OCR for PDFs and images
    - Google Vision API
    - AWS Textract
    - Azure Form Recognizer
    - pdfplumber for text extraction from PDFs
    
    Args:
        file: DocumentFile instance to extract text from
        
    Returns:
        Extracted text as string
    """
    # Extension point for OCR implementation
    # When implementing OCR, uncomment and modify the following:
    #
    # if file.extension == 'pdf':
    #     return _extract_text_from_pdf(file)
    # elif file.extension in ['jpg', 'jpeg', 'png', 'tiff']:
    #     return _extract_text_from_image(file)
    # elif file.extension == 'docx':
    #     return _extract_text_from_docx(file)
    #
    return ""


def _extract_text_from_pdf(file: DocumentFile) -> str:
    """Extract text from PDF file.
    
    Extension point for PDF text extraction.
    Could use pdfplumber, PyPDF2, or OCR for scanned PDFs.
    """
    # Future implementation
    return ""


def _extract_text_from_image(file: DocumentFile) -> str:
    """Extract text from image file using OCR.
    
    Extension point for image OCR.
    Could use Tesseract, Google Vision, etc.
    """
    # Future implementation
    return ""


def _extract_text_from_docx(file: DocumentFile) -> str:
    """Extract text from DOCX file.
    
    Extension point for DOCX text extraction.
    Could use python-docx.
    """
    # Future implementation
    return ""


def extract_ocr_text_for_document(document: Document) -> str:
    """Extract OCR text for all files in a document.
    
    This function coordinates OCR extraction across all files
    in the document's latest version.
    
    Args:
        document: Document instance
        
    Returns:
        Combined OCR text from all files
    """
    version = document.latest_version
    if not version:
        return ""
    
    all_text = []
    for file in version.files.all():
        text = extract_ocr_text(file)
        if text:
            all_text.append(text)
    
    return " ".join(all_text)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id: int):
    """Main task to process a document after upload.
    
    This task coordinates the entire processing pipeline:
    1. Generate thumbnails
    2. Generate previews
    3. Extract metadata
    4. Extract OCR text (extension point)
    5. Index for search
    6. Mark as ready
    """
    try:
        document = Document.objects.get(id=document_id)
        logger.info(f"Starting processing for document {document_id}")
        
        # Get latest version
        version = document.latest_version
        if not version:
            logger.error(f"No version found for document {document_id}")
            return
        
        # Process each file in the version
        for file in version.files.all():
            process_file.delay(file.id)
        
        # Wait for all files to be processed (simplified)
        # In production, use group/chord for parallel processing
        
        # Extract OCR text (extension point - currently no-op)
        ocr_text = extract_ocr_text_for_document(document)
        if ocr_text:
            logger.info(f"Extracted {len(ocr_text)} characters of OCR text for document {document_id}")
        
        # Index document for search
        search_service = SearchService()
        search_service.index_document(document)
        
        # Mark document as ready
        document.status = 'ready'
        document.save(update_fields=['status'])
        
        logger.info(f"Completed processing for document {document_id}")
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        document.status = 'draft'
        document.save(update_fields=['status'])
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_file(self, file_id: int):
    """Process a single document file.
    
    This task handles file-specific processing:
    1. Generate thumbnail
    2. Generate preview
    3. Extract file metadata
    """
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Starting processing for file {file_id}")
        
        file.processing_status = 'processing'
        file.save(update_fields=['processing_status'])
        
        # Generate thumbnail
        generate_thumbnail.delay(file_id)
        
        # Generate preview
        generate_preview.delay(file_id)
        
        # Extract metadata
        extract_metadata.delay(file_id)
        
        # Check for duplicates
        check_duplicate.delay(file_id)
        
        logger.info(f"Completed processing for file {file_id}")
        
    except DocumentFile.DoesNotExist:
        logger.error(f"File {file_id} not found")
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {e}")
        file.processing_status = 'failed'
        file.processing_error = str(e)
        file.save(update_fields=['processing_status', 'processing_error'])
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=2)
def generate_thumbnail(self, file_id: int):
    """Generate thumbnail for a document file."""
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Generating thumbnail for file {file_id}")
        
        # Only generate thumbnails for supported file types
        if file.extension not in ['pdf', 'pptx', 'ppt', 'docx', 'doc']:
            logger.info(f"Skipping thumbnail for {file.extension} file")
            return
        
        from pathlib import Path
        from django.conf import settings
        
        # Create thumbnails directory
        thumbnail_dir = Path(settings.MEDIA_ROOT) / 'thumbnails'
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate thumbnail based on file type
        if file.extension == 'pdf':
            _generate_pdf_thumbnail(file, thumbnail_dir)
        elif file.extension in ['docx', 'doc']:
            _generate_docx_thumbnail(file, thumbnail_dir)
        elif file.extension in ['pptx', 'ppt']:
            _generate_pptx_thumbnail(file, thumbnail_dir)
        else:
            logger.info(f"Thumbnail generation not supported for {file.extension} file")
            return
        
        logger.info(f"Generated thumbnail for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error generating thumbnail for file {file_id}: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=2)
def generate_preview(self, file_id: int):
    """Generate preview for a document file."""
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Generating preview for file {file_id}")
        
        # Generate preview based on file type
        if file.extension == 'pdf':
            _generate_pdf_preview(file)
        elif file.extension in ['docx', 'doc']:
            _generate_docx_preview(file)
        elif file.extension in ['pptx', 'ppt']:
            _generate_pptx_preview(file)
        elif file.extension in ['txt', 'md']:
            _generate_text_preview(file)
        else:
            logger.info(f"Preview generation not supported for {file.extension} file")
            file.processing_status = 'completed'
            file.save(update_fields=['processing_status'])
            return
        
        # Update processing status after successful preview generation
        file.processing_status = 'completed'
        file.save(update_fields=['processing_status'])
        
        logger.info(f"Generated preview for file {file_id}")
        
    except DocumentFile.DoesNotExist:
        logger.error(f"File {file_id} not found")
    except Exception as e:
        logger.error(f"Error generating preview for file {file_id}: {e}")
        # Update status to failed
        try:
            file = DocumentFile.objects.get(id=file_id)
            file.processing_status = 'failed'
            file.save(update_fields=['processing_status'])
        except:
            pass
        raise self.retry(exc=e, countdown=30)


def _generate_pdf_preview(file):
    """Generate preview for PDF files using PyMuPDF."""
    import fitz  # PyMuPDF
    from pathlib import Path
    from django.conf import settings
    
    preview_dir = Path(settings.MEDIA_ROOT) / 'previews'
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    if file.file and hasattr(file.file, 'path'):
        pdf_path = file.file.path
        doc = fitz.open(pdf_path)
        if doc.page_count > 0:
            # Store page count
            file.page_count = doc.page_count
            
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            preview_path = preview_dir / f"{file.id}_preview.jpg"
            pix.save(preview_path)
            doc.close()
            file.preview_path = f"previews/{file.id}_preview.jpg"
            file.save(update_fields=['preview_path', 'page_count'])
        else:
            doc.close()


def _generate_docx_preview(file):
    """Generate preview for DOCX files using python-docx."""
    try:
        from docx import Document
        from pathlib import Path
        from django.conf import settings
        
        preview_dir = Path(settings.MEDIA_ROOT) / 'previews'
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        if file.file and hasattr(file.file, 'path'):
            doc_path = file.file.path
            doc = Document(doc_path)
            
            # Create a simple text preview image with white background
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add title with dark text
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                title_font = ImageFont.load_default()
            
            draw.text((20, 20), "Document Preview", fill='#1F2937', font=title_font)
            
            # Add first few paragraphs
            try:
                text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                text_font = ImageFont.load_default()
            
            y_offset = 60
            for para in doc.paragraphs[:5]:
                text = para.text[:80] + "..." if len(para.text) > 80 else para.text
                draw.text((20, y_offset), text, fill='#374151', font=text_font)
                y_offset += 25
            
            preview_path = preview_dir / f"{file.id}_preview.jpg"
            img.save(preview_path)
            file.preview_path = f"previews/{file.id}_preview.jpg"
            file.save(update_fields=['preview_path'])
    except ImportError:
        logger.error("python-docx or PIL not installed")


def _generate_pptx_preview(file):
    """Generate preview for PPTX files using python-pptx."""
    try:
        from pptx import Presentation
        from pathlib import Path
        from django.conf import settings
        from PIL import Image, ImageDraw, ImageFont
        
        preview_dir = Path(settings.MEDIA_ROOT) / 'previews'
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        if file.file and hasattr(file.file, 'path'):
            ppt_path = file.file.path
            prs = Presentation(ppt_path)
            img = Image.new('RGB', (800, 600), color='#DC2626')
            draw = ImageDraw.Draw(img)
            
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                title_font = ImageFont.load_default()
            
            draw.text((20, 20), "Presentation Preview", fill='white', font=title_font)
            draw.text((20, 60), f"Slides: {len(prs.slides)}", fill='white', font=title_font)
            
            preview_path = preview_dir / f"{file.id}_preview.jpg"
            img.save(preview_path)
            file.preview_path = f"previews/{file.id}_preview.jpg"
            file.save(update_fields=['preview_path'])
    except ImportError:
        logger.error("python-pptx or PIL not installed")


def _generate_text_preview(file):
    """Generate preview for text files."""
    try:
        from pathlib import Path
        from django.conf import settings
        from PIL import Image, ImageDraw, ImageFont
        
        preview_dir = Path(settings.MEDIA_ROOT) / 'previews'
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        if file.file and hasattr(file.file, 'path'):
            text_path = file.file.path
            
            with open(text_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Create a simple text preview image
            img = Image.new('RGB', (800, 600), color='#059669')
            draw = ImageDraw.Draw(img)
            
            try:
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except:
                title_font = ImageFont.load_default()
            
            draw.text((20, 20), "Text File Preview", fill='white', font=title_font)
            
            try:
                text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
            except:
                text_font = ImageFont.load_default()
            
            y_offset = 60
            lines = content.split('\n')[:20]
            for line in lines:
                text = line[:80] + "..." if len(line) > 80 else line
                draw.text((20, y_offset), text, fill='white', font=text_font)
                y_offset += 25
            
            preview_path = preview_dir / f"{file.id}_preview.jpg"
            img.save(preview_path)
            file.preview_path = f"previews/{file.id}_preview.jpg"
            file.save(update_fields=['preview_path'])
    except Exception as e:
        logger.error(f"Error generating text preview: {e}")


def _generate_pdf_thumbnail(file, thumbnail_dir):
    """Generate thumbnail for PDF files using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        
        if file.file and hasattr(file.file, 'path'):
            pdf_path = file.file.path
            doc = fitz.open(pdf_path)
            if doc.page_count > 0:
                page = doc[0]
                # Create thumbnail with smaller dimensions
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))  # Lower resolution for thumbnail
                thumbnail_path = thumbnail_dir / f"{file.id}_thumbnail.jpg"
                pix.save(thumbnail_path)
                doc.close()
                file.thumbnail_path = f"thumbnails/{file.id}_thumbnail.jpg"
                file.save(update_fields=['thumbnail_path'])
            else:
                doc.close()
    except ImportError:
        logger.error("PyMuPDF not installed for PDF thumbnail generation")
        # Fallback: use preview as thumbnail
        if file.preview_path:
            file.thumbnail_path = file.preview_path
            file.save(update_fields=['thumbnail_path'])
    except Exception as e:
        logger.error(f"Error generating PDF thumbnail: {e}")


def _generate_docx_thumbnail(file, thumbnail_dir):
    """Generate thumbnail for DOCX files."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple thumbnail with document icon
        img = Image.new('RGB', (200, 150), color='#2563EB')
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            title_font = ImageFont.load_default()
        
        draw.text((20, 20), "DOCX", fill='white', font=title_font)
        
        thumbnail_path = thumbnail_dir / f"{file.id}_thumbnail.jpg"
        img.save(thumbnail_path)
        file.thumbnail_path = f"thumbnails/{file.id}_thumbnail.jpg"
        file.save(update_fields=['thumbnail_path'])
    except Exception as e:
        logger.error(f"Error generating DOCX thumbnail: {e}")
        # Fallback: use preview as thumbnail
        if file.preview_path:
            file.thumbnail_path = file.preview_path
            file.save(update_fields=['thumbnail_path'])


def _generate_pptx_thumbnail(file, thumbnail_dir):
    """Generate thumbnail for PPTX files."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple thumbnail with presentation icon
        img = Image.new('RGB', (200, 150), color='#DC2626')
        draw = ImageDraw.Draw(img)
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            title_font = ImageFont.load_default()
        
        draw.text((20, 20), "PPTX", fill='white', font=title_font)
        
        thumbnail_path = thumbnail_dir / f"{file.id}_thumbnail.jpg"
        img.save(thumbnail_path)
        file.thumbnail_path = f"thumbnails/{file.id}_thumbnail.jpg"
        file.save(update_fields=['thumbnail_path'])
    except Exception as e:
        logger.error(f"Error generating PPTX thumbnail: {e}")
        # Fallback: use preview as thumbnail
        if file.preview_path:
            file.thumbnail_path = file.preview_path
            file.save(update_fields=['thumbnail_path'])


@shared_task(bind=True, max_retries=2)
def extract_metadata(self, file_id: int):
    """Extract metadata from a document file."""
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Extracting metadata for file {file_id}")
        
        # This would use libraries like PyPDF2, python-docx, etc.
        # to extract author, title, creation date, etc.
        # For now, this is a placeholder
        
        logger.info(f"Extracted metadata for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error extracting metadata for file {file_id}: {e}")
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=1)
def check_duplicate(self, file_id: int):
    """Check for duplicate files based on checksum."""
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Checking duplicates for file {file_id}")
        
        from ..storage.models import FileChecksum
        duplicate_files = DocumentFile.objects.filter(
            checksum=file.checksum
        ).exclude(id=file.id)
        
        if duplicate_files.exists():
            logger.warning(f"Found {duplicate_files.count()} duplicates for file {file_id}")
            # Could trigger notification or mark document as potential duplicate
        
        logger.info(f"Checked duplicates for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error checking duplicates for file {file_id}: {e}")
        # Don't retry duplicate check - it's not critical


@shared_task(bind=True, max_retries=1)
def perform_ocr(self, file_id: int):
    """Perform OCR on a document file (future feature).
    
    This task will extract text from images/PDFs for search indexing.
    """
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Performing OCR for file {file_id}")
        
        # This would use libraries like Tesseract, pdf2image, etc.
        # For now, this is a placeholder for future implementation
        
        logger.info(f"Completed OCR for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error performing OCR for file {file_id}: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=1)
def virus_scan(self, file_id: int):
    """Scan a document file for viruses (future feature).
    
    This task will integrate with virus scanning services.
    """
    try:
        file = DocumentFile.objects.get(id=file_id)
        logger.info(f"Scanning file {file_id} for viruses")
        
        # This would integrate with ClamAV or similar
        # For now, this is a placeholder for future implementation
        
        logger.info(f"Completed virus scan for file {file_id}")
        
    except Exception as e:
        logger.error(f"Error scanning file {file_id} for viruses: {e}")
        # Don't retry virus scan - it's not critical


@shared_task
def update_search_index(document_id: int):
    """Update search index for a document."""
    try:
        document = Document.objects.get(id=document_id)
        search_service = SearchService()
        search_service.index_document(document)
        logger.info(f"Updated search index for document {document_id}")
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for search index update")


@shared_task
def remove_from_search_index(document_id: int):
    """Remove a document from the search index."""
    try:
        document = Document.objects.get(id=document_id)
        search_service = SearchService()
        search_service.remove_from_index(document)
        logger.info(f"Removed document {document_id} from search index")
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for search index removal")


@shared_task
def reindex_all_documents():
    """Reindex all documents (maintenance task)."""
    try:
        search_service = SearchService()
        documents = Document.objects.filter(status='ready')
        
        for document in documents:
            search_service.index_document(document)
        
        logger.info(f"Reindexed {documents.count()} documents")
        
    except Exception as e:
        logger.error(f"Error reindexing documents: {e}")


@shared_task
def update_document_analytics(document_id: int):
    """Update cached analytics for a document after engagement.
    
    This task recalculates engagement statistics asynchronously
    to avoid blocking user interactions.
    """
    try:
        from documents.engagement.models import DocumentAnalytics, DocumentView, DocumentDownload, DocumentBookmark, DocumentRating, DocumentShare
        from django.utils import timezone
        from datetime import timedelta
        
        document = Document.objects.get(id=document_id)
        logger.info(f"Updating analytics for document {document_id}")
        
        # Get or create analytics record
        analytics, created = DocumentAnalytics.objects.get_or_create(
            document=document
        )
        
        # Update engagement counts
        analytics.view_count = document.views.count()
        analytics.download_count = document.downloads.count()
        analytics.bookmark_count = document.bookmarks.count()
        analytics.share_count = document.shares.count()
        
        # Update rating statistics
        ratings = document.ratings.all()
        analytics.rating_count = ratings.count()
        analytics.positive_rating_count = ratings.filter(rating=1).count()
        analytics.negative_rating_count = ratings.filter(rating=-1).count()
        
        # Update rating percentages
        analytics.update_rating_percentages()
        
        # Calculate trending score (based on last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_views = document.views.filter(viewed_at__gte=seven_days_ago).count()
        recent_downloads = document.downloads.filter(downloaded_at__gte=seven_days_ago).count()
        recent_bookmarks = document.bookmarks.filter(created_at__gte=seven_days_ago).count()
        
        # Simple trending algorithm: weighted recent engagement
        analytics.trending_score = (
            recent_views * 1.0 +
            recent_downloads * 2.0 +
            recent_bookmarks * 3.0
        )
        
        # Calculate popularity score (long-term engagement)
        analytics.popularity_score = (
            analytics.view_count * 1.0 +
            analytics.download_count * 2.0 +
            analytics.bookmark_count * 3.0 +
            analytics.positive_rating_count * 5.0
        )
        
        # Update last activity timestamp
        all_activities = []
        if document.views.exists():
            all_activities.append(document.views.latest('viewed_at').viewed_at)
        if document.downloads.exists():
            all_activities.append(document.downloads.latest('downloaded_at').downloaded_at)
        if document.bookmarks.exists():
            all_activities.append(document.bookmarks.latest('created_at').created_at)
        if document.ratings.exists():
            all_activities.append(document.ratings.latest('created_at').created_at)
        if document.shares.exists():
            all_activities.append(document.shares.latest('shared_at').shared_at)
        
        if all_activities:
            analytics.last_activity = max(all_activities)
        
        analytics.save()
        
        logger.info(f"Updated analytics for document {document_id}")
        
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found for analytics update")
    except Exception as e:
        logger.error(f"Error updating analytics for document {document_id}: {e}")


@shared_task
def update_analytics_for_all_documents():
    """Update analytics for all documents (maintenance task)."""
    try:
        documents = Document.objects.filter(status='ready')
        
        for document in documents:
            update_document_analytics.delay(document.id)
        
        logger.info(f"Scheduled analytics update for {documents.count()} documents")
        
    except Exception as e:
        logger.error(f"Error scheduling analytics updates: {e}")
