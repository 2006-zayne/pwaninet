from django.test import TestCase, Client
from django.urls import reverse
from users.models import User, Follow
from groups.models import Group
from documents.academic.models import (
    Faculty, School, Department, Programme, AcademicLevel, AcademicYear, Semester, AcademicUnit, ProgrammeUnit
)
from documents.models import Document, Category, DocumentAcademicUnit
from recommendations.services.user_recommender import get_friend_suggestions_for_user
from recommendations.services.group_recommender import get_recommended_groups_for_user
from recommendations.services.document_recommender import get_for_you_documents


class RecommendationsEngineTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Academic hierarchy fixtures
        self.faculty = Faculty.objects.create(code='SCI', name='Faculty of Science')
        self.school = School.objects.create(code='COMP', name='School of Computing', faculty=self.faculty)
        self.dept_cs = Department.objects.create(code='CS', name='Department of Computer Science', school=self.school)
        self.dept_edu = Department.objects.create(code='EDU', name='Department of Education', school=self.school)

        self.level1 = AcademicLevel.objects.create(level=1, name='Year 1')
        self.level2 = AcademicLevel.objects.create(level=2, name='Year 2')
        self.year = AcademicYear.objects.create(
            code='2025/2026', name='2025/2026', start_date='2025-09-01', end_date='2026-06-30'
        )
        self.sem1 = Semester.objects.create(
            academic_year=self.year, number=1, start_date='2025-09-01', end_date='2025-12-20'
        )

        self.programme_cs = Programme.objects.create(
            code='BSCCS',
            name='BSc. Computer Science',
            department=self.dept_cs,
            degree_type='Bachelor',
            duration_years=4
        )
        self.programme_edu = Programme.objects.create(
            code='BEDSCI',
            name='Bachelor of Education',
            department=self.dept_edu,
            degree_type='Bachelor',
            duration_years=4
        )

        # Create target user
        self.user = User.objects.create_user(
            username='new_student',
            email='new@pwani.ac.ke',
            password='Password123!',
            programme=self.programme_cs,
            academic_level=self.level1,
            semester=self.sem1,
            has_completed_onboarding=False
        )

        # Peer 1: Same programme & level
        self.classmate = User.objects.create_user(
            username='cs_classmate',
            email='classmate@pwani.ac.ke',
            password='Password123!',
            programme=self.programme_cs,
            academic_level=self.level1,
            semester=self.sem1
        )

        # Peer 2: Same programme, different level
        self.senior_cs = User.objects.create_user(
            username='cs_senior',
            email='senior@pwani.ac.ke',
            password='Password123!',
            programme=self.programme_cs,
            academic_level=self.level2,
            semester=self.sem1
        )

        # Peer 3: Different programme
        self.other_student = User.objects.create_user(
            username='edu_student',
            email='edu@pwani.ac.ke',
            password='Password123!',
            programme=self.programme_edu,
            academic_level=self.level1,
            semester=self.sem1
        )

    def test_user_recommender_classmate_prioritization(self):
        suggestions = get_friend_suggestions_for_user(self.user, limit=5, use_cache=False)
        self.assertGreaterEqual(len(suggestions), 2)
        # Classmate in same programme & level should rank first
        self.assertEqual(suggestions[0].id, self.classmate.id)
        self.assertEqual(suggestions[0].recommendation_reason, "Classmate • Same Year")

    def test_user_recommender_excludes_self_and_following(self):
        # Follow the classmate
        Follow.objects.create(follower=self.user, followed=self.classmate)

        suggestions = get_friend_suggestions_for_user(self.user, limit=5, use_cache=False)
        suggested_ids = [u.id for u in suggestions]
        self.assertNotIn(self.user.id, suggested_ids)
        self.assertNotIn(self.classmate.id, suggested_ids)
        # Senior CS is now top candidate
        self.assertEqual(suggestions[0].id, self.senior_cs.id)

    def test_group_recommender_prioritizes_programme_groups(self):
        cs_group = Group.objects.create(
            name='CS Tech Club',
            programme=self.programme_cs,
            academic_level=self.level1
        )
        edu_group = Group.objects.create(
            name='Education Society',
            programme=self.programme_edu,
            academic_level=self.level1
        )

        groups = get_recommended_groups_for_user(self.user, limit=5, use_cache=False)
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual(groups[0].id, cs_group.id)

    def test_group_recommender_cold_start_never_empty(self):
        fresh_user = User.objects.create_user(
            username='freshman',
            email='fresh@pwani.ac.ke',
            password='Password123!'
        )
        Group.objects.create(name='Campus General Forum')
        groups = get_recommended_groups_for_user(fresh_user, limit=5, use_cache=False)
        self.assertGreater(len(groups), 0)

    def test_document_recommender_matches_semester_units(self):
        category = Category.objects.create(name='Lecture Notes', code='lecture_notes')
        unit_intro_cs = AcademicUnit.objects.create(code='CSC101', name='Intro to Computer Science')
        unit_history = AcademicUnit.objects.create(code='HIS101', name='World History')

        # Link unit to programme & level & sem
        ProgrammeUnit.objects.create(
            programme=self.programme_cs,
            academic_unit=unit_intro_cs,
            academic_level=self.level1,
            academic_year=self.year,
            semester=self.sem1
        )

        # Doc 1: Linked to CSC 101
        doc_cs = Document.objects.create(
            title='CSC 101 Lecture Notes',
            category=category,
            uploaded_by=self.classmate,
            status='ready',
            is_available=True,
            visibility='public'
        )
        DocumentAcademicUnit.objects.create(
            document=doc_cs,
            academic_unit=unit_intro_cs,
            academic_level=self.level1,
            academic_year=self.year,
            semester=self.sem1
        )

        # Doc 2: Linked to HIS 101
        doc_his = Document.objects.create(
            title='History Notes',
            category=category,
            uploaded_by=self.other_student,
            status='ready',
            is_available=True,
            visibility='public'
        )
        DocumentAcademicUnit.objects.create(
            document=doc_his,
            academic_unit=unit_history,
            academic_level=self.level1,
            academic_year=self.year,
            semester=self.sem1
        )

        recommended_docs = get_for_you_documents(self.user, limit=5, use_cache=False)
        self.assertGreater(len(recommended_docs), 0)
        self.assertEqual(recommended_docs[0].id, doc_cs.id)
        self.assertEqual(recommended_docs[0].matching_badge, "Matches CSC101")


class OnboardingFlowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.faculty = Faculty.objects.create(code='SCIT', name='Faculty of Science and IT')
        self.school = School.objects.create(code='SIT', name='School of IT', faculty=self.faculty)
        self.dept = Department.objects.create(code='ITD', name='Department of IT', school=self.school)
        self.level = AcademicLevel.objects.create(level=1, name='Year 1')
        self.programme = Programme.objects.create(
            code='BSCIT',
            name='Information Technology',
            department=self.dept,
            degree_type='Bachelor',
            duration_years=4
        )

        self.user = User.objects.create_user(
            username='onboarding_tester',
            email='tester@pwani.ac.ke',
            password='Password123!',
            programme=self.programme,
            academic_level=self.level,
            has_completed_onboarding=False
        )
        self.peer = User.objects.create_user(
            username='it_peer',
            email='peer@pwani.ac.ke',
            password='Password123!',
            programme=self.programme,
            academic_level=self.level
        )

    def test_uncompleted_onboarding_redirects_from_home(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('posts:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:onboarding'), response.url)

    def test_onboarding_wizard_renders_classmates(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:onboarding'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find your classmates & peers')
        self.assertContains(response, 'it_peer')

    def test_batch_follow_and_complete_onboarding(self):
        self.client.force_login(self.user)

        # 1. Batch follow
        response = self.client.post(reverse('users:onboarding_batch_follow'), {'user_ids': [self.peer.id]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Follow.objects.filter(follower=self.user, followed=self.peer).exists())

        # Verify that follow event was published for notifications
        from notifications.models import PlatformEvent
        self.assertTrue(
            PlatformEvent.objects.filter(
                actor=self.user,
                target_id=str(self.peer.id)
            ).exists()
        )

        # 2. Complete onboarding
        response = self.client.get(reverse('users:onboarding_complete'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('posts:home'))

        # Verify user state
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_completed_onboarding)

        # 3. Now visiting home should succeed without redirect
        home_response = self.client.get(reverse('posts:home'))
        self.assertEqual(home_response.status_code, 200)
