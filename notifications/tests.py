from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Notifications
from courses.models import Course, Year
from groups.models import Group
from posts.models import Post

User = get_user_model()


class NotificationModelTest(TestCase):
    """Test cases for Notifications model"""
    
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
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            notification_type=Notifications.FOLLOW,
            msg='user1 started following you'
        )
        self.assertEqual(notification.recipient, self.user2)
        self.assertEqual(notification.sender, self.user1)
        self.assertEqual(notification.notification_type, 'FOLLOW')
    
    def test_notification_str(self):
        """Test notification string representation"""
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            notification_type=Notifications.LIKE,
            msg='user1 liked your post'
        )
        self.assertIn('LIKE', str(notification))
    
    def test_notification_with_group(self):
        """Test notification with group reference"""
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            group=self.group,
            notification_type=Notifications.INVITE,
            msg='You have been invited to Test Group'
        )
        self.assertEqual(notification.group, self.group)
    
    def test_notification_with_post(self):
        """Test notification with post reference"""
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            post=self.post,
            notification_type=Notifications.LIKE,
            msg='user1 liked your post'
        )
        self.assertEqual(notification.post, self.post)
    
    def test_notification_type_choices(self):
        """Test notification type field choices"""
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            notification_type=Notifications.GROUP_APPROVED,
            msg='Your group join request was approved'
        )
        self.assertEqual(notification.notification_type, 'GROUP_APPROVED')
    
    def test_notification_read_status(self):
        """Test notification read status"""
        notification = Notifications.objects.create(
            recipient=self.user2,
            sender=self.user1,
            notification_type=Notifications.FOLLOW,
            msg='user1 started following you',
            is_read=False
        )
        self.assertFalse(notification.is_read)
        
        notification.is_read = True
        notification.save()
        self.assertTrue(notification.is_read)
