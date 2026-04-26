from django.db import models
from django.conf import settings


class Group(models.Model):
    name = models.CharField(max_length=200, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    description = models.TextField(max_length=500, blank=True)
    group_pic = models.ImageField(upload_to='group_profile_pic', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='group_covers/', blank=True, null=True)
    is_official = models.BooleanField(default=False)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    year = models.ForeignKey('courses.Year', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    @property
    def get_photo_url(self):
        if self.group_pic and hasattr(self.group_pic, 'url'):
            return self.group_pic.url
        return f"{settings.STATIC_URL}images/default_group.jpg"


class MembershipRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MODERATOR = 'MODERATOR', 'Moderator'
    DELEGATE = 'DELEGATE', 'Delegate'
    MEMBER = 'MEMBER', 'Member'


class MembershipStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='group_memberships')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.PENDING)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'group')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} - {self.group.name} ({self.role})"
