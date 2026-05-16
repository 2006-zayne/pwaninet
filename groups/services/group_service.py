from groups.queries.group_queries import get_all_non_member_groups, get_following_ids, get_group_posts, get_suggested_groups_from_following, get_user_groups, is_group_member, search_invite_candidates

def build_groups_dashboard_context(user):
    return {
        'user_groups': get_user_groups(user),
        'all_groups': get_all_non_member_groups(user),
        'suggested_groups': get_suggested_groups_from_following(user, limit = 10) }


def build_group_detail_context(user, group, query):
    from groups.models import Membership, MembershipRole, MembershipStatus
    memberships = group.memberships.filter(status=MembershipStatus.APPROVED).select_related('user')
    user_membership = group.memberships.filter(user=user).first()
    is_admin = user_membership and user_membership.role == MembershipRole.ADMIN and user_membership.status == MembershipStatus.APPROVED
    is_pending = user_membership and user_membership.status == MembershipStatus.PENDING
    is_rejected = user_membership and user_membership.status == MembershipStatus.REJECTED
    following_ids = list(get_following_ids(user))
    return {
        'group': group,
        'posts': get_group_posts(group),
        'is_member': is_group_member(group, user),
        'is_admin': is_admin,
        'is_pending': is_pending,
        'is_rejected': is_rejected,
        'memberships': memberships,
        'search_results': search_invite_candidates(query, group, limit = 10),
        'query': query,
        'following_ids': following_ids }

