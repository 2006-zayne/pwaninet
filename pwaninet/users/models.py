from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
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

    def clean(self):
        super().clean()
        # Ensure only one president exists (only check when role is being set to PRESIDENT)
        if self.global_role == GlobalRole.PRESIDENT:
            # Check if this is a new instance or role is being changed to PRESIDENT
            if self.pk is None or User.objects.filter(pk=self.pk, global_role=GlobalRole.PRESIDENT).exists():
                return  # Already president or new instance, skip check

            existing_president = User.objects.filter(global_role=GlobalRole.PRESIDENT).exclude(pk=self.pk).first()
            if existing_president:
                raise ValidationError({
                    'global_role': f'There can only be one president. {existing_president.username} is already the president.'
                })

    def save(self, *args, **kwargs):
        # Only run full_clean if global_role is being changed
        if self.pk is not None:
            old_user = User.objects.filter(pk=self.pk).first()
            if old_user and old_user.global_role != self.global_role:
                self.full_clean()
        else:
            self.full_clean()
        super().save(*args, **kwargs)

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
