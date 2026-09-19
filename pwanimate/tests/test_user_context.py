"""
Comprehensive Test Suite for Pwanimate UserContext and UserContextService.

Covers:
- Identity normalization and display name conventions
- Academic hierarchy resolution (programme, department, school, level, year, semester)
- Legacy course/year fallback resolution
- Incomplete academic placement resilience (no crashes)
- Interests text normalization and deduplication
- Skills JSON array normalization and defensive handling
- Authoritative collaboration status preservation
- Social graph structural context (approved groups and following IDs)
- Strict security boundary (no sensitive fields in DTO or serialization)
- Database query efficiency and N+1 prevention
- Orchestrator request plumbing
"""

from dataclasses import FrozenInstanceError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, SimpleTestCase

from courses.models import Course, Year
from documents.academic.models import (
    Faculty,
    School,
    Department,
    Programme,
    AcademicLevel,
    AcademicYear,
    Semester,
)
from groups.models import Group, Membership, MembershipStatus
from users.models import Follow, CollaborationStatus
from pwanimate.context import (
    UserContext,
    UserContextService,
    normalize_interests,
    normalize_skills,
    resolve_display_name,
)
from pwanimate.orchestrator.types import OrchestrationRequest

User = get_user_model()


class NormalizationUnitTests(SimpleTestCase):
    """Fast offline unit tests for normalization helpers and DTO structure."""

    def test_normalize_interests_clean(self):
        raw = "Python, AI,  Web Development, Python"
        expected = ["Python", "AI", "Web Development"]
        self.assertEqual(normalize_interests(raw), expected)

    def test_normalize_interests_whitespace_and_empty(self):
        self.assertEqual(normalize_interests(""), [])
        self.assertEqual(normalize_interests("   "), [])
        self.assertEqual(normalize_interests(None), [])
        self.assertEqual(normalize_interests(", , , "), [])

    def test_normalize_interests_internal_whitespace(self):
        raw = "  Machine   Learning  ,   Data   Science  "
        self.assertEqual(normalize_interests(raw), ["Machine Learning", "Data Science"])

    def test_normalize_interests_case_insensitive_dedup(self):
        raw = "AI, ai, Ai, Artificial Intelligence"
        self.assertEqual(normalize_interests(raw), ["AI", "Artificial Intelligence"])

    def test_normalize_skills_list(self):
        skills = ["Python", "JavaScript", "Django"]
        self.assertEqual(normalize_skills(skills), ["Python", "JavaScript", "Django"])

    def test_normalize_skills_dedup_and_whitespace(self):
        skills = [" Python ", "python", "  React  ", "REACT", "Django"]
        self.assertEqual(normalize_skills(skills), ["Python", "React", "Django"])

    def test_normalize_skills_json_string(self):
        json_str = '["Python", "Machine Learning", "PyTorch"]'
        self.assertEqual(normalize_skills(json_str), ["Python", "Machine Learning", "PyTorch"])

    def test_normalize_skills_newline_string(self):
        newline_str = "Python\nJavaScript\n  Docker  \nPython"
        self.assertEqual(normalize_skills(newline_str), ["Python", "JavaScript", "Docker"])

    def test_normalize_skills_empty_and_none(self):
        self.assertEqual(normalize_skills(None), [])
        self.assertEqual(normalize_skills([]), [])
        self.assertEqual(normalize_skills(""), [])
        self.assertEqual(normalize_skills("   "), [])

    def test_normalize_skills_defensive_types(self):
        # Defensively handles unexpected types without crashing
        self.assertEqual(normalize_skills(123), [])
        self.assertEqual(normalize_skills({"key": "val"}), [])
        self.assertEqual(normalize_skills([{"name": "Python"}, 456, "Django"]), ["Python", "Django"])

    def test_resolve_display_name_variations(self):
        class DummyUser:
            def __init__(self, username, first="", second="", last=""):
                self.username = username
                self.first_name = first
                self.second_name = second
                self.last_name = last

            def get_full_name(self):
                return f"{self.first_name} {self.last_name}".strip()

        # All 3 names populated
        u1 = DummyUser("jdoe", first="John", second="Michael", last="Doe")
        self.assertEqual(resolve_display_name(u1), "John Michael Doe")

        # First and last only
        u2 = DummyUser("jdoe", first="John", last="Doe")
        self.assertEqual(resolve_display_name(u2), "John Doe")

        # First name only
        u3 = DummyUser("jdoe", first="John")
        self.assertEqual(resolve_display_name(u3), "John")

        # Username fallback when names are absent
        u4 = DummyUser("jdoe")
        self.assertEqual(resolve_display_name(u4), "jdoe")


