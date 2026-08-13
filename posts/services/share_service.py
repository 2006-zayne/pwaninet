from posts.models import SharedPost, Post, PostImage
from django.core.exceptions import ValidationError
from django.db import models
from notifications.events import publish_event, EventTypes, EventSources, EventActions


def share_post(user, post, shared_to_user=None, shared_to_group=None, message=None):
    """
    Share a post to another user's profile or to a group.
    
    Args:
        user: The user sharing the post
        post: The post to share
        shared_to_user: The user to share the post to (optional)
        shared_to_group: The group to share the post to (optional)
        message: Optional message with the share
    
    Returns:
        SharedPost instance
    
    Raises:
        ValidationError: If sharing to self, not a group member, or already shared
    """
    # Ensure either user or group is provided, but not both
    if not shared_to_user and not shared_to_group:
        raise ValidationError("You must share to either a user or a group.")
    if shared_to_user and shared_to_group:
        raise ValidationError("You can only share to either a user or a group, not both.")
    
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
    
    # User sharing logic
    if shared_to_user:
        if shared_to_user == user:
            raise ValidationError("You cannot share posts to yourself.")
        
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
        
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if post.thumbnail:
            thumbnail_url = post.thumbnail.url
        elif post.images.exists():
            thumbnail_url = post.images.first().get_thumbnail_url('400')
        elif post.video_poster:
            thumbnail_url = post.video_poster.url
        elif post.shared_document:
            try:
                from documents.models import DocumentFile
                if post.shared_document.latest_version:
                    first_file = post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        # Emit event for new notification engine
        publish_event(
            event_type=EventTypes.POSTS_POST_SHARED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=user,
            target_type='Post',
            target_id=str(post.id),
            context_type='POST',
            context_id=str(post.id),
            audience=str(shared_to_user.id),
            metadata={
                'message': message[:100] if message else '',
                'sharer_username': user.username,
                'recipient_username': shared_to_user.username,
                'recipient_id': str(shared_to_user.id),
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': post.content[:100] if post.content else '',
                'actor_username': user.username,  # Add for title template compatibility
            }
        )
        
        # Notification is now handled by the event system
    
    # Group sharing logic
    elif shared_to_group:
        from groups.models import Membership, MembershipStatus
        try:
            Membership.objects.get(
                user=user,
                group=shared_to_group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            raise ValidationError("You can only share to groups you're a member of.")

        # Check if already shared to this group
        if SharedPost.objects.filter(
            original_post=post,
            sharer=user,
            shared_to_group=shared_to_group
        ).exists():
            raise ValidationError("You have already shared this post to this group.")

        # Create a repost in the group's feed
        repost = Post.objects.create(
            author=user,
            content=message or '',
            group=shared_to_group,
            video=post.video,
            docs=post.docs,
            gradient_class=post.gradient_class,
            repost_of=post
        )

        # Copy images from original post
        for image in post.images.all():
            PostImage.objects.create(post=repost, image=image.image)

        # Also create a SharedPost record for tracking
        shared_post = SharedPost.objects.create(
            original_post=post,
            sharer=user,
            shared_to_group=shared_to_group,
            message=message
        )

        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if post.thumbnail:
            thumbnail_url = post.thumbnail.url
        elif post.images.exists():
            thumbnail_url = post.images.first().get_thumbnail_url('400')
        elif post.video_poster:
            thumbnail_url = post.video_poster.url
        elif post.shared_document:
            try:
                from documents.models import DocumentFile
                if post.shared_document.latest_version:
                    first_file = post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        # Emit event for new notification engine
        publish_event(
            event_type=EventTypes.POSTS_POST_SHARED_TO_GROUP.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=user,
            target_type='Post',
            target_id=str(repost.id),
            context_type='POST',
            context_id=str(post.id),
            metadata={
                'message': message[:100] if message else '',
                'sharer_username': user.username,
                'group_name': shared_to_group.name,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': post.content[:100] if post.content else '',
                'group_id': str(shared_to_group.id),
                'actor_username': user.username,  # Add for title template compatibility
            }
        )

        # Create notification for group members
        # Notify admins and moderators of the group
        from groups.models import MembershipRole
        group_members = Membership.objects.filter(
            group=shared_to_group,
            status=MembershipStatus.APPROVED,
            role__in=[MembershipRole.ADMIN, MembershipRole.MODERATOR]
        ).select_related('user')

        for membership in group_members:
            if membership.user != user:  # Don't notify yourself
                # Notification is now handled by the event system
                pass
    
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
    ).select_related('sharer', 'shared_to', 'shared_to_group')


def get_group_shares(group):
    """
    Get all posts shared to a group.
    
    Args:
        group: The group
    
    Returns:
        QuerySet of SharedPost instances
    """
    return SharedPost.objects.filter(
        shared_to_group=group
    ).select_related('original_post', 'original_post__author', 'sharer')


def get_user_shareable_groups(user):
    """
    Get all groups a user can share posts to (groups they're a member of).
    
    Args:
        user: The user
    
    Returns:
        QuerySet of Group instances
    """
    from groups.models import Membership, MembershipStatus
    group_ids = Membership.objects.filter(
        user=user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True)
    from groups.models import Group
    return Group.objects.filter(id__in=group_ids)


def get_user_received_shares(user):
    """
    Get all posts shared to a user (both direct shares and shares to groups they're in).
    
    Args:
        user: The user
    
    Returns:
        QuerySet of SharedPost instances
    """
    from groups.models import Membership, MembershipStatus
    # Get groups the user is a member of
    group_ids = Membership.objects.filter(
        user=user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True)
    
    # Get shares directly to user and to their groups
    return SharedPost.objects.filter(
        models.Q(shared_to=user) | models.Q(shared_to_group_id__in=group_ids)
    ).select_related('original_post', 'original_post__author', 'sharer', 'shared_to_group')
