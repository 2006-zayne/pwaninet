from django.contrib import messages
from posts.models import Comment, CommentLike, PostImageComment, PostImageLike
from posts.queries.comment_queries import get_liked_comment_ids_for_user, get_ranked_comments_queryset
from users.services.feed_service import invalidate_home_feed_context
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

DEFAULT_VISIBLE_COMMENTS = 3

def build_comments_context(post, user, show_all_comments = False):
    ranked_comments = get_ranked_comments_queryset(post)
    visible_comments = ranked_comments if show_all_comments else ranked_comments[:DEFAULT_VISIBLE_COMMENTS]
    return {
        'post': post,
        'visible_comments': visible_comments,
        'show_all_comments': show_all_comments,
        'has_more_comments': post.comments.filter(parent_comment__isnull=True).count() > DEFAULT_VISIBLE_COMMENTS,
        'liked_comment_ids': get_liked_comment_ids_for_user(user, post) }


def add_comment_to_post(post, author, content, parent_comment=None):
    content = (content or '').strip()
    if not content:
        return None
    comment = Comment.objects.create(post = post, author = author, content = content, parent_comment=parent_comment)
    
    # Increment parent comment's reply_count if this is a reply
    if parent_comment:
        parent_comment.reply_count += 1
        parent_comment.save(update_fields=['reply_count'])
        
        # Notification is now handled by the event system in signals.py
    
    invalidate_home_feed_context(author.id)
    
    # Broadcast new comment via WebSocket to post-specific channel
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"post_comments_{post.id}",
        {
            'type': 'new_comment',
            'comment': {
                'id': comment.id,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name(),
                    'profile_pic': comment.author.profile_pic.url if comment.author.profile_pic else None
                },
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'likes_count': comment.likes.count(),
                'parent_comment_id': comment.parent_comment.id if comment.parent_comment else None,
                'reply_count': comment.reply_count
            }
        }
    )
    
    # Broadcast comment count update to global feed channel
    async_to_sync(channel_layer.group_send)(
        "feed_updates",
        {
            'type': 'post_comment_update',
            'post_id': post.id,
            'comment_count': post.comments.filter(parent_comment__isnull=True).count()
        }
    )
    
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
    
    # Broadcast like update via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"post_comments_{comment.post.id}",
        {
            'type': 'comment_like_update',
            'comment_id': comment.id,
            'likes_count': comment.likes.count()
        }
    )
    
    if comment.is_liked_by(user):
        return {
            'comment': comment,
            'liked_comment_ids': {
                comment.id} }
    return {
        'comment': comment,
        'liked_comment_ids': set() }


def add_comment_to_image(post_image, author, content):
    """Add a comment to a post image, mirroring the post comment functionality"""
    content = (content or '').strip()
    if not content:
        return None
    
    comment = PostImageComment.objects.create(
        post_image=post_image,
        author=author,
        content=content
    )
    
    invalidate_home_feed_context(author.id)
    
    # Broadcast new comment via WebSocket to image-specific channel
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"post_image_comments_{post_image.id}",
        {
            'type': 'new_image_comment',
            'comment': {
                'id': comment.id,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name(),
                    'profile_pic': comment.author.profile_pic.url if comment.author.profile_pic else None
                },
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            }
        }
    )
    
    return comment


def handle_add_image_comment_request(request, post_image):
    """Handle adding a comment to a post image, mirroring the post comment functionality"""
    comment = add_comment_to_image(post_image, request.user, request.POST.get('content'))
    if comment:
        messages.success(request, 'Comment added successfully.')
    else:
        messages.error(request, 'Comment cannot be empty.')
    return comment

