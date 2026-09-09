from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import NotificationObject
from courses.models import Course, Year
from groups.models import Group
from posts.models import Post

User = get_user_model()


class NotificationModelTest(TestCase):
    """Test cases for NotificationObject model (new notification engine)"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            course=self.course,
            year=self.year,
            password='testpass123'
        )
        self.group = Group.objects.create(name='Test Group', created_by=self.user1, course=self.course)
        self.post = Post.objects.create(author=self.user1, content='Test post', course=self.course)
    
    def test_notification_creation(self):
        """Test that a notification can be created"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='FOLLOW',
            category='SOCIAL',
            priority='NORMAL',
            title='user1 started following you',
            summary='New follower',
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(notification.recipient, self.user2)
        self.assertEqual(notification.notification_type, 'FOLLOW')
        self.assertEqual(notification.status, 'CREATED')
    
    def test_notification_str(self):
        """Test notification string representation"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='LIKE',
            category='SOCIAL',
            priority='LOW',
            title='user1 liked your post',
            summary='Post like',
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertIn('LIKE', str(notification))
    
    def test_notification_with_context(self):
        """Test notification with context reference"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='INVITE',
            category='GROUP',
            priority='HIGH',
            title='You have been invited to Test Group',
            summary='Group invitation',
            context_type='GROUP',
            context_id=str(self.group.id),
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(notification.context_type, 'GROUP')
        self.assertEqual(notification.context_id, str(self.group.id))
    
    def test_notification_with_source_events(self):
        """Test notification with source events reference"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='LIKE',
            category='SOCIAL',
            priority='LOW',
            title='user1 liked your post',
            summary='Post like',
            source_events=['event-123', 'event-456'],
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(len(notification.source_events), 2)
        self.assertIn('event-123', notification.source_events)
    
    def test_notification_type_choices(self):
        """Test notification type field choices"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='GROUP_APPROVED',
            category='GROUP',
            priority='NORMAL',
            title='Your group join request was approved',
            summary='Group approved',
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(notification.notification_type, 'GROUP_APPROVED')
    
    def test_notification_status(self):
        """Test notification status lifecycle"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='FOLLOW',
            category='SOCIAL',
            priority='NORMAL',
            title='user1 started following you',
            summary='New follower',
            status='CREATED',
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(notification.status, 'CREATED')
        
        notification.status = 'READ'
        notification.save()
        self.assertEqual(notification.status, 'READ')
    
    def test_notification_aggregation(self):
        """Test notification aggregation fields"""
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='LIKE',
            category='SOCIAL',
            priority='LOW',
            title='Multiple users liked your post',
            summary='Post likes',
            aggregation_key='post-123',
            event_count=5,
            metadata={'actor_id': str(self.user1.id), 'actor_username': self.user1.username}
        )
        self.assertEqual(notification.event_count, 5)
        self.assertEqual(notification.aggregation_key, 'post-123')


class NotificationTargetUrlTests(TestCase):
    """Test resolve_notification_target_url service function."""

    def setUp(self):
        self.user1 = User.objects.create_user(username='author', email='a@example.com', password='pw')
        self.user2 = User.objects.create_user(username='reader', email='r@example.com', password='pw')
        self.post = Post.objects.create(author=self.user1, content='Hello world')
        self.group = Group.objects.create(name='Engineers', created_by=self.user1)

    def test_resolve_post_url(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='LIKE',
            category='SOCIAL',
            context_type='POST',
            context_id=str(self.post.id),
            metadata={'actor_username': self.user2.username}
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, f'/post/{self.post.share_id}/')

    def test_resolve_comment_url(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='COMMENT',
            category='SOCIAL',
            context_type='POST',
            context_id=str(self.post.id),
            metadata={'actor_username': self.user2.username, 'target_id': 99}
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, f'/post/{self.post.share_id}/#comment-99')

    def test_resolve_group_url(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user2,
            notification_type='INVITE',
            category='GROUP',
            context_type='GROUP',
            context_id=str(self.group.id),
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, f'/groups/{self.group.id}/')

    def test_resolve_profile_url(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='FOLLOW',
            category='SOCIAL',
            metadata={'actor_username': 'grace'}
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, '/users/user/grace/')

    def test_resolve_custom_url_in_metadata(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='CUSTOM',
            category='SYSTEM',
            metadata={'url': '/custom-landing-page/'}
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, '/custom-landing-page/')

    def test_resolve_fallback_url(self):
        from notifications.services.notification_service import resolve_notification_target_url
        notification = NotificationObject.objects.create(
            recipient=self.user1,
            notification_type='UNKNOWN',
            category='SYSTEM',
        )
        url = resolve_notification_target_url(notification)
        self.assertEqual(url, '/notifications/')


class NotificationOpenViewTests(TestCase):
    """Test GET /notifications/<uuid>/ and /notifications/<uuid> click-through view."""

    def setUp(self):
        self.user = User.objects.create_user(username='tester', email='t@example.com', password='pw')
        self.post = Post.objects.create(author=self.user, content='Sample Post')
        self.notification = NotificationObject.objects.create(
            recipient=self.user,
            notification_type='LIKE',
            category='SOCIAL',
            status='CREATED',
            context_type='POST',
            context_id=str(self.post.id),
        )

    def test_open_notification_with_trailing_slash(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/notifications/{self.notification.notification_id}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/post/{self.post.share_id}/')

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'READ')

    def test_open_notification_without_trailing_slash(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/notifications/{self.notification.notification_id}')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f'/post/{self.post.share_id}/')

        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, 'READ')

    def test_open_nonexistent_notification_redirects_safely(self):
        import uuid
        random_id = uuid.uuid4()
        response = self.client.get(f'/notifications/{random_id}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/notifications/')
