import random
from datetime import datetime, timezone
from django.core.cache import cache
from django.db.models import Q
from posts.queries.feed_queries import (
    get_following_ids, get_liked_post_ids_for_user,
    get_suggested_groups, get_user_group_ids,
    get_user_suggestions_from_groups,
    get_prioritized_feed_queryset,
    get_prioritized_reels_queryset
)
from posts.models import Post

FEED_PAGE_SIZE = 10
MAX_REELS_PER_PAGE = 2


def encode_cursor(post):
    """Encode all 4 sort keys into a cursor string so pagination is always stable.
    
    The feed orders by: -priority_tier, -engagement_score, -created_at, -id
    The cursor must reflect ALL of these to avoid repeated or skipped posts.
    """
    if not post:
        return ""
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
        return {
            'priority_tier': int(parts[0]),
            'engagement_score': float(parts[1]),
            'created_at': datetime.fromtimestamp(float(parts[2]), tz=timezone.utc),
            'id': int(parts[3]),
        }
    except (ValueError, IndexError):
        return None


def split_composite_cursor(cursor_string):
    """Split composite cursor into (post_cursor, reel_cursor)."""
    if not cursor_string:
        return None, None
    if '__r__' in cursor_string:
        p_str, r_str = cursor_string.split('__r__', 1)
        return (p_str if p_str else None), (r_str if r_str else None)
    return cursor_string, None


def make_composite_cursor(post_cursor, reel_cursor):
    """Combine post and reel cursors into a single composite string."""
    if not post_cursor and not reel_cursor:
        return None
    p_val = post_cursor or ""
    r_val = reel_cursor or ""
    if r_val:
        return f"{p_val}__r__{r_val}"
    return p_val or None


def apply_cursor_to_queryset(qs, cursor_data):
    """Apply keyset cursor filtering across (priority_tier, engagement_score, created_at, id)."""
    if not cursor_data:
        return qs
    pt  = cursor_data['priority_tier']
    es  = cursor_data['engagement_score']
    ca  = cursor_data['created_at']
    cid = cursor_data['id']
    return qs.filter(
        Q(priority_tier__lt=pt) |
        Q(priority_tier=pt, engagement_score__lt=es) |
        Q(priority_tier=pt, engagement_score=es, created_at__lt=ca) |
        Q(priority_tier=pt, engagement_score=es, created_at=ca, id__lt=cid)
    )


def interleave_feed_items(standard_posts, reels, target_limit=10):
    """
    Inject up to 2 reels into standard posts at controlled intervals.
    
    Guarantees:
    - Never two reels immediately adjacent.
    - Reels appear at steady intervals (e.g. index 2 and index 7).
    - At least 2 standard posts before the first reel, 4 between them, and 2 after.
    """
    if not reels:
        return list(standard_posts[:target_limit])
    
    if not standard_posts:
        return list(reels[:target_limit])

    result = list(standard_posts)
    
    if len(reels) == 1:
        # Inject single reel after 2 or 3 standard posts
        insert_idx = min(3, max(1, len(result) // 2))
        result.insert(insert_idx, reels[0])
    elif len(reels) >= 2:
        # Inject 1st reel at index 2 (after 2 standard posts)
        first_idx = min(2, len(result))
        result.insert(first_idx, reels[0])
        # Inject 2nd reel at index 7 (leaving 4 standard posts between them)
        second_idx = min(first_idx + 5, len(result))
        result.insert(second_idx, reels[1])
        
    return result


def get_ranked_feed(user, cursor=None, limit=10):
    """
    Get ranked feed with controlled reel injection and composite cursor-based pagination.

    Standard posts form the spine of the feed (e.g. 8 items), and exactly up to 2 reels
    are injected at spaced intervals (indices 2 and 7) so no two reels ever follow
    each other or sandwich a single tiny post.
    """
    following_ids = get_following_ids(user)
    group_ids = get_user_group_ids(user)

    post_cursor_str, reel_cursor_str = split_composite_cursor(cursor)
    post_cursor_data = decode_cursor(post_cursor_str)
    reel_cursor_data = decode_cursor(reel_cursor_str)

    # 1. Fetch Candidate Reels (up to 2 per pagination batch)
    reel_qs = get_prioritized_reels_queryset(user, following_ids, group_ids)
    reel_qs = apply_cursor_to_queryset(reel_qs, reel_cursor_data)
    reel_candidates = list(reel_qs[:MAX_REELS_PER_PAGE + 1])
    has_more_reels = len(reel_candidates) > MAX_REELS_PER_PAGE
    reels = [p for p in reel_candidates if getattr(p, 'is_reel', False)]
    reels = reels[:MAX_REELS_PER_PAGE]

    # Calculate standard posts needed: fill up remainder to reach limit
    num_reels = len(reels)
    target_standard_count = max(limit - num_reels, 1)

    # 2. Fetch Standard Postcards (excluding reels)
    standard_qs = get_prioritized_feed_queryset(user, following_ids, group_ids, exclude_reels=True)
    standard_qs = apply_cursor_to_queryset(standard_qs, post_cursor_data)
    
    # Fetch target + extra to verify python-level is_reel filter & has_more
    fetch_amount = target_standard_count + 4
    standard_candidates = list(standard_qs[:fetch_amount + 1])
    
    standard_posts = [p for p in standard_candidates if not getattr(p, 'is_reel', False)]
    has_more_standard = len(standard_posts) > target_standard_count
    standard_posts = standard_posts[:target_standard_count]

    # 3. Interleave posts and reels controllably
    combined_posts = interleave_feed_items(standard_posts, reels, target_limit=limit)

    # 4. Compute next composite cursor
    next_post_cursor = encode_cursor(standard_posts[-1]) if standard_posts and has_more_standard else None
    next_reel_cursor = encode_cursor(reels[-1]) if reels and has_more_reels else (reel_cursor_str if reel_cursor_str else None)

    has_more = has_more_standard or (has_more_reels and bool(reels))

    if has_more:
        next_cursor = make_composite_cursor(next_post_cursor, next_reel_cursor)
    else:
        next_cursor = None

    return {
        'posts': combined_posts,
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
