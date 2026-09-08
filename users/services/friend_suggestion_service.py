"""
Friend suggestion service for personalized user recommendations.
Delegates to UnifiedRecommendationEngine.
"""

from django.core.cache import cache
from recommendations.services.engine import UnifiedRecommendationEngine


def get_friend_suggestions_for_user(user, limit=5, use_cache=True):
    """
    Get friend suggestions for a user with caching via UnifiedRecommendationEngine.
    """
    return UnifiedRecommendationEngine.get_recommended_users(
        user=user,
        limit=limit,
        use_cache=use_cache,
        context='general'
    )


def invalidate_friend_suggestions_cache(user_id):
    """Invalidate friend suggestions cache when user follows/unfollows someone."""
    UnifiedRecommendationEngine.invalidate_all_user_caches(user_id)
