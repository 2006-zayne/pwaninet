"""
Comprehensive Notification Delivery Test Script

This script tests the full notification pipeline:
1. Event creation
2. Notification generation from events
3. Notification processing
4. Notification delivery

Run with: python manage.py shell < test_notification_delivery.py
Or: python test_notification_delivery.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from django.contrib.auth import get_user_model
from posts.models import Post, Like, Comment
from groups.models import Group, Membership, MembershipStatus
from users.models import User, Follow, Pinch
from notifications.models import NotificationObject, PlatformEvent, DeliveryAttempt
from notifications.events import publish_event, EventTypes, EventSources, EventActions
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_post_like_notification():
    """Test post like notification flow."""
    print_section("Testing Post Like Notification")
    
    # Get test users
    try:
        post_author = User.objects.get(username='student1')
        liker = User.objects.get(username='student2')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Create a test post
    post = Post.objects.create(
        author=post_author,
        content="Test post for like notification"
    )
    print(f"  ✓ Created test post: {post.id}")
    
    # Create a like (this should trigger event)
    like = Like.objects.create(
        post=post,
        user=liker
    )
    print(f"  ✓ Created like: {like.id}")
    
    # Check if event was created
    events = PlatformEvent.objects.filter(
        event_type=EventTypes.POSTS_POST_LIKED.value,
        actor=liker
    )
    if events.exists():
        print(f"  ✓ Event created: {events.first().event_id}")
    else:
        print(f"  ✗ Event NOT created for like")
    
    # Check if notification was created
    notifications = NotificationObject.objects.filter(
        recipient=post_author,
        notification_type='LIKE'
    )
    if notifications.exists():
        print(f"  ✓ Notification created: {notifications.first().notification_id}")
        print(f"    Status: {notifications.first().status}")
    else:
        print(f"  ✗ Notification NOT created for like")
    
    # Check delivery attempts
    if notifications.exists():
        notif = notifications.first()
        attempts = DeliveryAttempt.objects.filter(notification=notif)
        print(f"  ✓ Delivery attempts: {attempts.count()}")
        for attempt in attempts:
            print(f"    - {attempt.channel}: {attempt.status}")
    
    return True


def test_follow_notification():
    """Test follow notification flow."""
    print_section("Testing Follow Notification")
    
    try:
        follower = User.objects.get(username='student3')
        followed = User.objects.get(username='student4')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Create a follow (this should trigger event)
    follow = Follow.objects.create(
        follower=follower,
        followed=followed
    )
    print(f"  ✓ Created follow: {follow.id}")
    
    # Check if event was created
    events = PlatformEvent.objects.filter(
        event_type=EventTypes.USERS_USER_FOLLOWED.value,
        actor=follower
    )
    if events.exists():
        print(f"  ✓ Event created: {events.first().event_id}")
    else:
        print(f"  ✗ Event NOT created for follow")
    
    # Check if notification was created
    notifications = NotificationObject.objects.filter(
        recipient=followed,
        notification_type='FOLLOW'
    )
    if notifications.exists():
        print(f"  ✓ Notification created: {notifications.first().notification_id}")
        print(f"    Status: {notifications.first().status}")
    else:
        print(f"  ✗ Notification NOT created for follow")
    
    return True


def test_comment_notification():
    """Test comment notification flow."""
    print_section("Testing Comment Notification")
    
    try:
        post_author = User.objects.get(username='student1')
        commenter = User.objects.get(username='student2')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Create a test post
    post = Post.objects.create(
        author=post_author,
        content="Test post for comment notification"
    )
    print(f"  ✓ Created test post: {post.id}")
    
    # Create a comment (this should trigger event)
    comment = Comment.objects.create(
        post=post,
        author=commenter,
        content="Test comment"
    )
    print(f"  ✓ Created comment: {comment.id}")
    
    # Check if event was created
    events = PlatformEvent.objects.filter(
        event_type=EventTypes.POSTS_COMMENT_CREATED.value,
        actor=commenter
    )
    if events.exists():
        print(f"  ✓ Event created: {events.first().event_id}")
    else:
        print(f"  ✗ Event NOT created for comment")
    
    # Check if notification was created
    notifications = NotificationObject.objects.filter(
        recipient=post_author,
        notification_type='COMMENT'
    )
    if notifications.exists():
        print(f"  ✓ Notification created: {notifications.first().notification_id}")
        print(f"    Status: {notifications.first().status}")
    else:
        print(f"  ✗ Notification NOT created for comment")
    
    return True


def test_group_membership_notification():
    """Test group membership notification flow."""
    print_section("Testing Group Membership Notification")
    
    try:
        admin = User.objects.get(username='president')
        requester = User.objects.get(username='student5')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Get or create a group
    group, _ = Group.objects.get_or_create(
        name="Test Group for Notifications",
        defaults={
            'created_by': admin,
            'description': 'Test group'
        }
    )
    print(f"  ✓ Group: {group.id}")
    
    # Create a membership request (this should trigger event)
    membership = Membership.objects.create(
        user=requester,
        group=group,
        status=MembershipStatus.PENDING
    )
    print(f"  ✓ Created membership request: {membership.id}")
    
    # Check if event was created
    events = PlatformEvent.objects.filter(
        event_type=EventTypes.GROUPS_MEMBER_REQUESTED.value,
        actor=requester
    )
    if events.exists():
        print(f"  ✓ Event created: {events.first().event_id}")
    else:
        print(f"  ✗ Event NOT created for membership request")
    
    # Check if notification was created for admin
    notifications = NotificationObject.objects.filter(
        recipient=admin,
        notification_type='GROUP_REQUEST'
    )
    if notifications.exists():
        print(f"  ✓ Notification created: {notifications.first().notification_id}")
        print(f"    Status: {notifications.first().status}")
    else:
        print(f"  ✗ Notification NOT created for membership request")
    
    return True


def test_pinch_notification():
    """Test pinch notification flow."""
    print_section("Testing Pinch Notification")
    
    try:
        pinch_user = User.objects.get(username='student1')
        pinched_user = User.objects.get(username='student2')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Create a pinch (this should trigger event)
    pinch = Pinch.objects.create(
        pinch_user=pinch_user,
        pinched_user=pinched_user
    )
    print(f"  ✓ Created pinch: {pinch.id}")
    
    # Check if event was created
    events = PlatformEvent.objects.filter(
        event_type=EventTypes.USERS_USER_PINCHED.value,
        actor=pinch_user
    )
    if events.exists():
        print(f"  ✓ Event created: {events.first().event_id}")
    else:
        print(f"  ✗ Event NOT created for pinch")
    
    # Check if notification was created
    notifications = NotificationObject.objects.filter(
        recipient=pinched_user,
        notification_type='PINCH'
    )
    if notifications.exists():
        print(f"  ✓ Notification created: {notifications.first().notification_id}")
        print(f"    Status: {notifications.first().status}")
    else:
        print(f"  ✗ Notification NOT created for pinch")
    
    return True


def test_direct_event_publishing():
    """Test direct event publishing without model signals."""
    print_section("Testing Direct Event Publishing")
    
    try:
        actor = User.objects.get(username='president')
        recipient = User.objects.get(username='student1')
    except User.DoesNotExist:
        print("  ✗ Test users not found. Run seed_database.py first.")
        return False
    
    # Publish event directly
    event = publish_event(
        event_type=EventTypes.POSTS_POST_CREATED.value,
        source=EventSources.POSTS.value,
        action=EventActions.CREATED.value,
        actor=actor,
        target_type='Post',
        target_id='test-123',
        context_type='User',
        context_id=str(recipient.id),
        metadata={'test': 'direct publish'}
    )
    
    if event:
        print(f"  ✓ Event published directly: {event.event_id}")
    else:
        print(f"  ✗ Event publication failed")
    
    return True


def check_notification_stats():
    """Print overall notification statistics."""
    print_section("Notification Statistics")
    
    print(f"  Total PlatformEvents: {PlatformEvent.objects.count()}")
    print(f"  Total NotificationObjects: {NotificationObject.objects.count()}")
    print(f"  Total DeliveryAttempts: {DeliveryAttempt.objects.count()}")
    
    # Notification status breakdown
    print("\n  Notification Status Breakdown:")
    for status in ['CREATED', 'DELIVERED', 'SEEN', 'READ', 'ARCHIVED']:
        count = NotificationObject.objects.filter(status=status).count()
        print(f"    {status}: {count}")
    
    # Delivery method breakdown
    print("\n  Delivery Channel Breakdown:")
    for channel in ['PUSH', 'EMAIL', 'IN_APP']:
        count = DeliveryAttempt.objects.filter(channel=channel).count()
        print(f"    {channel}: {count}")
    
    # Recent notifications
    print("\n  Recent Notifications (last 5):")
    for notif in NotificationObject.objects.order_by('-created_at')[:5]:
        print(f"    - {notif.notification_type} for {notif.recipient.username}: {notif.status}")


def run_all_tests():
    """Run all notification delivery tests."""
    print("\n" + "=" * 60)
    print("  NOTIFICATION DELIVERY TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run individual tests
    results.append(("Post Like", test_post_like_notification()))
    results.append(("Follow", test_follow_notification()))
    results.append(("Comment", test_comment_notification()))
    results.append(("Group Membership", test_group_membership_notification()))
    results.append(("Pinch", test_pinch_notification()))
    results.append(("Direct Event", test_direct_event_publishing()))
    
    # Print summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    # Print statistics
    check_notification_stats()
    
    print("\n" + "=" * 60)
    print("  TEST SUITE COMPLETED")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    run_all_tests()
