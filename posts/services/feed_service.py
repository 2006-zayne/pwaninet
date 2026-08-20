import random
from datetime import datetime
from django.core.cache import cache
from django.db.models import Q, Count
from posts.queries.feed_queries import (
    get_following_ids, get_liked_post_ids_for_user,
    get_suggested_groups, get_user_group_ids,
    get_user_suggestions_from_groups
)
from posts.models import Post

FEED_PAGE_SIZE = 10


def encode_cursor(post):
    """Encode post id and created_at into a cursor string."""
    return f"{post.id}|{post.created_at.timestamp()}"


def decode_cursor(cursor_string):
    """Decode cursor string into post id and created_at."""
    if not cursor_string:
        return None
    try:
        parts = cursor_string.split('|')
        if len(parts) != 2:
            return None
        post_id = int(parts[0])
        created_at_timestamp = float(parts[1])
        from datetime import datetime, timezone
        created_at = datetime.fromtimestamp(created_at_timestamp, tz=timezone.utc)
        return {'id': post_id, 'created_at': created_at}
    except (ValueError, IndexError):
        return None


def get_ranked_feed(user, cursor=None, limit=10):
    """
    Get ranked feed with cursor-based pagination (scales well).
    
    Args:
        user: The user requesting the feed
        cursor: Optional cursor string for pagination
        limit: Number of posts to return (default 10)
    
    Returns:
        dict with posts, next_cursor, has_more
    """
    # Get user's relationships
    following_ids = get_following_ids(user)
    group_ids = get_user_group_ids(user)
    
    # Use the improved feed algorithm from feed_queries (includes filters)
    from posts.queries.feed_queries import get_prioritized_feed_queryset
    feed_qs = get_prioritized_feed_queryset(user, following_ids, group_ids)
    
    # Apply cursor filtering if provided
    cursor_data = decode_cursor(cursor)
    if cursor_data:
        # Filter posts that come after the cursor post
        # Since we order by -priority_tier, -engagement_score, -created_at, -id
        # We use id and created_at for reliable pagination
        feed_qs = feed_qs.filter(
            Q(created_at__lt=cursor_data['created_at']) |
            Q(created_at=cursor_data['created_at'], id__lt=cursor_data['id'])
        )
    
    # Fetch one extra to check if there are more results
    posts = list(feed_qs[:limit + 1])
    has_more = len(posts) > limit
    
    if has_more:
        posts = posts[:limit]
        next_cursor = encode_cursor(posts[-1])
    else:
        next_cursor = None
    
    return {
        'posts': posts,
        'next_cursor': next_cursor,
        'has_more': has_more
    }


def build_home_feed_context(user, cursor=None, limit=10):
    """Build context for home feed with cursor-based pagination."""
    feed_data = get_ranked_feed(user, cursor=cursor, limit=limit)
    
    posts = feed_data['posts']
    post_ids = [p.id for p in posts]
    liked_post_ids = get_liked_post_ids_for_user(user, post_ids)
    
    # Cache following_ids for 60 seconds to reduce database queries
    following_ids_cache_key = f'feed:following_ids:{user.id}'
    following_ids = cache.get(following_ids_cache_key)
    if following_ids is None:
        following_ids = get_following_ids(user)
        cache.set(following_ids_cache_key, following_ids, timeout=60)
    
    # Only include group suggestions on initial load (no cursor)
    is_initial_load = cursor is None
    
    context = {
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'following_ids': following_ids,
        'next_cursor': feed_data['next_cursor'],
        'has_more': feed_data['has_more'],
    }
    
    if is_initial_load:
        # Cache suggested groups for 5 minutes
        suggested_groups_cache_key = f'feed:suggested_groups:{user.id}'
        suggested_groups = cache.get(suggested_groups_cache_key)
        if suggested_groups is None:
            suggested_groups = get_suggested_groups(user, following_ids)
            cache.set(suggested_groups_cache_key, list(suggested_groups), timeout=300)
        context['suggested_groups'] = suggested_groups
    
    # Friend suggestions appear in feed on all loads (initial and paginated)
    # Cache user suggestions for 5 minutes
    user_suggestions_cache_key = f'feed:user_suggestions:{user.id}'
    user_suggestions = cache.get(user_suggestions_cache_key)
    if user_suggestions is None:
        user_suggestions = get_user_suggestions_from_groups(user)
        cache.set(user_suggestions_cache_key, list(user_suggestions), timeout=300)
    
    context['suggested_users'] = user_suggestions
    context['following_ids'] = following_ids
    context['suggestion_index'] = random.randint(2, 6) if user_suggestions else None
    
    return context
