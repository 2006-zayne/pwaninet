"""
Unit tests for Event Infrastructure (Phase 1)

Tests for event models, registry, validator, and publisher.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from notifications.models import PlatformEvent, EventArchive
from notifications.events.registry import EventTypes, EventSources, EventActions
from notifications.events.validator import EventValidator
from notifications.events.publisher import EventPublisher, publish_event

User = get_user_model()


class EventRegistryTests(TestCase):
    """Test the event registry enums."""
    
    def test_event_types_enum(self):
        """Test EventTypes enum has expected values."""
        self.assertEqual(EventTypes.POSTS_POST_LIKED.value, "posts.post.liked")
        self.assertEqual(EventTypes.POSTS_COMMENT_CREATED.value, "posts.comment.created")
        self.assertEqual(EventTypes.DOCUMENTS_DOCUMENT_UPLOADED.value, "documents.document.uploaded")
    
    def test_get_all_event_types(self):
        """Test getting all event types."""
        all_types = EventTypes.get_all_event_types()
        self.assertIsInstance(all_types, list)
        self.assertIn("posts.post.liked", all_types)
        self.assertIn("documents.document.uploaded", all_types)
    
    def test_is_valid_event_type(self):
        """Test event type validation."""
        self.assertTrue(EventTypes.is_valid_event_type("posts.post.liked"))
        self.assertFalse(EventTypes.is_valid_event_type("invalid.event.type"))
    
    def test_get_domain_events(self):
        """Test getting events by domain."""
        posts_events = EventTypes.get_domain_events("posts")
        self.assertIn("posts.post.liked", posts_events)
        self.assertIn("posts.comment.created", posts_events)
        self.assertNotIn("documents.document.uploaded", posts_events)
    
    def test_event_sources_enum(self):
        """Test EventSources enum has expected values."""
        self.assertEqual(EventSources.POSTS.value, "POSTS")
        self.assertEqual(EventSources.DOCUMENTS.value, "DOCUMENTS")
    
    def test_is_valid_source(self):
        """Test source validation."""
        self.assertTrue(EventSources.is_valid_source("POSTS"))
        self.assertFalse(EventSources.is_valid_source("INVALID_SOURCE"))
    
    def test_event_actions_enum(self):
        """Test EventActions enum has expected values."""
        self.assertEqual(EventActions.CREATED.value, "created")
        self.assertEqual(EventActions.LIKED.value, "liked")
        self.assertEqual(EventActions.COMPLETED.value, "completed")
    
    def test_is_valid_action(self):
        """Test action validation."""
        self.assertTrue(EventActions.is_valid_action("created"))
        self.assertTrue(EventActions.is_valid_action("liked"))
        self.assertFalse(EventActions.is_valid_action("creating"))  # Not past tense


class EventValidatorTests(TestCase):
    """Test the event validator."""
    
    def test_validate_valid_event_data(self):
        """Test validation of valid event data."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123',
            'actor': None,
            'context_type': None,
            'context_id': None,
            'audience': None,
            'metadata': {}
        }
        # Should not raise
        validated = EventValidator.validate_event_data(event_data)
        self.assertEqual(validated['event_type'], 'posts.post.liked')
    
    def test_validate_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            # Missing action, target_type, target_id
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_invalid_event_type(self):
        """Test validation fails with invalid event type."""
        event_data = {
            'event_type': 'invalid.event.type',
            'source': 'POSTS',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123'
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_invalid_source(self):
        """Test validation fails with invalid source."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'INVALID_SOURCE',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123'
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_invalid_action(self):
        """Test validation fails with invalid action."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'creating',  # Not past tense
            'target_type': 'Post',
            'target_id': '123'
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_event_type_action_mismatch(self):
        """Test validation fails when event type doesn't match action."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'created',  # Mismatch
            'target_type': 'Post',
            'target_id': '123'
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_invalid_metadata(self):
        """Test validation fails with invalid metadata."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123',
            'metadata': "not a dict"
        }
        with self.assertRaises(ValidationError):
            EventValidator.validate_event_data(event_data)
    
    def test_validate_context_consistency(self):
        """Test context type and ID consistency."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123',
            'context_type': 'Group',  # Has type but no ID
            'context_id': None
        }
        # This should pass validation (context is optional)
        validated = EventValidator.validate_event_data(event_data)
        self.assertEqual(validated['context_type'], 'Group')


class EventModelTests(TestCase):
    """Test the PlatformEvent model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_create_platform_event(self):
        """Test creating a platform event."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user,
            metadata={'test': 'data'}
        )
        self.assertIsNotNone(event.event_id)
        self.assertEqual(event.event_type, 'posts.post.liked')
        self.assertEqual(event.source, 'POSTS')
        self.assertEqual(event.action, 'liked')
        self.assertEqual(event.target_type, 'Post')
        self.assertEqual(event.target_id, '123')
        self.assertEqual(event.actor, self.user)
    
    def test_event_str_representation(self):
        """Test event string representation."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        str_repr = str(event)
        self.assertIn('posts.post.liked', str_repr)
        # Actor might be None or show username depending on implementation
        # Just check the event type is present
    
    def test_event_target_property(self):
        """Test event target property."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        self.assertEqual(event.target, 'Post:123')
    
    def test_event_context_property(self):
        """Test event context property."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user,
            context_type='Group',
            context_id='456'
        )
        self.assertEqual(event.context, 'Group:456')
    
    def test_event_context_property_none(self):
        """Test event context property when context is None."""
        event = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        self.assertIsNone(event.context)
    
    def test_event_correlation_events(self):
        """Test getting correlated events."""
        correlation_id = '550e8400-e29b-41d4-a716-446655440000'
        
        event1 = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user,
            correlation_id=correlation_id
        )
        
        event2 = PlatformEvent.objects.create(
            event_type='posts.comment.created',
            source='POSTS',
            action='created',
            target_type='Comment',
            target_id='456',
            actor=self.user,
            correlation_id=correlation_id
        )
        
        correlated = event1.get_correlation_events()
        self.assertEqual(correlated.count(), 2)
        self.assertIn(event1, correlated)
        self.assertIn(event2, correlated)
    
    def test_event_ordering(self):
        """Test events are ordered by timestamp descending."""
        event1 = PlatformEvent.objects.create(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        
        event2 = PlatformEvent.objects.create(
            event_type='posts.comment.created',
            source='POSTS',
            action='created',
            target_type='Comment',
            target_id='456',
            actor=self.user
        )
        
        events = list(PlatformEvent.objects.all())
        self.assertEqual(events[0], event2)  # Most recent first
        self.assertEqual(events[1], event1)


class EventPublisherTests(TestCase):
    """Test the event publisher."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_publish_event(self):
        """Test publishing an event."""
        event = EventPublisher.publish(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, 'posts.post.liked')
        self.assertEqual(event.source, 'POSTS')
        self.assertEqual(event.actor, self.user)
    
    def test_publish_event_with_all_fields(self):
        """Test publishing an event with all optional fields."""
        event = EventPublisher.publish(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user,
            context_type='Group',
            context_id='456',
            audience='WORKSPACE_MEMBERS',
            metadata={'test': 'data'},
            correlation_id='550e8400-e29b-41d4-a716-446655440000',
            version='1.0'
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.context_type, 'Group')
        self.assertEqual(event.context_id, '456')
        self.assertEqual(event.audience, 'WORKSPACE_MEMBERS')
        self.assertEqual(event.metadata, {'test': 'data'})
    
    def test_publish_event_invalid_data(self):
        """Test publishing with invalid data returns None."""
        event = EventPublisher.publish(
            event_type='invalid.event.type',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        
        self.assertIsNone(event)
    
    def test_publish_from_dict(self):
        """Test publishing from dictionary."""
        event_data = {
            'event_type': 'posts.post.liked',
            'source': 'POSTS',
            'action': 'liked',
            'target_type': 'Post',
            'target_id': '123',
            'actor': self.user
        }
        
        event = EventPublisher.publish_from_dict(event_data)
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, 'posts.post.liked')
    
    def test_publish_legacy_notification_event(self):
        """Test publishing from legacy notification."""
        event = EventPublisher.publish_legacy_notification_event(
            notification_type='LIKE',
            recipient=self.user,
            sender=self.user,
            notification_msg='Test message',
            post=None,
            group=None
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.metadata['legacy_notification_type'], 'LIKE')
        self.assertEqual(event.metadata['notification_message'], 'Test message')
    
    def test_convenience_publish_event_function(self):
        """Test the convenience publish_event function."""
        event = publish_event(
            event_type='posts.post.liked',
            source='POSTS',
            action='liked',
            target_type='Post',
            target_id='123',
            actor=self.user
        )
        
        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, 'posts.post.liked')
    
    def test_publish_event_without_actor(self):
        """Test publishing an event without an actor (system event)."""
        event = EventPublisher.publish(
            event_type='core.semester.changed',
            source='SYSTEM',
            action='changed',
            target_type='Semester',
            target_id='1',
            actor=None
        )
        
        self.assertIsNotNone(event)
        self.assertIsNone(event.actor)


class EventArchiveTests(TestCase):
    """Test the EventArchive model."""
    
    def test_create_event_archive(self):
        """Test creating an event archive."""
        archive = EventArchive.objects.create(
            event_id='550e8400-e29b-41d4-a716-446655440000',
            event_data={'test': 'data'},
            original_timestamp='2026-08-03T00:00:00Z'
        )
        
        self.assertIsNotNone(archive.event_id)
        self.assertEqual(archive.event_data, {'test': 'data'})
    
    def test_archive_str_representation(self):
        """Test archive string representation."""
        archive = EventArchive.objects.create(
            event_id='550e8400-e29b-41d4-a716-446655440000',
            event_data={'test': 'data'},
            original_timestamp='2026-08-03T00:00:00Z'
        )
        
        str_repr = str(archive)
        self.assertIn('550e8400-e29b-41d4-a716-446655440000', str_repr)
