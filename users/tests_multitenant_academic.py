from django.test import TestCase, Client
from django.urls import reverse
from users.models import User
from documents.academic.models import Institution, Faculty, School, Department, Programme, AcademicLevel
from users.forms import AcademicProfileUpdateForm


class MultiTenantAcademicTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Institution 1: Pwani University
        self.pu = Institution.objects.create(
            name="Pwani University",
            short_name="PU",
            slug="pwani-university",
            country="Kenya",
            city="Kilifi",
            is_active=True
        )
        self.pu_faculty = Faculty.objects.create(
            institution=self.pu,
            code="SPAS_FAC",
            name="School of Pure and Applied Sciences Faculty",
            slug="spas-fac"
        )
        self.pu_school = School.objects.create(
            institution=self.pu,
            faculty=self.pu_faculty,
            code="SPAS",
            name="School of Pure and Applied Sciences",
            slug="spas"
        )
        self.pu_dept = Department.objects.create(
            school=self.pu_school,
            code="COMP",
            name="Department of Computing",
            slug="dept-comp"
        )
        self.pu_prog = Programme.objects.create(
            department=self.pu_dept,
            code="BSC-CS",
            name="Bachelor of Science in Computer Science",
            slug="bsc-cs",
            degree_type="Bachelor",
            duration_years=4,
            is_active=True
        )

        # Create Institution 2: Kenyatta University (for multi-tenant verification)
        self.ku = Institution.objects.create(
            name="Kenyatta University",
            short_name="KU",
            slug="kenyatta-university",
            country="Kenya",
            city="Nairobi",
            is_active=True
        )
        self.ku_school = School.objects.create(
            institution=self.ku,
            code="KU_SET",
            name="School of Engineering and Technology",
            slug="ku-set"
        )
        self.ku_dept = Department.objects.create(
            school=self.ku_school,
            code="KU_IT",
            name="Department of Information Technology",
            slug="ku-it"
        )
        self.ku_prog = Programme.objects.create(
            department=self.ku_dept,
            code="BSC-IT",
            name="Bachelor of Science in Information Technology",
            slug="bsc-it",
            degree_type="Bachelor",
            duration_years=4,
            is_active=True
        )

        # Academic Levels
        self.level1, _ = AcademicLevel.objects.get_or_create(level=1, name="Year 1")
        self.level4, _ = AcademicLevel.objects.get_or_create(level=4, name="Year 4")

        # Test User
        self.user = User.objects.create_user(
            username="multitenant_student",
            email="student@pu.ac.ke",
            password="TestPassword123!"
        )

    def test_smart_bio_dynamic_resolution(self):
        """Verify user.get_display_bio() synthesizes intelligent strings accurately."""
        # Case 1: Fresh user without academic info
        self.assertEqual(self.user.get_display_bio(), "Scholar on Vasto")

        # Case 2: Institution only
        self.user.institution = self.pu
        self.assertEqual(self.user.get_display_bio(), "Student at Pwani University")

        # Case 3: Institution + Programme
        self.user.programme = self.pu_prog
        self.assertEqual(self.user.get_display_bio(), "Bachelor of Science in Computer Science student at Pwani University")

        # Case 4: Institution + Programme + Level
        self.user.academic_level = self.level4
        self.assertEqual(self.user.get_display_bio(), "Year 4 Bachelor of Science in Computer Science student at Pwani University")

        # Case 5: Custom bio takes priority
        self.user.bio = "Passionate full-stack hacker & cybersecurity nerd"
        self.assertEqual(self.user.get_display_bio(), "Passionate full-stack hacker & cybersecurity nerd")

    def test_multi_tenant_programme_isolation(self):
        """Cross-tenant programmes cannot be saved together."""
        form = AcademicProfileUpdateForm(
            data={
                'institution': self.pu.id,
                'programme': self.ku_prog.id,  # Mismatch: KU programme with PU institution
                'academic_level': self.level1.id,
            },
            user=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertIn('programme', form.errors)

    def test_settings_academic_view_get(self):
        """Verify the settings academic view loads with active institutions."""
        self.client.login(username="multitenant_student", password="TestPassword123!")
        response = self.client.get(reverse('users:settings_academic'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pwani University")
        self.assertContains(response, "Kenyatta University")

    def test_settings_academic_view_post_updates_and_smart_bio(self):
        """Verify updating academic details auto-populates smart bio if empty."""
        self.client.login(username="multitenant_student", password="TestPassword123!")
        response = self.client.post(
            reverse('users:settings_academic'),
            data={
                'institution': self.pu.id,
                'programme': self.pu_prog.id,
                'academic_level': self.level4.id,
                'bio': '',  # Blank: should auto-generate
            }
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.institution, self.pu)
        self.assertEqual(self.user.programme, self.pu_prog)
        self.assertEqual(self.user.academic_level, self.level4)
        self.assertIn("Pwani University", self.user.bio)

    def test_api_user_academic_endpoint(self):
        """Test REST API endpoint for GET and POST/PATCH."""
        self.client.login(username="multitenant_student", password="TestPassword123!")
        
        # GET
        get_res = self.client.get(reverse('users:api_user_academic'))
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertEqual(data['status'], 'success')
        
        # POST update to KU
        post_res = self.client.post(
            reverse('users:api_user_academic'),
            data={
                'institution': self.ku.id,
                'programme': self.ku_prog.id,
                'academic_level': self.level1.id,
                'bio': 'KU Innovator',
            }
        )
        self.assertEqual(post_res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.institution, self.ku)
        self.assertEqual(self.user.programme, self.ku_prog)
        self.assertEqual(self.user.bio, 'KU Innovator')
