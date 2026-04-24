from datetime import timedelta

from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone

from core.models import Follow, Groups, Like, Post, User


def get_following_ids(user):
    return list(
        Follow.objects.filter(follower=user).values_list("followed_id", flat=True)
    )


def get_user_group_ids(user):
    return list(user.joined_groups.values_list("id", flat=True))


def get_prioritized_feed_queryset(user, following_ids, user_group_ids):
    return (
        Post.objects.filter(
            Q(author_id__in=following_ids)
            | Q(group_id__in=user_group_ids)
            | Q(course=user.course, unit__year=user.year)
        )
        .select_related("author", "unit", "group")
        .prefetch_related("likes", "comments")
        .annotate(
            engagement_count=Count("likes"),
            priority_tier=Case(
                When(author_id__in=following_ids, then=Value(100)),
                When(group_id__in=user_group_ids, then=Value(50)),
                default=Value(20),
                output_field=IntegerField(),
            ),
            recency_score=Case(
                When(date__gte=timezone.now() - timedelta(days=7), then=Value(20)),
                When(date__gte=timezone.now() - timedelta(days=30), then=Value(10)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .distinct()
        .order_by("-priority_tier", "-engagement_count", "-recency_score", "-date")
    )


def get_prioritized_feed_posts(user, following_ids, user_group_ids, limit=15):
    return list(get_prioritized_feed_queryset(user, following_ids, user_group_ids)[:limit])


def get_liked_post_ids_for_user(user, post_ids):
    return set(
        Like.objects.filter(user=user, post_id__in=post_ids).values_list(
            "post_id", flat=True
        )
    )


def get_suggested_groups(user, following_ids, limit=5):
    return (
        Groups.objects.filter(members__id__in=following_ids)
        .exclude(members=user)
        .annotate(member_count=Count("members"))
        .order_by("-member_count")
        .distinct()[:limit]
    )


def get_user_suggestions_from_groups(user, limit=5):
    already_following = Follow.objects.filter(follower=user).values_list(
        "followed_id", flat=True
    )
    my_groups = user.joined_groups.all()
    return User.objects.filter(joined_groups__in=my_groups).exclude(
        Q(id__in=already_following) | Q(id=user.id)
    ).distinct()[:limit]


def get_friend_suggestions(user, limit=5):
    """
    Get friend suggestions based on:
    - Same course (high priority: 50 points)
    - Same year (high priority: 40 points)
    - Friend of friends (30 points)
    - Same group (20 points)
    
    Returns up to 'limit' users ranked by points.
    """
    already_following = Follow.objects.filter(follower=user).values_list(
        "followed_id", flat=True
    )
    
    # Get friends of friends (people following my followers or vice versa)
    my_followers = Follow.objects.filter(followed=user).values_list("follower_id", flat=True)
    my_following = Follow.objects.filter(follower=user).values_list("followed_id", flat=True)
    
    friends_of_friends = Follow.objects.filter(
        Q(follower_id__in=my_followers) | Q(followed_id__in=my_following)
    ).values_list("followed_id", "follower_id", flat=False)
    
    # Exclude self and already following
    exclude_ids = list(already_following) + [user.id]
    
    # Start with users from the same course
    suggestions = User.objects.filter(
        course=user.course
    ).exclude(
        id__in=exclude_ids
    ).annotate(
        suggestion_points=Case(
            # Same course AND same year (highest priority)
            When(course=user.course, year=user.year, then=Value(90)),
            # Same course (high priority)
            When(course=user.course, then=Value(50)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )
    
    # Add points for same year
    suggestions = suggestions.annotate(
        year_bonus=Case(
            When(year=user.year, then=Value(40)),
            default=Value(0),
            output_field=IntegerField(),
        )
    )
    
    # Add points for same groups
    suggestions = suggestions.annotate(
        group_bonus=Count('joined_groups', filter=Q(
            joined_groups__in=user.joined_groups.all()
        ), distinct=True) * 20
    )
    
    # Annotate total points
    from django.db.models import F, ExpressionWrapper
    suggestions = suggestions.annotate(
        final_score=ExpressionWrapper(
            F('suggestion_points') + F('year_bonus') + F('group_bonus'),
            output_field=IntegerField()
        )
    )
    
    # Order by score descending, then by username for stability
    suggestions = suggestions.filter(
        final_score__gt=0
    ).order_by('-final_score', 'username').distinct()[:limit]
    
    return list(suggestions)
