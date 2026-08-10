"""
Unit tests for Delivery Engine (Phase 6)

Tests for delivery adapters and delivery engine.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from notifications.models import NotificationObject, DeliveryAttempt
from notifications.delivery.engine import DeliveryEngine, deliver_notification
from notifications.delivery.adapters import InAppAdapter, EmailAdapter, PushAdapter, SMSAdapter, get_adapter

User = get_user_model()


class DeliveryAdapterTests(TestCase):
    """Test the delivery adapters."""
    
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
        self.attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
    
    def test_in_app_adapter_deliver(self):
        """Test In-App adapter delivery."""
        adapter = InAppAdapter()
        success = adapter.deliver(self.notification, self.attempt)
        
        self.assertTrue(success)
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'DELIVERED')
    
    def test_in_app_adapter_validate(self):
        """Test In-App adapter validation."""
        adapter = InAppAdapter()
        valid = adapter.validate(self.notification)
        
        self.assertTrue(valid)
    
    def test_email_adapter_validate_with_email(self):
        """Test Email adapter validation with email."""
        adapter = EmailAdapter()
        valid = adapter.validate(self.notification)
        
        self.assertTrue(valid)
    
    def test_email_adapter_validate_without_email(self):
        """Test Email adapter validation without email."""
        self.user.email = ''
        self.user.save()
        
        adapter = EmailAdapter()
        valid = adapter.validate(self.notification)
        
        self.assertFalse(valid)
    
    def test_push_adapter_validate(self):
        """Test Push adapter validation (placeholder)."""
        adapter = PushAdapter()
        valid = adapter.validate(self.notification)
        
        # Placeholder returns True
        self.assertTrue(valid)
    
    def test_sms_adapter_validate(self):
        """Test SMS adapter validation (placeholder)."""
        adapter = SMSAdapter()
        valid = adapter.validate(self.notification)
        
        # Placeholder returns True
        self.assertTrue(valid)
    
    def test_get_adapter(self):
        """Test getting adapter by channel."""
        in_app_adapter = get_adapter('IN_APP')
        self.assertIsInstance(in_app_adapter, InAppAdapter)
        
        email_adapter = get_adapter('EMAIL')
        self.assertIsInstance(email_adapter, EmailAdapter)
        
        push_adapter = get_adapter('PUSH')
        self.assertIsInstance(push_adapter, PushAdapter)
        
        sms_adapter = get_adapter('SMS')
        self.assertIsInstance(sms_adapter, SMSAdapter)


class DeliveryAttemptTests(TestCase):
    """Test the DeliveryAttempt model."""
    
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
    
    def test_create_delivery_attempt(self):
        """_test creating a delivery attempt."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
        
        self.assertEqual(attempt.notification, self.notification)
        self.assertEqual(attempt.channel, 'IN_APP')
        self.assertEqual(attempt.status, 'PENDING')
        self.assertEqual(attempt.attempt_count, 0)
    
    def test_mark_as_queued(self):
        """Test marking delivery as queued."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
        
        attempt.mark_as_queued()
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'QUEUED')
        self.assertIsNotNone(attempt.queued_at)
    
    def test_mark_as_sending(self):
        """Test marking delivery as sending."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='QUEUED'
        )
        
        attempt.mark_as_sending()
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'SENDING')
        self.assertIsNotNone(attempt.sent_at)
    
    def test_mark_as_delivered(self):
        """Test marking delivery as delivered."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='SENDING'
        )
        
        attempt.mark_as_delivered()
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'DELIVERED')
        self.assertIsNotNone(attempt.delivered_at)
    
    def test_mark_as_failed(self):
        """Test marking delivery as failed."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='SENDING'
        )
        
        attempt.mark_as_failed(error_message='Connection error', error_code='CONN_ERR')
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'FAILED')
        self.assertIsNotNone(attempt.failed_at)
        self.assertEqual(attempt.error_message, 'Connection error')
        self.assertEqual(attempt.error_code, 'CONN_ERR')
    
    def test_schedule_retry(self):
        """Test scheduling a retry."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='FAILED'
        )
        
        attempt.schedule_retry(30)
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'RETRY_SCHEDULED')
        self.assertEqual(attempt.attempt_count, 1)
        self.assertIsNotNone(attempt.next_retry_at)
    
    def test_mark_as_expired(self):
        """Test marking delivery as expired."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
        
        attempt.mark_as_expired()
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'EXPIRED')
    
    def test_mark_as_cancelled(self):
        """Test marking delivery as cancelled."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
        
        attempt.mark_as_cancelled()
        
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'CANCELLED')
    
    def test_delivery_attempt_str_representation(self):
        """Test delivery attempt string representation."""
        attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='IN_APP',
            status='PENDING'
        )
        
        str_repr = str(attempt)
        self.assertIn('IN_APP', str_repr)
        self.assertIn(str(self.notification.notification_id), str_repr)
        self.assertIn('PENDING', str_repr)


class DeliveryEngineTests(TestCase):
    """Test the Delivery Engine."""
    
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
    
    def test_deliver_notification_single_channel(self):
        """Test delivering notification through single channel."""
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP'])
        
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].channel, 'IN_APP')
        self.assertEqual(attempts[0].status, 'DELIVERED')
    
    def test_deliver_notification_multiple_channels(self):
        """Test delivering notification through multiple channels."""
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP', 'EMAIL'])
        
        self.assertEqual(len(attempts), 2)
        
        channels = [attempt.channel for attempt in attempts]
        self.assertIn('IN_APP', channels)
        self.assertIn('EMAIL', channels)
    
    def test_deliver_notification_expired(self):
        """Test that expired notifications are not delivered."""
        self.notification.expires_at = timezone.now() - timedelta(hours=1)
        self.notification.save()
        
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP'])
        
        self.assertEqual(len(attempts), 0)
    
    def test_deliver_notification_with_future_expiration(self):
        """Test that notifications with future expiration are delivered."""
        self.notification.expires_at = timezone.now() + timedelta(hours=1)
        self.notification.save()
        
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP'])
        
        self.assertEqual(len(attempts), 1)
    
    def test_deliver_notification_invalid_channel(self):
        """Test delivering through invalid channel."""
        attempts = DeliveryEngine.deliver_notification(self.notification, ['INVALID_CHANNEL'])
        
        self.assertEqual(len(attempts), 0)
    
    def test_get_delivery_status(self):
        """Test getting delivery status for notification."""
        DeliveryEngine.deliver_notification(self.notification, ['IN_APP', 'EMAIL'])
        
        status = DeliveryEngine.get_delivery_status(self.notification)
        
        self.assertIn('IN_APP', status)
        self.assertIn('EMAIL', status)
    
    def test_mark_notification_as_delivered(self):
        """Test marking notification as delivered."""
        DeliveryEngine.mark_notification_as_delivered(self.notification)
        
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'DELIVERED')
    
    def test_convenience_deliver_notification_function(self):
        """Test the convenience deliver_notification function."""
        attempts = deliver_notification(self.notification, ['IN_APP'])
        
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].channel, 'IN_APP')
    
    def test_channel_independence(self):
        """Test that failure in one channel doesn't block others."""
        # This test verifies that channels are independent per ADR-028
        # Email adapter will fail validation (no email)
        self.user.email = ''
        self.user.save()
        
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP', 'EMAIL'])
        
        # In-App should succeed, Email should fail validation
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].channel, 'IN_APP')
        self.assertEqual(attempts[0].status, 'DELIVERED')
    
    def test_delivery_attempt_count(self):
        """Test that delivery attempts are tracked."""
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP'])
        
        self.assertEqual(attempts[0].attempt_count, 0)
    
    def test_delivery_timestamps(self):
        """Test that delivery timestamps are recorded."""
        attempts = DeliveryEngine.deliver_notification(self.notification, ['IN_APP'])
        
        attempt = attempts[0]
        self.assertIsNotNone(attempt.queued_at)
        self.assertIsNotNone(attempt.sent_at)
        self.assertIsNotNone(attempt.delivered_at)
