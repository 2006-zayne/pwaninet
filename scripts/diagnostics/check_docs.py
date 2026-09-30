import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()
from documents.documents.models import Document
from django.db.models import Count

print('Document status counts:')
for item in Document.objects.values('status').annotate(count=Count('id')):
    print(f"  {item['status']}: {item['count']}")

print('\nUpdating stuck processing documents to ready status...')
processing_docs = Document.objects.filter(status='processing', visibility='public')
for doc in processing_docs:
    doc.status = 'ready'
    doc.save(update_fields=['status'])
    print(f"  Updated ID {doc.id}: {doc.title[:30]}... to ready")

print('\nUpdating stuck draft documents to ready status...')
draft_docs = Document.objects.filter(status='draft', visibility='public')
for doc in draft_docs:
    doc.status = 'ready'
    doc.save(update_fields=['status'])
    print(f"  Updated ID {doc.id}: {doc.title[:30]}... to ready")

print('\nUpdating private processing documents to public and ready...')
private_processing_docs = Document.objects.filter(status='processing', visibility='private')
for doc in private_processing_docs:
    doc.status = 'ready'
    doc.visibility = 'public'
    doc.save(update_fields=['status', 'visibility'])
    print(f"  Updated ID {doc.id}: {doc.title[:30]}... to ready and public")

print('\nUpdated document status counts:')
for item in Document.objects.values('status').annotate(count=Count('id')):
    print(f"  {item['status']}: {item['count']}")

print('\nUpdated visibility counts:')
for item in Document.objects.values('visibility').annotate(count=Count('id')):
    print(f"  {item['visibility']}: {item['count']}")


