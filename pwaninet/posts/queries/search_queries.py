from django.db.models import Q
from users.models import Follow, User, GlobalRole
from groups.models import Group

def search_users(query, current_user, limit=20):
    if not query:
        return User.objects.none()

    query_lower = query.lower()

    # Check for role keywords
    role_keywords = {
        'president': GlobalRole.PRESIDENT,
        'delegate': GlobalRole.DELEGATE,
        'verified': GlobalRole.VERIFIED,
        'founder': GlobalROle.Founder,
    }

    # If query matches a role keyword, search by role
    if query_lower in role_keywords:
        return User.objects.filter(
            global_role=role_keywords[query_lower]
        ).exclude(id=current_user.id)[:limit]

    # Otherwise search by name/username
    return User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(second_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=current_user.id)[:limit]


def search_groups(query, limit=20):
    if not query:
        return Group.objects.none()
    return Group.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    )[:limit]


def get_following_ids(user):
    return Follow.objects.filter(follower=user).values_list('followed_id', flat=True)


def get_user_groups(user):
    return Group.objects.filter(memberships__user=user)
