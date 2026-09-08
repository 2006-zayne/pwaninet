from django.db.models.signals import post_save
from django.dispatch import receiver
from posts.models import Like, Comment, CommentLike
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
            from django.utils import timezone
            publish_event(
                event_type=EventTypes.POSTS_POST_LIKED.value,
                source=EventSources.POSTS.value,
                action=EventActions.LIKED.value,
                actor=liker,
                target_type='Post',
                target_id=str(post.id),
                context_type='POST',
                context_id=str(post.id),
                metadata={
                    'post_content': post.content[:100],
                    'liker_username': liker.username,
                    'thumbnail_url': thumbnail_url,
                    'resource_type': 'POST',
                    'group_id': str(post.group.id) if post.group else None,
                    'actor_timestamp': timezone.now().isoformat(),
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
                    'comment_content': (comment.content[:50] + '...') if comment.content and len(comment.content) > 50 else (comment.content or ''),
                    'liker_username': liker.username
                }
            )


