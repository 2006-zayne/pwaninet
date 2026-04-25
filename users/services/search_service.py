from django.core.cache import cache
from posts.queries.search_queries import get_following_ids, get_user_groups, search_groups, search_users

def build_search_context(user, raw_query):
    query = (raw_query or '').strip()
    cache_key = f'search:context:user:{user.id}:q:{query.lower()}'
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return cached_context
    following_ids = list(get_following_ids(user))
    user_groups = get_user_groups(user)
    users = search_users(query, user)
    groups = search_groups(query)
    context = {
        'query': query,
        'users': users,
        'groups': groups,
        'following_ids': following_ids,
    }
    if query:
        cache.set(cache_key, context, timeout=60)
    return context
