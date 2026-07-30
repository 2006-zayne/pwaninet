from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from django.utils import timezone
import os
import hashlib
from pathlib import Path

from documents.documents.models import Document, DocumentFile, DocumentVersion


class Command(BaseCommand):
    help = 'Process pending documents (generate previews, extract metadata)'

    def handle(self, *args, **options):
        self.stdout.write('Processing pending documents...')
        
        # Get documents with processing status
        pending_files = DocumentFile.objects.filter(
            processing_status='pending'
        ).select_related('document_version__document')
        
        if not pending_files.exists():
            self.stdout.write('No pending documents to process')
            return
        
        for file_obj in pending_files:
            self.process_file(file_obj)
        
        self.stdout.write(self.style.SUCCESS(f'Processed {pending_files.count()} documents'))

    def process_file(self, file_obj):
        """Process a single document file."""
        try:
            self.stdout.write(f'Processing: {file_obj.original_filename}')
            
            # Update status to processing
            file_obj.processing_status = 'processing'
            file_obj.save()
            
            # Generate checksum
            if not file_obj.checksum:
                file_obj.checksum = self.generate_checksum(file_obj.file.path)
                file_obj.save()
            
            # Generate preview (for PDFs)
            if file_obj.mime_type == 'application/pdf':
                self.generate_pdf_preview(file_obj)
            
            # Extract metadata
            self.extract_metadata(file_obj)
            
            # Mark as ready
            file_obj.processing_status = 'ready'
            file_obj.processed_at = timezone.now()
            file_obj.save()
            
            # Update document status
            document = file_obj.document_version.document
            document.status = 'ready'
            document.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully processed: {file_obj.original_filename}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to process {file_obj.original_filename}: {str(e)}'))
            file_obj.processing_status = 'failed'
            file_obj.processing_error = str(e)
            file_obj.save()

    def generate_checksum(self, file_path):
        """Generate SHA-256 checksum for file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def generate_pdf_preview(self, file_obj):
        """Generate thumbnail and preview for PDF files."""
        try:
            from PIL import Image
            import fitz  # PyMuPDF
            
            # Create preview directory
            preview_dir = Path(settings.MEDIA_ROOT) / 'previews'
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            thumbnail_dir = Path(settings.MEDIA_ROOT) / 'thumbnails'
            thumbnail_dir.mkdir(parents=True, exist_ok=True)
            
            # Open PDF
            pdf_document = fitz.open(file_obj.file.path)
            
            # Generate thumbnail (first page)
            if pdf_document.page_count > 0:
                page = pdf_document[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Save thumbnail
                thumbnail_path = thumbnail_dir / f"{file_obj.id}_thumb.png"
                img.save(thumbnail_path, 'PNG')
                file_obj.thumbnail_path = f"thumbnails/{file_obj.id}_thumb.png"
                
                # Generate preview (first 3 pages)
                preview_images = []
                for i in range(min(3, pdf_document.page_count)):
                    page = pdf_document[i]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    preview_images.append(img)
                
                # Combine preview images into a single image
                if preview_images:
                    widths, heights = zip(*(i.size for i in preview_images))
                    total_width = max(widths)
                    total_height = sum(heights)
                    
                    combined = Image.new('RGB', (total_width, total_height))
                    y_offset = 0
                    for img in preview_images:
                        combined.paste(img, (0, y_offset))
                        y_offset += img.height
                    
                    preview_path = preview_dir / f"{file_obj.id}_preview.png"
                    combined.save(preview_path, 'PNG')
                    file_obj.preview_path = f"previews/{file_obj.id}_preview.png"
            
            pdf_document.close()
            file_obj.save()
            
        except ImportError:
            self.stdout.write(self.style.WARNING('PyMuPDF or PIL not installed. Skipping preview generation.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Preview generation failed: {str(e)}'))

    def extract_metadata(self, file_obj):
        """Extract metadata from document file."""
        try:
            # For PDFs, extract basic metadata
            if file_obj.mime_type == 'application/pdf':
                import fitz
                pdf_document = fitz.open(file_obj.file.path)
                metadata = pdf_document.metadata
                
                # Update document with extracted metadata if available
                document = file_obj.document_version.document
                
                if metadata.get('title') and not document.title:
                    document.title = metadata['title'][:500]
                    document.save()
                
                if metadata.get('author'):
                    # Could create DocumentAuthor entry here
                    pass
                
                pdf_document.close()
                
        except ImportError:
            self.stdout.write(self.style.WARNING('PyMuPDF not installed. Skipping metadata extraction.'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Metadata extraction failed: {str(e)}'))
