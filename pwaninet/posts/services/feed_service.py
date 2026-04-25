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
    """Encode post score, created_at, and id into a cursor string."""
    score = post.score
    created_at = post.created_at.isoformat()
    post_id = post.id
    return f"{score}|{created_at}|{post_id}"


def decode_cursor(cursor_string):
    """Decode cursor string into score, created_at, and id."""
    if not cursor_string:
        return None
    try:
        parts = cursor_string.split('|')
        if len(parts) != 3:
            return None
        score = float(parts[0])
        created_at = datetime.fromisoformat(parts[1])
        post_id = int(parts[2])
        return {'score': score, 'created_at': created_at, 'id': post_id}
    except (ValueError, IndexError):
        return None


def get_ranked_feed(user, cursor=None, limit=10):
    """
    Get ranked feed with cursor-based pagination.
    
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
    
    # Build base queryset with filters for relevant posts
    base_qs = Post.objects.filter(
        Q(author_id__in=following_ids) |
        Q(group_id__in=group_ids) |
        Q(course=user.course, unit__year=user.year)
    )
    
    # Annotate with counts and compute score
    feed_qs = base_qs.annotate(
        like_count_annotated=Count('likes', distinct=True),
        comment_count_annotated=Count('comments', distinct=True),
        score=Count('likes', distinct=True) + (2 * Count('comments', distinct=True))
    )
    
    # Apply cursor filtering if provided
    cursor_data = decode_cursor(cursor)
    if cursor_data:
        feed_qs = feed_qs.filter(
            Q(score__lt=cursor_data['score']) |
            Q(score=cursor_data['score'], created_at__lt=cursor_data['created_at']) |
            Q(score=cursor_data['score'], created_at=cursor_data['created_at'], id__lt=cursor_data['id'])
        )
    
    # Order by score DESC, created_at DESC, id DESC
    feed_qs = feed_qs.order_by('-score', '-created_at', '-id')
    
    # Optimize with select_related and prefetch_related
    feed_qs = feed_qs.select_related('author', 'group', 'course', 'unit')
    feed_qs = feed_qs.prefetch_related('likes', 'comments')
    
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
    suggested_groups = get_suggested_groups(user, get_following_ids(user))
    user_suggestions = get_user_suggestions_from_groups(user)
    following_ids = get_following_ids(user)
    
    context = {
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'suggested_groups': suggested_groups,
        'suggested_friends': user_suggestions,
        'following_ids': following_ids,
        'suggestion_index': random.randint(2, 6) if user_suggestions else None,
        'next_cursor': feed_data['next_cursor'],
        'has_more': feed_data['has_more'],
    }
    return context


def invalidate_home_feed_context(user_id):
    # Cursor-based pagination doesn't require page-based cache invalidation
    # This function is kept for backwards compatibility
    pass