class UserContextContractTests(SimpleTestCase):
    """Tests for UserContext immutability, serialization, and security boundaries."""

    def test_dto_immutability(self):
        ctx = UserContext(
            user_id=1,
            username="student1",
            display_name="Student One",
            interests=["AI"],
            skills=["Python"],
        )
        with self.assertRaises(FrozenInstanceError):
            ctx.username = "modified"  # type: ignore

    def test_to_dict_structure(self):
        ctx = UserContext(
            user_id=42,
            username="alice",
            display_name="Alice Wambui",
            programme_id=10,
            programme_name="BSc Computer Science",
            department_id=5,
            department_name="Department of Computing",
            school_id=2,
            school_name="School of Pure and Applied Sciences",
            academic_level_id=3,
            academic_level_name="Year 3",
            academic_year="2025/2026",
            semester=1,
            interests=["AI", "Python"],
            skills=["Python", "Django"],
            collaboration_status="open_to_projects",
            approved_group_ids=[101, 102],
            following_user_ids=[55, 60],
        )
        serialized = ctx.to_dict()

        self.assertEqual(serialized["user_id"], 42)
        self.assertEqual(serialized["username"], "alice")
        self.assertEqual(serialized["display_name"], "Alice Wambui")
        self.assertEqual(serialized["programme_name"], "BSc Computer Science")
        self.assertEqual(serialized["department_name"], "Department of Computing")
        self.assertEqual(serialized["school_name"], "School of Pure and Applied Sciences")
        self.assertEqual(serialized["academic_level_name"], "Year 3")
        self.assertEqual(serialized["academic_year"], "2025/2026")
        self.assertEqual(serialized["semester"], 1)
        self.assertEqual(serialized["interests"], ["AI", "Python"])
        self.assertEqual(serialized["skills"], ["Python", "Django"])
        self.assertEqual(serialized["collaboration_status"], "open_to_projects")
        self.assertEqual(serialized["approved_group_ids"], [101, 102])
        self.assertEqual(serialized["following_user_ids"], [55, 60])

    def test_strict_security_boundary(self):
        """Verify sensitive credentials and internal fields are completely excluded from UserContext."""
        ctx = UserContext(
            user_id=1,
            username="testuser",
            display_name="Test User",
        )
        serialized = ctx.to_dict()

        sensitive_fields = [
            "password",
            "password_hash",
            "email",
            "recovery_codes",
            "totp_secret",
            "mfa_secret",
            "encrypted_secret",
            "session",
            "session_key",
            "token",
            "auth_token",
            "ip_address",
            "device_id",
            "device_name",
            "_state",
        ]
        for field_name in sensitive_fields:
            self.assertNotIn(
                field_name,
                serialized,
                f"Security breach: sensitive field '{field_name}' found in UserContext.to_dict()",
            )


