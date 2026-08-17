from groups.queries.group_queries import get_all_non_member_groups, get_following_ids, get_group_posts, get_suggested_groups_from_following, get_user_groups, is_group_member, search_invite_candidates
from posts.models import Post

def build_groups_dashboard_context(user):
    return {
        'user_groups': get_user_groups(user),
        'all_groups': get_all_non_member_groups(user),
        'suggested_groups': get_suggested_groups_from_following(user, limit = 10) }


def build_group_detail_context(user, group, query, page=1):
    from groups.models import Membership, MembershipRole, MembershipStatus, JoinPolicy
    from django.core.paginator import Paginator
    memberships = group.memberships.filter(status=MembershipStatus.APPROVED).select_related('user')
    user_membership = group.memberships.filter(user=user).first()
    is_admin = user_membership and user_membership.role == MembershipRole.ADMIN and user_membership.status == MembershipStatus.APPROVED
    is_pending = user_membership and user_membership.status == MembershipStatus.PENDING
    is_rejected = user_membership and user_membership.status == MembershipStatus.REJECTED
    is_member = is_group_member(group, user)
    is_invite_only = group.join_policy == JoinPolicy.INVITE_ONLY
    following_ids = list(get_following_ids(user))
    
    # Pagination for posts - only show posts to approved members
    if is_member:
        posts_queryset = get_group_posts(group)
    else:
        # Non-members see no posts
        posts_queryset = Post.objects.none()
    
    posts_per_page = 10
    paginator = Paginator(posts_queryset, posts_per_page)
    posts_page = paginator.get_page(page)
    
    return {
        'group': group,
        'posts': posts_page,
        'total_posts_count': posts_queryset.count(),
        'is_member': is_member,
        'is_admin': is_admin,
        'is_pending': is_pending,
        'is_rejected': is_rejected,
        'is_invite_only': is_invite_only,
        'memberships': memberships,
        'search_results': search_invite_candidates(query, group, limit = 10),
        'query': query,
        'following_ids': following_ids,
        'page': page,
        'has_next': posts_page.has_next(),
        'has_previous': posts_page.has_previous(),
        'next_page': page + 1 if posts_page.has_next() else None,
        'previous_page': page - 1 if posts_page.has_previous() else None }

