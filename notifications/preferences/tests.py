"""
Unit tests for Preference Engine (Phase 4)

Tests for notification preferences and preference engine.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import time, datetime, timedelta
from notifications.models import NotificationObject, NotificationPreference
from notifications.preferences.engine import PreferenceEngine, evaluate_notification

User = get_user_model()


class NotificationPreferenceTests(TestCase):
    """Test the NotificationPreference model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_preference(self):
        """Test creating a notification preference."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            email_enabled=True,
            push_enabled=False,
            in_app_enabled=True
        )
        
        self.assertEqual(pref.user, self.user)
        self.assertTrue(pref.email_enabled)
        self.assertFalse(pref.push_enabled)
        self.assertTrue(pref.in_app_enabled)
    
    def test_preference_str_representation(self):
        """Test preference string representation."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            email_enabled=True
        )
        
        str_repr = str(pref)
        self.assertIn('testuser', str_repr)
    
    def test_type_preferences(self):
        """Test type-specific preferences."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            type_preferences={
                'SOCIAL_LIKE': {'email': True, 'push': True, 'in_app': True}
            }
        )
        
        self.assertEqual(pref.get_type_preference('SOCIAL_LIKE', 'email'), True)
        self.assertEqual(pref.get_type_preference('SOCIAL_LIKE', 'push'), True)
    
    def test_quiet_hours(self):
        """Test quiet hours property."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            quiet_hours_enabled=True,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0)
        )
        
        self.assertIsNotNone(pref.quiet_hours_start)
        self.assertIsNotNone(pref.quiet_hours_end)


class PreferenceEngineTests(TestCase):
    """Test the Preference Engine."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification'
        )
    
    def test_evaluate_notification_no_preferences(self):
        """Test evaluation with no user preferences (use defaults)."""
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        # Default: all channels allowed
        self.assertTrue(allowed)
        self.assertIn('IN_APP', channels)
    
    def test_evaluate_notification_with_preference(self):
        """Test evaluation with user preference."""
        NotificationPreference.objects.create(
            user=self.user,
            in_app_enabled=True,
            push_enabled=False,
            email_enabled=False
        )
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        self.assertTrue(allowed)
        self.assertIn('IN_APP', channels)
        self.assertNotIn('PUSH', channels)
        self.assertNotIn('EMAIL', channels)
    
    def test_evaluate_notification_with_type_preference(self):
        """Test evaluation with type-specific preference."""
        pref = NotificationPreference.objects.create(
            user=self.user,
            in_app_enabled=False,
            push_enabled=False,
            email_enabled=False
        )
        
        # Set type-specific preference to enable LIKE notifications
        pref.set_type_preference('SOCIAL_LIKE', 'in_app', True)
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        self.assertTrue(allowed)
        self.assertIn('IN_APP', channels)
    
    def test_mandatory_notification_security_category(self):
        """Test that SECURITY category notifications are mandatory."""
        self.notification.category = 'SECURITY'
        self.notification.save()
        
        # Create preference to disable all notifications
        NotificationPreference.objects.create(
            user=self.user,
            in_app_enabled=False,
            push_enabled=False,
            email_enabled=False
        )
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        # Mandatory notifications bypass preferences
        self.assertTrue(allowed)
        self.assertEqual(channels, ['IN_APP', 'PUSH', 'EMAIL'])
    
    def test_mandatory_notification_critical_priority(self):
        """Test that CRITICAL priority notifications are mandatory."""
        self.notification.priority = 'CRITICAL'
        self.notification.save()
        
        # Create preference to disable all notifications
        NotificationPreference.objects.create(
            user=self.user,
            in_app_enabled=False,
            push_enabled=False,
            email_enabled=False
        )
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        # Mandatory notifications bypass preferences
        self.assertTrue(allowed)
        self.assertEqual(channels, ['IN_APP', 'PUSH', 'EMAIL'])
    
    def test_do_not_disturb(self):
        """Test do not disturb functionality."""
        NotificationPreference.objects.create(
            user=self.user,
            do_not_disturb_until=timezone.now() + timedelta(hours=1)
        )
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        self.assertFalse(allowed)
    
    def test_do_not_disturb_expired(self):
        """Test that expired do not disturb doesn't block."""
        NotificationPreference.objects.create(
            user=self.user,
            do_not_disturb_until=timezone.now() - timedelta(hours=1)
        )
        
        allowed, channels = PreferenceEngine.evaluate_notification(self.notification, 'IN_APP')
        
        self.assertTrue(allowed)
    
    def test_convenience_evaluate_notification_function(self):
        """Test the convenience evaluate_notification function."""
        allowed, channels = evaluate_notification(self.notification, 'IN_APP')
        
        self.assertIsInstance(allowed, bool)
        self.assertIsInstance(channels, list)


class DefaultPreferencesTests(TestCase):
    """Test default preference creation."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_default_preferences(self):
        """Test creating default preferences for a new user."""
        PreferenceEngine.create_default_preferences(self.user)
        
        preferences = NotificationPreference.objects.filter(user=self.user)
        
        # Should have 1 preference (OneToOne)
        self.assertEqual(preferences.count(), 1)
        
        pref = preferences.first()
        self.assertTrue(pref.in_app_enabled)
        self.assertFalse(pref.push_enabled)
        self.assertTrue(pref.email_enabled)
