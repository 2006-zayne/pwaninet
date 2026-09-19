"""
Unit and Integration Tests for Pwanimate People Discovery.

Validates:
1. Strict privacy boundary enforcement (PRIVATE, FOLLOWERS, blocks, hidden authors,
   author preference 'none', inactive users, and self-exclusion).
2. Grounded candidate discovery across skills, interests, collaboration readiness,
   and academic scope (explicit and relative via UserContext).
3. Zero-hallucination guarantee (returns empty list when no matches exist).
4. Evidence transparency and absence of sensitive attributes.
5. Domain tool execution via ToolRegistry, adapter conversion, and ToolRouter intent matching.
6. Constant query boundedness (O(1) database queries).
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from users.models import (
    PrivacyLevel,
    CollaborationStatus,
    Follow,
    Block,
    HiddenAuthor,
)
from posts.models import AuthorPreference
from documents.academic.models import (
    Faculty,
    School,
    Department,
    Programme,
    AcademicLevel,
)
from pwanimate.context.user_context import UserContext
from pwanimate.people.types import PeopleQuery, PersonResult
from pwanimate.people.service import PeopleDiscoveryService
from pwanimate.tools.domain.people import PeopleDiscoveryTool
from pwanimate.tools.registry import get_default_tool_registry
from pwanimate.tools.router import ToolRouter
from pwanimate.tools.adapter import tool_result_to_context_items

User = get_user_model()


class PeopleDiscoveryTestBase(TestCase):
    """Base setup with academic hierarchy and sample users."""

    def setUp(self):
        # 1. Academic Hierarchy
        self.faculty = Faculty.objects.create(code="FSCI", name="Faculty of Science")
        self.school = School.objects.create(
            code="COMP", name="School of Computing", faculty=self.faculty
        )
        self.dept_cs = Department.objects.create(
            code="CS", name="Department of Computer Science", school=self.school
        )
        self.dept_it = Department.objects.create(
            code="IT", name="Department of Information Tech", school=self.school
        )

        self.programme_cs = Programme.objects.create(
            code="BSCCS",
            name="BSc Computer Science",
            department=self.dept_cs,
            degree_type="Bachelor",
            duration_years=4,
        )
        self.programme_it = Programme.objects.create(
            code="BSCIT",
            name="BSc Information Technology",
            department=self.dept_it,
            degree_type="Bachelor",
            duration_years=4,
        )

        self.level_1 = AcademicLevel.objects.create(level=1, name="Year 1")
        self.level_2 = AcademicLevel.objects.create(level=2, name="Year 2")

        # 2. Reusable Viewer User
        self.viewer = User.objects.create_user(
            username="test_viewer",
            email="viewer@pwani.ac.ke",
            password="ViewerPassword123!",
            first_name="Jane",
            last_name="Viewer",
            programme=self.programme_cs,
            academic_level=self.level_1,
            skills=["Python"],
            interests="Machine Learning",
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        from pwanimate.context.user_context import UserContextService
        self.viewer_context = UserContextService().build(self.viewer)

        self.service = PeopleDiscoveryService()


class PrivacyBoundaryTests(PeopleDiscoveryTestBase):
    """Test suite ensuring strict privacy boundary enforcement."""

    def test_private_profile_excluded(self):
        """Candidates with PrivacyLevel.PRIVATE must never be returned to other users."""
        User.objects.create_user(
            username="secret_coder",
            email="secret@pwani.ac.ke",
            password="SecretPassword123!",
            skills=["Python", "Django"],
            profile_privacy=PrivacyLevel.PRIVATE,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn("secret_coder", usernames)

    def test_followers_only_excluded_when_not_following(self):
        """Candidates with FOLLOWERS privacy are excluded if viewer does not follow them."""
        candidate = User.objects.create_user(
            username="followers_coder",
            email="followers@pwani.ac.ke",
            password="FollowersPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.FOLLOWERS,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(candidate.username, usernames)

    def test_followers_only_included_when_following(self):
        """Candidates with FOLLOWERS privacy are discoverable when viewer follows them."""
        candidate = User.objects.create_user(
            username="followed_coder",
            email="followed@pwani.ac.ke",
            password="FollowedPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.FOLLOWERS,
        )
        Follow.objects.create(follower=self.viewer, followed=candidate)

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertIn(candidate.username, usernames)

    def test_blocked_candidate_excluded(self):
        """Candidates blocked by the viewer are excluded from discovery."""
        blocked_user = User.objects.create_user(
            username="blocked_peer",
            email="blocked@pwani.ac.ke",
            password="BlockedPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        Block.objects.create(blocker=self.viewer, blocked=blocked_user)

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(blocked_user.username, usernames)

    def test_candidate_who_blocked_viewer_excluded(self):
        """Candidates who blocked the viewer are excluded (bidirectional block)."""
        blocker_user = User.objects.create_user(
            username="blocker_peer",
            email="blocker@pwani.ac.ke",
            password="BlockerPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        Block.objects.create(blocker=blocker_user, blocked=self.viewer)

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(blocker_user.username, usernames)

    def test_hidden_author_excluded(self):
        """Candidates hidden by the viewer via HiddenAuthor are excluded."""
        hidden_user = User.objects.create_user(
            username="hidden_peer",
            email="hidden@pwani.ac.ke",
            password="HiddenPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        HiddenAuthor.objects.create(hider=self.viewer, hidden_author=hidden_user)

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(hidden_user.username, usernames)

    def test_author_preference_none_excluded(self):
        """Candidates where viewer set AuthorPreference(preference='none') are excluded."""
        unwanted_user = User.objects.create_user(
            username="unwanted_peer",
            email="unwanted@pwani.ac.ke",
            password="UnwantedPassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        AuthorPreference.objects.create(
            user=self.viewer, author=unwanted_user, preference="none"
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(unwanted_user.username, usernames)

    def test_inactive_user_excluded(self):
        """Inactive accounts (is_active=False) are never returned."""
        inactive_user = User.objects.create_user(
            username="inactive_peer",
            email="inactive@pwani.ac.ke",
            password="InactivePassword123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
            is_active=False,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]
        self.assertNotIn(inactive_user.username, usernames)

    def test_self_excluded(self):
        """The viewer must never be returned in their own discovery queries."""
        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        user_ids = [r.user_id for r in results]
        self.assertNotIn(self.viewer.id, user_ids)

    def test_unauthenticated_viewer_sees_only_public(self):
        """Anonymous viewers can only see PrivacyLevel.PUBLIC users."""
        User.objects.create_user(
            username="auth_only_peer",
            email="auth_only@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.AUTHENTICATED,
        )
        public_user = User.objects.create_user(
            username="public_peer",
            email="public@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=None)
        usernames = [r.username for r in results]
        self.assertIn(public_user.username, usernames)
        self.assertNotIn("auth_only_peer", usernames)


class MatchingAndDiscoveryTests(PeopleDiscoveryTestBase):
    """Test suite validating query filtering across skills, interests, status, and scope."""

    def test_explicit_skill_matching(self):
        """Candidates with matching skills in their JSONField list are discovered."""
        py_dev = User.objects.create_user(
            username="py_dev",
            email="py@pwani.ac.ke",
            password="Password123!",
            skills=["Python", "Django", "FastAPI"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        js_dev = User.objects.create_user(
            username="js_dev",
            email="js@pwani.ac.ke",
            password="Password123!",
            skills=["React", "TypeScript"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Django"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]

        self.assertIn(py_dev.username, usernames)
        self.assertNotIn(js_dev.username, usernames)

    def test_explicit_interest_matching(self):
        """Candidates with matching interests in their TextField are discovered."""
        ai_enthusiast = User.objects.create_user(
            username="ai_dev",
            email="ai@pwani.ac.ke",
            password="Password123!",
            interests="Artificial Intelligence, Robotics, Computer Vision",
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        history_fan = User.objects.create_user(
            username="history_dev",
            email="history@pwani.ac.ke",
            password="Password123!",
            interests="Ancient History, Literature",
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_interests=["Robotics"])
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]

        self.assertIn(ai_enthusiast.username, usernames)
        self.assertNotIn(history_fan.username, usernames)

    def test_collaboration_status_filtering(self):
        """Filtering by collaboration status matches available peers."""
        proj_peer = User.objects.create_user(
            username="proj_peer",
            email="proj@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        busy_peer = User.objects.create_user(
            username="busy_peer",
            email="busy@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            collaboration_status=CollaborationStatus.NOT_LOOKING,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(
            target_skills=["Python"],
            required_collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
        )
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]

        self.assertIn(proj_peer.username, usernames)
        self.assertNotIn(busy_peer.username, usernames)

    def test_academic_scope_filtering_explicit(self):
        """Filtering by statutory programme code or name constrains results."""
        cs_peer = User.objects.create_user(
            username="cs_peer",
            email="cs@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_cs,
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        it_peer = User.objects.create_user(
            username="it_peer",
            email="it@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_it,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Python"], academic_scope="BSCCS")
        results = self.service.discover(query, viewer=self.viewer)
        usernames = [r.username for r in results]

        self.assertIn(cs_peer.username, usernames)
        self.assertNotIn(it_peer.username, usernames)

    def test_academic_scope_relative_via_user_context(self):
        """Relative scope 'my_programme' resolves viewer's programme via UserContext."""
        same_prog_peer = User.objects.create_user(
            username="same_prog_peer",
            email="same_prog@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_cs,
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        diff_prog_peer = User.objects.create_user(
            username="diff_prog_peer",
            email="diff_prog@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_it,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Python"], academic_scope="my_programme")
        results = self.service.discover(
            query, viewer=self.viewer, viewer_context=self.viewer_context
        )
        usernames = [r.username for r in results]

        self.assertIn(same_prog_peer.username, usernames)
        self.assertNotIn(diff_prog_peer.username, usernames)

    def test_ranking_recommender_scoring(self):
        """Classmates in the same programme and academic level rank higher."""
        classmate = User.objects.create_user(
            username="classmate_rank",
            email="classmate@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_cs,
            academic_level=self.level_1,
            profile_privacy=PrivacyLevel.PUBLIC,
        )
        other_peer = User.objects.create_user(
            username="other_rank",
            email="other@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            programme=self.programme_it,
            academic_level=self.level_2,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)

        self.assertGreaterEqual(len(results), 2)
        # Classmate should be first due to +100pts academic tier score
        self.assertEqual(results[0].username, classmate.username)
        self.assertGreater(results[0].recommendation_score, results[1].recommendation_score)


