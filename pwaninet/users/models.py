from django.db import models
from django.contrib.auth.models import AbstractUser
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


class GlobalRole(models.TextChoices):
    PRESIDENT = 'PRESIDENT', 'President'
    DELEGATE = 'DELEGATE', 'Delegate'
    VERIFIED = 'VERIFIED', 'Verified'
    NORMAL = 'NORMAL', 'Normal'


class User(AbstractUser):
    first_name = models.CharField(max_length=200, null=True, blank=True)
    second_name = models.CharField(max_length=200, null=True, blank=True)
    last_name = models.CharField(max_length=200, null=True, blank=True)
    year = models.ForeignKey('courses.Year', on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    global_role = models.CharField(max_length=20, choices=GlobalRole.choices, default=GlobalRole.NORMAL)
    profile_pic = models.ImageField(default='profile_pic/default_pic1.jpg', upload_to='profile_pic')
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)

    # Notification preferences
    notify_on_like = models.BooleanField(default=True)
    notify_on_follow = models.BooleanField(default=True)
    notify_on_invite = models.BooleanField(default=True)
    notify_on_group_request = models.BooleanField(default=True)
    notify_on_group_approved = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.first_name} {self.second_name}".strip() or self.username
    
    @property
    def is_profile_complete(self):
        return bool(self.course and self.year)


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relationships', db_index=True)
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relationships', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('follower', 'followed')

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


class DeviceAccount(models.Model):
    """Tracks accounts that have been used on a specific device"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_accounts')
    device_id = models.CharField(max_length=255, db_index=True)
    last_used = models.DateTimeField(auto_now=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'device_id')
        ordering = ['-last_used']

    def __str__(self):
        return f"{self.user.username} on device {self.device_id}"
