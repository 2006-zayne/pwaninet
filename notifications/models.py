from django.db import models
from django.conf import settings


class PushSubscription(models.Model):
    """Model for storing web push notification subscriptions."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        db_index=True
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.TextField()
    auth = models.TextField()
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"PushSubscription for {self.user.username} (active={self.is_active})"


class Notifications(models.Model):
    INVITE = 'INVITE'
    ALERTE = 'ALERT'
    LIKE = 'LIKE'
    FOLLOW = 'FOLLOW'
    GROUP_REQUEST = 'GROUP_REQUEST'
    GROUP_APPROVED = 'GROUP_APPROVED'
    GROUP_REJECTED = 'GROUP_REJECTED'
    POST_SHARED = 'POST_SHARED'
    POST_SHARED_TO_GROUP = 'POST_SHARED_TO_GROUP'
    PINCH = 'PINCH'
    COMMENT_REPLY = 'COMMENT_REPLY'

    TYPE_CHOICES = [
        (INVITE, 'Group Invite'),
        (ALERTE, 'General Alert'),
        (LIKE, 'Post Like'),
        (FOLLOW, 'New Follower'),
        (GROUP_REQUEST, 'Group Join Request'),
        (GROUP_APPROVED, 'Group Join Approved'),
        (GROUP_REJECTED, 'Group Join Rejected'),
        (POST_SHARED, 'Post Shared to User'),
        (POST_SHARED_TO_GROUP, 'Post Shared to Group'),
        (PINCH, 'Profile Pinch'),
        (COMMENT_REPLY, 'Comment Reply')
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', db_index=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications', db_index=True)
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=ALERTE, db_index=True)
    msg = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"
