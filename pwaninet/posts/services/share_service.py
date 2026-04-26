from posts.models import SharedPost, Post
from django.core.exceptions import ValidationError
from notifications.services.notification_service import create_notification


def share_post(user, post, shared_to_user, message=None):
    """
    Share a post to another user's profile.
    
    Args:
        user: The user sharing the post
        post: The post to share
        shared_to_user: The user to share the post to
        message: Optional message with the share
    
    Returns:
        SharedPost instance
    
    Raises:
        ValidationError: If sharing to self or already shared
    """
    if shared_to_user == user:
        raise ValidationError("You cannot share posts to yourself.")
    
    # Check if user can view the post
    if post.group:
        from groups.models import Membership, MembershipStatus
        try:
            Membership.objects.get(
                user=user,
                group=post.group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            raise ValidationError("You cannot share posts from groups you're not a member of.")
    
    # Check if already shared to this user
    if SharedPost.objects.filter(
        original_post=post,
        sharer=user,
        shared_to=shared_to_user
    ).exists():
        raise ValidationError("You have already shared this post to this user.")
    
    shared_post = SharedPost.objects.create(
        original_post=post,
        sharer=user,
        shared_to=shared_to_user,
        message=message
    )
    
    # Create notification for the recipient
    create_notification(
        recipient=shared_to_user,
        notification_type='post_shared',
        actor=user,
        target=post,
        message=message or f"{user.username} shared a post with you"
    )
    
    return shared_post


def get_shared_posts(user):
    """
    Get all posts shared to a user.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of SharedPost instances
    """
    return SharedPost.objects.filter(
        shared_to=user
    ).select_related('original_post', 'original_post__author', 'sharer')


def get_unviewed_shared_posts(user):
    """
    Get all unviewed posts shared to a user.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of SharedPost instances
    """
    return SharedPost.objects.filter(
        shared_to=user,
        is_viewed=False
    ).select_related('original_post', 'original_post__author', 'sharer')


def mark_share_as_viewed(share_id):
    """
    Mark a shared post as viewed.
    
    Args:
        share_id: The ID of the SharedPost
    
    Returns:
        bool: True if marked, False if not found
    """
    try:
        shared_post = SharedPost.objects.get(id=share_id)
        shared_post.is_viewed = True
        shared_post.save()
        return True
    except SharedPost.DoesNotExist:
        return False


def mark_all_shares_as_viewed(user):
    """
    Mark all shared posts for a user as viewed.
    
    Args:
        user: The user
    
    Returns:
        int: Number of shares marked as viewed
    """
    count = SharedPost.objects.filter(
        shared_to=user,
        is_viewed=False
    ).update(is_viewed=True)
    return count


def get_post_shares(post):
    """
    Get all shares of a post.
    
    Args:
        post: The post
    
    Returns:
        QuerySet of SharedPost instances
    """
    return SharedPost.objects.filter(
        original_post=post
    ).select_related('sharer', 'shared_to')
