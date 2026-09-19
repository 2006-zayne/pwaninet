"""
Unit and Integration Tests for Pwanimate Grounded People Presentation (Phase 4).

Validates:
1. OrchestrationResponse serialization of `people` and structured `blocks`.
2. PwanimateMessage.people dynamic property extraction from sources.
3. MessageSerializer read-only inclusion of `people`.
4. Strict absence of sensitive fields (email, phone, password, tokens).
5. Strict absence of internal recommendation scores in UI rendering.
6. Reusable person_card.html template rendering (avatars, fallbacks, badges, HTMX navigation).
7. End-to-end people discovery chat flow:
   - "Find CS students who know Django"
   - "Who is open to study groups?"
   - "Find people in my programme who are interested in AI"
   - Zero-match discovery ("QuantumTeleportation999") returning empty list without hallucinations.
"""

from unittest.mock import MagicMock
from django.test import TestCase, SimpleTestCase
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import PrivacyLevel, CollaborationStatus
from documents.academic.models import Faculty, School, Department, Programme, AcademicLevel
from pwanimate.context.user_context import UserContext
from pwanimate.models import PwanimateConversation, PwanimateMessage
from pwanimate.orchestrator.types import OrchestrationRequest, OrchestrationResponse
from pwanimate.orchestrator.service import PwanimateOrchestrator
from pwanimate.ai.gateway import AIGateway, LLMResponse, LLMRouter
from pwanimate.ai.gateway.quota_tracker import get_quota_tracker
from pwanimate.ai.providers import MockLLMProvider
from pwanimate.api.serializers import MessageSerializer
from pwanimate.api.views import PwanimateChatView

User = get_user_model()


class OrchestrationResponseSerializationTests(SimpleTestCase):
    """Test OrchestrationResponse DTO serialization for people and blocks."""

    def test_response_to_dict_with_people(self):
        person_data = {
            "username": "student1",
            "display_name": "Student One",
            "profile_url": "/users/user/student1/",
            "avatar_url": None,
            "headline": "CS Major",
            "programme_name": "Computer Science",
            "academic_level": "Year 2",
            "collaboration_status": "open_to_projects",
            "matched_skills": ["Python", "Django"],
            "matched_interests": ["Web Dev"],
            "evidence": {"academic_alignment": "Same Department"},
            "recommendation_score": 85,
        }
        resp = OrchestrationResponse(
            answer="Here is a student you might like to connect with.",
            people=[person_data],
        )
        d = resp.to_dict()

        self.assertIn("people", d)
        self.assertEqual(len(d["people"]), 1)
        self.assertEqual(d["people"][0]["username"], "student1")
        self.assertIn("blocks", d)
        self.assertEqual(len(d["blocks"]), 1)
        self.assertEqual(d["blocks"][0]["type"], "people")
        self.assertEqual(d["blocks"][0]["people"][0]["username"], "student1")

    def test_response_to_dict_empty_people(self):
        resp = OrchestrationResponse(
            answer="No students found.",
            people=[],
        )
        d = resp.to_dict()
        self.assertEqual(d["people"], [])
        self.assertEqual(d["blocks"], [])


class PwanimateMessagePeoplePropertyTests(TestCase):
    """Test dynamic @property people on PwanimateMessage."""

    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="password123")
        self.conv = PwanimateConversation.objects.create(user=self.user, title="Test Chat")

    def test_message_people_property_with_user_source(self):
        person_payload = {
            "username": "alex",
            "display_name": "Alex Tech",
            "profile_url": "/users/user/alex/",
            "matched_skills": ["Python"],
        }
        sources = [
            {
                "source": "user",
                "id": "user_alex",
                "title": "Alex Tech (@alex)",
                "citation": "[@alex]",
                "url": "/users/user/alex/",
                "person": person_payload,
            },
            {
                "source": "document",
                "id": "doc_123",
                "title": "Syllabus",
                "citation": "[Syllabus]",
                "url": "/documents/123/",
            },
        ]
        msg = PwanimateMessage.objects.create(
            conversation=self.conv,
            role="assistant",
            content="Here are the recommended peers.",
            sources=sources,
        )

        self.assertEqual(len(msg.people), 1)
        self.assertEqual(msg.people[0]["username"], "alex")
        self.assertEqual(msg.people[0]["matched_skills"], ["Python"])

    def test_message_people_property_without_user_source(self):
        sources = [
            {
                "source": "document",
                "id": "doc_1",
                "title": "Lecture 1",
            }
        ]
        msg = PwanimateMessage.objects.create(
            conversation=self.conv,
            role="assistant",
            content="Document only.",
            sources=sources,
        )
        self.assertEqual(msg.people, [])

    def test_message_people_property_empty_sources(self):
        msg = PwanimateMessage.objects.create(
            conversation=self.conv,
            role="assistant",
            content="No sources.",
            sources=[],
        )
        self.assertEqual(msg.people, [])

    def test_message_serializer_includes_people(self):
        person_payload = {
            "username": "maria",
            "display_name": "Maria DB",
            "profile_url": "/users/user/maria/",
        }
        msg = PwanimateMessage.objects.create(
            conversation=self.conv,
            role="assistant",
            content="Maria is available.",
            sources=[{"source": "user", "person": person_payload}],
        )
        serializer = MessageSerializer(msg)
        data = serializer.data
        self.assertIn("people", data)
        self.assertEqual(len(data["people"]), 1)
        self.assertEqual(data["people"][0]["username"], "maria")


