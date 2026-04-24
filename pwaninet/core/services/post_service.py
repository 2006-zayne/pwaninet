from django.shortcuts import get_object_or_404

from core.models import Groups, Like, Notifications, User
from core.services.feed_service import invalidate_home_feed_context


def prepare_post_form_initial(group_id):
    if not group_id:
        return {}
    return {"group": get_object_or_404(Groups, id=group_id)}


def create_post_for_user(form, user, group_id=None):
    post = form.save(commit=False)
    post.author = user

    if group_id:
        post.group = get_object_or_404(Groups, id=group_id)

    post.course = user.course
    post.year = user.year

    if post.unit:
        post.course = post.unit.course

    post.save()
    form.save_images(post)
    form.save_m2m()
    invalidate_home_feed_context(user.id)

    if post.group:
        recipients = post.group.members.exclude(id=user.id)
        msg_text = f"posted in the {post.group.name} squad."
    else:
        recipients = User.objects.filter(course=user.course, year=user.year).exclude(id=user.id)
        msg_text = "posted a new update in the global feed."

    Notifications.objects.bulk_create(
        [Notifications(recipient=student, sender=user, msg=msg_text) for student in recipients]
    )

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
        "like_count": post.likes.count(),
    }
