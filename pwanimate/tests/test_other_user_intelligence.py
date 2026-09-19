"""
Test Suite for Other-User Profile Intelligence & Natural Language Discovery Routing.

Tests:
1. ToolRouter pattern expansion for single-user profile questions (studies, skills, interests, collaboration, identity).
2. ToolRouter pattern expansion for natural language people discovery (collaborators, coursemates, compound skill + status).
3. UserProfileTool privacy boundaries (bidirectional blocks, privacy levels, email protection).
4. Tool Context Adapter grounding of profile metadata (interests, collaboration status, academic level, canonical URLs).
5. Orchestrator single-user card generation and grounding in response.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from documents.academic.models import (
    Faculty,
    School,
    Department,
    Programme,
    AcademicLevel,
)
from users.models import PrivacyLevel, Follow, Block, CollaborationStatus
from pwanimate.tools.router import ToolRouter
from pwanimate.tools.domain.users import UserProfileTool
from pwanimate.tools.adapter import tool_result_to_context_items
from pwanimate.tools.exceptions import ToolPermissionError, ToolNotFoundError
from pwanimate.orchestrator import OrchestrationRequest, PwanimateOrchestrator
from pwanimate.ai.gateway import AIGateway, LLMRouter
from pwanimate.ai.providers import MockLLMProvider

User = get_user_model()


class OtherUserRoutingTestCase(TestCase):
    """Test ToolRouter patterns for single-user inquiries and natural language discovery."""

    def setUp(self):
        self.router = ToolRouter()

    def test_academic_and_study_inquiries_route_to_user_profile(self):
        queries = [
            "What does @student1 study?",
            "What is @student1 studying?",
            "What programme is @student1 in?",
            "what course does @student1 take?",
            "what is the programme of @student1?",
            "What year is @student1?",
            "academic level of @student1",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "user_profile", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("username"), "student1", f"Wrong username for: '{q}'")

    def test_skills_and_stack_inquiries_route_to_user_profile(self):
        queries = [
            "What skills does @student1 have?",
            "What are @student1's skills?",
            "what are the skills of @student1?",
            "Does @student1 know Python?",
            "what does @student1 know?",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "user_profile", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("username"), "student1", f"Wrong username for: '{q}'")

    def test_interests_and_collaboration_inquiries_route_to_user_profile(self):
        queries = [
            "What is @student1 interested in?",
            "What are @student1's interests?",
            "Is @student1 open to collaboration?",
            "Is @student1 open to projects?",
            "is @student1 available for collaboration?",
            "what is the collaboration status of @student1?",
            "Does @student1 have any projects?",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "user_profile", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("username"), "student1", f"Wrong username for: '{q}'")

    def test_identity_and_mention_fallbacks_route_to_user_profile(self):
        queries = [
            "Tell me about @student1",
            "Can you tell me about @student1?",
            "Who is @student1?",
            "lookup @student1",
            "show me @student1",
            "view @student1",
            "profile of @student1",
            "@student1",
            "Give me info on @student1",
            "background details on @student1",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "user_profile", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("username"), "student1", f"Wrong username for: '{q}'")

    def test_collaborator_inquiry_routes_to_people_discovery(self):
        queries = [
            "I'm building a startup and I need collaborators within the uni can you help me out?",
            "I need collaborators for a startup",
            "Looking for collaborators",
            "Find me collaborators",
            "Help me find collaborators",
            "Can you connect me with collaborators?",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "people_discovery", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("collaboration_status"), "open_to_projects")

    def test_coursemates_inquiry_routes_to_people_discovery(self):
        queries = [
            "just help me find my coursemates then",
            "find my coursemates",
            "find my classmates",
            "show me my coursemates",
            "who are my coursemates",
            "help me find my coursemates",
        ]
        for q in queries:
            route = self.router.route(q)
            self.assertIsNotNone(route, f"Failed to route: '{q}'")
            self.assertEqual(route.tool_name, "people_discovery", f"Wrong tool for: '{q}'")
            self.assertEqual(route.parameters.get("academic_scope"), "my_programme")

    def test_compound_topic_and_status_discovery_routes_correctly(self):
        # 1. Tech + open to collaboration
        r1 = self.router.route("Find students interested in tech who are open to collaboration")
        self.assertIsNotNone(r1)
        self.assertEqual(r1.tool_name, "people_discovery")
        self.assertEqual(r1.parameters.get("skills"), ["tech"])
        self.assertEqual(r1.parameters.get("collaboration_status"), "any_open")

        # 2. Django + open to projects
        r2 = self.router.route("Find students who know Django and are open to projects")
        self.assertIsNotNone(r2)
        self.assertEqual(r2.tool_name, "people_discovery")
        self.assertEqual(r2.parameters.get("skills"), ["Django"])
        self.assertEqual(r2.parameters.get("collaboration_status"), "open_to_projects")

        # 3. Conversational referral: "Can you refer me to some of the students who are interested in tech projects?"
        r3 = self.router.route("Can you refer me to some of the students who are interested in tech projects?")
        self.assertIsNotNone(r3)
        self.assertEqual(r3.tool_name, "people_discovery")
        self.assertEqual(r3.parameters.get("skills"), ["tech"])
        self.assertEqual(r3.parameters.get("collaboration_status"), "open_to_projects")


class OtherUserProfileSecurityAndPrivacyTestCase(TestCase):
    """Test UserProfileTool privacy enforcement, bidirectional blocks, and rich metadata."""

    def setUp(self):
        self.faculty = Faculty.objects.create(code="FSCI", name="Faculty of Science")
        self.school = School.objects.create(code="COMP", name="School of Computing", faculty=self.faculty)
        self.dept = Department.objects.create(name="Department of Computing", code="COMP", school=self.school)
        self.level_yr2, _ = AcademicLevel.objects.get_or_create(level=2, defaults={"name": "Year 2"})
        self.prog = Programme.objects.create(
            name="Bachelor of Science in Computer Science",
            code="BSC-CS",
            department=self.dept,
            degree_type="Bachelor",
            duration_years=4,
        )

        self.viewer = User.objects.create_user(username="viewer_user", password="password123")
        self.follower = User.objects.create_user(username="follower_user", password="password123")
        self.blocker = User.objects.create_user(username="blocker_user", password="password123")
        self.staff_user = User.objects.create_user(username="staff_user", password="password123", is_staff=True)

        self.target_public = User.objects.create_user(
            username="target_public",
            first_name="Kelvin",
            last_name="Kiprop",
            headline="Software Engineer",
            bio="Building backend services.",
            programme=self.prog,
            academic_level=self.level_yr2,
            skills=["Python", "Django", "PostgreSQL"],
            interests="AI, Open Source, Distributed Systems",
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            profile_privacy=PrivacyLevel.PUBLIC,
            email="kelvin@pwaninet.local",
        )

        self.target_private = User.objects.create_user(
            username="target_private",
            profile_privacy=PrivacyLevel.PRIVATE,
            email="private@pwaninet.local",
        )

        self.target_followers = User.objects.create_user(
            username="target_followers",
            profile_privacy=PrivacyLevel.FOLLOWERS,
            email="followers@pwaninet.local",
        )
        Follow.objects.create(follower=self.follower, followed=self.target_followers)

        self.target_blocked = User.objects.create_user(
            username="target_blocked",
            profile_privacy=PrivacyLevel.PUBLIC,
            email="blocked@pwaninet.local",
        )
        # Block: viewer blocked target_blocked
        Block.objects.create(blocker=self.viewer, blocked=self.target_blocked)

        self.tool = UserProfileTool()

    def test_public_user_returns_rich_metadata_without_email(self):
        result = self.tool.execute(user=self.viewer, username="target_public")
        self.assertTrue(result.success)
        data = result.data

        self.assertEqual(data["username"], "target_public")
        self.assertEqual(data["display_name"], "Kelvin Kiprop")
        self.assertEqual(data["programme_name"], "Bachelor of Science in Computer Science")
        self.assertEqual(data["academic_level"], "Year 2")
        self.assertEqual(data["skills"], ["Python", "Django", "PostgreSQL"])
        self.assertEqual(data["interests"], "AI, Open Source, Distributed Systems")
        self.assertEqual(data["matched_interests"], ["AI", "Open Source", "Distributed Systems"])
        self.assertEqual(data["collaboration_status"], "open_to_projects")
        self.assertTrue(data["profile_url"].endswith("/users/user/target_public/"))
        # Security invariant: email must NOT be returned to other viewers
        self.assertNotIn("email", data)

    def test_email_returned_only_to_self_and_staff(self):
        # 1. Viewing own profile
        res_self = self.tool.execute(user=self.target_public, username="target_public")
        self.assertIn("email", res_self.data)
        self.assertEqual(res_self.data["email"], "kelvin@pwaninet.local")

        # 2. Staff viewing profile
        res_staff = self.tool.execute(user=self.staff_user, username="target_public")
        self.assertIn("email", res_staff.data)

        # 3. Regular viewer does not see email
        res_other = self.tool.execute(user=self.viewer, username="target_public")
        self.assertNotIn("email", res_other.data)

    def test_private_profile_denied_for_other_users(self):
        with self.assertRaises(ToolPermissionError) as ctx:
            self.tool.execute(user=self.viewer, username="target_private")
        self.assertIn("private", str(ctx.exception).lower())

        # Accessible by self
        res_self = self.tool.execute(user=self.target_private, username="target_private")
        self.assertTrue(res_self.success)

    def test_followers_profile_denied_for_non_follower(self):
        # Non-follower denied
        with self.assertRaises(ToolPermissionError):
            self.tool.execute(user=self.viewer, username="target_followers")

        # Follower allowed
        res_follower = self.tool.execute(user=self.follower, username="target_followers")
        self.assertTrue(res_follower.success)

    def test_bidirectional_block_denies_profile_access(self):
        # 1. Viewer blocked target
        with self.assertRaises(ToolPermissionError) as ctx:
            self.tool.execute(user=self.viewer, username="target_blocked")
        self.assertIn("not accessible", str(ctx.exception).lower())

        # 2. Target blocked viewer
        target_reverse_blocked = User.objects.create_user(
            username="target_rev_block",
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        Block.objects.create(blocker=target_reverse_blocked, blocked=self.viewer)
        with self.assertRaises(ToolPermissionError) as ctx:
            self.tool.execute(user=self.viewer, username="target_rev_block")
        self.assertIn("not accessible", str(ctx.exception).lower())


class OtherUserAdapterAndOrchestrationTestCase(TestCase):
    """Test Tool Context Adapter and Orchestration integration for other-user profiles."""

    def setUp(self):
        self.faculty = Faculty.objects.create(code="FSCI", name="Faculty of Science")
        self.school = School.objects.create(code="COMP", name="School of Computing", faculty=self.faculty)
        self.dept = Department.objects.create(name="Department of Computing", code="COMP", school=self.school)
        self.level_yr3, _ = AcademicLevel.objects.get_or_create(level=3, defaults={"name": "Year 3"})
        self.prog = Programme.objects.create(
            name="Bachelor of Science in Computer Science",
            code="BSC-CS",
            department=self.dept,
            degree_type="Bachelor",
            duration_years=4,
        )

        self.viewer = User.objects.create_user(username="test_viewer", password="password123")
        self.target = User.objects.create_user(
            username="target_student",
            first_name="Jane",
            last_name="Doe",
            headline="Data Science Enthusiast",
            bio="Passionate about machine learning and NLP.",
            programme=self.prog,
            academic_level=self.level_yr3,
            skills=["Python", "TensorFlow", "Pandas"],
            interests="Machine Learning, Data Science, Kaggle",
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            profile_privacy=PrivacyLevel.PUBLIC,
            email="jane@pwaninet.local",
        )

        self.tool = UserProfileTool()

    def test_adapter_includes_interests_collaboration_and_academic_level(self):
        tool_res = self.tool.execute(user=self.viewer, username="target_student")
        items = tool_result_to_context_items("user_profile", tool_res)

        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source, "user")
        self.assertEqual(item.citation, "[@target_student]")
        self.assertTrue(item.url.endswith("/users/user/target_student/"))

        # Verify all rich fields are present in prompt context body
        self.assertIn("Jane Doe (@target_student)", item.content)
        self.assertIn("Bachelor of Science in Computer Science", item.content)
        self.assertIn("Academic Level: Year 3", item.content)
        self.assertIn("Interests: Machine Learning, Data Science, Kaggle", item.content)
        self.assertIn("Collaboration Status: open_to_projects", item.content)
        self.assertIn("Skills: Python, TensorFlow, Pandas", item.content)
        # Email must NOT be in the body
        self.assertNotIn("jane@pwaninet.local", item.content)

    def test_orchestrator_returns_single_person_card_when_user_profile_succeeds(self):
        # Configure MockLLMProvider in AIGateway
        mock_provider = MockLLMProvider(
            default_response_text="@target_student (Jane Doe) is a Year 3 Computer Science student. [@target_student]"
        )
        router = LLMRouter(default_provider="mock", providers={"mock": mock_provider})
        gateway = AIGateway(router=router)

        orchestrator = PwanimateOrchestrator(gateway=gateway)

        req = OrchestrationRequest(
            user=self.viewer,
            query="What does @target_student study?",
            provider="mock",
            model="mock-model",
        )
        resp = orchestrator.run(req)

        self.assertEqual(resp.metadata.get("tool_name"), "user_profile")
        self.assertEqual(len(resp.people), 1)
        person_card = resp.people[0]
        self.assertEqual(person_card["username"], "target_student")
        self.assertEqual(person_card["display_name"], "Jane Doe")
        self.assertEqual(person_card["programme_name"], "Bachelor of Science in Computer Science")
        self.assertEqual(person_card["academic_level"], "Year 3")
        self.assertEqual(person_card["collaboration_status"], "open_to_projects")
        self.assertEqual(person_card["matched_skills"], ["Python", "TensorFlow", "Pandas"])
        self.assertEqual(person_card["matched_interests"], ["Machine Learning", "Data Science", "Kaggle"])
        self.assertTrue(person_card["profile_url"].endswith("/users/user/target_student/"))

        # Verify person source summary
        self.assertTrue(any("person" in s and s["person"]["username"] == "target_student" for s in resp.sources))
