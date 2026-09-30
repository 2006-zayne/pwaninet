"""One-time in-chat surfacing of recent unread posts from a user's network."""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def get_pending_friend_post_updates(user, limit=3):
    """Return recent unread post notifications from accounts the user follows or follows them."""
    if not user or not getattr(user, "is_authenticated", False):
        return []

    try:
        from notifications.models import NotificationObject
        from users.models import Follow
        from posts.models import Post

        cutoff = timezone.now() - timedelta(days=7)
        notifications = NotificationObject.objects.filter(
            recipient=user,
            notification_type="POST_CREATED",
            created_at__gte=cutoff,
            metadata__pwanimate_surfaced_at__isnull=True,
        ).exclude(status__in=["READ", "ARCHIVED", "EXPIRED"]).order_by("-created_at")[:30]

        updates = []
        for notification in notifications:
            metadata = notification.metadata if isinstance(notification.metadata, dict) else {}
            if metadata.get("pwanimate_surfaced_at"):
                continue
            try:
                author_id = int(metadata.get("actor_id"))
                post_id = int(metadata.get("target_id") or notification.context_id)
            except (TypeError, ValueError):
                continue

            is_connected = Follow.objects.filter(
                Q(follower=user, followed_id=author_id)
                | Q(follower_id=author_id, followed=user)
            ).exists()
            if not is_connected:
                continue

            post = Post.objects.filter(id=post_id, author_id=author_id).only(
                "id", "share_id", "content", "created_at"
            ).first()
            if not post:
                continue

            excerpt = " ".join(strip_tags(post.content or "").split())[:280]
            updates.append({
                "notification_id": str(notification.notification_id),
                "author": metadata.get("actor_username") or notification.title,
                "excerpt": excerpt,
                "url": f"/post/{post.share_id}/" if post.share_id else "",
                "created_at": post.created_at.isoformat() if post.created_at else "",
            })
            if len(updates) >= limit:
                break
        return updates
    except Exception as exc:
        logger.info("Could not load friend-post updates for Pwanimate: %s", type(exc).__name__)
        return []


def mark_friend_post_updates_surfaced(user, updates):
    """Mark only the supplied notification records as already surfaced by Pwanimate."""
    if not user or not updates:
        return

    from notifications.models import NotificationObject

    notification_ids = [item.get("notification_id") for item in updates if item.get("notification_id")]
    if not notification_ids:
        return

    surfaced_at = timezone.now().isoformat()
    with transaction.atomic():
        records = NotificationObject.objects.select_for_update().filter(
            recipient=user,
            notification_id__in=notification_ids,
            notification_type="POST_CREATED",
        )
        for notification in records:
            metadata = notification.metadata if isinstance(notification.metadata, dict) else {}
            if metadata.get("pwanimate_surfaced_at"):
                continue
            metadata["pwanimate_surfaced_at"] = surfaced_at
            notification.metadata = metadata
            notification.save(update_fields=["metadata"])
