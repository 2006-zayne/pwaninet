"""
Test script to verify notification creation flow
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from posts.models import Post, Like
from notifications.models import NotificationObject, PlatformEvent
from notifications.events import publish_event, EventTypes, EventSources, EventActions

User = get_user_model()

# Create test users
try:
    user1 = User.objects.get(username='test_user1')
except User.DoesNotExist:
    user1 = User.objects.create_user(username='test_user1', email='test1@example.com', password='testpass123')

try:
    user2 = User.objects.get(username='test_user2')
except User.DoesNotExist:
    user2 = User.objects.create_user(username='test_user2', email='test2@example.com', password='testpass123')

# Create a test post
post = Post.objects.create(
    author=user1,
    content='Test post for notification testing'
)

print(f"Created post {post.id} by {user1.username}")

# Create a like (this should trigger notification via signal)
like = Like.objects.create(
    user=user2,
    post=post
)

print(f"Created like by {user2.username} on post {post.id}")

# Check if notification was created
notifications = NotificationObject.objects.filter(recipient=user1)
print(f"Notifications for {user1.username}: {notifications.count()}")

for notif in notifications:
    print(f"  - {notif.notification_id}: {notif.notification_type} - {notif.title}")

# Check if platform event was created
events = PlatformEvent.objects.filter(event_type=EventTypes.POSTS_POST_LIKED.value)
print(f"Platform events: {events.count()}")

for event in events:
    print(f"  - {event.event_id}: {event.event_type}")

print("\nTest complete!")
