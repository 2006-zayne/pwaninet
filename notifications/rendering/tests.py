"""
Tests for Notification Rendering System
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import NotificationObject
from notifications.rendering import (
    get_payload_adapter,
    render_notification,
    render_notification_list
)
from notifications.rendering.profile_registry import profile_registry

User = get_user_model()


class NotificationRegistryTests(TestCase):
    """Tests for the notification renderer registry."""
    
    def test_registry_has_all_legacy_types(self):
        """Test that all legacy notification types are registered."""
        legacy_types = [
            'POST_LIKE', 'POST_COMMENT', 'POST_MENTION', 'FOLLOW', 'POST_SHARE',
            'GROUP_JOIN_REQUEST', 'GROUP_JOIN_APPROVED', 'GROUP_JOIN_REJECTED',
            'GROUP_INVITE', 'DOCUMENT_SHARED', 'SYSTEM_ALERT'
        ]
        
        for notification_type in legacy_types:
            profile = profile_registry.get_profile(notification_type)
            self.assertIsNotNone(profile, f"No profile registered for {notification_type}")
    
    def test_registry_has_profiles(self):
        """Test that rendering profiles are registered."""
        self.assertIsNotNone(profile_registry.get_profile('POST_LIKE'))
        self.assertIsNotNone(profile_registry.get_profile('FOLLOW'))
        self.assertIsNotNone(profile_registry.get_profile('GROUP_INVITE'))
    
    def test_get_profile(self):
        """Test getting a profile by type."""
        profile = profile_registry.get_profile('POST_LIKE')
        self.assertIsNotNone(profile)
        self.assertEqual(profile.id, 'POST_LIKE')


class PayloadAdapterTests(TestCase):
    """Tests for payload adapters."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com')
    
    def test_notification_object_adapter_returns_standard_payload(self):
        """Test that NotificationObject adapter returns standard payload structure."""
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='LIKE',
            title='liked your post',
            status='CREATED',
            priority='NORMAL'
        )
        
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        # Verify standard payload structure
        self.assertIn('id', payload)
        self.assertIn('type', payload)
        self.assertIn('created_at', payload)
        self.assertIn('read', payload)
        self.assertIn('priority', payload)
        self.assertIn('actor', payload)
        self.assertIn('content', payload)
        self.assertIn('metadata', payload)
        self.assertIn('status', payload)
        self.assertIn('rendering_hints', payload)
    
    def test_notification_object_adapter_actor_resolution(self):
        """Test that NotificationObject adapter resolves actor correctly."""
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='FOLLOW',
            title='started following you',
            status='CREATED',
            priority='NORMAL',
            metadata={'actor_id': str(self.user2.id), 'actor_username': 'user2'}
        )
        
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        self.assertIsNotNone(payload['actor'])
        self.assertEqual(payload['actor']['id'], str(self.user2.id))
        self.assertEqual(payload['actor']['username'], 'user2')
    
    def test_notification_object_adapter_priority_mapping(self):
        """Test that NotificationObject adapter uses priority from model."""
        # High priority types
        invite = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='INVITE',
            title='invited you',
            status='CREATED',
            priority='HIGH'
        )
        adapter = get_payload_adapter(invite)
        payload = adapter.to_standard_payload(invite)
        self.assertEqual(payload['priority'], 'HIGH')
        
        # Low priority types
        like = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='LIKE',
            title='liked your post',
            status='CREATED',
            priority='LOW'
        )
        adapter = get_payload_adapter(like)
        payload = adapter.to_standard_payload(like)
        self.assertEqual(payload['priority'], 'LOW')


class RenderingServiceTests(TestCase):
    """Tests for the notification rendering service."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com')
    
    def test_render_notification_returns_html(self):
        """Test that render_notification returns HTML string."""
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='LIKE',
            title='liked your post',
            status='CREATED',
            priority='NORMAL',
            metadata={'actor_id': str(self.user2.id), 'actor_username': 'user2'}
        )
        
        html = render_notification(notification)
        
        self.assertIsInstance(html, str)
        self.assertIn('notification-', html)
    
    def test_render_notification_list_returns_html(self):
        """Test that render_notification_list returns HTML string."""
        notifications = [
            NotificationObject.objects.create(
                recipient=self.user1,
                notification_type='LIKE',
                title='liked your post',
                status='CREATED',
                priority='NORMAL',
                metadata={'actor_id': str(self.user2.id), 'actor_username': 'user2'}
            ),
            NotificationObject.objects.create(
                recipient=self.user1,
                notification_type='FOLLOW',
                title='started following you',
                status='CREATED',
                priority='NORMAL',
                metadata={'actor_id': str(self.user2.id), 'actor_username': 'user2'}
            )
        ]
        
        html = render_notification_list(notifications)
        
        self.assertIsInstance(html, str)
        self.assertIn('notification-', html)
    
    def test_render_notification_includes_context(self):
        """Test that rendered notification includes context data."""
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='LIKE',
            title='liked your post',
            status='CREATED',
            priority='NORMAL',
            metadata={'actor_id': str(self.user2.id)}
        )
        
        html = render_notification(notification)
        
        # Should include notification ID
        self.assertIn('notification-', html)
        # Should include notification type
        self.assertIn('LIKE', html)


class RendererTests(TestCase):
    """Tests for individual notification renderers."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(username='user1', email='user1@test.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@test.com')
