from django.db.models import Q
from users.models import Follow, User, GlobalRole
from groups.models import Group

def search_users(query, current_user, limit=20):
    if not query:
        return User.objects.none()

    query_lower = query.lower()

    from users.services.privacy import apply_user_discovery_exclusions
    discoverable = apply_user_discovery_exclusions(User.objects.all(), viewer=current_user)

    # Check for role keywords
    role_keywords = {
        'president': GlobalRole.PRESIDENT,
        'delegate': GlobalRole.DELEGATE,
        'verified': GlobalRole.VERIFIED,
    }

    # If query matches a role keyword, search by role
    if query_lower in role_keywords:
        return discoverable.filter(
            global_role=role_keywords[query_lower]
        ).exclude(id=current_user.id).select_related('course', 'year')[:limit]

    # Otherwise search by name/username
    return discoverable.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(second_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=current_user.id).select_related('course', 'year')[:limit]


def search_groups(query, limit=20):
    if not query:
        return Group.objects.none()
    return Group.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    ).select_related('course', 'year')[:limit]


def get_following_ids(user):
    return Follow.objects.filter(follower=user).values_list('followed_id', flat=True)


def get_user_groups(user):
    return Group.objects.filter(memberships__user=user)
