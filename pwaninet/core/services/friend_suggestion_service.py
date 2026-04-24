"""
Friend suggestion service for personalized user recommendations.

Ranking algorithm considers:
- Same course (high priority: up to 90pts if course + year match)
- Same year (high priority: 40pts)
- Same group (medium priority: 20pts per group)
- Friend of friends (bonus consideration in future versions)

Returns randomized suggestions to avoid predictability.
"""

import random
from django.core.cache import cache
from core.queries.feed_queries import get_friend_suggestions


def get_friend_suggestions_for_user(user, limit=5, use_cache=True):
    """
    Get friend suggestions for a user with caching.
    
    Args:
        user: The User instance to get suggestions for
        limit: Maximum number of suggestions to return (5-10)
        use_cache: Whether to use cache (default: True)
    
    Returns:
        List of suggested User instances, randomized
    """
    limit = min(max(limit, 5), 10)  # Ensure between 5-10
    cache_key = f"friend_suggestions:user:{user.id}:limit:{limit}"
    
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    # Get suggestions from query
    suggestions = get_friend_suggestions(user, limit=limit)
    
    # Randomize the order for variety
    suggestions_list = list(suggestions)
    random.shuffle(suggestions_list)
    
    # Cache for 1 hour
    cache.set(cache_key, suggestions_list, timeout=3600)
    
    return suggestions_list


def invalidate_friend_suggestions_cache(user_id):
    """Invalidate friend suggestions cache when user follows someone."""
    # Delete all cached suggestions for this user
    cache_key_pattern = f"friend_suggestions:user:{user_id}:*"
    
    # We'll delete specific keys we know about
    for limit in [5, 10]:
        cache_key = f"friend_suggestions:user:{user_id}:limit:{limit}"
        cache.delete(cache_key)
