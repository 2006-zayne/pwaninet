"""
Unit tests for Notification Models (Phase 2)

Tests for NotificationObject and NotificationAction models.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import NotificationObject, NotificationAction
from notifications.notifications.registry import (
    NotificationTypes,
    NotificationCategories,
    NotificationPriorities,
    NotificationStatuses,
    DeliveryPolicies,
    ActionTypes
)

User = get_user_model()


class NotificationRegistryTests(TestCase):
    """Test the notification registry enums."""
    
    def test_notification_types_enum(self):
        """Test NotificationTypes enum has expected values."""
        self.assertEqual(NotificationTypes.LIKE.value, "LIKE")
        self.assertEqual(NotificationTypes.COMMENT.value, "COMMENT")
        self.assertEqual(NotificationTypes.ASSIGNMENT.value, "ASSIGNMENT")
    
    def test_get_all_types(self):
        """Test getting all notification types."""
        all_types = NotificationTypes.get_all_types()
        self.assertIsInstance(all_types, list)
        self.assertIn("LIKE", all_types)
        self.assertIn("ASSIGNMENT", all_types)
    
    def test_is_valid_type(self):
        """Test notification type validation."""
        self.assertTrue(NotificationTypes.is_valid_type("LIKE"))
        self.assertFalse(NotificationTypes.is_valid_type("INVALID"))
    
    def test_notification_categories_enum(self):
        """Test NotificationCategories enum has expected values."""
        self.assertEqual(NotificationCategories.SOCIAL.value, "SOCIAL")
        self.assertEqual(NotificationCategories.ACADEMIC.value, "ACADEMIC")
    
    def test_get_types_for_category(self):
        """Test getting types for a specific category."""
        social_types = NotificationCategories.get_types_for_category("SOCIAL")
        self.assertIn("LIKE", social_types)
        self.assertIn("COMMENT", social_types)
        self.assertNotIn("ASSIGNMENT", social_types)
    
    def test_notification_priorities_enum(self):
        """Test NotificationPriorities enum has expected values."""
        self.assertEqual(NotificationPriorities.CRITICAL.value, "CRITICAL")
        self.assertEqual(NotificationPriorities.NORMAL.value, "NORMAL")
    
    def test_get_priority_order(self):
        """Test getting numeric priority order."""
        self.assertEqual(NotificationPriorities.get_priority_order("CRITICAL"), 4)
        self.assertEqual(NotificationPriorities.get_priority_order("NORMAL"), 2)
        self.assertEqual(NotificationPriorities.get_priority_order("LOW"), 1)
    
    def test_notification_statuses_enum(self):
        """Test NotificationStatuses enum has expected values."""
        self.assertEqual(NotificationStatuses.CREATED.value, "CREATED")
        self.assertEqual(NotificationStatuses.READ.value, "READ")
    
    def test_is_terminal_status(self):
        """Test terminal status detection."""
        self.assertTrue(NotificationStatuses.is_terminal_status("READ"))
        self.assertTrue(NotificationStatuses.is_terminal_status("ARCHIVED"))
        self.assertFalse(NotificationStatuses.is_terminal_status("DELIVERED"))
    
    def test_delivery_policies_enum(self):
        """Test DeliveryPolicies enum has expected values."""
        self.assertEqual(DeliveryPolicies.IMMEDIATE.value, "IMMEDIATE")
        self.assertEqual(DeliveryPolicies.DIGEST.value, "DIGEST")
    
    def test_action_types_enum(self):
        """Test ActionTypes enum has expected values."""
        self.assertEqual(ActionTypes.ACCEPT.value, "ACCEPT")
        self.assertEqual(ActionTypes.DECLINE.value, "DECLINE")


class NotificationObjectTests(TestCase):
    """Test the NotificationObject model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_notification_object(self):
        """Test creating a notification object."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Your post was liked',
            summary='Brian liked your post'
        )
        
        self.assertIsNotNone(notification.notification_id)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.notification_type, 'LIKE')
        self.assertEqual(notification.category, 'SOCIAL')
        self.assertEqual(notification.priority, 'NORMAL')
        self.assertEqual(notification.title, 'Your post was liked')
        self.assertEqual(notification.status, 'CREATED')
        self.assertEqual(notification.delivery_policy, 'IMMEDIATE')
    
    def test_notification_str_representation(self):
        """Test notification string representation."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification'
        )
        str_repr = str(notification)
        self.assertIn('LIKE', str_repr)
        self.assertIn('testuser', str_repr)
    
    def test_notification_with_source_events(self):
        """Test notification with source events."""
        source_events = ['evt-001', 'evt-002', 'evt-003']
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Your post was liked',
            source_events=source_events
        )
        
        self.assertEqual(notification.source_events, source_events)
        self.assertEqual(notification.event_count, 1)  # Default
    
    def test_notification_with_aggregation_data(self):
        """Test notification with aggregation data."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Your post received likes',
            aggregation_key='like:post:123',
            event_count=5,
            first_event_time='2026-08-03T10:00:00Z',
            latest_event_time='2026-08-03T10:08:00Z'
        )
        
        self.assertEqual(notification.aggregation_key, 'like:post:123')
        self.assertEqual(notification.event_count, 5)
    
    def test_notification_with_context(self):
        """Test notification with context."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='ASSIGNMENT',
            category='ACADEMIC',
            priority='HIGH',
            title='New assignment available',
            context_type='Course',
            context_id='CSC221'
        )
        
        self.assertEqual(notification.context_type, 'Course')
        self.assertEqual(notification.context_id, 'CSC221')
    
    def test_notification_with_expiration(self):
        """Test notification with expiration."""
        from datetime import datetime, timedelta
        
        expires_at = datetime.now() + timedelta(hours=24)
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='MEETING',
            category='ACADEMIC',
            priority='HIGH',
            title='Meeting starting soon',
            expires_at=expires_at
        )
        
        self.assertIsNotNone(notification.expires_at)
    
    def test_notification_with_metadata(self):
        """Test notification with metadata."""
        metadata = {
            'avatar_url': 'https://example.com/avatar.jpg',
            'deep_link': '/posts/123',
            'thumbnail_url': 'https://example.com/thumb.jpg'
        }
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Your post was liked',
            metadata=metadata
        )
        
        self.assertEqual(notification.metadata, metadata)
    
    def test_notification_is_read_property(self):
        """Test is_read property."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            status='CREATED'
        )
        
        self.assertFalse(notification.is_read)
        
        notification.status = 'READ'
        notification.save()
        
        self.assertTrue(notification.is_read)
    
    def test_notification_is_delivered_property(self):
        """Test is_delivered property."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            status='CREATED'
        )
        
        self.assertFalse(notification.is_delivered)
        
        notification.status = 'DELIVERED'
        notification.save()
        
        self.assertTrue(notification.is_delivered)
    
    def test_mark_as_read(self):
        """Test mark_as_read method."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            status='DELIVERED'
        )
        
        notification.mark_as_read()
        
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'READ')
    
    def test_mark_as_delivered(self):
        """Test mark_as_delivered method."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            status='QUEUED'
        )
        
        notification.mark_as_delivered()
        
        notification.refresh_from_db()
        self.assertEqual(notification.status, 'DELIVERED')
    
    def test_notification_ordering(self):
        """Test notifications are ordered by created_at descending."""
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='First notification'
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='Second notification'
        )
        
        from datetime import timedelta
        from django.utils import timezone
        now = timezone.now()
        NotificationObject.objects.filter(pk=notification1.pk).update(
            created_at=now - timedelta(seconds=10),
            updated_at=now - timedelta(seconds=10)
        )
        NotificationObject.objects.filter(pk=notification2.pk).update(
            created_at=now,
            updated_at=now
        )
        
        notifications = list(NotificationObject.objects.all())
        self.assertEqual(notifications[0].notification_id, notification2.notification_id)  # Most recent first
        self.assertEqual(notifications[1].notification_id, notification1.notification_id)
    
    def test_critical_priority_notification(self):
        """Test creating a critical priority notification."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='SECURITY',
            category='SECURITY',
            priority='CRITICAL',
            title='Security alert',
            delivery_policy='IMMEDIATE'
        )
        
        self.assertEqual(notification.priority, 'CRITICAL')
        self.assertEqual(notification.notification_type, 'SECURITY')
    
    def test_digest_delivery_policy(self):
        """Test creating a digest delivery policy notification."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='SYSTEM',
            category='SYSTEM',
            priority='LOW',
            title='Daily digest',
            delivery_policy='DIGEST'
        )
        
        self.assertEqual(notification.delivery_policy, 'DIGEST')


