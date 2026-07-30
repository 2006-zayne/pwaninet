#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from documents.documents.models import DocumentFile

print('Regenerating previews for existing documents...')

# Supported file types for preview generation
supported_extensions = ['pdf', 'docx', 'doc', 'pptx', 'ppt', 'txt', 'md']

all_files = DocumentFile.objects.filter(extension__in=supported_extensions)
print(f'Total supported files found: {all_files.count()}')

files_without_previews = all_files.filter(preview_path__isnull=True) | all_files.filter(preview_path='')
print(f'Files without previews: {files_without_previews.count()}')

for file in files_without_previews:
    print(f"Generating preview for file {file.id} ({file.extension})...")
    try:
        from documents.tasks.processing import generate_preview
        generate_preview(file.id)
        print(f"  ✓ Preview generated for file {file.id}")
    except Exception as e:
        print(f"  ✗ Error generating preview for file {file.id}: {e}")

print(f'\nProcessed {files_without_previews.count()} files.')
print('Note: Previews are generated synchronously in this script.')