class EvidenceAndAuthenticityTests(PeopleDiscoveryTestBase):
    """Test suite validating transparency, ground truth, and zero hallucinations."""

    def test_zero_hallucinations_empty_result(self):
        """When no matching users exist in the database, return an empty list."""
        query = PeopleQuery(target_skills=["NonExistentQuantumSkill999"])
        results = self.service.discover(query, viewer=self.viewer)
        self.assertEqual(results, [])

    def test_factual_evidence_integrity(self):
        """Evidence dictionary matches database ground truth attributes."""
        peer = User.objects.create_user(
            username="factual_peer",
            email="factual@pwani.ac.ke",
            password="Password123!",
            first_name="Alice",
            last_name="Smith",
            skills=["Python", "Django", "PostgreSQL"],
            interests="Machine Learning, Data Science",
            collaboration_status=CollaborationStatus.OPEN_TO_PROJECTS,
            programme=self.programme_cs,
            academic_level=self.level_1,
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(
            target_skills=["Python", "Django"], target_interests=["Machine Learning"]
        )
        results = self.service.discover(query, viewer=self.viewer)

        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r.username, "factual_peer")
        self.assertEqual(r.display_name, "Alice Smith")
        self.assertEqual(r.profile_url, "/users/user/factual_peer/")
        self.assertEqual(set(r.matched_skills), {"Python", "Django"})
        self.assertEqual(r.matched_interests, ["Machine Learning"])
        self.assertEqual(r.evidence["collaboration_status"], CollaborationStatus.OPEN_TO_PROJECTS)
        self.assertIn("Classmate", r.evidence["academic_alignment"])

    def test_no_sensitive_fields_in_result(self):
        """PersonResult and to_dict() must never leak email, phone, or password."""
        User.objects.create_user(
            username="privacy_peer",
            email="private_email@pwani.ac.ke",
            password="SuperSecretPassword!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        query = PeopleQuery(target_skills=["Python"])
        results = self.service.discover(query, viewer=self.viewer)
        self.assertEqual(len(results), 1)
        data = results[0].to_dict()

        self.assertNotIn("email", data)
        self.assertNotIn("password", data)
        self.assertNotIn("phone", data)
        self.assertNotIn("token", data)


class DomainToolAndRoutingTests(PeopleDiscoveryTestBase):
    """Test suite validating domain tool execution, router matching, and context adapter."""

    def test_tool_execution_via_registry(self):
        """Execute PeopleDiscoveryTool via ToolRegistry."""
        User.objects.create_user(
            username="tool_peer",
            email="tool@pwani.ac.ke",
            password="Password123!",
            skills=["Rust", "Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        registry = get_default_tool_registry()
        tool = registry.get("people_discovery")
        self.assertIsNotNone(tool)

        result = registry.execute(
            name="people_discovery",
            user=self.viewer,
            user_context=self.viewer_context,
            skills=["Rust"],
        )

        self.assertTrue(result.success)
        self.assertEqual(result.metadata["count"], 1)
        self.assertEqual(result.data[0]["username"], "tool_peer")

    def test_router_matches_skill_query(self):
        """ToolRouter deterministically routes 'Find students interested in Python'."""
        router = ToolRouter()
        route = router.route("Find students interested in Python", user=self.viewer)

        self.assertIsNotNone(route)
        self.assertEqual(route.tool_name, "people_discovery")
        self.assertIn("Python", route.parameters.get("skills", []))
        self.assertEqual(route.matched_intent, "people_skill_discovery")

    def test_router_matches_open_to_projects(self):
        """ToolRouter deterministically routes 'Who is open to working on an AI project?'."""
        router = ToolRouter()
        route = router.route("Who is open to working on an AI project?", user=self.viewer)

        self.assertIsNotNone(route)
        self.assertEqual(route.tool_name, "people_discovery")
        self.assertEqual(route.parameters.get("collaboration_status"), "open_to_projects")
        self.assertIn("AI", route.parameters.get("skills", []))
        self.assertEqual(route.matched_intent, "people_open_to_projects")

    def test_router_matches_academic_and_skill(self):
        """ToolRouter deterministically routes 'Find CS students who know Django'."""
        router = ToolRouter()
        route = router.route("Find CS students who know Django", user=self.viewer)

        self.assertIsNotNone(route)
        self.assertEqual(route.tool_name, "people_discovery")
        self.assertEqual(route.parameters.get("academic_scope"), "CS")
        self.assertIn("Django", route.parameters.get("skills", []))
        self.assertEqual(route.matched_intent, "people_academic_and_skill_discovery")

    def test_router_matches_in_my_programme(self):
        """ToolRouter deterministically routes 'Find people in my programme who are interested in AI'."""
        router = ToolRouter()
        route = router.route(
            "Find people in my programme who are interested in AI", user=self.viewer
        )

        self.assertIsNotNone(route)
        self.assertEqual(route.tool_name, "people_discovery")
        self.assertEqual(route.parameters.get("academic_scope"), "my_programme")
        self.assertIn("AI", route.parameters.get("interests", []))

    def test_context_adapter_generates_grounded_items(self):
        """tool_result_to_context_items creates grounded ContextItem with user source and profile URL."""
        User.objects.create_user(
            username="adapter_peer",
            email="adapter@pwani.ac.ke",
            password="Password123!",
            skills=["Python"],
            profile_privacy=PrivacyLevel.PUBLIC,
        )

        tool = PeopleDiscoveryTool()
        tool_result = tool.execute(user=self.viewer, skills=["Python"])
        items = tool_result_to_context_items("people_discovery", tool_result)

        self.assertGreaterEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item.source, "user")
        self.assertIn("[@adapter_peer]", item.citation)
        self.assertEqual(item.url, "/users/user/adapter_peer/")
        self.assertIn("Peer: adapter_peer", item.content)


class QueryBoundednessTests(PeopleDiscoveryTestBase):
    """Test suite ensuring O(1) query budget without N+1 candidate query loops."""

    def test_constant_query_budget(self):
        """Verify that fetching multiple candidates executes within a small, bounded number of queries."""
        # Create 5 candidates
        for idx in range(5):
            User.objects.create_user(
                username=f"scale_peer_{idx}",
                email=f"scale_{idx}@pwani.ac.ke",
                password="Password123!",
                skills=["Python", f"Skill_{idx}"],
                programme=self.programme_cs,
                academic_level=self.level_1,
                profile_privacy=PrivacyLevel.PUBLIC,
            )

        query = PeopleQuery(target_skills=["Python"], limit=10)

        # Baseline count without preloaded context: exactly 7 bounded queries:
        # - 2 for bidirectional blocks (blocker + blocked)
        # - 1 for hidden authors
        # - 1 for author preference 'none'
        # - 1 for following user IDs (reused across privacy and mutual connections)
        # - 1 for shared approved group memberships
        # - 1 for the main candidate SELECT with all LEFT OUTER JOINs
        with self.assertNumQueries(7):
            results = self.service.discover(query, viewer=self.viewer)
            self.assertEqual(len(results), 5)

        # When viewer_context is provided, following IDs and group IDs are already available:
        with self.assertNumQueries(5):
            results_ctx = self.service.discover(
                query, viewer=self.viewer, viewer_context=self.viewer_context
            )
            self.assertEqual(len(results_ctx), 5)