class UserContextServiceIntegrationTests(TestCase):
    """Database integration tests verifying UserContextService behavior and query efficiency."""

    def setUp(self):
        # 1. Academic hierarchy fixtures
        self.faculty = Faculty.objects.create(code="SCI", name="Faculty of Science")
        self.school = School.objects.create(code="COMP", name="School of Computing", faculty=self.faculty)
        self.dept = Department.objects.create(code="CS", name="Department of Computer Science", school=self.school)

        self.programme = Programme.objects.create(
            code="BSCCS",
            name="BSc. Computer Science",
            department=self.dept,
            degree_type="Bachelor",
            duration_years=4,
        )
        self.level3 = AcademicLevel.objects.create(level=3, name="Year 3")
        self.academic_year = AcademicYear.objects.create(
            code="2025/2026",
            name="2025/2026",
            start_date="2025-09-01",
            end_date="2026-06-30",
        )
        self.semester1 = Semester.objects.create(
            academic_year=self.academic_year,
            number=1,
            start_date="2025-09-01",
            end_date="2025-12-20",
        )

        # 2. Main target student
        self.user = User.objects.create_user(
            username="alice_test",
            email="alice@pwani.ac.ke",
            password="TestPassword123!",
            first_name="Alice",
            second_name="Wambui",
            last_name="Kamau",
            programme=self.programme,
            academic_level=self.level3,
            academic_year=self.academic_year,
            semester=self.semester1,
            interests="Artificial Intelligence, Python, Robotics, AI",
            skills=["Python", "PyTorch", "Django", "Python"],
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
        )

        # 3. Peers and Groups
        self.peer1 = User.objects.create_user(username="bob_peer", password="password")
        self.peer2 = User.objects.create_user(username="charlie_peer", password="password")

        self.group_approved = Group.objects.create(name="AI Innovators Club")
        self.group_pending = Group.objects.create(name="Web Dev Group")

        # Approved membership
        Membership.objects.create(
            user=self.user,
            group=self.group_approved,
            status=MembershipStatus.APPROVED,
        )
        # Pending membership (should be excluded)
        Membership.objects.create(
            user=self.user,
            group=self.group_pending,
            status=MembershipStatus.PENDING,
        )

        # Follow relationships
        Follow.objects.create(follower=self.user, followed=self.peer1)
        Follow.objects.create(follower=self.user, followed=self.peer2)

    def test_build_full_academic_context(self):
        service = UserContextService()
        ctx = service.build(self.user)

        # Identity
        self.assertEqual(ctx.user_id, self.user.id)
        self.assertEqual(ctx.username, "alice_test")
        self.assertEqual(ctx.display_name, "Alice Wambui Kamau")

        # Academic hierarchy
        self.assertEqual(ctx.programme_id, self.programme.id)
        self.assertEqual(ctx.programme_name, "BSc. Computer Science")
        self.assertEqual(ctx.department_id, self.dept.id)
        self.assertEqual(ctx.department_name, "Department of Computer Science")
        self.assertEqual(ctx.school_id, self.school.id)
        self.assertEqual(ctx.school_name, "School of Computing")
        self.assertEqual(ctx.academic_level_id, self.level3.id)
        self.assertEqual(ctx.academic_level_name, "Year 3")
        self.assertEqual(ctx.academic_year, "2025/2026")
        self.assertEqual(ctx.semester, 1)

        # Normalized interests and skills
        self.assertEqual(ctx.interests, ["Artificial Intelligence", "Python", "Robotics", "AI"])
        self.assertEqual(ctx.skills, ["Python", "PyTorch", "Django"])

        # Collaboration
        self.assertEqual(ctx.collaboration_status, "open_to_projects")

        # Social Context (only approved groups and followed peer IDs)
        self.assertEqual(ctx.approved_group_ids, [self.group_approved.id])
        self.assertNotIn(self.group_pending.id, ctx.approved_group_ids)
        self.assertEqual(set(ctx.following_user_ids), {self.peer1.id, self.peer2.id})

    def test_build_minimal_user_resilience(self):
        """Ensure users without any academic placement or profile metadata resolve safely without errors."""
        bare_user = User.objects.create_user(
            username="bare_student",
            password="password",
        )

        service = UserContextService()
        ctx = service.build(bare_user)

        self.assertEqual(ctx.user_id, bare_user.id)
        self.assertEqual(ctx.username, "bare_student")
        self.assertEqual(ctx.display_name, "bare_student")
        self.assertIsNone(ctx.programme_id)
        self.assertIsNone(ctx.programme_name)
        self.assertIsNone(ctx.department_id)
        self.assertIsNone(ctx.school_id)
        self.assertIsNone(ctx.academic_level_id)
        self.assertIsNone(ctx.academic_year)
        self.assertIsNone(ctx.semester)
        self.assertEqual(ctx.interests, [])
        self.assertEqual(ctx.skills, [])
        self.assertEqual(ctx.collaboration_status, "")
        self.assertEqual(ctx.approved_group_ids, [])
        self.assertEqual(ctx.following_user_ids, [])

    def test_build_legacy_course_and_year_fallback(self):
        """Verify legacy Course and Year models resolve gracefully when modern Programme is not assigned."""
        legacy_course = Course.objects.create(name="Diploma in IT", code="DIT")
        legacy_year = Year.objects.create(level=2, course=legacy_course)

        legacy_user = User.objects.create_user(
            username="legacy_student",
            password="password",
            course=legacy_course,
            year=legacy_year,
        )

        service = UserContextService()
        ctx = service.build(legacy_user)

        self.assertEqual(ctx.programme_name, "Diploma in IT")
        self.assertEqual(ctx.academic_level_name, "Year 2")

    def test_unauthenticated_user_raises_value_error(self):
        service = UserContextService()
        with self.assertRaises(ValueError):
            service.build(None)

        with self.assertRaises(ValueError):
            service.build(AnonymousUser())

    def test_query_efficiency_bounded(self):
        """
        Verify that building UserContext executes exactly a constant, bounded
        number of database queries (1 select_related user query + 1 group query + 1 follow query).
        """
        service = UserContextService()

        # Warm up connection
        _ = service.build(self.user)

        # Exactly 3 queries: User+Academic Hierarchy, Approved Groups, Follows
        with self.assertNumQueries(3):
            _ = service.build(self.user)

    def test_orchestrator_request_plumbing(self):
        """Verify OrchestrationRequest accepts and holds user_context."""
        service = UserContextService()
        ctx = service.build(self.user)

        req = OrchestrationRequest(
            query="Find collaborators",
            user=self.user,
            user_context=ctx,
        )
        self.assertEqual(req.user_context, ctx)
        self.assertEqual(req.user_context.user_id, self.user.id)
        self.assertEqual(req.user_context.collaboration_status, "open_to_projects")

    # -------------------------------------------------------------------------
    # Phase 2B: Pipeline Integration Tests
    # -------------------------------------------------------------------------
    def test_format_context_block_structure_and_safety(self):
        """Verify format_context_block produces compact, structured text and excludes all secrets."""
        service = UserContextService()
        ctx = service.build(self.user)
        text = ctx.format_context_block()

        # Structure checks
        self.assertTrue(text.startswith("<user_context>"))
        self.assertTrue(text.endswith("</user_context>"))
        self.assertIn(f"- Username: {self.user.username}", text)
        self.assertIn(f"- Display Name: {ctx.display_name}", text)
        self.assertIn(f"- Programme: {ctx.programme_name}", text)
        self.assertIn(f"- Department: {ctx.department_name}", text)
        self.assertIn(f"- School: {ctx.school_name}", text)
        self.assertIn(f"- Level: {ctx.academic_level_name}", text)
        self.assertIn(f"- Year: {ctx.academic_year}", text)
        self.assertIn(f"- Semester: {ctx.semester}", text)
        self.assertIn("Interests: Artificial Intelligence, Python, Robotics, AI", text)
        self.assertIn("Skills: Python, PyTorch, Django", text)
        self.assertIn("- Collaboration Status: open_to_projects", text)
        self.assertIn("- Approved Groups Count: 1", text)

        # Strict security assertions: no passwords, emails, tokens, secrets
        self.assertNotIn("email", text.lower())
        self.assertNotIn(self.user.email, text)
        self.assertNotIn("password", text.lower())
        self.assertNotIn("token", text.lower())
        self.assertNotIn("secret", text.lower())
        self.assertNotIn("session", text.lower())

    def test_format_context_block_minimal_profile(self):
        """Verify format_context_block succeeds gracefully on minimal/empty profiles."""
        minimal_user = User.objects.create_user(
            username="minimal_student",
            password="testpassword",
        )
        service = UserContextService()
        ctx = service.build(minimal_user)
        text = ctx.format_context_block()

        self.assertIn("<user_context>", text)
        self.assertIn("</user_context>", text)
        self.assertIn("- Username: minimal_student", text)
        self.assertNotIn("Academic:", text)
        self.assertNotIn("Profile:", text)

    def test_single_build_per_orchestration_turn(self):
        """
        Verify that a single orchestration request builds UserContext at most once,
        preventing repeated database query overhead across downstream components.
        """
        from unittest.mock import patch
        from pwanimate.orchestrator import PwanimateOrchestrator
        from pwanimate.ai.gateway import AIGateway, LLMRouter
        from pwanimate.ai.providers import MockLLMProvider

        mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": mock_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        orchestrator = PwanimateOrchestrator(gateway=gateway)

        req = OrchestrationRequest(
            query="Explain operating systems processes",
            user=self.user,
        )

        with patch.object(UserContextService, "build", wraps=UserContextService().build) as spy_build:
            resp = orchestrator.run(req)

            # UserContextService.build must be called exactly once
            self.assertEqual(spy_build.call_count, 1)
            self.assertIsNotNone(req.user_context)
            self.assertEqual(req.user_context.user_id, self.user.id)

    def test_user_context_injected_into_rag_grounding_context(self):
        """
        Verify that UserContext is automatically attached to ContextPackage during RAG turns.
        """
        from unittest.mock import MagicMock
        from pwanimate.orchestrator import PwanimateOrchestrator
        from pwanimate.retrieval import UnifiedRetrievalService, RetrievalResponse, RetrievalResult, SourceType
        from pwanimate.ai.gateway import AIGateway, LLMRouter
        from pwanimate.ai.providers import MockLLMProvider

        # Mock retrieval with 1 result
        mock_retrieval = MagicMock(spec=UnifiedRetrievalService)
        mock_retrieval.retrieve.return_value = RetrievalResponse(
            query="CPU scheduling",
            results=[
                RetrievalResult(
                    source=SourceType.DOCUMENT,
                    object_id=1,
                    title="OS Notes",
                    snippet="Round robin is a scheduling algorithm.",
                    score=0.9,
                    citation="[OS Notes, p. 1]",
                    url="/doc/1/",
                )
            ],
            total_count=1,
            execution_time_ms=5.0,
        )

        mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": mock_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        orchestrator = PwanimateOrchestrator(retrieval_service=mock_retrieval, gateway=gateway)

        req = OrchestrationRequest(
            query="Explain round robin scheduling",
            user=self.user,
        )
        resp = orchestrator.run(req)

        self.assertEqual(resp.provider, "mock")
        self.assertIsNotNone(req.user_context)

        # Check that last LLMRequest received ContextPackage with user_context attached
        last_req = mock_provider.last_request
        self.assertIsNotNone(last_req)
        self.assertIsNotNone(last_req.context)
        self.assertIsNotNone(last_req.context.user_context)
        self.assertEqual(last_req.context.user_context.username, self.user.username)

        # Check that format_context_text outputs both user_context and retrieved_context
        formatted = last_req.context.format_context_text()
        self.assertIn("<user_context>", formatted)
        self.assertIn("<retrieved_context", formatted)

    def test_orchestrator_resilience_when_user_context_build_fails(self):
        """
        Verify that if UserContext construction fails unexpectedly, the orchestrator
        logs a warning and continues processing without crashing or failing the request.
        """
        from unittest.mock import patch
        from pwanimate.orchestrator import PwanimateOrchestrator
        from pwanimate.ai.gateway import AIGateway, LLMRouter
        from pwanimate.ai.providers import MockLLMProvider

        mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": mock_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        orchestrator = PwanimateOrchestrator(gateway=gateway)

        req = OrchestrationRequest(
            query="Hello there!",
            user=self.user,
        )

        with patch.object(UserContextService, "build", side_effect=RuntimeError("Database temporary glitch")):
            # Must not raise RuntimeError
            resp = orchestrator.run(req)
            self.assertIsNotNone(resp)
            self.assertEqual(resp.provider, "mock")
            self.assertIsNone(req.user_context)

