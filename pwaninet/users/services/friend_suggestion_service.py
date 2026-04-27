# Source Generated with Decompyle++
# File: friend_suggestion_service.cpython-312.pyc (Python 3.12)

'''
Friend suggestion service for personalized user recommendations.

Ranking algorithm considers:
- Same course (high priority: up to 90pts if course + year match)
- Same year (high priority: 40pts)
- Same group (medium priority: 20pts per group)
- Friend of friends (bonus consideration in future versions)

Returns randomized suggestions to avoid predictability.
'''
import random
from django.core.cache import cache
from posts.queries.feed_queries import get_user_suggestions_from_groups

def get_friend_suggestions_for_user(user, limit=5, use_cache=True):
    '''
    Get friend suggestions for a user with caching.
    
    Args:
        user: The User instance to get suggestions for
        limit: Maximum number of suggestions to return (5-10)
        use_cache: Whether to use cache (default: True)
    
    Returns:
        List of suggested User instances, ranked by score
    '''
    limit = min(max(limit, 5), 10)
    cache_key = f'friend_suggestions:user:{user.id}:limit:{limit}'
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    suggestions = list(get_user_suggestions_from_groups(user, limit))
    # No longer randomizing - results are now ranked by suggestion_score
    if use_cache:
        cache.set(cache_key, suggestions, timeout=300)
    return suggestions


def invalidate_friend_suggestions_cache(user_id):
    '''Invalidate friend suggestions cache when user follows someone.'''
    cache_key_pattern = f'friend_suggestions:user:{user_id}:*'
    for limit in (5, 10):
        cache_key = f'friend_suggestions:user:{user_id}:limit:{limit}'
        cache.delete(cache_key)