class PersonCardTemplateRenderingTests(SimpleTestCase):
    """Test person_card.html template rendering for accessibility, badges, and privacy."""

    def test_full_person_card_rendering(self):
        person = {
            "username": "codeninja",
            "display_name": "Code Ninja",
            "profile_url": "/users/user/codeninja/",
            "avatar_url": "/media/profiles/ninja.jpg",
            "headline": "Building open-source tools",
            "programme_name": "Computer Science",
            "academic_level": "Year 3",
            "collaboration_status": "open_to_projects",
            "matched_skills": ["Python", "Django", "PostgreSQL"],
            "matched_interests": ["Machine Learning"],
            "evidence": {
                "academic_alignment": "Same Programme",
                "mutual_connections_count": 3,
                "shared_groups_count": 2,
            },
            "recommendation_score": 92.5,
        }

        html = render_to_string("pwanimate/partials/person_card.html", {"person": person})

        # Basic identity
        self.assertIn("Code Ninja", html)
        self.assertIn("@codeninja", html)
        self.assertIn("/users/user/codeninja/", html)
        self.assertIn("/media/profiles/ninja.jpg", html)
        self.assertIn("Building open-source tools", html)
        self.assertIn("Computer Science", html)
        self.assertIn("Year 3", html)

        # HTMX attributes
        self.assertIn('hx-get="/users/user/codeninja/"', html)
        self.assertIn('hx-target="#page-content-target"', html)
        self.assertIn('hx-push-url="true"', html)

        # Badges
        self.assertIn("Open to Projects", html)
        self.assertIn("Python", html)
        self.assertIn("Django", html)
        self.assertIn("PostgreSQL", html)
        self.assertIn("Machine Learning", html)
        self.assertIn("Same Programme", html)
        self.assertIn("3 mutual", html)
        self.assertIn("2 groups", html)

        # SECURITY / PRIVACY CHECKS:
        # Internal recommendation score must NEVER appear in rendered output
        self.assertNotIn("92.5", html)
        self.assertNotIn("recommendation_score", html)

        # Sensitive credentials must not exist
        self.assertNotIn("password", html)
        self.assertNotIn("token", html)
        self.assertNotIn("email", html)

    def test_avatar_fallback_rendering(self):
        person = {
            "username": "zack",
            "display_name": "Zack Brown",
            "profile_url": "/users/user/zack/",
            "avatar_url": None,
            "collaboration_status": "open_to_study_groups",
            "matched_skills": [],
            "matched_interests": [],
            "evidence": {},
        }
        html = render_to_string("pwanimate/partials/person_card.html", {"person": person})

        # Initial fallback placeholder
        self.assertIn("pwanimate-avatar-placeholder", html)
        self.assertIn("Z", html)
        self.assertIn("Open to Study Groups", html)

    def test_not_looking_collaboration_status_not_rendered_as_badge(self):
        person = {
            "username": "quiet_student",
            "display_name": "Quiet Student",
            "profile_url": "/users/user/quiet_student/",
            "avatar_url": None,
            "collaboration_status": "not_looking",
            "matched_skills": ["Python"],
            "matched_interests": [],
            "evidence": {},
        }
        html = render_to_string("pwanimate/partials/person_card.html", {"person": person})

        self.assertNotIn("Open to", html)
        self.assertNotIn("not_looking", html)
        self.assertIn("Python", html)


