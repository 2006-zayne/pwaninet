from datetime import timedelta
from django.db.models import Case, Count, IntegerField, Q, Value, When, F, FloatField
from django.db.models.functions import Cast
from django.utils import timezone
from users.models import Follow, User
from groups.models import Group, Membership, MembershipStatus
from posts.models import Like, Post, Repost, Comment, HiddenPost

def get_following_ids(user):
    return list(Follow.objects.filter(follower = user).values_list('followed_id', flat = True))


def get_user_group_ids(user):
    return list(Membership.objects.filter(user=user, status=MembershipStatus.APPROVED).values_list('group_id', flat=True))


def get_prioritized_feed_queryset(user, following_ids, user_group_ids):
    """Improved feed algorithm with time decay, author affinity, and view counts."""
    hours_since_creation = Cast(
        (timezone.now() - F('created_at')) / timedelta(hours=1),
        FloatField()
    )

    # Build query - always include posts from followed users
    # BUT filter out group posts from groups the user is not a member of
    filters = Q(author_id__in=following_ids) & (Q(group__isnull=True) | Q(group_id__in=user_group_ids))

    # Add optional filters (only if they exist)
    if user_group_ids:
        filters |= Q(group_id__in=user_group_ids)
    if user.course:
        filters |= Q(course=user.course)
    if hasattr(user, 'year') and user.year:
        filters |= Q(unit__year=user.year)

    # Exclude hidden posts
    hidden_post_ids = HiddenPost.objects.filter(user=user).values_list('post_id', flat=True)
    if hidden_post_ids:
        filters &= ~Q(id__in=hidden_post_ids)

    return Post.objects.filter(filters).select_related('author', 'unit', 'group').prefetch_related('likes', 'comments').annotate(
        like_count_annotated=Count('likes', distinct=True),
        comment_count_annotated=Count('comments', distinct=True),
        repost_count_annotated=Count('repost_children', distinct=True),
        
        # Author affinity: boost posts from authors user frequently engages with
        author_affinity=Case(
            When(author_id__in=following_ids, then=Value(30)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Priority tier based on source
        priority_tier=Case(
            When(author_id__in=following_ids, then=Value(100)), 
            When(group_id__in=user_group_ids, then=Value(80)), 
            When(course=user.course, unit__year=user.year, then=Value(70)),
            When(course=user.course, then=Value(50)),  # Same course, any year
            When(unit__year=user.year, then=Value(40)),  # Same year, any course
            default=Value(20), 
            output_field=IntegerField()
        ),
        
        # Recency score with exponential decay - give older posts a minimum score
        recency_score=Case(
            When(created_at__gte=timezone.now() - timedelta(hours=6), then=Value(50)),
            When(created_at__gte=timezone.now() - timedelta(days=1), then=Value(40)),
            When(created_at__gte=timezone.now() - timedelta(days=3), then=Value(30)),
            When(created_at__gte=timezone.now() - timedelta(days=7), then=Value(20)),
            When(created_at__gte=timezone.now() - timedelta(days=30), then=Value(10)),
            default=Value(5),  # Give older posts a minimum score so they still appear
            output_field=IntegerField()
        )
    ).annotate(
        # Comprehensive engagement score with weighted factors
        engagement_score=(
            F('like_count_annotated') * 1.0 +
            F('comment_count_annotated') * 2.0 +
            F('repost_count_annotated') * 3.0 +
            F('author_affinity') +
            F('recency_score')
        )
    ).distinct().order_by('-priority_tier', '-engagement_score', '-created_at', '-id')


def get_prioritized_feed_posts(user, following_ids, user_group_ids, limit = 15):
    return list(get_prioritized_feed_queryset(user, following_ids, user_group_ids)[:limit])


def get_liked_post_ids_for_user(user, post_ids):
    if not user or not user.is_authenticated or not post_ids:
        return set()
    likes = Like.objects.filter(user=user, post_id__in=post_ids).values_list('post_id', 'post__share_id')
    liked_ids = set()
    for pid, share_id in likes:
        liked_ids.add(pid)
        liked_ids.add(share_id)
        liked_ids.add(str(share_id))
    return liked_ids


def get_suggested_groups(user, following_ids, limit = 5):
    return Group.objects.filter(memberships__user_id__in=following_ids, memberships__status=MembershipStatus.APPROVED).exclude(memberships__user=user).annotate(member_count=Count('memberships')).order_by('-member_count').distinct()[:limit]


def get_user_suggestions_from_groups(user, limit = 5):
    """Improved friend suggestion with scoring based on multiple factors."""
    already_following = Follow.objects.filter(follower = user).values_list('followed_id', flat = True)
    my_groups = Membership.objects.filter(user=user, status=MembershipStatus.APPROVED)
    
    # Get users from same groups with scoring
    candidates = User.objects.filter(
        group_memberships__group__in=my_groups.values('group_id')
    ).exclude(
        Q(id__in=already_following) | Q(id=user.id)
    ).distinct().annotate(
        # Score based on shared groups
        shared_groups_count=Count('group_memberships', distinct=True),
        
        # Course affinity
        course_match=Case(
            When(course=user.course, then=Value(40)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Year affinity
        year_match=Case(
            When(year=user.year, then=Value(30)),
            default=Value(0),
            output_field=IntegerField()
        ),
        
        # Friend of friends (people your follows follow)
        fof_count=Count(
            'follower_relationships',
            filter=Q(follower_relationships__follower_id__in=already_following),
            distinct=True
        )
    ).annotate(
        # Comprehensive suggestion score
        suggestion_score=(
            F('shared_groups_count') * 25 +  # 25 pts per shared group
            F('course_match') +
            F('year_match') +
            F('fof_count') * 15  # 15 pts per friend-of-friend connection
        )
    ).order_by('-suggestion_score', '-shared_groups_count', 'username')[:limit]
    
    return candidates
