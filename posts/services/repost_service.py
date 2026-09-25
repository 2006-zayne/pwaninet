from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from posts.models import Repost, Post
from django.core.exceptions import ValidationError
from notifications.events import publish_event, EventTypes, EventSources, EventActions
import logging

logger = logging.getLogger(__name__)


def broadcast_repost_update(post, user, is_reposted):
    """Broadcast real-time repost metric update via WebSockets."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            avatar_url = '/static/images/default-avatar.png'
            try:
                if user.profile_pic and hasattr(user.profile_pic, 'url'):
                    avatar_url = user.profile_pic.url
            except Exception:
                pass

            async_to_sync(channel_layer.group_send)(
                "feed_updates",
                {
                    'type': 'post_repost_update',
                    'post_id': post.id,
                    'share_id': str(post.share_id),
                    'repost_count': post.repost_count,
                    'is_reposted': is_reposted,
                    'user_id': user.id,
                    'user_username': user.username,
                    'user_name': user.get_full_name() or user.username,
                    'user_avatar': avatar_url,
                }
            )
    except Exception as e:
        logger.warning(f"Error broadcasting repost update via WebSocket: {e}")


def create_repost(user, post, group=None, content=None):
    """
    Create a repost for a user without duplicating the post object.
    
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

    # Invalidate cached counts if any
    if hasattr(post, '_repost_count'):
        delattr(post, '_repost_count')

    # Notify author
    try:
        thumbnail_url = None
        if post.thumbnail:
            thumbnail_url = post.thumbnail.url
        elif post.images.exists():
            thumbnail_url = post.images.first().get_thumbnail_url('400')
        elif post.video_poster:
            thumbnail_url = post.video_poster.url

        publish_event(
            event_type=EventTypes.POSTS_POST_REPOSTED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=user,
            target_type='Post',
            target_id=str(post.id),
            context_type='POST',
            context_id=str(post.id),
            metadata={
                'actor_username': user.username,
                'original_post_author_id': post.author.id,
                'original_post_author_username': post.author.username,
                'repost_content': content[:100] if content else None,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': post.content[:100] if post.content else '',
                'group_id': str(post.group.id) if post.group else None,
            }
        )
    except Exception as e:
        logger.warning(f"Error publishing repost event: {e}")

    broadcast_repost_update(post, user, is_reposted=True)
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

        if hasattr(post, '_repost_count'):
            delattr(post, '_repost_count')

        broadcast_repost_update(post, user, is_reposted=False)
        return True
    except Repost.DoesNotExist:
        return False


def toggle_repost(user, post, group=None, content=None):
    """
    Toggle repost for a user.
    If already reposted, removes the repost.
    If not reposted, creates a new repost.
    """
    existing = Repost.objects.filter(original_post=post, reposter=user, group=group).first()
    if existing:
        existing.delete()
        if hasattr(post, '_repost_count'):
            delattr(post, '_repost_count')
        is_reposted = False
    else:
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

        Repost.objects.create(
            original_post=post,
            reposter=user,
            group=group,
            content=content
        )
        if hasattr(post, '_repost_count'):
            delattr(post, '_repost_count')
        is_reposted = True

        # Publish notification event
        try:
            thumbnail_url = None
            if post.thumbnail:
                thumbnail_url = post.thumbnail.url
            elif post.images.exists():
                thumbnail_url = post.images.first().get_thumbnail_url('400')
            elif post.video_poster:
                thumbnail_url = post.video_poster.url

            publish_event(
                event_type=EventTypes.POSTS_POST_REPOSTED.value,
                source=EventSources.POSTS.value,
                action=EventActions.SHARED.value,
                actor=user,
                target_type='Post',
                target_id=str(post.id),
                context_type='POST',
                context_id=str(post.id),
                metadata={
                    'actor_username': user.username,
                    'original_post_author_id': post.author.id,
                    'original_post_author_username': post.author.username,
                    'repost_content': content[:100] if content else None,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                    'post_content': post.content[:100] if post.content else '',
                    'group_id': str(post.group.id) if post.group else None,
                }
            )
        except Exception as e:
            logger.warning(f"Error publishing repost event: {e}")

    broadcast_repost_update(post, user, is_reposted=is_reposted)
    return {
        'is_reposted': is_reposted,
        'repost_count': post.repost_count,
        'post': post
    }


def get_post_reposts(post):
    """
    Get all reposts of a post.
    """
    return Repost.objects.filter(original_post=post).select_related('reposter', 'group')


def is_post_reposted_by(user, post):
    """
    Check if a user has reposted a post.
    """
    if not user or not user.is_authenticated:
        return False
    return Repost.objects.filter(original_post=post, reposter=user).exists()
