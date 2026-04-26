from posts.models import HiddenPost, Post
from django.core.exceptions import ValidationError


def hide_post(user, post):
    """
    Hide a post for a user.
    
    Args:
        user: The user hiding the post
        post: The post to hide
    
    Returns:
        HiddenPost instance
    
    Raises:
        ValidationError: If post is already hidden
    """
    if HiddenPost.objects.filter(user=user, post=post).exists():
        raise ValidationError("You have already hidden this post.")
    
    hidden_post = HiddenPost.objects.create(user=user, post=post)
    return hidden_post


def unhide_post(user, post):
    """
    Unhide a post for a user.
    
    Args:
        user: The user who hid the post
        post: The post to unhide
    
    Returns:
        bool: True if unhidden, False if not found
    """
    try:
        hidden_post = HiddenPost.objects.get(user=user, post=post)
        hidden_post.delete()
        return True
    except HiddenPost.DoesNotExist:
        return False


def is_post_hidden(user, post):
    """
    Check if a post is hidden by a user.
    
    Args:
        user: The user to check
        post: The post to check
    
    Returns:
        bool: True if hidden, False otherwise
    """
    if not user.is_authenticated:
        return False
    return HiddenPost.objects.filter(user=user, post=post).exists()


def get_hidden_posts(user):
    """
    Get all posts hidden by a user.
    
    Args:
        user: The user
    
    Returns:
        QuerySet of HiddenPost instances
    """
    return HiddenPost.objects.filter(user=user).select_related('post', 'post__author')


def get_hidden_post_ids(user):
    """
    Get IDs of all posts hidden by a user.
    
    Args:
        user: The user
    
    Returns:
        set of post IDs
    """
    return set(HiddenPost.objects.filter(user=user).values_list('post_id', flat=True))
