#!/usr/bin/env python3
"""Reprocess all documents in the system.

Usage:
    # Queue all document processing tasks asynchronously via Celery (default):
    /home/zayne/projects/venv/bin/python scripts/reprocess_all_documents.py

    # Process all documents directly and synchronously in the script (without Celery worker):
    /home/zayne/projects/venv/bin/python scripts/reprocess_all_documents.py --direct
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pwaninet.settings")

# Try to find and use virtualenv if django not in current python
try:
    import django
except ModuleNotFoundError:
    venv_site = "/home/zayne/projects/venv/lib/python3.12/site-packages"
    if os.path.exists(venv_site):
        sys.path.insert(0, venv_site)
    import django

django.setup()

from documents.models import Document, DocumentFile
from documents.tasks.processing import (
    process_document,
    _generate_pdf_preview,
    _generate_pdf_thumbnail,
    _generate_docx_preview,
    _generate_docx_thumbnail,
    _generate_pptx_preview,
    _generate_pptx_thumbnail,
    _generate_text_preview,
)
from django.conf import settings
from pathlib import Path


def process_direct():
    thumbnail_dir = Path(settings.MEDIA_ROOT) / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    
    files = DocumentFile.objects.all()
    total = files.count()
    print(f"Processing {total} DocumentFiles directly...")
    
    success_count = 0
    fail_count = 0
    
    for idx, file in enumerate(files.iterator(), start=1):
        ext = (file.extension or "").lower()
        print(f"[{idx}/{total}] Processing file {file.id} ({ext})...", end=" ")
        try:
            if ext == "pdf":
                _generate_pdf_preview(file)
                _generate_pdf_thumbnail(file, thumbnail_dir)
            elif ext in ["docx", "doc"]:
                _generate_docx_preview(file)
                _generate_docx_thumbnail(file, thumbnail_dir)
            elif ext in ["pptx", "ppt"]:
                _generate_pptx_preview(file)
                _generate_pptx_thumbnail(file, thumbnail_dir)
            elif ext in ["txt", "md"]:
                _generate_text_preview(file)
            else:
                print(f"(unsupported ext {ext})")
                continue
            
            file.refresh_from_db()
            print(f"OK -> preview: {file.preview_path or 'none'}, thumb: {file.thumbnail_path or 'none'}")
            success_count += 1
        except Exception as e:
            print(f"FAILED: {e}")
            fail_count += 1
            
    print(f"\nDirect processing finished: {success_count} succeeded, {fail_count} failed.")


def process_celery():
    total = Document.objects.count()
    print(f"Found {total} documents. Enqueuing Celery tasks...")

    for idx, doc in enumerate(Document.objects.iterator(), start=1):
        process_document.delay(doc.id)
        print(f"[{idx}/{total}] Enqueued document ID {doc.id}")

    print("All tasks queued. Monitor Celery workers for progress.")


def main():
    parser = argparse.ArgumentParser(description="Reprocess all documents")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Run preview and thumbnail generation directly in this process without Celery"
    )
    args = parser.parse_args()

    if args.direct:
        process_direct()
    else:
        process_celery()


if __name__ == "__main__":
    main()

