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
    """Encode all 4 sort keys into a cursor string so pagination is always stable.
    
    The feed orders by: -priority_tier, -engagement_score, -created_at, -id
    The cursor must reflect ALL of these to avoid repeated or skipped posts.
    """
    return (
        f"{post.priority_tier}|"
        f"{post.engagement_score}|"
        f"{post.created_at.timestamp()}|"
        f"{post.id}"
    )


def decode_cursor(cursor_string):
    """Decode cursor string into all 4 sort key values."""
    if not cursor_string:
        return None
    try:
        parts = cursor_string.split('|')
        if len(parts) != 4:
            return None
        from datetime import datetime, timezone
        return {
            'priority_tier': int(parts[0]),
            'engagement_score': float(parts[1]),
            'created_at': datetime.fromtimestamp(float(parts[2]), tz=timezone.utc),
            'id': int(parts[3]),
        }
    except (ValueError, IndexError):
        return None


def get_ranked_feed(user, cursor=None, limit=10):
    """
    Get ranked feed with cursor-based pagination.

    Ordering: -priority_tier, -engagement_score, -created_at, -id
    Cursor encodes all 4 sort keys so that no post is ever repeated or skipped,
    even when many posts share the same timestamp or engagement score.

    Args:
        user: The user requesting the feed
        cursor: Optional cursor string for pagination
        limit: Number of posts to return (default 10)

    Returns:
        dict with posts, next_cursor, has_more
    """
    following_ids = get_following_ids(user)
    group_ids = get_user_group_ids(user)

    from posts.queries.feed_queries import get_prioritized_feed_queryset
    feed_qs = get_prioritized_feed_queryset(user, following_ids, group_ids)

    # Apply cursor filtering using all 4 sort columns.
    # This is the keyset-pagination equivalent of:
    #   WHERE (pt, es, ca, id) < (cursor_pt, cursor_es, cursor_ca, cursor_id)
    # ordered DESC on all keys.
    cursor_data = decode_cursor(cursor)
    if cursor_data:
        pt  = cursor_data['priority_tier']
        es  = cursor_data['engagement_score']
        ca  = cursor_data['created_at']
        cid = cursor_data['id']
        feed_qs = feed_qs.filter(
            # Lower priority_tier entirely
            Q(priority_tier__lt=pt) |
            # Same priority_tier, lower engagement_score
            Q(priority_tier=pt, engagement_score__lt=es) |
            # Same priority_tier + engagement_score, older created_at
            Q(priority_tier=pt, engagement_score=es, created_at__lt=ca) |
            # Same priority_tier + engagement_score + created_at, lower id (tie-break)
            Q(priority_tier=pt, engagement_score=es, created_at=ca, id__lt=cid)
        )

    # Fetch limit+1 to cheaply determine has_more
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
        'has_more': has_more,
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
        from recommendations.services.engine import UnifiedRecommendationEngine
        suggested_groups = UnifiedRecommendationEngine.get_recommended_groups(
            user, limit=5, context='feed'
        )
        context['suggested_groups'] = suggested_groups

    # Friend suggestions appear in feed on all loads (initial and paginated)
    from recommendations.services.engine import UnifiedRecommendationEngine
    user_suggestions = UnifiedRecommendationEngine.get_recommended_users(
        user, limit=5, context='feed'
    )
    
    context['suggested_users'] = user_suggestions
    context['following_ids'] = following_ids
    context['suggestion_index'] = random.randint(2, 6) if user_suggestions else None
    
    return context
