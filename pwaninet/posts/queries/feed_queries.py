from datetime import timedelta
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone
from users.models import Follow, User
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post

def get_following_ids(user):
    return list(Follow.objects.filter(follower = user).values_list('followed_id', flat = True))


def get_user_group_ids(user):
    return list(Membership.objects.filter(user=user, status=MembershipStatus.APPROVED).values_list('group_id', flat=True))


def get_prioritized_feed_queryset(user, following_ids, user_group_ids):
    return Post.objects.filter(
        Q(author_id__in=following_ids) | 
        Q(group_id__in=user_group_ids) | 
        Q(course=user.course, unit__year=user.year)
    ).select_related('author', 'unit', 'group').prefetch_related('likes').annotate(
        engagement_count=Count('likes', distinct=True), 
        priority_tier=Case(
            When(author_id__in=following_ids, then=Value(100)), 
            When(group_id__in=user_group_ids, then=Value(50)), 
            default=Value(20), 
            output_field=IntegerField()
        ), 
        recency_score=Case(
            When(created_at__gte=timezone.now() - timedelta(days=7), then=Value(20)), 
            When(created_at__gte=timezone.now() - timedelta(days=30), then=Value(10)), 
            default=Value(0), 
            output_field=IntegerField()
        )
    ).distinct().order_by('-priority_tier', '-engagement_count', '-recency_score', '-created_at', '-id')


def get_prioritized_feed_posts(user, following_ids, user_group_ids, limit = 15):
    return list(get_prioritized_feed_queryset(user, following_ids, user_group_ids)[:limit])


def get_liked_post_ids_for_user(user, post_ids):
    return set(Like.objects.filter(user = user, post_id__in = post_ids).values_list('post_id', flat = True))


def get_suggested_groups(user, following_ids, limit = 5):
    return Group.objects.filter(memberships__user_id__in=following_ids, memberships__status=MembershipStatus.APPROVED).exclude(memberships__user=user).annotate(member_count=Count('memberships')).order_by('-member_count').distinct()[:limit]


def get_user_suggestions_from_groups(user, limit = 5):
    already_following = Follow.objects.filter(follower = user).values_list('followed_id', flat = True)
    my_groups = Membership.objects.filter(user=user, status=MembershipStatus.APPROVED)
    return User.objects.filter(group_memberships__group__in=my_groups.values('group_id')).exclude(Q(id__in=already_following) | Q(id=user.id)).distinct()[:limit]
