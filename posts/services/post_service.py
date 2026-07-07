from django.shortcuts import get_object_or_404
from django.db import transaction
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post, PostImage
from users.models import User
from notifications.models import Notifications
from users.services.feed_service import invalidate_home_feed_context
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def create_post_for_user(form, user, files, group_id=None):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"create_post_for_user called. files: {files}")
    logger.info(f"files keys: {list(files.keys()) if files else 'None'}")
    
    with transaction.atomic():
        post = form.save(commit=False)

        post.author = user
        post.course = user.course
        post.year = user.year

        # Group handling
        if group_id:
            post.group = get_object_or_404(Group, id=group_id)

        # Unit override
        if post.unit:
            post.course = post.unit.course

        # Check if any media is being uploaded and set gradient to 'none'
        has_media = False
        if files:
            if 'images' in files and files.getlist('images'):
                has_media = True
            if 'video' in files and files.get('video'):
                has_media = True
            if 'docs' in files and files.get('docs'):
                has_media = True
            if 'audio' in files and files.get('audio'):
                has_media = True
        
        if has_media:
            post.gradient_class = 'none'
            logger.info(f"Media detected, setting gradient_class to 'none'")

        post.save()
        logger.info(f"Post saved with ID: {post.id}, gradient_class: {post.gradient_class}")

        # Handle multiple image uploads
        if files and 'images' in files:
            images = files.getlist('images')
            logger.info(f"Processing {len(images)} images")
            for idx, image_file in enumerate(images[:15]):  # Max 15 images
                logger.info(f"Creating PostImage {idx}: {image_file.name}")
                PostImage.objects.create(
                    post=post,
                    image=image_file,
                    order=idx
                )
            logger.info(f"Finished creating PostImage objects. Total: {post.images.count()}")
        else:
            logger.info("No images found in files")

        # Handle audio upload
        if files and 'audio' in files:
            audio_file = files.get('audio')
            logger.info(f"Audio file found: {audio_file.name if audio_file else 'None'}")
            if audio_file and hasattr(audio_file, 'name') and audio_file.name:
                try:
                    post.audio = audio_file
                    post.save()
                    logger.info(f"Audio saved successfully: {post.audio}")
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error saving audio file: {e}")
                    pass

        # Handle video upload
        if files and 'video' in files:
            video_file = files.get('video')
            logger.info(f"Video file found: {video_file.name if video_file else 'None'}")
            if video_file and hasattr(video_file, 'name') and video_file.name:
                try:
                    post.video = video_file
                    post.save()
                    logger.info(f"Video saved successfully: {post.video}")
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error saving video file: {e}")
                    pass

        # Handle docs upload
        if files and 'docs' in files:
            docs_file = files.get('docs')
            logger.info(f"Docs file found: {docs_file.name if docs_file else 'None'}")
            if docs_file and hasattr(docs_file, 'name') and docs_file.name:
                try:
                    post.docs = docs_file
                    post.save()
                    logger.info(f"Docs saved successfully: {post.docs}")
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    logger.error(f"Error saving docs file: {e}")
                    pass

    logger.info(f"Final post state - images: {post.images.count()}, video: {post.video.name if post.video else 'None'}, docs: {post.docs.name if post.docs else 'None'}, audio: {post.audio.name if post.audio else 'None'}, gradient_class: {post.gradient_class}")
    logger.info(f"get_intel_file returns: {post.get_intel_file.url if post.get_intel_file else 'None'}")
    return post

    # Invalidate feeds (outside transaction)
    invalidate_home_feed_context(user.id)

    # Notifications (outside transaction)
    if post.group:
        recipients = User.objects.filter(
            group_memberships__group=post.group,
            group_memberships__status=MembershipStatus.APPROVED
        ).exclude(id=user.id)
        msg_text = f"posted in the {post.group.name} squad."
    else:
        recipients = User.objects.filter(
            course=user.course,
            year=user.year
        ).exclude(id=user.id)
        msg_text = "posted a new update in the global feed."

    Notifications.objects.bulk_create([
        Notifications(
            recipient=recipient,
            sender=user,
            post=post,
            notification_type=Notifications.ALERTE,
            msg=msg_text,
        )
        for recipient in recipients
    ])
   

@transaction.atomic


def toggle_post_like_for_user(post, user):
    like_qs = Like.objects.filter(user=user, post=post)

    if like_qs.exists():
        like_qs.delete()
        is_liked = False
    else:
        Like.objects.create(user=user, post=post)
        is_liked = True

    invalidate_home_feed_context(user.id)

    if post.author_id != user.id:
        invalidate_home_feed_context(post.author_id)
    
    # Broadcast like update via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "feed_updates",
        {
            'type': 'post_like_update',
            'post_id': post.id,
            'like_count': post.likes.count(),
            'is_liked': is_liked,
            'user_id': user.id
        }
    )

    return {
        "post": post,
        "is_liked": is_liked,
        "like_count": post.likes.count()
    }