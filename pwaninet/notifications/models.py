from django.db import models
from django.conf import settings


class Notifications(models.Model):
    INVITE = 'INVITE'
    ALERTE = 'ALERT'
    LIKE = 'LIKE'
    FOLLOW = 'FOLLOW'
    GROUP_REQUEST = 'GROUP_REQUEST'
    GROUP_APPROVED = 'GROUP_APPROVED'
    GROUP_REJECTED = 'GROUP_REJECTED'
    
    TYPE_CHOICES = [
        (INVITE, 'Group Invite'), 
        (ALERTE, 'General Alert'),
        (LIKE, 'Post Like'),
        (FOLLOW, 'New Follower'),
        (GROUP_REQUEST, 'Group Join Request'),
        (GROUP_APPROVED, 'Group Join Approved'),
        (GROUP_REJECTED, 'Group Join Rejected')
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
