from django.db.models.signals import post_save
from django.dispatch import receiver
from posts.models import Like, Comment, CommentLike
from users.models import Follow, Pinch
from groups.models import Membership, MembershipStatus
from notifications.models import NotificationObject
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        liker = instance.user
        post_author = post.author
        
        if liker != post_author:
            # Get thumbnail URL for notification preview
            thumbnail_url = None
            if post.thumbnail:
                thumbnail_url = post.thumbnail.url
            elif post.images.exists():
                thumbnail_url = post.images.first().get_thumbnail_url('400')
            elif post.video_poster:
                thumbnail_url = post.video_poster.url
            elif post.shared_document:
                # For shared documents, try to get document preview
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
                event_type=EventTypes.POSTS_POST_LIKED.value,
                source=EventSources.POSTS.value,
                action=EventActions.LIKED.value,
                actor=liker,
                target_type='Post',
                target_id=str(post.id),
                context_type='GROUP' if post.group else None,
                context_id=str(post.group.id) if post.group else None,
                metadata={
                    'post_content': post.content[:100],
                    'liker_username': liker.username,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                }
            )


@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        commenter = instance.author
        post_author = post.author
        
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if post.thumbnail:
            thumbnail_url = post.thumbnail.url
        elif post.images.exists():
            thumbnail_url = post.images.first().get_thumbnail_url('400')
        elif post.video_poster:
            thumbnail_url = post.video_poster.url
        elif post.shared_document:
            # For shared documents, try to get document preview
            try:
                from documents.models import DocumentFile
                if post.shared_document.latest_version:
                    first_file = post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        # Check if this is a reply to a comment
        if instance.parent_comment:
            parent_author = instance.parent_comment.author
            
            if commenter != parent_author:
                # Emit event for comment reply
                publish_event(
                    event_type=EventTypes.POSTS_COMMENT_REPLIED.value,
                    source=EventSources.POSTS.value,
                    action=EventActions.REPLIED.value,
                    actor=commenter,
                    target_type='Comment',
                    target_id=str(instance.parent_comment.id),
                    context_type='POST',
                    context_id=str(post.id),
                    metadata={
                        'reply_content': instance.content[:100],
                        'commenter_username': commenter.username,
                        'parent_comment_content': instance.parent_comment.content[:100],
                        'thumbnail_url': thumbnail_url,
                        'resource_type': 'POST',
                    }
                )
        
        # Regular comment on post
        if commenter != post_author:
            # Emit event for new notification engine
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_CREATED.value,
                source=EventSources.POSTS.value,
                action=EventActions.COMMENTED.value,
                actor=commenter,
                target_type='Post',
                target_id=str(post.id),
                context_type='GROUP' if post.group else None,
                context_id=str(post.group.id) if post.group else None,
                metadata={
                    'comment_content': instance.content[:100],
                    'commenter_username': commenter.username,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                }
            )


@receiver(post_save, sender=CommentLike)
def create_comment_like_notification(sender, instance, created, **kwargs):
    if created:
        comment = instance.comment
        liker = instance.user
        comment_author = comment.author
        
        if liker != comment_author:
            # Emit event for new notification engine
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_LIKED.value,
                source=EventSources.POSTS.value,
                action=EventActions.LIKED.value,
                actor=liker,
                target_type='Comment',
                target_id=str(comment.id),
                context_type='POST',
                context_id=str(comment.post.id),
                metadata={
                    'comment_content': comment.content[:100],
                    'liker_username': liker.username
                }
            )


@receiver(post_save, sender=Follow)
def create_follow_notification(sender, instance, created, **kwargs):
    if created:
        follower = instance.follower
        followed = instance.followed
        
        # Emit event for new notification engine
        publish_event(
            event_type=EventTypes.USERS_USER_FOLLOWED.value,
            source=EventSources.USERS.value,
            action=EventActions.FOLLOWED.value,
            actor=follower,
            target_type='User',
            target_id=str(followed.id),
            metadata={
                'follower_username': follower.username,
                'followed_username': followed.username
            }
        )


@receiver(post_save, sender=Pinch)
def create_pinch_notification(sender, instance, created, **kwargs):
    if created:
        pinch_user = instance.pinch_user
        pinched_user = instance.pinched_user
        
        # Emit event for new notification engine
        publish_event(
            event_type=EventTypes.USERS_USER_PINCHED.value,
            source=EventSources.USERS.value,
            action=EventActions.PINCHED.value,
            actor=pinch_user,
            target_type='User',
            target_id=str(pinched_user.id),
            metadata={
                'pinch_username': pinch_user.username,
                'pinched_username': pinched_user.username
            }
        )


@receiver(post_save, sender=Membership)
def create_membership_notification(sender, instance, created, **kwargs):
    """Handle membership changes (join requests, approvals, invites)."""
    if created:
        # New membership request
        if instance.status == MembershipStatus.PENDING:
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_REQUESTED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.REQUESTED.value,
                actor=instance.user,
                target_type='Group',
                target_id=str(instance.group.id),
                metadata={
                    'group_name': instance.group.name,
                    'user_username': instance.user.username
                }
            )
        
        # Membership approved
        elif instance.status == MembershipStatus.APPROVED:
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_APPROVED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.APPROVED.value,
                target_type='Group',
                target_id=str(instance.group.id),
                actor=instance.group.created_by if instance.group.created_by else None,
                context_type='User',
                context_id=str(instance.user.id),
                metadata={
                    'group_name': instance.group.name,
                    'user_username': instance.user.username
                }
            )
        
        # Membership rejected
        elif instance.status == MembershipStatus.REJECTED:
            publish_event(
                event_type=EventTypes.GROUPS_MEMBER_REJECTED.value,
                source=EventSources.GROUPS.value,
                action=EventActions.REJECTED.value,
                target_type='Group',
                target_id=str(instance.group.id),
                actor=instance.group.created_by if instance.group.created_by else None,
                context_type='User',
                context_id=str(instance.user.id),
                metadata={
                    'group_name': instance.group.name,
                    'user_username': instance.user.username
                }
            )
