from django.shortcuts import get_object_or_404
from core.models import Groups, Like, Notifications, User
from core.services.feed_service import invalidate_home_feed_context

def create_post_for_user(form, user, files, group_id=None):
    post = form.save(commit=False)

    # Core fields
    post.author = user
    post.course = user.course
    post.year = user.year

    # Group handling
    if group_id:
        post.group = get_object_or_404(Groups, id=group_id)

    # Unit override
    if post.unit:
        post.course = post.unit.course

    post.save()
    form.save_m2m()

    #  Handle images PROPERLY
    PostImage = post._meta.get_field('image').related_model
    images = files.getlist('images')

    for img in images:
        PostImage.objects.create(post=post, image=img)

    # Invalidate feeds
    invalidate_home_feed_context(user.id)

    # Notifications
    if post.group:
        recipients = post.group.members.exclude(id=user.id)
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

    return post
   



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