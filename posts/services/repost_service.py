from posts.models import Repost, Post
from django.core.exceptions import ValidationError


def create_repost(user, post, group=None, content=None):
    """
    Create a repost for a user.
    
    Args:
        user: The user creating the repost
        post: The original post being reposted
        group: Optional group to repost to
        content: Optional comment with the repost
    
    Returns:
        Repost instance
    
    Raises:
        ValidationError: If user tries to repost their own post or already reposted
    """
    if post.author == user:
        raise ValidationError("You cannot repost your own post.")
    
    # Check if already reposted to this location
    if Repost.objects.filter(
        original_post=post,
        reposter=user,
        group=group
    ).exists():
        raise ValidationError("You have already reposted this post.")
    
    # Check group membership if reposting to a group
    if group:
        from groups.models import Membership, MembershipStatus
        try:
            Membership.objects.get(
                user=user,
                group=group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            raise ValidationError("You must be an approved member to repost to this group.")
    
    repost = Repost.objects.create(
        original_post=post,
        reposter=user,
        group=group,
        content=content
    )
    return repost


def delete_repost(user, post, group=None):
    """
    Delete a repost for a user.
    
    Args:
        user: The user who created the repost
        post: The original post
        group: Optional group filter
    
    Returns:
        bool: True if deleted, False if not found
    """
    try:
        repost = Repost.objects.get(
            original_post=post,
            reposter=user,
            group=group
        )
        repost.delete()
        return True
    except Repost.DoesNotExist:
        return False


def get_post_reposts(post):
    """
    Get all reposts of a post.
    
    Args:
        post: The original post
    
    Returns:
        QuerySet of Repost instances
    """
    return Repost.objects.filter(original_post=post).select_related('reposter', 'group')


def is_post_reposted_by(user, post):
    """
    Check if a user has reposted a post.
    
    Args:
        user: The user to check
        post: The post to check
    
    Returns:
        bool: True if reposted, False otherwise
    """
    if not user.is_authenticated:
        return False
    return Repost.objects.filter(original_post=post, reposter=user).exists()
