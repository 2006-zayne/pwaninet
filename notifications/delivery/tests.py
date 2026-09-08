"""
Unit tests for Delivery Engine (Phase 6)

Tests for delivery adapters and delivery engine.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from notifications.models import NotificationObject, DeliveryAttempt, PushSubscription
from notifications.delivery.engine import DeliveryEngine, deliver_notification
from notifications.delivery.adapters import InAppAdapter, EmailAdapter, PushAdapter, SMSAdapter, get_adapter
from unittest.mock import patch, MagicMock
import json

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
    
    def test_push_adapter_validate_without_subscription(self):
        """Test Push adapter validation without active subscription."""
        adapter = PushAdapter()
        valid = adapter.validate(self.notification)
        self.assertFalse(valid)

    def test_push_adapter_validate_with_subscription(self):
        """Test Push adapter validation with active subscription."""
        PushSubscription.objects.create(
            user=self.user,
            endpoint='https://fcm.googleapis.com/fcm/send/test',
            p256dh='test_p256dh',
            auth='test_auth',
            is_active=True
        )
        adapter = PushAdapter()
        valid = adapter.validate(self.notification)
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


class PushAdapterDeliveryTests(TestCase):
    """Test the PushAdapter delivery implementation for WebPush and FCM."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='pushtestuser',
            email='pushuser@example.com',
            password='testpass123'
        )
        self.notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='Push Notification Title',
            summary='Push summary body'
        )
        self.attempt = DeliveryAttempt.objects.create(
            notification=self.notification,
            channel='PUSH',
            status='PENDING'
        )
        self.adapter = PushAdapter()

    def test_push_adapter_no_subscriptions(self):
        """Test delivery returns True as graceful no-op when user has no subscriptions."""
        success = self.adapter.deliver(self.notification, self.attempt)
        self.assertTrue(success)

    @patch('pywebpush.webpush')
    def test_push_adapter_webpush_success(self, mock_webpush):
        """Test successful WebPush delivery via pywebpush."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_webpush.return_value = mock_response

        sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://updates.push.services.mozilla.com/wpush/v2/test',
            p256dh='test_p256dh_key',
            auth='test_auth_key',
            token_type='VAPID',
            platform='WEB',
            is_active=True
        )

        with patch('django.conf.settings.VAPID_PRIVATE_KEY', 'dummy_private_key'):
            success = self.adapter.deliver(self.notification, self.attempt)

        self.assertTrue(success)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, 'DELIVERED')
        sub.refresh_from_db()
        self.assertIsNotNone(sub.updated_at)
        mock_webpush.assert_called_once()

    @patch('pywebpush.webpush')
    def test_push_adapter_webpush_unregistered_deactivates(self, mock_webpush):
        """Test that 410 Gone from WebPush deactivates the subscription."""
        from pywebpush import WebPushException
        mock_response = MagicMock()
        mock_response.status_code = 410
        mock_webpush.side_effect = WebPushException('Subscription expired', response=mock_response)

        sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://fcm.googleapis.com/fcm/send/expired',
            p256dh='test_p256dh',
            auth='test_auth',
            token_type='VAPID',
            platform='PWA',
            is_active=True
        )

        with patch('django.conf.settings.VAPID_PRIVATE_KEY', 'dummy_private_key'):
            success = self.adapter.deliver(self.notification, self.attempt)

        self.assertFalse(success)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)

    @patch('notifications.delivery.adapters.get_firebase_app')
    @patch('firebase_admin.messaging.send')
    def test_push_adapter_fcm_success(self, mock_send, mock_get_app):
        """Test successful FCM native delivery."""
        mock_get_app.return_value = MagicMock()
        mock_send.return_value = 'projects/test/messages/msg_123'

        sub = PushSubscription.objects.create(
            user=self.user,
            fcm_token='test_fcm_token_device_abc',
            token_type='FCM',
            platform='ANDROID_NATIVE',
            is_active=True
        )

        success = self.adapter.deliver(self.notification, self.attempt)
        self.assertTrue(success)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, 'DELIVERED')
        sub.refresh_from_db()
        self.assertIsNotNone(sub.updated_at)
        mock_send.assert_called_once()

    @patch('notifications.delivery.adapters.get_firebase_app')
    @patch('firebase_admin.messaging.send')
    def test_push_adapter_fcm_unregistered_deactivates(self, mock_send, mock_get_app):
        """Test that UnregisteredError from FCM deactivates the subscription."""
        from firebase_admin import messaging
        mock_get_app.return_value = MagicMock()
        mock_send.side_effect = messaging.UnregisteredError('Device uninstalled app')

        sub = PushSubscription.objects.create(
            user=self.user,
            fcm_token='test_stale_token',
            token_type='FCM',
            platform='ANDROID_NATIVE',
            is_active=True
        )

        success = self.adapter.deliver(self.notification, self.attempt)
        self.assertFalse(success)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)


class PushAPITests(TestCase):
    """Test push notification HTTP APIs (VAPID key, subscribe, unsubscribe)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='testpass123'
        )
        self.client.force_login(self.user)

    def test_vapid_public_key_endpoint(self):
        """Test GET /api/push/vapid-public-key/."""
        response = self.client.get('/api/push/vapid-public-key/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('publicKey', data)
        self.assertIn('configured', data)

    def test_subscribe_webpush_w3c_payload(self):
        """Test POST /api/push/subscribe/ with W3C WebPush payload."""
        payload = {
            'endpoint': 'https://fcm.googleapis.com/fcm/send/w3c_device_1',
            'keys': {
                'p256dh': 'p256dh_test_key_sample',
                'auth': 'auth_test_secret_sample'
            },
            'platform': 'PWA',
            'token_type': 'VAPID'
        }
        response = self.client.post(
            '/api/push/subscribe/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')

        sub = PushSubscription.objects.get(endpoint=payload['endpoint'])
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.platform, 'PWA')
        self.assertEqual(sub.token_type, 'VAPID')
        self.assertEqual(sub.p256dh, 'p256dh_test_key_sample')
        self.assertTrue(sub.is_active)

    def test_subscribe_fcm_native_payload(self):
        """Test POST /api/push/subscribe/ with Capacitor FCM payload."""
        payload = {
            'token_type': 'FCM',
            'platform': 'ANDROID_NATIVE',
            'fcm_token': 'fcm_native_token_12345',
            'device_id': 'android_device_unique_id_999'
        }
        response = self.client.post(
            '/api/push/subscribe/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'success')

        sub = PushSubscription.objects.get(fcm_token='fcm_native_token_12345')
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.platform, 'ANDROID_NATIVE')
        self.assertEqual(sub.token_type, 'FCM')
        self.assertEqual(sub.device_id, 'android_device_unique_id_999')
        self.assertTrue(sub.is_active)

    def test_unsubscribe_endpoint(self):
        """Test POST /api/push/unsubscribe/."""
        sub = PushSubscription.objects.create(
            user=self.user,
            endpoint='https://fcm.googleapis.com/fcm/send/unsub_target',
            p256dh='p256dh',
            auth='auth',
            is_active=True
        )
        payload = {'endpoint': 'https://fcm.googleapis.com/fcm/send/unsub_target'}
        response = self.client.post(
            '/api/push/unsubscribe/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)


class PushContentCustomizationTests(TestCase):
    """Test push content resolution, smart tagging, and channel routing."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='custom_test_user',
            email='custom@example.com',
            password='testpass123'
        )
        self.adapter = PushAdapter()

    def test_resolve_push_content_with_message_engine(self):
        """Test that push body uses NotificationMessageEngine for rich conversational text."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='PINCH',
            category='SOCIAL',
            priority='NORMAL',
            title='Profile Pinched',
            summary='Your profile was pinched',
            metadata={
                'actor_id': 99,
                'actor_name': 'Grace Student',
                'actor_avatar': 'https://example.com/avatar.jpg',
                'url': '/users/profile/grace'
            }
        )

        content = self.adapter._resolve_push_content(notification)
        self.assertEqual(content['title'], 'PwaniNet')
        self.assertIn('Grace Student pinched you', content['body'])
        self.assertEqual(content['icon'], 'https://example.com/avatar.jpg')
        self.assertEqual(content['channel_id'], 'pwaninet_social')
        self.assertEqual(content['tag'], 'pwaninet-social-pinch')
        self.assertEqual(content['target_url'], '/users/profile/grace')

    def test_resolve_push_content_smart_tagging_aggregation(self):
        """Test that aggregation key takes precedence in smart tagging."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            aggregation_key='post_likes_88'
        )

        content = self.adapter._resolve_push_content(notification)
        self.assertEqual(content['tag'], 'pwaninet-post_likes_88')

    def test_resolve_push_content_smart_tagging_context(self):
        """Test that context type and ID are used when aggregation key is absent."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            context_type='POST',
            context_id=456
        )

        content = self.adapter._resolve_push_content(notification)
        self.assertEqual(content['tag'], 'pwaninet-post-456')

    def test_resolve_push_content_messaging_channel(self):
        """Test that messaging category maps to pwaninet_messages channel."""
        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='MESSAGE',
            category='MESSAGING',
            priority='HIGH'
        )

        content = self.adapter._resolve_push_content(notification)
        self.assertEqual(content['channel_id'], 'pwaninet_messages')

    @patch('pywebpush.webpush')
    def test_webpush_payload_includes_tag_and_renotify(self, mock_webpush):
        """Test that webpush payload JSON contains tag and renotify: True."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_webpush.return_value = mock_response

        PushSubscription.objects.create(
            user=self.user,
            endpoint='https://updates.push.services.mozilla.com/wpush/v2/custom',
            p256dh='test_p256dh',
            auth='test_auth',
            token_type='VAPID',
            platform='WEB',
            is_active=True
        )

        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='PINCH',
            category='SOCIAL',
            priority='NORMAL',
            metadata={'actor_name': 'Grace Student'}
        )

        with patch('django.conf.settings.VAPID_PRIVATE_KEY', 'dummy_key'):
            self.adapter.deliver(notification)

        mock_webpush.assert_called_once()
        call_kwargs = mock_webpush.call_args[1]
        sent_data = json.loads(call_kwargs['data'])

        self.assertEqual(sent_data['title'], 'PwaniNet')
        self.assertIn('Grace Student pinched you', sent_data['body'])
        self.assertTrue(sent_data['renotify'])
        self.assertEqual(sent_data['tag'], 'pwaninet-social-pinch')

    @patch('notifications.delivery.adapters.get_firebase_app')
    @patch('firebase_admin.messaging.send')
    def test_fcm_payload_includes_android_config(self, mock_send, mock_get_app):
        """Test that FCM message contains AndroidConfig with channel, color, and collapse key."""
        mock_get_app.return_value = MagicMock()
        mock_send.return_value = 'projects/test/messages/msg_fcm_custom'

        PushSubscription.objects.create(
            user=self.user,
            fcm_token='test_fcm_token_123',
            token_type='FCM',
            platform='ANDROID_NATIVE',
            is_active=True
        )

        notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='PINCH',
            category='SOCIAL',
            priority='NORMAL',
            metadata={'actor_name': 'Grace Student'}
        )

        self.adapter.deliver(notification)

        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]

        self.assertEqual(sent_message.notification.title, 'PwaniNet')
        self.assertIn('Grace Student pinched you', sent_message.notification.body)
        self.assertIsNotNone(sent_message.android)
        self.assertEqual(sent_message.android.notification.channel_id, 'pwaninet_social')
        self.assertEqual(sent_message.android.notification.color, '#2563eb')
        self.assertEqual(sent_message.android.collapse_key, 'pwaninet-social-pinch')


