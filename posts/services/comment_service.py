from django.contrib import messages
from posts.models import Comment, CommentLike, PostImageComment, PostImageLike
from posts.queries.comment_queries import get_liked_comment_ids_for_user, get_ranked_comments_queryset
from users.services.feed_service import invalidate_home_feed_context
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

DEFAULT_VISIBLE_COMMENTS = 3
COMMENTS_PAGE_SIZE = 15

def build_comments_context(post, user, show_all_comments=False, page=1, page_size=COMMENTS_PAGE_SIZE):
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    ranked_comments = get_ranked_comments_queryset(post)
    total_top_level_count = post.comments.filter(parent_comment__isnull=True).count()

    if not show_all_comments:
        visible_comments = ranked_comments[:DEFAULT_VISIBLE_COMMENTS]
        has_more_comments = total_top_level_count > DEFAULT_VISIBLE_COMMENTS
        return {
            'post': post,
            'visible_comments': visible_comments,
            'show_all_comments': False,
            'has_more_comments': has_more_comments,
            'has_next_page': False,
            'next_page_number': None,
            'total_comments_count': total_top_level_count,
            'liked_comment_ids': get_liked_comment_ids_for_user(user, post)
        }

    paginator = Paginator(ranked_comments, page_size)
    try:
        page_num = int(page)
    except (TypeError, ValueError):
        page_num = 1

    try:
        page_obj = paginator.page(page_num)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages > 0 else 1)

    has_next_page = page_obj.has_next()
    next_page_number = page_obj.next_page_number() if has_next_page else None

    return {
        'post': post,
        'visible_comments': page_obj.object_list,
        'show_all_comments': True,
        'has_more_comments': total_top_level_count > DEFAULT_VISIBLE_COMMENTS,
        'has_next_page': has_next_page,
        'next_page_number': next_page_number,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_comments_count': total_top_level_count,
        'page_obj': page_obj,
        'liked_comment_ids': get_liked_comment_ids_for_user(user, post)
    }


def add_comment_to_post(post, author, content, parent_comment=None, attachment_type='none', attachment_image=None, attachment_url='', attachment_meta=None):
    content = (content or '').strip()
    has_attachment = attachment_type != Comment.ATTACHMENT_NONE and (bool(attachment_image) or bool(attachment_url))
    if not content and not has_attachment:
        return None

    # Enforce maximum nesting depth: cap replies to 1 level below the root comment.
    # If the target comment is already a reply, resolve up to the root top-level comment
    # and auto-prefix @username mention if not present.
    if parent_comment:
        target_author = parent_comment.author
        if parent_comment.parent_comment:
            while parent_comment.parent_comment:
                parent_comment = parent_comment.parent_comment
            if target_author != author and not content.startswith(f"@{target_author.username}"):
                content = f"@{target_author.username} {content}"

    comment = Comment.objects.create(
        post=post,
        author=author,
        content=content,
        parent_comment=parent_comment,
        attachment_type=attachment_type or Comment.ATTACHMENT_NONE,
        attachment_image=attachment_image,
        attachment_url=attachment_url or '',
        attachment_meta=attachment_meta or {}
    )
    
    # Increment parent comment's reply_count if this is a reply
    if parent_comment:
        parent_comment.reply_count += 1
        parent_comment.save(update_fields=['reply_count'])
        
        # Notification is now handled by the event system in signals.py
    
    invalidate_home_feed_context(author.id)
    
    # Broadcast new comment via WebSocket to post-specific channels
    channel_layer = get_channel_layer()
    event_payload = {
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
            'attachment_type': comment.attachment_type,
            'attachment_url': comment.media_url,
            'attachment_meta': comment.attachment_meta,
            'created_at': comment.created_at.isoformat(),
            'likes_count': comment.likes.count(),
            'parent_comment_id': comment.parent_comment.id if comment.parent_comment else None,
            'reply_count': comment.reply_count
        }
    }
    async_to_sync(channel_layer.group_send)(
        f"post_comments_{post.id}",
        event_payload
    )
    if hasattr(post, 'share_id') and post.share_id:
        async_to_sync(channel_layer.group_send)(
            f"post_comments_{post.share_id}",
            event_payload
        )
    
    # Broadcast comment count update to global feed channel
    async_to_sync(channel_layer.group_send)(
        "feed_updates",
        {
            'type': 'post_comment_update',
            'post_id': post.id,
            'comment_count': post.comments.count()
        }
    )
    
    return comment