class NotificationActionTests(TestCase):
    """Test the NotificationAction model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='GROUP',
            category='WORKSPACE',
            priority='HIGH',
            title='Group invitation'
        )
    
    def test_create_notification_action(self):
        """Test creating a notification action."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept Invitation',
            url='/groups/123/accept',
            method='POST'
        )
        
        self.assertEqual(action.notification, self.notification)
        self.assertEqual(action.action_type, 'ACCEPT')
        self.assertEqual(action.label, 'Accept Invitation')
        self.assertEqual(action.url, '/groups/123/accept')
        self.assertEqual(action.method, 'POST')
        self.assertFalse(action.is_primary)
    
    def test_action_str_representation(self):
        """Test action string representation."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept Invitation'
        )
        
        str_repr = str(action)
        self.assertIn('Accept Invitation', str_repr)
    
    def test_primary_action(self):
        """Test creating a primary action."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept Invitation',
            is_primary=True,
            order=0
        )
        
        self.assertTrue(action.is_primary)
        self.assertEqual(action.order, 0)
    
    def test_action_with_payload(self):
        """Test action with payload data."""
        payload = {
            'group_id': '123',
            'user_id': str(self.user.id)
        }
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept Invitation',
            url='/groups/accept',
            method='POST',
            payload=payload
        )
        
        self.assertEqual(action.payload, payload)
    
    def test_multiple_actions_for_notification(self):
        """Test creating multiple actions for a notification."""
        accept_action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept',
            order=0
        )
        
        decline_action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='DECLINE',
            label='Decline',
            order=1
        )
        
        self.assertEqual(self.notification.actions.count(), 2)
        actions = list(self.notification.actions.all())
        self.assertEqual(actions[0], accept_action)  # Ordered by order field
        self.assertEqual(actions[1], decline_action)
    
    def test_action_ordering(self):
        """Test actions are ordered by order field."""
        action1 = NotificationAction.objects.create(
            notification=self.notification,
            action_type='VIEW',
            label='View Details',
            order=2
        )
        
        action2 = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept',
            order=0
        )
        
        action3 = NotificationAction.objects.create(
            notification=self.notification,
            action_type='DECLINE',
            label='Decline',
            order=1
        )
        
        actions = list(self.notification.actions.all())
        self.assertEqual(actions[0], action2)
        self.assertEqual(actions[1], action3)
        self.assertEqual(actions[2], action1)
    
    def test_custom_action_type(self):
        """Test creating a custom action type."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='CUSTOM',
            label='Custom Action',
            url='/custom/action'
        )
        
        self.assertEqual(action.action_type, 'CUSTOM')
    
    def test_action_without_url(self):
        """Test action without URL (e.g., mark as read)."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='MARK_READ',
            label='Mark as Read'
        )
        
        self.assertEqual(action.url, '')
    
    def test_action_cascade_delete(self):
        """Test that actions are deleted when notification is deleted."""
        action = NotificationAction.objects.create(
            notification=self.notification,
            action_type='ACCEPT',
            label='Accept'
        )
        
        action_id = action.id
        self.notification.delete()
        
        # Action should be deleted
        self.assertFalse(NotificationAction.objects.filter(id=action_id).exists())
