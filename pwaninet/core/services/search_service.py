from django.core.cache import cache

from core.queries.search_queries import (
    get_following_ids,
    get_user_groups,
    search_groups,
    search_users,
)


def build_search_context(user, raw_query):
    query = (raw_query or "").strip()
    cache_key = f"search:context:user:{user.id}:q:{query.lower()}"
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context

    context = {
        "query": query,
        "users": search_users(query, user, limit=20),
        "groups": search_groups(query, limit=20),
        "following_ids": get_following_ids(user),
        "user_groups": get_user_groups(user),
    }
    cache.set(cache_key, context, timeout=30)
    return context
