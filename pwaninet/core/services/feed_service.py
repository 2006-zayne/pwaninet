# Source Generated with Decompyle++
# File: feed_service.cpython-312.pyc (Python 3.12)

from django.core.cache import cache
from core.queries.feed_queries import get_following_ids, get_liked_post_ids_for_user, get_prioritized_feed_queryset, get_suggested_groups, get_user_group_ids, get_user_suggestions_from_groups
FEED_PAGE_SIZE = 10

def build_home_feed_context(user, page = (1,)):
    page = max(1, int(page))
    cache_key = f'''feed:home_context:user:{user.id}:page:{page}'''
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context
    following_ids = get_following_ids(user)
    group_ids = get_user_group_ids(user)
    liked_post_ids = get_liked_post_ids_for_user(user)
    feed_qs = get_prioritized_feed_queryset(user, following_ids, group_ids)
    start = (page - 1) * FEED_PAGE_SIZE
    end = start + FEED_PAGE_SIZE
    posts = feed_qs[start:end]
    suggested_groups = get_suggested_groups(user, group_ids)
    user_suggestions = get_user_suggestions_from_groups(user, group_ids)
    context = {
        'posts': list(posts),
        'liked_post_ids': liked_post_ids,
        'suggested_groups': suggested_groups,
        'user_suggestions': user_suggestions,
        'page': page,
        'has_next': feed_qs.count() > end,
    }
    cache.set(cache_key, context, timeout=60)
    return context


def invalidate_home_feed_context(user_id):
    cache.delete(f'''feed:home_context:user:{user_id}''')

