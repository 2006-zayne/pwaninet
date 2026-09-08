"""
Unified Recommendation Engine for PwaniNet.
Orchestrates multi-domain recommendations across Users, Groups, and Documents.
"""

import logging
from .user_recommender import (
    get_friend_suggestions_for_user,
    invalidate_user_recommendations_cache,
)
from .group_recommender import (
    get_recommended_groups_for_user,
    invalidate_group_recommendations_cache,
)
from .document_recommender import (
    get_for_you_documents,
    invalidate_document_recommendations_cache,
)

logger = logging.getLogger(__name__)


class UnifiedRecommendationEngine:
    """Unified facade service for intelligent entity recommendations."""

    @staticmethod
    def get_recommended_users(user, limit=10, use_cache=True, context='general'):
        """Fetch ranked friend / classmate recommendations."""
        return get_friend_suggestions_for_user(
            user=user,
            limit=limit,
            use_cache=use_cache,
            context=context
        )

    @staticmethod
    def get_recommended_groups(user, limit=8, use_cache=True, context='general'):
        """Fetch ranked group suggestions for feed, dashboard, or onboarding."""
        return get_recommended_groups_for_user(
            user=user,
            limit=limit,
            use_cache=use_cache,
            context=context
        )

    @staticmethod
    def get_for_you_documents(user, limit=8, use_cache=True):
        """Fetch curriculum-personalized documents for student's active units."""
        return get_for_you_documents(
            user=user,
            limit=limit,
            use_cache=use_cache
        )

    @classmethod
    def get_onboarding_data(cls, user):
        """
        Fetch combined pre-feed onboarding package.
        Returns suggested classmates, official joined groups, and discoverable groups.
        """
        from groups.models import Group, MembershipStatus

        classmates = cls.get_recommended_users(user, limit=12, use_cache=False, context='onboarding')
        recommended_groups = cls.get_recommended_groups(user, limit=8, use_cache=False, context='onboarding')

        # Identify official groups the user was already enrolled into
        enrolled_official_groups = list(
            Group.objects.filter(
                memberships__user=user,
                memberships__status=MembershipStatus.APPROVED,
                is_official=True
            ).select_related('programme', 'academic_level', 'course', 'year')
        )

        return {
            'classmates': classmates,
            'recommended_groups': recommended_groups,
            'official_groups': enrolled_official_groups,
        }

    @staticmethod
    def invalidate_all_user_caches(user_id):
        """Invalidate all recommendation caches when a user alters their graph/profile."""
        invalidate_user_recommendations_cache(user_id)
        invalidate_group_recommendations_cache(user_id)
        invalidate_document_recommendations_cache(user_id)
