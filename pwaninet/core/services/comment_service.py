# Source Generated with Decompyle++
# File: comment_service.cpython-312.pyc (Python 3.12)

from django.contrib import messages
from core.models import Comment, CommentLike, Notifications
from core.queries.comment_queries import get_liked_comment_ids_for_user, get_ranked_comments_queryset
from core.services.feed_service import invalidate_home_feed_context
from core.services.notification_service import invalidate_unread_count_cache
DEFAULT_VISIBLE_COMMENTS = 3

def build_comments_context(post, user, show_all_comments = (False,)):
    ranked_comments = get_ranked_comments_queryset(post)
    visible_comments = ranked_comments if show_all_comments else ranked_comments[:DEFAULT_VISIBLE_COMMENTS]
    return {
        'post': post,
        'visible_comments': visible_comments,
        'show_all_comments': show_all_comments,
        'has_more_comments': post.comments.count() > DEFAULT_VISIBLE_COMMENTS,
        'liked_comment_ids': get_liked_comment_ids_for_user(user, post) }


def add_comment_to_post(post, author, content):
    if not content:
        content
    content = ''.strip()
    if not content:
        return None
    comment = Comment.objects.create(post = post, author = author, content = content)
    if post.author != author:
        Notifications.objects.create(recipient = post.author, sender = author, post = post, notification_type = Notifications.ALERTE, msg = 'commented on your post.')
        invalidate_unread_count_cache(post.author.id)
    invalidate_home_feed_context(author.id)
    return comment


def handle_add_comment_request(request, post):
    comment = add_comment_to_post(post, request.user, request.POST.get('content'))
    if comment:
        messages.success(request, 'Comment added successfully.')
    else:
        messages.error(request, 'Comment cannot be empty.')
    return comment


def toggle_comment_like_for_user(comment, user):
    like_qs = CommentLike.objects.filter(user = user, comment = comment)
    if like_qs.exists():
        like_qs.delete()
    else:
        CommentLike.objects.create(user = user, comment = comment)
    if comment.is_liked_by(user):
        return {
            'comment': comment,
            'liked_comment_ids': {
                comment.id} }
    return {
        'comment': None,
        'liked_comment_ids': comment() }