class EndToEndPeoplePresentationTests(TestCase):
    """Integration test simulating discovery queries through Orchestrator and API endpoint."""

    def setUp(self):
        # 1. Academic Hierarchy
        self.faculty = Faculty.objects.create(code="FSCI", name="Faculty of Science")
        self.school = School.objects.create(code="COMP", name="School of Computing", faculty=self.faculty)
        self.dept_cs = Department.objects.create(code="CS", name="Department of Computer Science", school=self.school)
        self.prog_cs = Programme.objects.create(code="CS", name="BSc Computer Science", department=self.dept_cs, duration_years=4)
        self.prog_it = Programme.objects.create(code="BSC-IT", name="BSc Information Tech", department=self.dept_cs, duration_years=4)

        self.lvl_2 = AcademicLevel.objects.create(level=2, name="Year 2")
        self.lvl_3 = AcademicLevel.objects.create(level=3, name="Year 3")
        self.lvl_4 = AcademicLevel.objects.create(level=4, name="Year 4")

        # 2. Users
        self.viewer = User.objects.create_user(
            username="viewer",
            email="viewer@example.com",
            password="password123",
            first_name="View",
            last_name="Er",
            programme=self.prog_cs,
            academic_level=self.lvl_2,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        self.dev_django = User.objects.create_user(
            username="djangodev",
            email="django@example.com",
            password="password123",
            first_name="Django",
            last_name="Expert",
            programme=self.prog_cs,
            academic_level=self.lvl_3,
            skills=["Django", "Python", "PostgreSQL"],
            interests="Web Development, Software Engineering",
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        self.study_peer = User.objects.create_user(
            username="studypeer",
            email="peer@example.com",
            password="password123",
            first_name="Study",
            last_name="Buddy",
            programme=self.prog_cs,
            academic_level=self.lvl_2,
            skills=["Calculus", "Algorithms"],
            interests="AI, Mathematics",
            collaboration_status=CollaborationStatus.OPEN_TO_STUDY_GROUPS,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        self.ai_student = User.objects.create_user(
            username="aistudent",
            email="ai@example.com",
            password="password123",
            first_name="AI",
            last_name="Researcher",
            programme=self.prog_cs,
            academic_level=self.lvl_4,
            skills=["PyTorch", "Machine Learning"],
            interests="Artificial Intelligence, Computer Vision",
            collaboration_status=CollaborationStatus.OPEN_TO_NETWORKING,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        # Configure mock orchestrator for deterministic and offline testing
        self.mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": self.mock_provider}, default_provider="mock")
        self.gateway = AIGateway(router=router)
        self.orchestrator = PwanimateOrchestrator(gateway=self.gateway)
        PwanimateChatView.orchestrator = self.orchestrator

        self.client = APIClient()
        self.client.force_authenticate(user=self.viewer)

    def tearDown(self):
        PwanimateChatView.orchestrator = None
        get_quota_tracker().clear()

    def test_query_find_cs_students_who_know_django(self):
        """Query 'Find CS students who know Django' returns djangodev in people list."""
        url = reverse("pwanimate_api:chat")
        payload = {"message": "Find CS students who know Django"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("people", data)
        self.assertGreaterEqual(len(data["people"]), 1)

        usernames = [p["username"] for p in data["people"]]
        self.assertIn("djangodev", usernames)

        dev_card = next(p for p in data["people"] if p["username"] == "djangodev")
        self.assertEqual(dev_card["profile_url"], "/users/user/djangodev/")
        self.assertEqual(dev_card["collaboration_status"], "open_to_projects")
        self.assertIn("Django", dev_card["matched_skills"])

        # Check structured blocks
        self.assertIn("blocks", data)
        self.assertEqual(data["blocks"][0]["type"], "people")

        # Check persistence
        last_msg = PwanimateMessage.objects.filter(role="assistant").last()
        self.assertIsNotNone(last_msg)
        self.assertGreaterEqual(len(last_msg.people), 1)
        self.assertIn("djangodev", [p["username"] for p in last_msg.people])

    def test_query_who_is_open_to_study_groups(self):
        """Query 'Who is open to study groups?' discovers studypeer."""
        url = reverse("pwanimate_api:chat")
        payload = {"message": "Who is open to study groups?"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("people", data)
        usernames = [p["username"] for p in data["people"]]
        self.assertIn("studypeer", usernames)

        peer_card = next(p for p in data["people"] if p["username"] == "studypeer")
        self.assertEqual(peer_card["collaboration_status"], "open_to_study_groups")

    def test_query_programme_and_ai_interest(self):
        """Query 'Find people in my programme who are interested in AI'."""
        url = reverse("pwanimate_api:chat")
        payload = {"message": "Find people in my programme who are interested in AI"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("people", data)
        usernames = [p["username"] for p in data["people"]]
        self.assertTrue("aistudent" in usernames or "studypeer" in usernames)

    def test_zero_match_query_returns_empty_people_list(self):
        """Query 'Find students who know QuantumTeleportation999' returns empty list."""
        url = reverse("pwanimate_api:chat")
        payload = {"message": "Find students who know QuantumTeleportation999"}

        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["people"], [])
        self.assertEqual(data["blocks"], [])

        last_msg = PwanimateMessage.objects.filter(role="assistant").last()
        self.assertIsNotNone(last_msg)
        self.assertEqual(last_msg.people, [])
