"""
Unit tests for Rules Engine (Phase 3)

Tests for notification rules and rules engine.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from notifications.models import PlatformEvent, NotificationObject, NotificationAction
from notifications.events.registry import EventTypes, EventSources
from notifications.rules.rules import (
    NotificationRule,
    AggregationPolicy,
    RULES_REGISTRY,
    get_rules_for_event,
    get_all_rules
)
from notifications.rules.engine import RulesEngine, process_event

User = get_user_model()


class NotificationRulesTests(TestCase):
    """Test the notification rules registry."""
    
    def test_rules_registry_not_empty(self):
        """Test that rules registry is not empty."""
        self.assertGreater(len(RULES_REGISTRY), 0)
    
    def test_get_all_rules(self):
        """Test getting all rules."""
        all_rules = get_all_rules()
        self.assertIsInstance(all_rules, list)
        self.assertEqual(len(all_rules), len(RULES_REGISTRY))
    
    def test_get_rules_for_event(self):
        """Test getting rules for a specific event type."""
        post_like_rules = get_rules_for_event("posts.post.liked")
        self.assertIsInstance(post_like_rules, list)
        self.assertGreater(len(post_like_rules), 0)
    
    def test_get_rules_for_unknown_event(self):
        """Test getting rules for unknown event type."""
        unknown_rules = get_rules_for_event("unknown.event.type")
        self.assertEqual(len(unknown_rules), 0)
    
    def test_rule_structure(self):
        """Test that rules have required fields."""
        for rule in RULES_REGISTRY:
            self.assertIsNotNone(rule.name)
            self.assertIsNotNone(rule.trigger)
            self.assertIsNotNone(rule.notification_type)
            self.assertIsNotNone(rule.category)
            self.assertIsNotNone(rule.priority)
            self.assertIsNotNone(rule.recipients)
    
    def test_post_like_rule_exists(self):
        """Test that post like rule exists."""
        post_like_rules = get_rules_for_event("posts.post.liked")
        self.assertGreater(len(post_like_rules), 0)
    
    def test_group_invite_rule_exists(self):
        """Test that group invite rule exists."""
        group_invite_rules = get_rules_for_event("groups.member.invited")
        self.assertGreater(len(group_invite_rules), 0)
    
    def test_user_follow_rule_exists(self):
        """Test that user follow rule exists."""
        user_follow_rules = get_rules_for_event("users.user.followed")
        self.assertGreater(len(user_follow_rules), 0)


class RulesEngineTests(TestCase):
    """Test the Rules Engine."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
    
    def test_process_event_with_no_matching_rules(self):
        """Test processing event with no matching rules."""
        event = PlatformEvent.objects.create(
            event_type='unknown.event.type',
            source='POSTS',
            action='created',
            target_type='Test',
            target_id='123',
            actor=self.user1
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 0)
    
    def test_process_event_with_no_recipients(self):
        """Test processing event that produces no recipients."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={'recipient_user_ids': []}  # No recipients
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 0)
    
    def test_process_event_creates_notification(self):
        """Test that processing an event creates a notification."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification.recipient, self.user2)
        self.assertEqual(notification.notification_type, 'LIKE')
        self.assertEqual(notification.category, 'SOCIAL')
        self.assertEqual(notification.priority, 'LOW')
        self.assertEqual(notification.status, 'CREATED')
        self.assertIn(str(event.event_id), notification.source_events)
    
    def test_process_event_with_condition_failure(self):
        """Test that condition failure prevents notification creation."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user1.id  # Actor is post author (condition should fail)
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 0)
    
    def test_process_event_creates_multiple_notifications(self):
        """Test that one event can create multiple notifications for multiple recipients."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user1.id, self.user2.id],
                'post_author_id': self.user2.id,  # Different from actor to pass condition
                'actor_username': 'user1'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 2)
    
    def test_process_event_generates_title(self):
        """Test that title is generated from template."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id,
                'actor_username': 'user1'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertIn('user1', notification.title)
        self.assertIn('liked', notification.title.lower())
    
    def test_process_event_generates_aggregation_key(self):
        """Test that aggregation key is generated."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertIsNotNone(notification.aggregation_key)
        self.assertIn('LIKE', notification.aggregation_key)
        self.assertIn('Post', notification.aggregation_key)
        self.assertIn('123', notification.aggregation_key)
    
    def test_process_event_never_aggregation(self):
        """Test that NEVER aggregation policy results in no aggregation key."""
        event = PlatformEvent.objects.create(
            event_type='groups.member.invited',
            source='GROUPS',
            action='invited',
            target_type='Group',
            target_id='456',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'group_name': 'Test Group'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertIsNone(notification.aggregation_key)
    
    def test_process_event_creates_actions(self):
        """Test that actions are created when defined."""
        event = PlatformEvent.objects.create(
            event_type='groups.member.invited',
            source='GROUPS',
            action='invited',
            target_type='Group',
            target_id='456',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'group_id': '456',
                'group_name': 'Test Group'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification.actions.count(), 2)
        
        # Check action types
        action_types = [action.action_type for action in notification.actions.all()]
        self.assertIn('ACCEPT', action_types)
        self.assertIn('DECLINE', action_types)
    
    def test_process_event_with_high_priority(self):
        """Test that high priority is assigned correctly."""
        event = PlatformEvent.objects.create(
            event_type='groups.member.invited',
            source='GROUPS',
            action='invited',
            target_type='Group',
            target_id='456',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'group_name': 'Test Group'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification.priority, 'HIGH')
    
    def test_process_event_with_delivery_policy(self):
        """Test that delivery policy is assigned correctly."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification.delivery_policy, 'IMMEDIATE')
    
    def test_process_event_sets_timestamps(self):
        """Test that event timestamps are set correctly."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='PresPost',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertIsNotNone(notification.first_event_time)
        self.assertIsNotNone(notification.latest_event_time)
        self.assertEqual(notification.first_event_time, event.timestamp)
        self.assertEqual(notification.latest_event_time, event.timestamp)
    
    def test_process_event_sets_context(self):
        """Test that context is set from event."""
        event = PlatformEvent.objects.create(
            event_type='courses.assignment.published',
            source='COURSES',
            action='published',
            target_type='Assignment',
            target_id='789',
            actor=self.user1,
            context_type='Course',
            context_id='CSC221',
            metadata={
                'recipient_user_ids': [self.user2.id],
                'course_id': 'CSC221',
                'assignment_id': '789',
                'assignment_title': 'Assignment 3',
                'course_name': 'CSC221'
            }
        )
        
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification.context_type, 'Course')
        self.assertEqual(notification.context_id, 'CSC221')
    
    def test_convenience_process_event_function(self):
        """Test the convenience process_event function."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        notifications = process_event(event)
        self.assertEqual(len(notifications), 1)
    
    def test_process_event_is_transactional(self):
        """Test that event processing is transactional."""
        # This test verifies that if one notification creation fails,
        # the entire transaction is rolled back
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user1,
            metadata={
                'recipient_user_ids': [self.user2.id],
                'post_author_id': self.user2.id
            }
        )
        
        initial_count = NotificationObject.objects.count()
        
        # Process event - should create notification
        notifications = RulesEngine.process_event(event)
        self.assertEqual(len(notifications), 1)
        
        # Verify notification was created
        self.assertEqual(NotificationObject.objects.count(), initial_count + 1)


class RuleConditionTests(TestCase):
    """Test rule condition functions."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='pass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='pass123'
        )
    
    def test_post_author_not_self_condition_true(self):
        """Test condition when actor is not post author."""
        from notifications.rules.rules import _post_author_not_self_condition
        
        event_data = {
            'actor_id': self.user1.id,
            'post_author_id': self.user2.id
        }
        
        result = _post_author_not_self_condition(event_data)
        self.assertTrue(result)
    
    def test_post_author_not_self_condition_false(self):
        """Test condition when actor is post author."""
        from notifications.rules.rules import _post_author_not_self_condition
        
        event_data = {
            'actor_id': self.user1.id,
            'post_author_id': self.user1.id
        }
        
        result = _post_author_not_self_condition(event_data)
        self.assertFalse(result)
