import random
from django.core.cache import cache
from posts.queries.feed_queries import (
    get_following_ids, get_liked_post_ids_for_user,
    get_prioritized_feed_queryset, get_suggested_groups,
    get_user_group_ids, get_user_suggestions_from_groups
)

FEED_PAGE_SIZE = 10

def build_home_feed_context(user, page=1):
    page = max(1, int(page))
    cache_key = f'feed:home_context:user:{user.id}:page:{page}'
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context

    following_ids = get_following_ids(user)
    group_ids = get_user_group_ids(user)
    # get_prioritized_feed_queryset handles the ranking algorithm logic
    feed_qs = get_prioritized_feed_queryset(user, following_ids, group_ids)

    # Optimize the queryset to avoid N+1 issues when rendering the feed
    feed_qs = feed_qs.select_related('author', 'unit', 'group', 'course')

    start = (page - 1) * FEED_PAGE_SIZE
    # Fetch one extra item to check for next page presence efficiently
    posts = list(feed_qs[start : start + FEED_PAGE_SIZE + 1])
    has_next = len(posts) > FEED_PAGE_SIZE
    if has_next:
        posts = posts[:-1]

    post_ids = [p.id for p in posts]
    liked_post_ids = get_liked_post_ids_for_user(user, post_ids)
    suggested_groups = get_suggested_groups(user, following_ids)
    user_suggestions = get_user_suggestions_from_groups(user)

    context = {
        'posts': posts,
        'liked_post_ids': liked_post_ids,
        'suggested_groups': suggested_groups,
        'suggested_friends': user_suggestions,
        'following_ids': following_ids,
        'suggestion_index': random.randint(2, 6) if user_suggestions else None,
        'page': page,
        'has_next': has_next,
    }
    cache.set(cache_key, context, timeout=60)
    return context


def invalidate_home_feed_context(user_id):
    # Invalidate the first several pages of the home feed cache
    keys = [f'feed:home_context:user:{user_id}:page:{i}' for i in range(1, 11)]
    cache.delete_many(keys)
