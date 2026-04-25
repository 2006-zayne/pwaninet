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
    bio = models.TextField(max_length=500, blank=True)
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.second_name}".strip() or self.username
    
    @property
    def is_profile_complete(self):
        return bool(self.course and self.year)


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relationships')
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relationships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed')

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"
