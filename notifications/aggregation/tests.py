"""
Unit tests for Aggregation Engine (Phase 5)

Tests for notification aggregation.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from notifications.models import NotificationObject, PlatformEvent
from notifications.aggregation.engine import AggregationEngine, aggregate_notifications

User = get_user_model()


class AggregationEngineTests(TestCase):
    """Test the Aggregation Engine."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_aggregate_empty_list(self):
        """Test aggregating an empty list."""
        result = AggregationEngine.aggregate_notifications([])
        self.assertEqual(result, [])
    
    def test_aggregate_single_notification(self):
        """Test aggregating a single notification (no change)."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            aggregation_key='like:post:123'
        )
        
        result = AggregationEngine.aggregate_notifications([notification])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].notification_id, notification.notification_id)
    
    def test_aggregate_by_aggregation_key(self):
        """Test that notifications are grouped by aggregation key."""
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1']
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:456',  # Different key
            source_events=['evt2']
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # No aggregation, different keys
    
    def test_aggregate_within_window(self):
        """Test aggregation within the aggregation window."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 1)  # Aggregated
        
        # Check that source events were merged
        self.assertEqual(len(result[0].source_events), 2)
        self.assertIn('evt1', result[0].source_events)
        self.assertIn('evt2', result[0].source_events)
    
    def test_aggregate_outside_window(self):
        """Test that notifications outside the window are not aggregated."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=40),  # Outside 30-min window
            first_event_time=now - timedelta(minutes=40),
            latest_event_time=now - timedelta(minutes=40)
        )
        
        # Wait a moment to ensure different timestamps
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        # Verify the time difference is indeed outside the window
        time_diff = notification2.latest_event_time - notification1.first_event_time
        self.assertGreater(time_diff.total_seconds(), 30 * 60)  # More than 30 minutes
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (outside window)
    
    def test_never_aggregate_types(self):
        """Test that certain notification types are never aggregated."""
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='INVITE',  # Never aggregate
            category='WORKSPACE',
            priority='HIGH',
            title='Group invite 1',
            aggregation_key='invite:group:123',
            source_events=['evt1']
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='INVITE',
            category='WORKSPACE',
            priority='HIGH',
            title='Group invite 2',
            aggregation_key='invite:group:123',
            source_events=['evt2']
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (never aggregate type)
    
    def test_critical_notifications_not_aggregated(self):
        """Test that critical notifications are never aggregated."""
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='SECURITY',
            category='SECURITY',
            priority='CRITICAL',  # Critical
            title='Security alert 1',
            aggregation_key='security:alert:123',
            source_events=['evt1']
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='SECURITY',
            category='SECURITY',
            priority='CRITICAL',
            title='Security alert 2',
            aggregation_key='security:alert:123',
            source_events=['evt2']
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (critical)
    
    def test_no_aggregation_key(self):
        """Test that notifications without aggregation key are not aggregated."""
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key=None,  # No aggregation key
            source_events=['evt1']
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key=None,
            source_events=['evt2']
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (no key)
    
    def test_event_count_updated(self):
        """Test that event count is updated after aggregation."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1', 'evt2'],
            event_count=2,
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt3'],
            event_count=1,
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].event_count, 3)  # 2 + 1
    
    def test_first_and_latest_event_times_updated(self):
        """Test that first and latest event times are updated."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 1)
        
        self.assertEqual(result[0].first_event_time, notification1.first_event_time)
        self.assertEqual(result[0].latest_event_time, notification2.latest_event_time)
    
    def test_summary_generation(self):
        """Test that summary is generated for aggregated notifications."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            summary='Brian liked your post',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            summary='Kevin liked your post',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 1)
        self.assertIn('2 people liked your post', result[0].summary)
    
    def test_summary_generation_many_events(self):
        """Test summary generation for many events."""
        now = timezone.now()
        
        notifications = []
        for i in range(5):
            notification = NotificationObject.objects.create(
                recipient=self.user,
                notification_type='LIKE',
                category='SOCIAL',
                priority='NORMAL',
                title=f'Test notification {i}',
                aggregation_key='like:post:123',
                source_events=[f'evt{i}'],
                created_at=now - timedelta(minutes=i),
                first_event_time=now - timedelta(minutes=i),
                latest_event_time=now - timedelta(minutes=i)
            )
            notifications.append(notification)
        
        result = AggregationEngine.aggregate_notifications(notifications)
        self.assertEqual(len(result), 1)
        self.assertIn('5 people liked your post', result[0].summary)
    
    def test_different_recipients_not_aggregated(self):
        """Test that notifications for different recipients are not aggregated."""
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=user2,  # Different recipient
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (different recipients)
    
    def test_different_categories_not_aggregated(self):
        """Test that notifications with different categories are not aggregated."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='like:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='ACADEMIC',  # Different category
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='like:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (different categories)
    
    def test_get_aggregation_window(self):
        """Test getting aggregation window for notification type."""
        window = AggregationEngine.get_aggregation_window('LIKE')
        self.assertEqual(window, 30)  # 30 minutes
        
        window = AggregationEngine.get_aggregation_window('INVITE')
        self.assertIsNone(window)  # Never aggregate
    
    def test_convenience_aggregate_notifications_function(self):
        """Test the convenience aggregate_notifications function."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification',
            aggregation_key='like:post:123'
        )
        
        result = aggregate_notifications([notification])
        self.assertEqual(len(result), 1)
    
    def test_comment_aggregation_window(self):
        """Test that comments have a 15-minute aggregation window."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='comment:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=10),
            first_event_time=now - timedelta(minutes=10),
            latest_event_time=now - timedelta(minutes=10)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='comment:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 1)  # Aggregated (within 15-min window)
    
    def test_comment_aggregation_outside_window(self):
        """Test that comments outside 15-minute window are not aggregated."""
        now = timezone.now()
        
        notification1 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 1',
            aggregation_key='comment:post:123',
            source_events=['evt1'],
            created_at=now - timedelta(minutes=20),  # Outside 15-min window
            first_event_time=now - timedelta(minutes=20),
            latest_event_time=now - timedelta(minutes=20)
        )
        
        notification2 = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='Test notification 2',
            aggregation_key='comment:post:123',
            source_events=['evt2'],
            created_at=now,
            first_event_time=now,
            latest_event_time=now
        )
        
        # Verify the time difference is indeed outside the window
        time_diff = notification2.latest_event_time - notification1.first_event_time
        self.assertGreater(time_diff.total_seconds(), 15 * 60)  # More than 15 minutes
        
        result = AggregationEngine.aggregate_notifications([notification1, notification2])
        self.assertEqual(len(result), 2)  # Not aggregated (outside window)
