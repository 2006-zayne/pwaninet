# Source Generated with Decompyle++
# File: group_queries.cpython-312.pyc (Python 3.12)

from core.models import Follow, Groups, Post, User

def get_user_groups(user):
    return Groups.objects.filter(members = user)


def get_all_non_member_groups(user):
    return Groups.objects.all().exclude(members = user)


def get_following_ids(user):
    return Follow.objects.filter(follower = user).values_list('followed_id', flat = True)


def get_suggested_groups_from_following(user, limit = 10):
    following_ids = get_following_ids(user)
    return Groups.objects.filter(members__id__in = following_ids).exclude(members = user).distinct()[:limit]


def get_group_posts(group):
    return Post.objects.filter(group = group).select_related('author', 'unit', 'group').prefetch_related('likes').order_by('-date')


def is_group_member(group, user):
    return group.members.filter(id = user.id).exists()


def get_group_member_exclusion_ids(group):
    return group.members.values_list('id', flat = True)


def search_invite_candidates(query, group, limit = 10):
    if not query:
        return None
    return User.objects.filter(username__icontains = query).exclude(id__in = get_group_member_exclusion_ids(group))[:limit]

