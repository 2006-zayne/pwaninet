from django.shortcuts import get_object_or_404
from django.db import transaction
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post, PostImage
from users.models import User
from notifications.models import Notifications
from users.services.feed_service import invalidate_home_feed_context

def create_post_for_user(form, user, files, group_id=None):
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

        post.save()

        # Handle multiple image uploads
        if files and 'images' in files:
            images = files.getlist('images')
            for idx, image_file in enumerate(images[:15]):  # Max 15 images
                PostImage.objects.create(
                    post=post,
                    image=image_file,
                    order=idx
                )

        # Handle audio upload
        if files and 'audio' in files:
            audio_file = files.get('audio')
            if audio_file and hasattr(audio_file, 'name') and audio_file.name:
                try:
                    post.audio = audio_file
                    post.save()
                except Exception as e:
                    # Log error but don't fail the entire post creation
                    print(f"Error saving audio file: {e}")
                    pass

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

    return {
        "post": post,
        "is_liked": is_liked,
        "like_count": post.likes.count()
    }