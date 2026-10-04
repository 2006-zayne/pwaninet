from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from courses.models import Course, Year

User = get_user_model()


class DjangoAdminLinkTests(TestCase):
    """Test cases for Django Admin links inside PwaniNet UI"""

    def setUp(self):
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)

        self.staff_user = User.objects.create_user(
            username='staffadmin',
            email='staff@example.com',
            course=self.course,
            year=self.year,
            password='Password123!',
            is_staff=True,
            is_superuser=True,
            has_completed_onboarding=True,
        )

        self.regular_user = User.objects.create_user(
            username='regularstudent',
            email='student@example.com',
            course=self.course,
            year=self.year,
            password='Password123!',
            is_staff=False,
            has_completed_onboarding=True,
        )

        self.staff_client = Client()
        self.staff_client.force_login(self.staff_user)

        self.regular_client = Client()
        self.regular_client.force_login(self.regular_user)

    def test_settings_page_has_django_admin_for_staff(self):
        """Staff users should see Django Admin link in settings"""
        response = self.staff_client.get(reverse('users:settings'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('/admin/', content)
        self.assertIn('Django Admin', content)
        self.assertIn('data-bypass-htmx="true"', content)

    def test_settings_page_hides_django_admin_for_regular_user(self):
        """Regular users should not see Django Admin link in settings"""
        response = self.regular_client.get(reverse('users:settings'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('Django Admin', content)

    def test_profile_page_has_django_admin_for_staff(self):
        """Staff user viewing own profile should see DJANGO ADMIN button"""
        response = self.staff_client.get(reverse('users:profile', args=[self.staff_user.username]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('DJANGO ADMIN', content)
        self.assertIn('/admin/', content)
        self.assertIn('data-bypass-htmx="true"', content)

    def test_profile_page_hides_django_admin_for_regular_user(self):
        """Regular user viewing own profile should not see DJANGO ADMIN button"""
        response = self.regular_client.get(reverse('users:profile', args=[self.regular_user.username]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('DJANGO ADMIN', content)

    def test_admin_dashboard_has_django_admin_button(self):
        """Admin dashboard should have a Django Admin button in header"""
        response = self.staff_client.get(reverse('admin_dashboard:dashboard_home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Django Admin', content)
        self.assertIn('/admin/', content)
        self.assertIn('data-bypass-htmx="true"', content)

    def test_top_nav_and_left_rail_have_django_admin_for_staff(self):
        """Top navigation and desktop left rail should contain Django Admin links for staff"""
        response = self.staff_client.get(reverse('posts:home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('/admin/', content)
        self.assertIn('Django Admin', content)

    def test_django_admin_base_template_has_return_to_pwaninet_link(self):
        """Django admin site should render PwaniNet branding and Return to PwaniNet link"""
        response = self.staff_client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('PWANI', content)
        self.assertIn('NET', content)
        self.assertIn('Return to PwaniNet App', content)
        self.assertIn('Admin Dashboard', content)
