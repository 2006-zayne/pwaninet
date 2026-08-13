"""
Signal handlers for Posts app to emit PlatformEvents for the notification engine.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from posts.models import Like, Comment, Repost, Post
from notifications.events import publish_event, EventTypes, EventSources, EventActions

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=Like)
def like_deleted(sender, instance, **kwargs):
    """Emit event when a post like is removed (optional, for tracking)."""
    # Unlike events are typically not needed for notifications
    pass


@receiver(post_save, sender=Comment)
def comment_created(sender, instance, created, **kwargs):
    """Emit event when a comment is created."""
    if created:
        if instance.parent_comment:
            # This is a reply
            # Get thumbnail URL for notification preview
            thumbnail_url = None
            post = instance.post
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
            
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_REPLIED.value,
                source=EventSources.POSTS.value,
                action=EventActions.REPLIED.value,
                actor=instance.author,
                target_type='Comment',
                target_id=instance.parent_comment.id,
                context_type='POST',
                context_id=str(post.id),
                metadata={
                    'post_author_id': post.author.id,
                    'post_author_username': post.author.username,
                    'parent_comment_id': instance.parent_comment.id,
                    'parent_comment_author_id': instance.parent_comment.author.id,
                    'parent_comment_author_username': instance.parent_comment.author.username,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                    'post_content': post.content[:100] if post.content else '',
                    'comment_content': (instance.parent_comment.content[:50] + '...') if instance.parent_comment.content and len(instance.parent_comment.content) > 50 else (instance.parent_comment.content or ''),
                }
            )
        else:
            # This is a top-level comment
            # Get thumbnail URL for notification preview
            thumbnail_url = None
            post = instance.post
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
            
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_CREATED.value,
                source=EventSources.POSTS.value,
                action=EventActions.COMMENTED.value,
                actor=instance.author,
                target_type='Comment',
                target_id=instance.id,
                context_type='POST',
                context_id=str(post.id),
                metadata={
                    'post_author_id': post.author.id,
                    'post_author_username': post.author.username,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                    'post_content': post.content[:100] if post.content else '',
                    'comment_content': (instance.content[:50] + '...') if instance.content and len(instance.content) > 50 else (instance.content or ''),
                    'target_id': str(instance.id),
                }
            )


@receiver(post_save, sender=Repost)
def repost_created(sender, instance, created, **kwargs):
    """Emit event when a post is reposted via Repost model."""
    logger.info(f'[repost_created] Signal triggered, created={created}, reposter={instance.reposter.username}')
    
    if created:
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if instance.original_post.thumbnail:
            thumbnail_url = instance.original_post.thumbnail.url
        elif instance.original_post.images.exists():
            thumbnail_url = instance.original_post.images.first().get_thumbnail_url('400')
        elif instance.original_post.video_poster:
            thumbnail_url = instance.original_post.video_poster.url
        elif instance.original_post.shared_document:
            try:
                from documents.models import DocumentFile
                if instance.original_post.shared_document.latest_version:
                    first_file = instance.original_post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        logger.info(f'[repost_created] Publishing event for repost by {instance.reposter.username} of post {instance.original_post.id}')
        
        publish_event(
            event_type=EventTypes.POSTS_POST_REPOSTED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=instance.reposter,
            target_type='Post',
            target_id=str(instance.original_post.id),
            context_type='POST',
            context_id=str(instance.original_post.id),
            metadata={
                'actor_username': instance.reposter.username,
                'original_post_author_id': instance.original_post.author.id,
                'original_post_author_username': instance.original_post.author.username,
                'repost_content': instance.content[:100] if instance.content else None,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': instance.original_post.content[:100] if instance.original_post.content else '',
                'group_id': str(instance.original_post.group.id) if instance.original_post.group else None,
            }
        )
        
        logger.info(f'[repost_created] Event published successfully')


@receiver(post_save, sender=Post)
def post_repost_created(sender, instance, created, **kwargs):
    """Emit event when a post is reposted via Post.repost_of field."""
    if created and instance.repost_of:
        logger.info(f'[post_repost_created] Signal triggered, created={created}, reposter={instance.author.username}')
        
        original_post = instance.repost_of
        
        # Get thumbnail URL for notification preview
        thumbnail_url = None
        if original_post.thumbnail:
            thumbnail_url = original_post.thumbnail.url
        elif original_post.images.exists():
            thumbnail_url = original_post.images.first().get_thumbnail_url('400')
        elif original_post.video_poster:
            thumbnail_url = original_post.video_poster.url
        elif original_post.shared_document:
            try:
                from documents.models import DocumentFile
                if original_post.shared_document.latest_version:
                    first_file = original_post.shared_document.latest_version.files.first()
                    if first_file and first_file.preview_path:
                        thumbnail_url = f"/media/{first_file.preview_path}"
            except:
                pass
        
        logger.info(f'[post_repost_created] Publishing event for repost by {instance.author.username} of post {original_post.id}')
        
        publish_event(
            event_type=EventTypes.POSTS_POST_REPOSTED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=instance.author,
            target_type='Post',
            target_id=str(original_post.id),
            context_type='POST',
            context_id=str(original_post.id),
            metadata={
                'actor_username': instance.author.username,
                'original_post_author_id': original_post.author.id,
                'original_post_author_username': original_post.author.username,
                'repost_content': instance.content[:100] if instance.content else None,
                'thumbnail_url': thumbnail_url,
                'resource_type': 'POST',
                'post_content': original_post.content[:100] if original_post.content else '',
                'group_id': str(original_post.group.id) if original_post.group else None,
            }
        )
        
        logger.info(f'[post_repost_created] Event published successfully')
