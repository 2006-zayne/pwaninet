"""
Privacy and User Discoverability Service for PwaniNet.

Provides authoritative, reusable query filters that enforce PwaniNet's
profile privacy levels, bidirectional block rules, hidden authors, and
author preferences across people discovery, recommendations, and search.
"""

from typing import Any, Optional, Set
from django.db.models import Q, QuerySet
from users.models import Block, Follow, HiddenAuthor, PrivacyLevel, User
from posts.models import AuthorPreference


def apply_user_discovery_exclusions(
    queryset: QuerySet,
    viewer: Optional[Any] = None,
    following_ids: Optional[Any] = None,
) -> QuerySet:
    """
    Apply authoritative PwaniNet privacy and social relationship exclusions
    to a candidate User queryset.

    Rules enforced:
    1. Active Status: Candidate must be active (is_active=True).
    2. Self-Exclusion: Viewer cannot discover themselves (exclude id=viewer.id).
    3. Block Exclusions: Bidirectional blocks are excluded (blocker=viewer OR blocked=viewer).
    4. Hidden Author Exclusions: Users hidden by the viewer (hider=viewer) are excluded.
    5. Author Preference Exclusions: Authors for whom viewer selected 'none' preference are excluded.
    6. Profile Privacy:
       - PRIVATE: Never discoverable by other users.
       - FOLLOWERS: Discoverable only if viewer follows candidate.
       - AUTHENTICATED: Discoverable only if viewer is authenticated.
       - PUBLIC: Discoverable by anyone.

    Args:
        queryset: Base User QuerySet to filter.
        viewer: The requesting User instance (authenticated or anonymous/None).

    Returns:
        Filtered User QuerySet conforming to all privacy boundaries.
    """
    # 1. Base filter: candidate must be active
    qs = queryset.filter(is_active=True)

    is_auth = viewer is not None and getattr(viewer, "is_authenticated", False)
    viewer_id = getattr(viewer, "id", None) if is_auth else None

    if not is_auth or viewer_id is None:
        # Unauthenticated: Only PUBLIC profiles, no blocks to evaluate
        return qs.none()

    # 2. Exclude requester themselves
    excluded_ids: Set[int] = {viewer_id}

    # 3. Exclude bidirectional blocks
    blocked_ids = Block.objects.filter(blocker_id=viewer_id).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked_id=viewer_id).values_list('blocker_id', flat=True)
    excluded_ids.update(blocked_ids)
    excluded_ids.update(blocked_by_ids)

    # 4. Exclude hidden authors
    hidden_ids = HiddenAuthor.objects.filter(hider_id=viewer_id).values_list('hidden_author_id', flat=True)
    excluded_ids.update(hidden_ids)

    # 5. Exclude AuthorPreference 'none'
    see_none_ids = AuthorPreference.objects.filter(user_id=viewer_id, preference='none').values_list('author_id', flat=True)
    excluded_ids.update(see_none_ids)

    # 6. Apply excluded IDs
    qs = qs.exclude(id__in=excluded_ids)

    # 7. Evaluate profile privacy
    if following_ids is None:
        following_ids = list(Follow.objects.filter(follower_id=viewer_id).values_list('followed_id', flat=True))
    else:
        following_ids = list(following_ids)

    privacy_q = (
        Q(profile_privacy=PrivacyLevel.AUTHENTICATED) |
        Q(profile_privacy=PrivacyLevel.FOLLOWERS, id__in=following_ids)
    )

    return qs.filter(privacy_q)


def get_discoverable_users(viewer: Optional[Any] = None) -> QuerySet:
    """
    Convenience method returning all discoverable User records for the given viewer.
    """
    return apply_user_discovery_exclusions(User.objects.all(), viewer=viewer)


def can_view_profile(viewer: Optional[Any], profile_user: User) -> bool:
    """Return whether the viewer may see a user's full profile."""
    if not profile_user.is_active:
        return False
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        if viewer.pk == profile_user.pk:
            return True
        if Block.objects.filter(blocker_id=profile_user.pk, blocked_id=viewer.pk).exists():
            return False
        if Block.objects.filter(blocker_id=viewer.pk, blocked_id=profile_user.pk).exists():
            return False
        if profile_user.profile_privacy == PrivacyLevel.AUTHENTICATED:
            return True
        if profile_user.profile_privacy == PrivacyLevel.FOLLOWERS:
            return Follow.objects.filter(follower_id=viewer.pk, followed_id=profile_user.pk).exists()
    return False


def visible_posts_for(viewer: Optional[Any], queryset: Optional[QuerySet] = None) -> QuerySet:
    """Filter posts to those visible to a viewer, including block and group rules."""
    from posts.models import Post
    from groups.models import Membership, MembershipStatus

    qs = queryset if queryset is not None else Post.objects.all()
    if viewer is None or not getattr(viewer, 'is_authenticated', False):
        return qs.filter(visibility='PUBLIC')

    followed_author_ids = Follow.objects.filter(follower_id=viewer.pk).values_list('followed_id', flat=True)
    visible = (
        Q(author_id=viewer.pk) |
        Q(visibility__in=['PUBLIC', PrivacyLevel.AUTHENTICATED]) |
        Q(visibility=PrivacyLevel.FOLLOWERS, author_id__in=followed_author_ids)
    )
    group_ids = Membership.objects.filter(user_id=viewer.pk, status=MembershipStatus.APPROVED).values_list('group_id', flat=True)
    visible &= Q(group__isnull=True) | Q(group_id__in=group_ids)
    qs = qs.filter(visible)
    blocked_ids = Block.objects.filter(blocker_id=viewer.pk).values_list('blocked_id', flat=True)
    blocked_by_ids = Block.objects.filter(blocked_id=viewer.pk).values_list('blocker_id', flat=True)
    hidden_author_ids = HiddenAuthor.objects.filter(hider_id=viewer.pk).values_list('hidden_author_id', flat=True)
    return (qs.exclude(author_id__in=blocked_ids)
            .exclude(author_id__in=blocked_by_ids)
            .exclude(author_id__in=hidden_author_ids))
