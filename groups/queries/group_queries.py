from datetime import timedelta
from django.utils import timezone
from users.models import Follow, User
from groups.models import Group, Membership, MembershipStatus
from posts.models import Post
from django.db.models import Case, Count, IntegerField, Q, Value, When, F

def get_user_groups(user):
    return Group.objects.filter(memberships__user=user, memberships__status=MembershipStatus.APPROVED).distinct()


def get_all_non_member_groups(user):
    return Group.objects.exclude(memberships__user=user, memberships__status=MembershipStatus.APPROVED).distinct()


def get_following_ids(user):
    return Follow.objects.filter(follower = user).values_list('followed_id', flat = True)


def get_suggested_groups_from_following(user, limit = 10):
    """Improved group suggestion with scoring based on multiple factors."""
    following_ids = get_following_ids(user)
    user_groups = Membership.objects.filter(user=user, status=MembershipStatus.APPROVED)
    
    return Group.objects.filter(
        memberships__user_id__in=following_ids, 
        memberships__status=MembershipStatus.APPROVED
    ).exclude(memberships__user=user).distinct().annotate(
        # Member count indicates popularity
        member_count=Count('memberships', distinct=True),
        
        # How many of your follows are in this group
        following_member_count=Count(
            'memberships',
            filter=Q(memberships__user_id__in=following_ids),
            distinct=True
        ),
        
        # Course affinity
        course_match=Case(
            When(course=user.course, then=Value(30)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Year affinity
        year_match=Case(
            When(year=user.year, then=Value(20)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Recent activity (posts in last 7 days)
        recent_activity=Count(
            'posts',
            filter=Q(posts__created_at__gte=timezone.now() - timedelta(days=7)),
            distinct=True
        )
    ).annotate(
        # Comprehensive suggestion score
        suggestion_score=(
            F('following_member_count') * 20 +  # 20 pts per following member
            F('member_count') * 0.1 +  # Slight boost for popular groups
            F('course_match') +
            F('year_match') +
            F('recent_activity') * 5  # 5 pts per recent post
        )
    ).order_by('-suggestion_score', '-following_member_count', '-member_count', 'name')[:limit]


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

