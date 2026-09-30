#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from documents.documents.models import Document
from django.db.models import Count

print('Document status counts:')
for item in Document.objects.values('status').annotate(count=Count('id')):
    print(f"  {item['status']}: {item['count']}")

print('\nLast 10 documents with their status:')
for doc in Document.objects.all().order_by('-id')[:10]:
    print(f"  ID {doc.id}: {doc.title[:30]}... - Status: {doc.status}, Visibility: {doc.visibility}")
