"""
Comprehensive unit and integration test suite for Pwanimate Phase 3:
Unified Retrieval Architecture.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

from documents.models import Document, DocumentVersion, Category
from documents.academic.models import (
    Faculty, School, Department, Programme, AcademicUnit,
    AcademicLevel, AcademicYear, Semester, ProgrammeUnit
)
from documents.documents.models import DocumentAcademicUnit
from posts.models import Post, HiddenPost, AuthorPreference
from groups.models import Group, Membership, MembershipStatus, PostVisibility
from pwanimate.models import DocumentChunk
from pwanimate.ai.embeddings.mock import MockEmbeddingProvider
from pwanimate.retrieval.types import (
    RetrievalRequest,
    RetrievalResult,
    RetrievalResponse,
    SourceType,
    RetrievalMode,
)
from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService
from pwanimate.retrieval.services.unified_retrieval import UnifiedRetrievalService
from pwanimate.retrieval.adapters.pwaninet_search import PwaniNetSearchAdapter

User = get_user_model()


class RetrievalTestCase(TestCase):
    def setUp(self):
        self.mock_provider = MockEmbeddingProvider(dimensions=768)
        self.doc_service = DocumentSemanticRetrievalService(embedding_provider=self.mock_provider)
        self.search_adapter = PwaniNetSearchAdapter()
        self.unified_service = UnifiedRetrievalService(
            document_service=self.doc_service,
            search_adapter=self.search_adapter,
        )

        # Users
        self.uploader = User.objects.create_user(
            username='uploader_user',
            email='uploader@pwaninet.local',
            first_name='Alice',
            last_name='Uploader'
        )
        self.student_cs = User.objects.create_user(
            username='cs_student',
            email='cs@pwaninet.local',
            first_name='Bob',
            last_name='Coder'
        )
        self.student_bio = User.objects.create_user(
            username='bio_student',
            email='bio@pwaninet.local',
            first_name='Charlie',
            last_name='Darwin'
        )
        self.president_user = User.objects.create_user(
            username='pres_user',
            email='pres@pwaninet.local',
            global_role='PRESIDENT'
        )
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@pwaninet.local',
            is_staff=True
        )

        # Academic structure
        self.faculty = Faculty.objects.create(name="Faculty of Science", code="FOS")
        self.school = School.objects.create(name="School of Pure and Applied Sciences", code="SPAS", faculty=self.faculty)
        self.dept = Department.objects.create(name="Computing and Information Technology", code="CIT", school=self.school)
        self.prog_cs = Programme.objects.create(name="BSc Computer Science", code="BSCS", department=self.dept, degree_type="Bachelor", duration_years=4)
        self.prog_bio = Programme.objects.create(name="BSc Biochemistry", code="BSBC", department=self.dept, degree_type="Bachelor", duration_years=4)

        self.student_cs.programme = self.prog_cs
        self.student_cs.save()

        self.student_bio.programme = self.prog_bio
        self.student_bio.save()

        self.unit_os = AcademicUnit.objects.create(name="Operating Systems", code="CSC211")
        self.acad_year = AcademicYear.objects.create(name="2025/2026", code="2025/2026", start_date="2025-09-01", end_date="2026-06-30")
        self.semester = Semester.objects.create(academic_year=self.acad_year, number=1, start_date="2025-09-01", end_date="2026-01-31")
        self.level_2 = AcademicLevel.objects.create(level=2, name="Year 2")

        self.prog_unit = ProgrammeUnit.objects.create(
            programme=self.prog_cs,
            academic_unit=self.unit_os,
            academic_level=self.level_2,
            semester=self.semester
        )

        # Document category
        self.category = Category.objects.create(name="Lecture Notes", code="lecture_notes")

        # 1. Public Ready Document
        self.doc_public = Document.objects.create(
            title="Operating Systems Concepts",
            slug="operating-systems-concepts",
            category=self.category,
            uploaded_by=self.uploader,
            status='ready',
            is_available=True,
            visibility='public'
        )
        self.v_public = DocumentVersion.objects.create(
            document=self.doc_public,
            version_number=1,
            created_by=self.uploader,
            is_latest=True
        )
        self.chunk_public_1 = DocumentChunk.objects.create(
            document=self.doc_public,
            document_version=self.v_public,
            chunk_index=0,
            content="Processes and threads execution in modern operating systems kernel.",
            chunk_type="paragraph",
            page_number=5,
            section_heading="Process Management",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Processes and threads execution in modern operating systems kernel.")
        )
        self.chunk_public_2 = DocumentChunk.objects.create(
            document=self.doc_public,
            document_version=self.v_public,
            chunk_index=1,
            content="Virtual memory paging and segmentation mechanisms for RAM allocation.",
            chunk_type="paragraph",
            page_number=12,
            section_heading="Memory Management",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Virtual memory paging and segmentation mechanisms for RAM allocation.")
        )

        # 2. Private Document (Uploaded by Alice)
        self.doc_private = Document.objects.create(
            title="Alice Private Research Draft",
            slug="alice-private-research-draft",
            category=self.category,
            uploaded_by=self.uploader,
            status='ready',
            is_available=True,
            visibility='private'
        )
        self.v_private = DocumentVersion.objects.create(
            document=self.doc_private,
            version_number=1,
            created_by=self.uploader,
            is_latest=True
        )
        self.chunk_private = DocumentChunk.objects.create(
            document=self.doc_private,
            document_version=self.v_private,
            chunk_index=0,
            content="Confidential quantum computing research findings and proprietary algorithms.",
            chunk_type="paragraph",
            page_number=1,
            section_heading="Confidential Quantum Draft",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Confidential quantum computing research findings and proprietary algorithms.")
        )

        # 3. Restricted Document (Restricted to Computer Science via ProgrammeUnit)
        self.doc_restricted = Document.objects.create(
            title="Advanced Algorithms Exam Preparation",
            slug="advanced-algorithms-exam-preparation",
            category=self.category,
            uploaded_by=self.uploader,
            status='ready',
            is_available=True,
            visibility='restricted'
        )
        DocumentAcademicUnit.objects.create(
            document=self.doc_restricted,
            academic_unit=self.unit_os,
            academic_level=self.level_2,
            semester=self.semester,
            academic_year=self.acad_year
        )
        self.v_restricted = DocumentVersion.objects.create(
            document=self.doc_restricted,
            version_number=1,
            created_by=self.uploader,
            is_latest=True
        )
        self.chunk_restricted = DocumentChunk.objects.create(
            document=self.doc_restricted,
            document_version=self.v_restricted,
            chunk_index=0,
            content="Dynamic programming and Bellman-Ford algorithm questions for CSC211.",
            chunk_type="slide",
            slide_number=4,
            section_heading="Exam Revision",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Dynamic programming and Bellman-Ford algorithm questions for CSC211.")
        )

        # 4. Unavailable Document (is_available=False)
        self.doc_unavailable = Document.objects.create(
            title="Unavailable Historical Archive",
            slug="unavailable-historical-archive",
            category=self.category,
            uploaded_by=self.uploader,
            status='ready',
            is_available=False,
            visibility='public'
        )
        self.v_unavailable = DocumentVersion.objects.create(
            document=self.doc_unavailable,
            version_number=1,
            created_by=self.uploader,
            is_latest=True
        )
        self.chunk_unavailable = DocumentChunk.objects.create(
            document=self.doc_unavailable,
            document_version=self.v_unavailable,
            chunk_index=0,
            content="Archived historical records that should not be retrieved.",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Archived historical records that should not be retrieved.")
        )

        # 5. Draft Document (status='draft')
        self.doc_draft = Document.objects.create(
            title="Draft Operating Systems Syllabus",
            slug="draft-operating-systems-syllabus",
            category=self.category,
            uploaded_by=self.uploader,
            status='draft',
            is_available=True,
            visibility='public'
        )
        self.v_draft = DocumentVersion.objects.create(
            document=self.doc_draft,
            version_number=1,
            created_by=self.uploader,
            is_latest=True
        )
        self.chunk_draft = DocumentChunk.objects.create(
            document=self.doc_draft,
            document_version=self.v_draft,
            chunk_index=0,
            content="Draft notes for operating systems course outline.",
            is_active=True,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Draft notes for operating systems course outline.")
        )

        # 6. Inactive Chunk (Older version chunk with is_active=False)
        self.chunk_inactive = DocumentChunk.objects.create(
            document=self.doc_public,
            document_version=self.v_public,
            chunk_index=99,
            content="Old obsolete operating systems notes that was deactivated.",
            is_active=False,
            embedding_status="completed",
            embedding_model="mock-embedding-768",
            embedding=self.mock_provider.embed_query("Old obsolete operating systems notes that was deactivated.")
        )

        # 7. Chunks with incompatible embedding model
        self.chunk_wrong_model = DocumentChunk.objects.create(
            document=self.doc_public,
            document_version=self.v_public,
            chunk_index=98,
            content="Incompatible model vector chunk.",
            is_active=True,
            embedding_status="completed",
            embedding_model="legacy-model-v0",
            embedding=self.mock_provider.embed_query("Incompatible model vector chunk.")
        )

    # -------------------------------------------------------------------------
    # Authorization & Candidate Filtering Tests
    # -------------------------------------------------------------------------
    def test_anonymous_user_can_only_retrieve_public_ready_available_documents(self):
        req = RetrievalRequest(query="Processes and threads in operating systems", user=None)
        results = self.doc_service.retrieve(req)

        self.assertGreater(len(results), 0)
        returned_doc_ids = {r.metadata["document_id"] for r in results}
        self.assertIn(self.doc_public.id, returned_doc_ids)
        self.assertNotIn(self.doc_private.id, returned_doc_ids)
        self.assertNotIn(self.doc_restricted.id, returned_doc_ids)
        self.assertNotIn(self.doc_unavailable.id, returned_doc_ids)
        self.assertNotIn(self.doc_draft.id, returned_doc_ids)

    def test_uploader_can_retrieve_their_own_private_document(self):
        req = RetrievalRequest(
            query="quantum computing research algorithms",
            user=self.uploader
        )
        results = self.doc_service.retrieve(req)
        returned_doc_ids = {r.metadata["document_id"] for r in results}
        self.assertIn(self.doc_private.id, returned_doc_ids)

    def test_other_student_cannot_retrieve_private_document(self):
        req = RetrievalRequest(
            query="quantum computing research algorithms",
            user=self.student_cs
        )
        results = self.doc_service.retrieve(req)
        returned_doc_ids = {r.metadata["document_id"] for r in results}
        self.assertNotIn(self.doc_private.id, returned_doc_ids)

    def test_staff_and_president_can_retrieve_all_ready_available_documents(self):
        # Staff
        req_staff = RetrievalRequest(query="quantum computing algorithms", user=self.staff_user)
        results_staff = self.doc_service.retrieve(req_staff)
        self.assertIn(self.doc_private.id, {r.metadata["document_id"] for r in results_staff})

        # President
        req_pres = RetrievalRequest(query="quantum computing algorithms", user=self.president_user)
        results_pres = self.doc_service.retrieve(req_pres)
        self.assertIn(self.doc_private.id, {r.metadata["document_id"] for r in results_pres})

    def test_restricted_document_accessible_only_to_enrolled_programme_student(self):
        # CS student enrolled in programme with unit CSC211
        req_cs = RetrievalRequest(query="Bellman-Ford dynamic programming CSC211", user=self.student_cs)
        results_cs = self.doc_service.retrieve(req_cs)
        self.assertIn(self.doc_restricted.id, {r.metadata["document_id"] for r in results_cs})

        # Biochemistry student not enrolled in CS programme
        req_bio = RetrievalRequest(query="Bellman-Ford dynamic programming CSC211", user=self.student_bio)
        results_bio = self.doc_service.retrieve(req_bio)
        self.assertNotIn(self.doc_restricted.id, {r.metadata["document_id"] for r in results_bio})

    def test_unavailable_and_draft_documents_are_never_retrieved(self):
        req = RetrievalRequest(query="Historical archive syllabus", user=self.uploader)
        results = self.doc_service.retrieve(req)
        returned_doc_ids = {r.metadata["document_id"] for r in results}
        self.assertNotIn(self.doc_unavailable.id, returned_doc_ids)
        self.assertNotIn(self.doc_draft.id, returned_doc_ids)

    # -------------------------------------------------------------------------
    # Semantic Retrieval & Ranking Tests
    # -------------------------------------------------------------------------
    def test_semantic_ranking_returns_most_relevant_chunk_first(self):
        query = "Processes and threads execution in modern operating systems kernel."
        req = RetrievalRequest(query=query, user=self.student_cs, limit=5)
        results = self.doc_service.retrieve(req)

        self.assertGreater(len(results), 0)
        top_result = results[0]
        # Chunk 1 matches the query exactly in content
        self.assertEqual(top_result.object_id, self.chunk_public_1.id)
        self.assertAlmostEqual(top_result.score, 1.0, delta=0.01)

    def test_top_k_limit_is_respected(self):
        req = RetrievalRequest(query="operating systems memory processes", user=None, limit=1)
        results = self.doc_service.retrieve(req)
        self.assertEqual(len(results), 1)

    def test_inactive_and_incompatible_model_chunks_excluded(self):
        req = RetrievalRequest(query="obsolete notes incompatible model", user=None)
        results = self.doc_service.retrieve(req)
        returned_chunk_ids = {r.object_id for r in results}
        self.assertNotIn(self.chunk_inactive.id, returned_chunk_ids)
        self.assertNotIn(self.chunk_wrong_model.id, returned_chunk_ids)

    # -------------------------------------------------------------------------
    # Result Contract, Citations & URLs
    # -------------------------------------------------------------------------
    def test_result_contract_fields_and_citation_generation(self):
        req = RetrievalRequest(query="Processes and threads execution in modern operating systems kernel.", user=None, limit=1)
        results = self.doc_service.retrieve(req)
        self.assertEqual(len(results), 1)
        res = results[0]

        self.assertEqual(res.source, SourceType.DOCUMENT)
        self.assertEqual(res.title, "Operating Systems Concepts")
        self.assertEqual(res.url, f"/documents/document/{self.doc_public.share_id}/")
        self.assertIn("v1", res.citation)
        self.assertIn("p. 5", res.citation)
        self.assertIn("Process Management", res.citation)
        self.assertEqual(res.metadata["page_number"], 5)
        self.assertEqual(res.metadata["version_number"], 1)

        # Check serialization
        d = res.to_dict()
        self.assertEqual(d["source"], "document")
        self.assertEqual(d["title"], "Operating Systems Concepts")
        self.assertIn("citation", d)

    def test_slide_citation_generation(self):
        citation = self.doc_service.generate_citation(self.chunk_restricted)
        self.assertIn("Slide 4", citation)
        self.assertIn("Advanced Algorithms Exam Preparation", citation)

    # -------------------------------------------------------------------------
    # Edge Cases & Failure Behavior
    # -------------------------------------------------------------------------
    def test_empty_or_whitespace_query_returns_empty_list(self):
        for empty_q in ["", "   ", None]:
            req = RetrievalRequest(query=empty_q)
            results = self.doc_service.retrieve(req)
            self.assertEqual(results, [])

    # -------------------------------------------------------------------------
    # Unified Retrieval Service & Adapters Tests
    # -------------------------------------------------------------------------
    def test_unified_retrieval_service_multi_source_orchestration(self):
        # Create a post
        post = Post.objects.create(
            author=self.uploader,
            content="Studying operating systems processes for the exam."
        )

        # Create an open group
        group = Group.objects.create(
            name="CS Revision Group",
            join_policy="open",
            description="Discussion on algorithms and systems."
        )

        req = RetrievalRequest(
            query="operating systems",
            user=self.student_cs,
            sources=[SourceType.DOCUMENT, SourceType.POST, SourceType.GROUP],
            mode=RetrievalMode.HYBRID,
            limit=10
        )
        response = self.unified_service.retrieve(req)

        self.assertIsInstance(response, RetrievalResponse)
        self.assertEqual(response.query, "operating systems")
        self.assertGreater(len(response.results), 0)
        self.assertGreater(response.execution_time_ms, 0.0)
        self.assertIn("document", response.source_metrics)
        self.assertIn("post", response.source_metrics)
        self.assertIn("group", response.source_metrics)

    def test_adapter_people_search(self):
        req = RetrievalRequest(query="Alice", user=None, sources=[SourceType.USER])
        results = self.search_adapter.search_people(req)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].source, SourceType.USER)
        self.assertEqual(results[0].url, "/users/user/uploader_user/")

    def test_unified_retrieval_semantic_failure_falls_back_to_lexical(self):
        from unittest.mock import MagicMock
        from documents.services.search_service import SearchService
        SearchService().index_document(self.doc_public)

        failing_doc_service = MagicMock()
        failing_doc_service.retrieve.side_effect = RuntimeError("Embedding service unavailable")

        service = UnifiedRetrievalService(
            document_service=failing_doc_service,
            search_adapter=self.search_adapter,
        )

        req = RetrievalRequest(
            query="Operating Systems",
            user=self.student_cs,
            sources=[SourceType.DOCUMENT],
            mode=RetrievalMode.HYBRID,
            limit=5
        )
        response = service.retrieve(req)
        self.assertIsInstance(response, RetrievalResponse)
        # Should have fallen back to lexical search and found Operating Systems Concepts
        self.assertGreater(len(response.results), 0)
        self.assertEqual(response.results[0].title, "Operating Systems Concepts")


