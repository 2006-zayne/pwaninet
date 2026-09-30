import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from documents.models import Document
from documents.selectors.document_selectors import DocumentSelector

# Create a mock document in DB? Wait, DB is postgres and it's offline!
