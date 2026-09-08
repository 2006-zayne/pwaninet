"""
Group Recommendation Service.
Multi-tier ranking engine for discovering groups on PwaniNet (Feed, Dashboard, Onboarding).
"""

import logging
from django.core.cache import cache
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from groups.models import Group, Membership, MembershipStatus
from users.models import Follow

logger = logging.getLogger(__name__)


def get_recommended_groups_for_user(user, limit=8, use_cache=True, context='general'):
    """
    Get ranked group recommendations for a user.

    Ranking Tiers:
    - Tier 1: Official & Study groups matching user's programme + level (+100pts / +80pts)
    - Tier 2: Department-wide & Programme-wide community groups (+60pts)
    - Tier 3: Groups where user's followed connections are active members (+15pts per connection)
    - Tier 4: Most active public campus communities (+2pts per member, recency)

    Args:
        user: The User instance.
        limit: Maximum groups to return.
        use_cache: Whether to use cache.
        context: Usage context ('explore', 'dashboard', 'onboarding', 'general').

    Returns:
        List of Group instances with attached member counts and recommendation reason.
    """
    if not user or not user.is_authenticated:
        # For anonymous or empty context, return popular public groups
        return list(
            Group.objects.annotate(
                member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))
            ).order_by('-member_count', '-created_at')[:limit]
        )

    limit = max(1, min(limit, 50))
    cache_key = f'recommendations:groups:{user.id}:limit:{limit}:{context}'

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    # Exclude groups where user already has membership (approved or pending)
    user_group_ids = set(
        Membership.objects.filter(
            user=user,
            status__in=[MembershipStatus.APPROVED, MembershipStatus.PENDING]
        ).values_list('group_id', flat=True)
    )

    following_ids = list(
        Follow.objects.filter(follower=user).values_list('followed_id', flat=True)
    )

    candidates = Group.objects.exclude(id__in=user_group_ids)

    # ----------------- ACADEMIC ALIGNMENT SCORING -----------------
    academic_clauses = []

    if getattr(user, 'programme_id', None) and getattr(user, 'academic_level_id', None):
        academic_clauses.append(
            When(
                is_official=True,
                programme_id=user.programme_id,
                academic_level_id=user.academic_level_id,
                then=Value(100)
            )
        )
        academic_clauses.append(
            When(
                programme_id=user.programme_id,
                academic_level_id=user.academic_level_id,
                then=Value(80)
            )
        )

    if getattr(user, 'programme_id', None):
        academic_clauses.append(
            When(programme_id=user.programme_id, then=Value(60))
        )

    if getattr(user, 'course_id', None) and getattr(user, 'year_id', None):
        academic_clauses.append(
            When(course_id=user.course_id, year_id=user.year_id, then=Value(80))
        )
    elif getattr(user, 'course_id', None):
        academic_clauses.append(
            When(course_id=user.course_id, then=Value(50))
        )

    if getattr(user, 'academic_level_id', None):
        academic_clauses.append(
            When(academic_level_id=user.academic_level_id, then=Value(30))
        )

    if academic_clauses:
        academic_score_expr = Case(
            *academic_clauses,
            default=Value(0),
            output_field=IntegerField()
        )
    else:
        academic_score_expr = Value(0, output_field=IntegerField())

    # ----------------- SOCIAL & POPULARITY SCORING -----------------
    if following_ids:
        following_members_expr = Count(
            'memberships',
            filter=Q(
                memberships__user_id__in=following_ids,
                memberships__status=MembershipStatus.APPROVED
            ),
            distinct=True
        )
    else:
        following_members_expr = Value(0, output_field=IntegerField())

    total_members_expr = Count(
        'memberships',
        filter=Q(memberships__status=MembershipStatus.APPROVED),
        distinct=True
    )

    candidates = candidates.annotate(
        academic_score=academic_score_expr,
        following_members_count=following_members_expr,
        member_count=total_members_expr,
    ).annotate(
        recommendation_score=(
            F('academic_score') +
            (F('following_members_count') * 15) +
            (F('member_count') * 2)
        )
    ).select_related(
        'programme',
        'academic_level',
        'course',
        'year',
        'created_by'
    ).order_by('-recommendation_score', '-member_count', '-created_at')

    results = list(candidates[:limit])

    for group in results:
        group.recommendation_reason = _determine_group_reason(user, group)

    if use_cache:
        cache.set(cache_key, results, timeout=300)

    return results


def _determine_group_reason(current_user, group):
    """Determine explanation label for recommended group."""
    if group.is_official:
        return "Official Course Group"

    if current_user.programme_id and group.programme_id == current_user.programme_id:
        return f"{group.programme.name[:25]}" if group.programme else "Your Programme"

    if getattr(group, 'following_members_count', 0) > 0:
        count = group.following_members_count
        return f"{count} connection{'s' if count > 1 else ''} joined"

    if getattr(group, 'member_count', 0) > 20:
        return "Popular Campus Group"

    return "Community Group"


def invalidate_group_recommendations_cache(user_id):
    """Invalidate cached group suggestions for a user."""
    for limit in (5, 8, 10, 15, 20):
        for context in ('general', 'explore', 'dashboard', 'onboarding', 'feed'):
            cache.delete(f'recommendations:groups:{user_id}:limit:{limit}:{context}')
    cache.delete(f'feed:suggested_groups:{user_id}')
