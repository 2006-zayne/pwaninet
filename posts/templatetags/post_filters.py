import json
from django import template

register = template.Library()


@register.filter
def hex_to_rgba(hex_color, alpha):
    """
    Convert a hex color string to rgba format with the given alpha value.
    Example: '#0084ff' with alpha 0.06 -> 'rgba(0, 132, 255, 0.06)'
    
    Args:
        hex_color (str): Hex color string (e.g., "#0084ff" or "0084ff")
        alpha (float or str): Alpha transparency value between 0 and 1
        
    Returns:
        RGBA color string (e.g., "rgba(255, 255, 255, 0.06)")
    """
    if not hex_color:
        return f'rgba(0, 0, 0, {alpha})'
    hex_color = hex_color.lstrip('#')
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f'rgba({r}, {g}, {b}, {alpha})'
    except Exception:
        return f'rgba(0, 0, 0, {alpha})'


@register.simple_tag(takes_context=True)
def check_is_liked(context, post):
    """
    Determine whether the current user has liked this post.
    Checks in order:
    1. context['is_liked'] ONLY if context.get('post') == post (single post rendering)
    2. context['liked_post_ids'] (set of post IDs/share_ids populated by feed services/views)
    3. Direct database check via post.is_liked_by(user) if user is authenticated
    """
    if not post:
        return False

    if 'is_liked' in context and context['is_liked'] is not None:
        ctx_post = context.get('post')
        if ctx_post and (ctx_post == post or getattr(ctx_post, 'id', None) == getattr(post, 'id', None)):
            return bool(context['is_liked'])

    liked_post_ids = context.get('liked_post_ids')
    if liked_post_ids is not None:
        post_id = getattr(post, 'id', None)
        share_id = getattr(post, 'share_id', None)
        if (post_id in liked_post_ids) or (share_id in liked_post_ids) or (str(share_id) in liked_post_ids):
            return True
        # If liked_post_ids was explicitly calculated for this feed/set, trust it!
        return False

    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return post.is_liked_by(request.user)

    return False


@register.simple_tag(takes_context=True)
def check_is_reposted(context, post):
    """
    Determine whether the current user has reposted this post.
    """
    if not post:
        return False

    if 'user_has_reposted' in context and context['user_has_reposted'] is not None:
        ctx_post = context.get('post')
        if ctx_post and (ctx_post == post or getattr(ctx_post, 'id', None) == getattr(post, 'id', None)):
            return bool(context['user_has_reposted'])

    reposted_post_ids = context.get('reposted_post_ids')
    if reposted_post_ids is not None:
        post_id = getattr(post, 'id', None)
        share_id = getattr(post, 'share_id', None)
        if (post_id in reposted_post_ids) or (share_id in reposted_post_ids) or (str(share_id) in reposted_post_ids):
            return True
        return False

    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return post.is_reposted_by(request.user)

    return False


@register.filter
def repost_avatars(post, user=None):
    if not post or not hasattr(post, 'get_repost_avatars'):
        return []
    return post.get_repost_avatars(viewer=user, max_avatars=3)


@register.filter
def repost_badge_json(post, user=None):
    if not post or not hasattr(post, 'get_repost_badge_data'):
        return "{}"
    try:
        return json.dumps(post.get_repost_badge_data(viewer=user, max_avatars=3))
    except Exception:
        return "{}"


@register.filter
def repost_header_info(post, user=None):
    if not post or not hasattr(post, 'get_repost_header_info'):
        return {'show': False}
    try:
        return post.get_repost_header_info(viewer=user)
    except Exception:
        return {'show': False}
