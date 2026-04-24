from django.core.cache import cache

from core.queries.feed_queries import (
    get_following_ids,
    get_liked_post_ids_for_user,
    get_prioritized_feed_queryset,
    get_suggested_groups,
    get_user_group_ids,
    get_user_suggestions_from_groups,
)
from core.services.friend_suggestion_service import get_friend_suggestions_for_user

FEED_PAGE_SIZE = 10


def build_home_feed_context(user, page=1):
    page = max(1, int(page))
    cache_key = f"feed:home_context:user:{user.id}:page:{page}"
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context

    following_ids = get_following_ids(user)
    user_group_ids = get_user_group_ids(user)

    start = (page - 1) * FEED_PAGE_SIZE
    end = start + FEED_PAGE_SIZE + 1
    posts_slice = list(
        get_prioritized_feed_queryset(user, following_ids, user_group_ids)[start:end]
    )
    has_next = len(posts_slice) > FEED_PAGE_SIZE
    posts = posts_slice[:FEED_PAGE_SIZE]
    liked_post_ids = get_liked_post_ids_for_user(user, [post.id for post in posts])

    context = {
        "posts": posts,
        "liked_post_ids": liked_post_ids,
        "has_next": has_next,
        "next_page": page + 1,
        "page": page,
        "title": "PwaniNet Command Feed",
        # Add suggested friends to ALL pages
        "suggested_friends": get_friend_suggestions_for_user(user, limit=10),
    }
    
    if page == 1:
        context["suggested_groups"] = get_suggested_groups(user, following_ids, limit=5)
        context["suggestions"] = get_user_suggestions_from_groups(user, limit=5)
        cache.set(cache_key, context, timeout=20)
    else:
        cache.set(cache_key, context, timeout=45)
    return context


def invalidate_home_feed_context(user_id):
    cache.delete(f"feed:home_context:user:{user_id}")
