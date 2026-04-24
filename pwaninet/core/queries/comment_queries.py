from datetime import timedelta

from django.db.models import Case, Count, IntegerField, Value, When
from django.utils import timezone

from core.models import CommentLike


def get_ranked_comments_queryset(post):
    now = timezone.now()
    return post.comments.select_related("author").annotate(
        likes_count=Count("likes", distinct=True),
        recency_bonus=Case(
            When(created_at__gte=now - timedelta(hours=1), then=Value(3)),
            When(created_at__gte=now - timedelta(days=1), then=Value(2)),
            When(created_at__gte=now - timedelta(days=7), then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    ).order_by("-likes_count", "-recency_bonus", "-created_at")


def get_liked_comment_ids_for_user(user, post):
    if not user.is_authenticated:
        return set()
    return set(
        CommentLike.objects.filter(user=user, comment__post=post).values_list(
            "comment_id", flat=True
        )
    )
