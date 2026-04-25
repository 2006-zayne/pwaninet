from users.models import Follow, User
from groups.models import Group, Membership, MembershipStatus
from posts.models import Post

def get_user_groups(user):
    return Group.objects.filter(memberships__user=user, memberships__status=MembershipStatus.APPROVED).distinct()


def get_all_non_member_groups(user):
    return Group.objects.exclude(memberships__user=user, memberships__status=MembershipStatus.APPROVED).distinct()


def get_following_ids(user):
    return Follow.objects.filter(follower = user).values_list('followed_id', flat = True)


def get_suggested_groups_from_following(user, limit = 10):
    following_ids = get_following_ids(user)
    return Group.objects.filter(memberships__user_id__in=following_ids, memberships__status=MembershipStatus.APPROVED).exclude(memberships__user=user).distinct()[:limit]


def get_group_posts(group):
    return Post.objects.filter(group = group).select_related('author', 'unit', 'group').prefetch_related('likes').order_by('-created_at')


def is_group_member(group, user):
    return group.memberships.filter(user=user, status=MembershipStatus.APPROVED).exists()


def get_group_member_exclusion_ids(group):
    return group.memberships.filter(status=MembershipStatus.APPROVED).values_list('user_id', flat=True)


def search_invite_candidates(query, group, limit = 10):
    if not query:
        return None
    return User.objects.filter(username__icontains = query).exclude(id__in = get_group_member_exclusion_ids(group))[:limit]

