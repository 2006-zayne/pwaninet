from django.shortcuts import get_object_or_404
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post
from users.models import User
from notifications.models import Notifications
from posts.services.feed_service import invalidate_home_feed_context

def create_post_for_user(form, user, files, group_id=None):
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

    # Invalidate feeds
    invalidate_home_feed_context(user.id)

    # Notifications
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