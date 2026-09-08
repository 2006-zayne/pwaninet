"""
User / Friend Recommendation Service.
Multi-tier ranking engine for recommending classmates and peers on PwaniNet.
"""

import logging
from django.core.cache import cache
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from users.models import Follow, User
from groups.models import Membership, MembershipStatus

logger = logging.getLogger(__name__)


def get_friend_suggestions_for_user(user, limit=10, use_cache=True, context='general'):
    """
    Get ranked friend/classmate suggestions for a user.

    Ranking Tiers:
    - Tier 1: Same programme and academic level (exact classmates: +100pts)
    - Tier 2: Same department / school (+35pts / +20pts)
    - Tier 3: Shared approved groups (+20pts each) and Mutual connections (+15pts each)
    - Tier 4: Profile completeness & active campus peers (+10pts avatar bonus, recency)

    Args:
        user: The User instance to get suggestions for.
        limit: Maximum suggestions to return (default 10).
        use_cache: Whether to read from/write to cache (default True).
        context: Context tag ('onboarding', 'feed', 'general').

    Returns:
        List of User instances annotated with recommendation score and reason.
    """
    if not user or not user.is_authenticated:
        return []

    limit = max(1, min(limit, 50))
    cache_key = f'recommendations:users:{user.id}:limit:{limit}:{context}'

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    # Direct follow exclusion
    already_following = set(
        Follow.objects.filter(follower=user).values_list('followed_id', flat=True)
    )

    # Approved user groups for shared community scoring
    my_group_ids = list(
        Membership.objects.filter(
            user=user,
            status=MembershipStatus.APPROVED
        ).values_list('group_id', flat=True)
    )

    # Base candidate pool: active users excluding self and already followed
    candidates = User.objects.filter(is_active=True).exclude(
        Q(id__in=already_following) | Q(id=user.id)
    )

    # ----------------- ACADEMIC ALIGNMENT SCORING -----------------
    academic_clauses = []

    # Modern schema matching
    if getattr(user, 'programme_id', None) and getattr(user, 'academic_level_id', None):
        academic_clauses.append(
            When(
                programme_id=user.programme_id,
                academic_level_id=user.academic_level_id,
                then=Value(100)
            )
        )
    if getattr(user, 'programme_id', None):
        academic_clauses.append(
            When(programme_id=user.programme_id, then=Value(60))
        )

    # Legacy schema fallback
    if getattr(user, 'course_id', None) and getattr(user, 'year_id', None):
        academic_clauses.append(
            When(course_id=user.course_id, year_id=user.year_id, then=Value(100))
        )
    elif getattr(user, 'course_id', None):
        academic_clauses.append(
            When(course_id=user.course_id, then=Value(60))
        )

    # Level / Year match
    if getattr(user, 'academic_level_id', None):
        academic_clauses.append(
            When(academic_level_id=user.academic_level_id, then=Value(25))
        )
    elif getattr(user, 'year_id', None):
        academic_clauses.append(
            When(year_id=user.year_id, then=Value(25))
        )

    # Department & School match if programme department is available
    if getattr(user, 'programme', None) and getattr(user.programme, 'department_id', None):
        academic_clauses.append(
            When(programme__department_id=user.programme.department_id, then=Value(35))
        )
        if getattr(user.programme.department, 'school_id', None):
            academic_clauses.append(
                When(
                    programme__department__school_id=user.programme.department.school_id,
                    then=Value(20)
                )
            )

    # Semester match
    if getattr(user, 'semester_id', None):
        academic_clauses.append(
            When(semester_id=user.semester_id, then=Value(15))
        )

    if academic_clauses:
        academic_score_expr = Case(
            *academic_clauses,
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        academic_score_expr = Value(0, output_field=IntegerField())

    # ----------------- SOCIAL & COMMUNITY SCORING -----------------
    if my_group_ids:
        shared_groups_expr = Count(
            'group_memberships',
            filter=Q(
                group_memberships__group_id__in=my_group_ids,
                group_memberships__status=MembershipStatus.APPROVED
            ),
            distinct=True
        )
    else:
        shared_groups_expr = Value(0, output_field=IntegerField())

    if already_following:
        fof_expr = Count(
            'follower_relationships',
            filter=Q(follower_relationships__follower_id__in=already_following),
            distinct=True
        )
    else:
        fof_expr = Value(0, output_field=IntegerField())

    # Profile completeness signal
    avatar_bonus_expr = Case(
        When(
            ~Q(profile_pic='profile_pic/default_pic1.jpg') &
            Q(profile_pic__isnull=False) &
            ~Q(profile_pic=''),
            then=Value(10)
        ),
        default=Value(0),
        output_field=IntegerField()
    )

    candidates = candidates.annotate(
        academic_score=academic_score_expr,
        shared_groups_count=shared_groups_expr,
        fof_count=fof_expr,
        avatar_bonus=avatar_bonus_expr,
    ).annotate(
        recommendation_score=(
            F('academic_score') +
            (F('shared_groups_count') * 20) +
            (F('fof_count') * 15) +
            F('avatar_bonus')
        )
    ).select_related(
        'programme',
        'academic_level',
        'academic_year',
        'semester',
        'course',
        'year'
    ).order_by('-recommendation_score', '-date_joined')

    results = list(candidates[:limit])

    # Attach human-readable recommendation reasons for UI badges
    for candidate in results:
        candidate.recommendation_reason = _determine_user_reason(user, candidate)

    if use_cache:
        cache.set(cache_key, results, timeout=300)

    return results


def _determine_user_reason(current_user, candidate):
    """Determine the most relevant explanation badge for candidate."""
    if current_user.programme_id and candidate.programme_id == current_user.programme_id:
        if (
            current_user.academic_level_id and
            candidate.academic_level_id == current_user.academic_level_id
        ):
            return "Classmate • Same Year"
        return f"{candidate.programme.name[:25]}" if candidate.programme else "Same Programme"

    if current_user.course_id and candidate.course_id == current_user.course_id:
        if current_user.year_id and candidate.year_id == current_user.year_id:
            return "Classmate • Same Year"
        return "Same Course"

    if getattr(candidate, 'shared_groups_count', 0) > 0:
        count = candidate.shared_groups_count
        return f"{count} shared group{'s' if count > 1 else ''}"

    if getattr(candidate, 'fof_count', 0) > 0:
        return "Followed by your connections"

    if candidate.academic_level_id and candidate.academic_level_id == current_user.academic_level_id:
        return f"{candidate.academic_level.name}"

    return "Popular on campus"


def invalidate_user_recommendations_cache(user_id):
    """Invalidate all cached friend suggestions for a user."""
    for limit in (5, 8, 10, 15, 20):
        for context in ('general', 'onboarding', 'feed'):
            cache.delete(f'recommendations:users:{user_id}:limit:{limit}:{context}')
    # Also invalidate legacy keys if present
    for limit in (5, 10):
        cache.delete(f'friend_suggestions:user:{user_id}:limit:{limit}')
        cache.delete(f'feed:user_suggestions:{user_id}')