def handle_add_comment_request(request, post):
    import json
    parent_comment = None
    parent_id = request.POST.get('parent_id') or request.POST.get('parent_comment_id')
    if parent_id:
        parent_comment = Comment.objects.filter(id=parent_id, post=post).first()
    
    content = request.POST.get('content', '')
    attachment_type = request.POST.get('attachment_type', Comment.ATTACHMENT_NONE)
    attachment_url = request.POST.get('attachment_url', '')
    attachment_image = request.FILES.get('attachment_image') or request.FILES.get('image')
    
    # Save to user stickers if requested
    save_as_sticker = request.POST.get('save_as_sticker') in ('true', '1', True)
    if save_as_sticker and attachment_image and request.user.is_authenticated:
        try:
            from posts.models import UserSticker
            UserSticker.objects.create(user=request.user, image=attachment_image)
        except Exception:
            pass

    attachment_meta = {}
    meta_raw = request.POST.get('attachment_meta')
    if meta_raw:
        try:
            attachment_meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
        except Exception:
            attachment_meta = {}

    comment = add_comment_to_post(
        post=post,
        author=request.user,
        content=content,
        parent_comment=parent_comment,
        attachment_type=attachment_type,
        attachment_image=attachment_image,
        attachment_url=attachment_url,
        attachment_meta=attachment_meta
    )
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
    like_payload = {
        'type': 'comment_like_update',
        'comment_id': comment.id,
        'likes_count': comment.likes.count()
    }
    async_to_sync(channel_layer.group_send)(
        f"post_comments_{comment.post.id}",
        like_payload
    )
    if hasattr(comment.post, 'share_id') and comment.post.share_id:
        async_to_sync(channel_layer.group_send)(
            f"post_comments_{comment.post.share_id}",
            like_payload
        )
    
    if comment.is_liked_by(user):
        return {
            'comment': comment,
            'liked_comment_ids': {
                comment.id} }
    return {
        'comment': comment,
        'liked_comment_ids': set() }


def add_comment_to_image(post_image, author, content, attachment_type='none', attachment_image=None, attachment_url='', attachment_meta=None):
    """Add a comment to a post image, mirroring the post comment functionality"""
    content = (content or '').strip()
    has_attachment = attachment_type != Comment.ATTACHMENT_NONE and (bool(attachment_image) or bool(attachment_url))
    if not content and not has_attachment:
        return None
    
    comment = PostImageComment.objects.create(
        post_image=post_image,
        author=author,
        content=content,
        attachment_type=attachment_type or Comment.ATTACHMENT_NONE,
        attachment_image=attachment_image,
        attachment_url=attachment_url or '',
        attachment_meta=attachment_meta or {}
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
                'attachment_type': comment.attachment_type,
                'attachment_url': comment.media_url,
                'attachment_meta': comment.attachment_meta,
                'created_at': comment.created_at.isoformat()
            }
        }
    )
    
    return comment


def handle_add_image_comment_request(request, post_image):
    """Handle adding a comment to a post image, mirroring the post comment functionality"""
    import json
    content = request.POST.get('content', '')
    attachment_type = request.POST.get('attachment_type', Comment.ATTACHMENT_NONE)
    attachment_url = request.POST.get('attachment_url', '')
    attachment_image = request.FILES.get('attachment_image') or request.FILES.get('image')

    save_as_sticker = request.POST.get('save_as_sticker') in ('true', '1', True)
    if save_as_sticker and attachment_image and request.user.is_authenticated:
        try:
            from posts.models import UserSticker
            UserSticker.objects.create(user=request.user, image=attachment_image)
        except Exception:
            pass

    attachment_meta = {}
    meta_raw = request.POST.get('attachment_meta')
    if meta_raw:
        try:
            attachment_meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
        except Exception:
            attachment_meta = {}

    comment = add_comment_to_image(
        post_image=post_image,
        author=request.user,
        content=content,
        attachment_type=attachment_type,
        attachment_image=attachment_image,
        attachment_url=attachment_url,
        attachment_meta=attachment_meta
    )
    if comment:
        messages.success(request, 'Comment added successfully.')
    else:
        messages.error(request, 'Comment cannot be empty.')
    return comment

