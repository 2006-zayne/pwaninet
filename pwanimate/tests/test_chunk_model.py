import hashlib
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from documents.models import Document, DocumentVersion, Category
from pwanimate.models import DocumentChunk
from pwanimate.ingestion.types import (
    ExtractedElement,
    LocationMetadata,
    ElementType,
)

User = get_user_model()


class DocumentChunkModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='lecturer1',
            email='lecturer1@example.com',
            password='Password123!'
        )
        self.category = Category.objects.create(
            code='lecture_notes',
            name='Lecture Notes',
            is_active=True
        )
        self.doc1 = Document.objects.create(
            title="Operating Systems CSC221",
            slug="operating-systems-csc221",
            category=self.category,
            uploaded_by=self.user,
            status='ready'
        )
        self.doc1_v1 = DocumentVersion.objects.create(
            document=self.doc1,
            version_number=1,
            created_by=self.user,
            is_latest=False
        )
        self.doc1_v2 = DocumentVersion.objects.create(
            document=self.doc1,
            version_number=2,
            created_by=self.user,
            is_latest=True
        )

    def test_create_valid_chunk(self):
        content = "Processes and threads are fundamental abstractions in modern operating systems."
        chunk = DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=0,
            content=content,
            chunk_type='paragraph',
            page_number=1,
            section_heading="Process Management",
            metadata={"bbox": [50.0, 72.0, 500.0, 120.0]}
        )

        self.assertIsNotNone(chunk.id)
        # Verify auto-filled document FK
        self.assertEqual(chunk.document, self.doc1)
        # Verify deterministic hash auto-calculation
        expected_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        self.assertEqual(chunk.content_hash, expected_hash)
        # Verify lifecycle state default is inactive until ingestion finishes
        self.assertFalse(chunk.is_active)
        self.assertEqual(chunk.embedding_status, 'pending')
        self.assertEqual(chunk.char_count, len(content))

        # Test activation/deactivation helpers
        chunk.activate()
        self.assertTrue(chunk.is_active)
        chunk.deactivate()
        self.assertFalse(chunk.is_active)

    def test_version_isolation(self):
        # Version 1 chunks
        c_v1_0 = DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=0,
            content="Version 1 introductory section.",
            chunk_type='heading',
            is_active=False
        )
        c_v1_1 = DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=1,
            content="Version 1 details.",
            chunk_type='paragraph',
            is_active=False
        )

        # Version 2 chunks (re-chunked with newer lecture material)
        c_v2_0 = DocumentChunk.objects.create(
            document_version=self.doc1_v2,
            chunk_index=0,
            content="Version 2 revised introductory section.",
            chunk_type='heading',
            is_active=True
        )
        c_v2_1 = DocumentChunk.objects.create(
            document_version=self.doc1_v2,
            chunk_index=1,
            content="Version 2 updated details.",
            chunk_type='paragraph',
            is_active=True
        )

        # Version queries are isolated
        self.assertEqual(self.doc1_v1.chunks.count(), 2)
        self.assertEqual(self.doc1_v2.chunks.count(), 2)

        # Active status queries filter accurately
        active_chunks = DocumentChunk.objects.filter(document=self.doc1, is_active=True)
        self.assertEqual(active_chunks.count(), 2)
        self.assertEqual(set(active_chunks.values_list('document_version_id', flat=True)), {self.doc1_v2.id})

    def test_deterministic_ordering(self):
        # Insert chunks out of order
        DocumentChunk.objects.create(document_version=self.doc1_v1, chunk_index=3, content="Chunk 3")
        DocumentChunk.objects.create(document_version=self.doc1_v1, chunk_index=0, content="Chunk 0")
        DocumentChunk.objects.create(document_version=self.doc1_v1, chunk_index=2, content="Chunk 2")
        DocumentChunk.objects.create(document_version=self.doc1_v1, chunk_index=1, content="Chunk 1")

        chunks = list(self.doc1_v1.chunks.all())
        indexes = [c.chunk_index for c in chunks]
        self.assertEqual(indexes, [0, 1, 2, 3])

    def test_uniqueness_constraint_on_version_and_chunk_index(self):
        DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=0,
            content="Initial chunk 0"
        )
        # Attempt duplicate (document_version, chunk_index)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DocumentChunk.objects.create(
                    document_version=self.doc1_v1,
                    chunk_index=0,
                    content="Duplicate chunk 0"
                )

    def test_negative_chunk_index_rejected(self):
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                chunk = DocumentChunk(
                    document_version=self.doc1_v1,
                    chunk_index=-1,
                    content="Negative index chunk"
                )
                chunk.save()

    def test_empty_content_rejected(self):
        with self.assertRaises((IntegrityError, ValidationError)):
            with transaction.atomic():
                chunk = DocumentChunk(
                    document_version=self.doc1_v1,
                    chunk_index=0,
                    content=""
                )
                chunk.save()

    def test_document_version_mismatch_raises_validation_error(self):
        # Create a second document
        doc2 = Document.objects.create(
            title="Database Systems CSC222",
            slug="database-systems-csc222",
            category=self.category,
            uploaded_by=self.user,
            status='ready'
        )
        # Mismatch: document is doc2, but document_version belongs to doc1
        chunk = DocumentChunk(
            document=doc2,
            document_version=self.doc1_v1,
            chunk_index=0,
            content="Mismatch chunk"
        )
        with self.assertRaises(ValidationError):
            chunk.clean()

    def test_cascade_deletion(self):
        chunk = DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=0,
            content="To be deleted"
        )
        chunk_id = chunk.id

        # Deleting document_version deletes chunk
        self.doc1_v1.delete()
        self.assertFalse(DocumentChunk.objects.filter(id=chunk_id).exists())

    def test_phase_2b_extracted_element_compatibility(self):
        # Validate that an ExtractedElement from Phase 2B seamlessly maps to DocumentChunk
        elem = ExtractedElement(
            element_type=ElementType.HEADING,
            text="CPU Scheduling Algorithms",
            location=LocationMetadata(
                page_number=5,
                slide_number=None,
                section_heading="Chapter 3: Scheduling",
                extra={"bbox": [40.0, 50.0, 400.0, 80.0]}
            ),
            metadata={"char_count": 26}
        )

        chunk = DocumentChunk.objects.create(
            document_version=self.doc1_v1,
            chunk_index=5,
            content=elem.text,
            chunk_type=elem.element_type.value,
            page_number=elem.location.page_number,
            slide_number=elem.location.slide_number,
            section_heading=elem.location.section_heading or '',
            metadata=elem.location.extra,
            is_active=False
        )

        self.assertEqual(chunk.content, "CPU Scheduling Algorithms")
        self.assertEqual(chunk.chunk_type, "heading")
        self.assertEqual(chunk.page_number, 5)
        self.assertEqual(chunk.section_heading, "Chapter 3: Scheduling")
        self.assertEqual(chunk.metadata["bbox"], [40.0, 50.0, 400.0, 80.0])
