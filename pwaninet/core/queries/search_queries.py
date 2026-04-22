from django.db.models import Q

from core.models import Follow, Groups, User


def search_users(query, current_user, limit=20):
    if not query:
        return User.objects.none()
    return User.objects.filter(
        Q(username__icontains=query)
        | Q(first_name__icontains=query)
        | Q(second_name__icontains=query)
        | Q(last_name__icontains=query)
    ).exclude(id=current_user.id)[:limit]


def search_groups(query, limit=20):
    if not query:
        return Groups.objects.none()
    return Groups.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    )[:limit]


def get_following_ids(user):
    return Follow.objects.filter(follower=user).values_list("followed_id", flat=True)


def get_user_groups(user):
    return user.joined_groups.all()
