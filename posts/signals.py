"""
Signal handlers for Posts app to emit PlatformEvents for the notification engine.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from posts.models import Like, Comment, Repost
from notifications.events import publish_event, EventTypes, EventSources, EventActions


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
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_REPLIED.value,
                source=EventSources.POSTS.value,
                action=EventActions.REPLIED.value,
                actor=instance.author,
                target_type='Comment',
                target_id=instance.parent_comment.id,
                context_type='Post',
                context_id=instance.post.id,
                metadata={
                    'post_author_id': instance.post.author.id,
                    'post_author_username': instance.post.author.username,
                    'parent_comment_id': instance.parent_comment.id,
                    'parent_comment_author_id': instance.parent_comment.author.id,
                    'parent_comment_author_username': instance.parent_comment.author.username,
                }
            )
        else:
            # This is a top-level comment
            publish_event(
                event_type=EventTypes.POSTS_COMMENT_CREATED.value,
                source=EventSources.POSTS.value,
                action=EventActions.COMMENTED.value,
                actor=instance.author,
                target_type='Comment',
                target_id=instance.id,
                context_type='Post',
                context_id=instance.post.id,
                metadata={
                    'post_author_id': instance.post.author.id,
                    'post_author_username': instance.post.author.username,
                }
            )


@receiver(post_save, sender=Repost)
def repost_created(sender, instance, created, **kwargs):
    """Emit event when a post is reposted."""
    if created:
        publish_event(
            event_type=EventTypes.POSTS_POST_REPOSTED.value,
            source=EventSources.POSTS.value,
            action=EventActions.SHARED.value,
            actor=instance.reposter,
            target_type='Post',
            target_id=str(instance.original_post.id),
            context_type='GROUP' if instance.group else None,
            context_id=str(instance.group.id) if instance.group else None,
            metadata={
                'original_post_author_id': instance.original_post.author.id,
                'original_post_author_username': instance.original_post.author.username,
                'repost_content': instance.content[:100] if instance.content else None,
            }
        )
