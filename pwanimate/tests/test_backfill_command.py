"""
Unit tests for the Pwanimate backfill_pwanimate_chunks management command,
idempotency, embedding recovery, state transitions, and failure isolation.
"""

from io import StringIO
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth import get_user_model

from documents.models import Document, DocumentVersion, DocumentFile, Category
from pwanimate.models import DocumentChunk
from pwanimate.ai.embeddings.mock import MockEmbeddingProvider
from pwanimate.tasks.embeddings import embed_document_version
from pwanimate.tasks.ingestion import ingest_document_version

User = get_user_model()


class BackfillCommandTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="backfill_tester",
            email="backfill@example.com",
            password="Password123!",
        )
        self.category = Category.objects.create(
            code="test_cat",
            name="Test Category",
            is_active=True,
        )

        # Document 1: 0 chunks (eligible for backfill)
        self.doc1 = Document.objects.create(
            title="Introduction to Algorithms",
            slug="intro-algorithms",
            category=self.category,
            uploaded_by=self.user,
            status="ready",
        )
        self.doc1_v1 = DocumentVersion.objects.create(
            document=self.doc1,
            version_number=1,
            created_by=self.user,
            is_latest=True,
        )
        self.file1 = DocumentFile.objects.create(
            document_version=self.doc1_v1,
            original_filename="intro_algorithms.pdf",
            extension="pdf",
            mime_type="application/pdf",
            storage_path="documents/intro_algorithms.pdf",
            storage_provider="local",
            processing_status="ready",
            processing_error="",
            size_bytes=1024,
            uploaded_by=self.user,
        )

        # Document 2: Has healthy completed chunks (eligible for skip)
        self.doc2 = Document.objects.create(
            title="Operating Systems",
            slug="operating-systems",
            category=self.category,
            uploaded_by=self.user,
            status="ready",
        )
        self.doc2_v1 = DocumentVersion.objects.create(
            document=self.doc2,
            version_number=1,
            created_by=self.user,
            is_latest=True,
        )
        self.file2 = DocumentFile.objects.create(
            document_version=self.doc2_v1,
            original_filename="os_notes.pdf",
            extension="pdf",
            mime_type="application/pdf",
            storage_path="documents/os_notes.pdf",
            storage_provider="local",
            processing_status="ready",
            processing_error="",
            size_bytes=2048,
            uploaded_by=self.user,
        )
        self.chunk_healthy = DocumentChunk.objects.create(
            document=self.doc2,
            document_version=self.doc2_v1,
            chunk_index=0,
            content="Virtual memory and page tables manage address spaces.",
            content_hash="hash_healthy_0",
            chunk_type="paragraph",
            page_number=1,
            page_end=1,
            section_heading="Memory Management",
            metadata={"source_format": "pdf"},
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=[0.05] * 768,
        )

        # Document 3: Has pending / failed chunks (eligible for embedding recovery)
        self.doc3 = Document.objects.create(
            title="Database Systems",
            slug="database-systems",
            category=self.category,
            uploaded_by=self.user,
            status="ready",
        )
        self.doc3_v1 = DocumentVersion.objects.create(
            document=self.doc3,
            version_number=1,
            created_by=self.user,
            is_latest=True,
        )
        self.file3 = DocumentFile.objects.create(
            document_version=self.doc3_v1,
            original_filename="db_notes.pdf",
            extension="pdf",
            mime_type="application/pdf",
            storage_path="documents/db_notes.pdf",
            storage_provider="local",
            processing_status="ready",
            processing_error="",
            size_bytes=4096,
            uploaded_by=self.user,
        )
        self.chunk_pending = DocumentChunk.objects.create(
            document=self.doc3,
            document_version=self.doc3_v1,
            chunk_index=0,
            content="ACID properties guarantee transactional reliability.",
            content_hash="hash_pending_0",
            chunk_type="paragraph",
            page_number=5,
            page_end=5,
            section_heading="Transactions",
            metadata={"source_format": "pdf"},
            is_active=False,
            embedding_status="pending",
            embedding_model="",
            embedding=None,
        )
        self.chunk_failed = DocumentChunk.objects.create(
            document=self.doc3,
            document_version=self.doc3_v1,
            chunk_index=1,
            content="Two-phase locking prevents concurrency anomalies.",
            content_hash="hash_failed_1",
            chunk_type="paragraph",
            page_number=6,
            page_end=6,
            section_heading="Concurrency",
            metadata={"source_format": "pdf"},
            is_active=False,
            embedding_status="failed",
            embedding_model="",
            embedding=None,
        )

        # Document 4: Has no attached file (invalid/skip)
        self.doc4 = Document.objects.create(
            title="Orphan Document",
            slug="orphan-document",
            category=self.category,
            uploaded_by=self.user,
            status="ready",
        )
        self.doc4_v1 = DocumentVersion.objects.create(
            document=self.doc4,
            version_number=1,
            created_by=self.user,
            is_latest=True,
        )

    @patch("pwanimate.tasks.ingestion.ingest_document_version.delay")
    def test_backfill_discovery_0_chunks_dispatched(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", stdout=out)
        output = out.getvalue()

        # Doc 1 (0 chunks, valid file) must be dispatched
        mock_delay.assert_any_call(self.doc1_v1.id, force=False)
        self.assertEqual(mock_delay.call_count, 1)

        self.assertIn("Versions discovered: 4", output)
        self.assertIn("Versions dispatched:  1", output)
        self.assertIn("Skipped healthy:      2", output)  # Doc 2 and Doc 3 have chunks
        self.assertIn("Skipped invalid:      1", output)  # Doc 4 has no file

    @patch("pwanimate.tasks.ingestion.ingest_document_version.delay")
    def test_backfill_dry_run_no_writes_no_dispatch(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", "--dry-run", stdout=out)
        output = out.getvalue()

        # Zero tasks dispatched in dry run
        mock_delay.assert_not_called()

        self.assertIn("DRY RUN", output)
        self.assertIn("Found 1 eligible document versions.", output)
        self.assertIn("Introduction to Algorithms", output)
        self.assertIn("Eligible to dispatch: 1", output)

    @patch("pwanimate.tasks.ingestion.ingest_document_version.delay")
    def test_backfill_filtering_document_id(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", f"--document-id={self.doc1.id}", stdout=out)

        mock_delay.assert_called_once_with(self.doc1_v1.id, force=False)

        # Filtering to Doc 2 (healthy) should dispatch nothing
        mock_delay.reset_mock()
        call_command("backfill_pwanimate_chunks", f"--document-id={self.doc2.id}", stdout=out)
        mock_delay.assert_not_called()

    @patch("pwanimate.tasks.ingestion.ingest_document_version.delay")
    def test_backfill_filtering_version_id(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", f"--version-id={self.doc1_v1.id}", stdout=out)
        mock_delay.assert_called_once_with(self.doc1_v1.id, force=False)

    @patch("pwanimate.tasks.ingestion.ingest_document_version.delay")
    def test_backfill_force_flag_reingests_existing(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", f"--document-id={self.doc2.id}", "--force", stdout=out)
        # Even though Doc 2 has chunks, --force dispatches it with force=True
        mock_delay.assert_called_once_with(self.doc2_v1.id, force=True)

    @patch("pwanimate.tasks.embeddings.embed_document_version.delay")
    def test_retry_pending_embeddings_dispatched(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", "--retry-pending", stdout=out)
        output = out.getvalue()

        # Only Doc 3 has pending/failed chunks
        mock_delay.assert_called_once_with(version_id=self.doc3_v1.id)
        self.assertIn("Pending chunks:       1", output)
        self.assertIn("Failed chunks:        1", output)
        self.assertIn("Versions dispatched:  1", output)

    @patch("pwanimate.tasks.embeddings.embed_document_version.delay")
    def test_retry_pending_embeddings_dry_run(self, mock_delay):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", "--retry-pending", "--dry-run", stdout=out)
        output = out.getvalue()

        mock_delay.assert_not_called()
        self.assertIn("DRY RUN: No embedding tasks will be dispatched.", output)
        self.assertIn("would dispatch embed_document_version", output)
        self.assertIn("Versions to dispatch: 1", output)

    def test_report_mode_read_only(self):
        out = StringIO()
        call_command("backfill_pwanimate_chunks", "--report", stdout=out)
        output = out.getvalue()

        self.assertIn("=== Pwanimate Document Ingestion & Chunk Audit Report ===", output)
        self.assertIn(f"Document {self.doc1.id}", output)
        self.assertIn("[NOT INGESTED]", output)
        self.assertIn(f"Document {self.doc2.id}", output)
        self.assertIn("[READY]", output)
        self.assertIn(f"Document {self.doc3.id}", output)
        self.assertIn("[EMBEDDING INCOMPLETE]", output)
        self.assertIn(f"Document {self.doc4.id}", output)
        self.assertIn("[NO FILE]", output)
        self.assertIn("Report Summary", output)
        self.assertIn("Total Versions Inspected: 4", output)


class IngestionIdempotencyAndEmbeddingRecoveryTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recovery_tester",
            email="recovery@example.com",
            password="Password123!",
        )
        self.category = Category.objects.create(
            code="cs_courses",
            name="Computer Science",
            is_active=True,
        )
        self.doc = Document.objects.create(
            title="Distributed Systems In Practice",
            slug="distributed-systems-practice",
            category=self.category,
            uploaded_by=self.user,
            status="ready",
        )
        self.version = DocumentVersion.objects.create(
            document=self.doc,
            version_number=1,
            created_by=self.user,
            is_latest=True,
        )
        self.file = DocumentFile.objects.create(
            document_version=self.version,
            original_filename="recovery_notes.pdf",
            extension="pdf",
            mime_type="application/pdf",
            storage_path="documents/recovery_notes.pdf",
            storage_provider="local",
            processing_status="ready",
            processing_error="",
            size_bytes=1024,
            uploaded_by=self.user,
        )

    def test_idempotency_prevents_duplicate_chunks(self):
        # Create chunk 0
        c1 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=0,
            content="Chunk zero content",
            content_hash="hash_0",
            chunk_type="paragraph",
            section_heading="Intro",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-model",
            embedding=[0.1] * 768,
        )
        self.assertEqual(self.version.chunks.count(), 1)

        # Calling ingest_document_version without force must return already_ingested
        result = ingest_document_version(self.version.id, force=False)
        self.assertEqual(result["status"], "already_ingested")
        self.assertEqual(self.version.chunks.count(), 1)

    @patch("pwanimate.tasks.embeddings.get_embedding_provider")
    def test_embedding_recovery_resumes_pending_and_preserves_completed(self, mock_get_provider):
        # Mock provider returning 768-dim vectors
        mock_provider = MockEmbeddingProvider(dimensions=768)
        mock_get_provider.return_value = mock_provider

        # Chunk 0 is already completed
        chunk0 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=0,
            content="Already completed chunk",
            content_hash="h0",
            chunk_type="paragraph",
            section_heading="H1",
            is_active=True,
            embedding_status="completed",
            embedding_model=mock_provider.get_model_name(),
            embedding=[0.2] * 768,
        )

        # Chunk 1 is pending
        chunk1 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=1,
            content="Pending chunk waiting for recovery",
            content_hash="h1",
            chunk_type="paragraph",
            section_heading="H2",
            is_active=False,
            embedding_status="pending",
            embedding_model="",
            embedding=None,
        )

        # Chunk 2 was failed
        chunk2 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=2,
            content="Failed chunk waiting for retry",
            content_hash="h2",
            chunk_type="paragraph",
            section_heading="H3",
            is_active=False,
            embedding_status="failed",
            embedding_model="",
            embedding=None,
        )

        # Run embedding task (which is what --retry-pending triggers)
        res = embed_document_version(self.version.id)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["embedded_count"], 2)  # Only chunk 1 and 2

        # Verify chunk 0 was NOT touched
        chunk0.refresh_from_db()
        self.assertEqual(chunk0.embedding_status, "completed")
        self.assertEqual(chunk0.embedding[0], 0.2)

        # Verify chunk 1 and 2 transitioned to completed and is_active=True
        chunk1.refresh_from_db()
        self.assertEqual(chunk1.embedding_status, "completed")
        self.assertTrue(chunk1.is_active)
        self.assertEqual(len(chunk1.embedding), 768)

        chunk2.refresh_from_db()
        self.assertEqual(chunk2.embedding_status, "completed")
        self.assertTrue(chunk2.is_active)
        self.assertEqual(len(chunk2.embedding), 768)

    @patch("pwanimate.tasks.embeddings.get_embedding_provider")
    def test_state_transitions_and_dimension_validation(self, mock_get_provider):
        # Provider returns malformed vector (dimension 512 instead of 768)
        mock_provider = MagicMock()
        mock_provider.is_configured.return_value = True
        mock_provider.get_model_name.return_value = "faulty-provider"
        mock_provider.get_dimensions.return_value = 768
        mock_provider.embed_texts.return_value = [[0.1] * 512]  # Wrong dim!
        mock_get_provider.return_value = mock_provider

        chunk = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=0,
            content="Content for faulty vector",
            content_hash="hfaulty",
            chunk_type="paragraph",
            section_heading="H1",
            is_active=False,
            embedding_status="pending",
            embedding_model="",
            embedding=None,
        )

        embed_document_version(self.version.id)

        chunk.refresh_from_db()
        # Invalid dimension must remain is_active=False and embedding_status='failed'
        self.assertFalse(chunk.is_active)
        self.assertEqual(chunk.embedding_status, "failed")
        self.assertIn("Vector dimension mismatch", chunk.metadata.get("last_embedding_error", ""))

    @patch("pwanimate.tasks.embeddings.get_embedding_provider")
    def test_embedding_failure_isolation_preserves_earlier_batches(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.is_configured.return_value = True
        mock_provider.get_model_name.return_value = "batch-provider"
        mock_provider.get_dimensions.return_value = 768

        # Simulate batch 1 succeeding, batch 2 raising an exception
        call_count = 0
        def fake_embed(texts, task_type="RETRIEVAL_DOCUMENT"):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [[0.1] * 768 for _ in texts]
            raise RuntimeError("API Rate limit or timeout on batch 2")

        mock_provider.embed_texts.side_effect = fake_embed
        mock_get_provider.return_value = mock_provider

        # Create 2 chunks, and configure batch size = 1 via override_settings
        chunk1 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=0,
            content="Batch 1 content",
            content_hash="b1",
            chunk_type="paragraph",
            section_heading="H1",
            is_active=False,
            embedding_status="pending",
        )
        chunk2 = DocumentChunk.objects.create(
            document=self.doc,
            document_version=self.version,
            chunk_index=1,
            content="Batch 2 content",
            content_hash="b2",
            chunk_type="paragraph",
            section_heading="H2",
            is_active=False,
            embedding_status="pending",
        )

        with patch("pwanimate.tasks.embeddings.settings") as mock_settings:
            mock_settings.PWANIMATE_EMBEDDING_BATCH_SIZE = 1
            # embed_document_version retries on exception; suppress Celery retry in unit test
            with patch.object(embed_document_version, "retry", side_effect=RuntimeError("Retry called")):
                with self.assertRaises(RuntimeError):
                    embed_document_version(self.version.id)

        # Verification: Chunk 1 was committed as completed + active
        chunk1.refresh_from_db()
        self.assertEqual(chunk1.embedding_status, "completed")
        self.assertTrue(chunk1.is_active)
        self.assertIsNotNone(chunk1.embedding)

        # Chunk 2 failed and recorded error in metadata
        chunk2.refresh_from_db()
        self.assertEqual(chunk2.embedding_status, "failed")
        self.assertFalse(chunk2.is_active)
        self.assertIn("API Rate limit", chunk2.metadata.get("last_embedding_error", ""))
