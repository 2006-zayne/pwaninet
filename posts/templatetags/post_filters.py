from django import template

register = template.Library()

@register.filter
def hex_to_rgba(hex_color, alpha):
    """
    Convert hex color to rgba format.
    
    Args:
        hex_color: Hex color string (e.g., "#ffffff")
        alpha: Alpha value as string (e.g., "0.06")
    
    Returns:
        RGBA color string (e.g., "rgba(255, 255, 255, 0.06)")
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r}, {g}, {b}, {alpha})'


@register.simple_tag(takes_context=True)
def check_is_liked(context, post):
    """
    Determine whether the current user has liked this post.
    Checks in order:
    1. context['is_liked'] (if explicitly set by toggle_like view or post_detail_view)
    2. context['liked_post_ids'] (set of post IDs/share_ids populated by feed services/views)
    3. Direct database check via post.is_liked_by(user) if user is authenticated
    """
    if not post:
        return False

    if 'is_liked' in context and context['is_liked'] is not None:
        return bool(context['is_liked'])

    liked_post_ids = context.get('liked_post_ids')
    if liked_post_ids is not None:
        post_id = getattr(post, 'id', None)
        share_id = getattr(post, 'share_id', None)
        if (post_id in liked_post_ids) or (share_id in liked_post_ids) or (str(share_id) in liked_post_ids):
            return True
        return False

    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_authenticated:
        return post.is_liked_by(request.user)

    return False

