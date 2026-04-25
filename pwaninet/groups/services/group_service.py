from groups.queries.group_queries import get_all_non_member_groups, get_following_ids, get_group_posts, get_suggested_groups_from_following, get_user_groups, is_group_member, search_invite_candidates

def build_groups_dashboard_context(user):
    return {
        'user_groups': get_user_groups(user),
        'all_groups': get_all_non_member_groups(user),
        'suggested_groups': get_suggested_groups_from_following(user, limit = 10) }


def build_group_detail_context(user, group, query):
    return {
        'group': group,
        'posts': get_group_posts(group),
        'is_member': is_group_member(group, user),
        'search_results': search_invite_candidates(query, group, limit = 10),
        'query': query,
        'following_ids': get_following_ids(user) }

