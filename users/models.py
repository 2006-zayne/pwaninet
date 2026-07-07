from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from django.contrib.postgres.fields import JSONField


class GlobalRole(models.TextChoices):
    PRESIDENT = 'PRESIDENT', 'President'
    DELEGATE = 'DELEGATE', 'Delegate'
    VERIFIED = 'VERIFIED', 'Verified'
    NORMAL = 'NORMAL', 'Normal'


class ThemePreference(models.TextChoices):
    LIGHT = 'light', 'Light'
    DARK = 'dark', 'Dark'
    SYSTEM = 'system', 'System Default'


class CollaborationStatus(models.TextChoices):
    OPEN_TO_PROJECTS = 'open_to_projects', 'Open to Projects'
    OPEN_TO_STUDY_GROUPS = 'open_to_study_groups', 'Open to Study Groups'
    OPEN_TO_NETWORKING = 'open_to_networking', 'Open to Networking'
    NOT_LOOKING = 'not_looking', 'Not Looking'


class CustomUserManager(UserManager):
    pass


class User(AbstractUser):
    objects = CustomUserManager()
    first_name = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    second_name = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    last_name = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    year = models.ForeignKey('courses.Year', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    global_role = models.CharField(max_length=20, choices=GlobalRole.choices, default=GlobalRole.NORMAL, db_index=True)
    profile_pic = models.ImageField(default='profile_pic/default_pic1.jpg', upload_to='profile_pic', null=True, blank=True)
    cover_photo = models.ImageField(upload_to='covers/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    
    # Extended profile fields
    headline = models.CharField(max_length=100, blank=True, help_text="Professional tagline or headline")
    interests = models.TextField(blank=True, help_text="Comma-separated interests")
    collaboration_status = models.CharField(
        max_length=30,
        choices=CollaborationStatus.choices,
        blank=True,
        default='',
        help_text="Current collaboration availability"
    )
    skills = models.JSONField(default=list, blank=True, help_text="List of skills")
    projects = models.JSONField(default=list, blank=True, help_text="List of projects with title, description, and link")
    github_url = models.URLField(blank=True, help_text="GitHub profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")
    portfolio_url = models.URLField(blank=True, help_text="Portfolio website URL")
    twitter_url = models.URLField(blank=True, help_text="Twitter/X profile URL")

    # Notification preferences
    notify_on_like = models.BooleanField(default=True)
    notify_on_follow = models.BooleanField(default=True)
    notify_on_invite = models.BooleanField(default=True)
    notify_on_group_request = models.BooleanField(default=True)
    notify_on_group_approved = models.BooleanField(default=True)
    notify_on_pinch = models.BooleanField(default=True)
    notify_on_comment_reply = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)

    # Theme preference
    theme_preference = models.CharField(
        max_length=10,
        choices=ThemePreference.choices,
        default=ThemePreference.SYSTEM
    )

    # Online status tracking
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    # Onboarding tracking
    has_completed_onboarding = models.BooleanField(default=False, help_text="Whether user has completed the onboarding tour")

    # Email verification
    email_verified = models.BooleanField(default=False, help_text="Whether the user's email address has been verified")

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
    
    @property
    def profile_completion_percentage(self):
        """
        Calculate profile completion percentage based on:
        - Profile Picture: 15%
        - Bio: 10%
        - Headline: 10%
        - Skills: 20%
        - Projects: 20%
        - Collaboration Status: 10%
        - Links: 5%
        - Interests: 10%
        """
        score = 0
        
        # Profile Picture (15%)
        if self.profile_pic and self.profile_pic.name != 'profile_pic/default_pic1.jpg':
            score += 15
        
        # Bio (10%)
        if self.bio:
            score += 10
        
        # Headline (10%)
        if self.headline:
            score += 10
        
        # Skills (20%)
        if self.skills and len(self.skills) > 0:
            score += 20
        
        # Projects (20%)
        if self.projects and len(self.projects) > 0:
            score += 20
        
        # Collaboration Status (10%)
        if self.collaboration_status:
            score += 10
        
        # Links (5%)
        links_count = sum([
            bool(self.github_url),
            bool(self.linkedin_url),
            bool(self.portfolio_url),
            bool(self.twitter_url)
        ])
        if links_count > 0:
            score += 5
        
        # Interests (10%)
        if self.interests:
            score += 10
        
        return score


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relationships', db_index=True)
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relationships', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('follower', 'followed')
        indexes = [
            models.Index(fields=['follower', 'followed']),
            models.Index(fields=['followed', 'follower']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


class Pinch(models.Model):
    """Profile pinch interaction - one pinch per user pair per 24 hours"""
    pinch_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pinches_sent', db_index=True)
    pinched_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pinches_received', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['pinch_user', 'pinched_user']),
            models.Index(fields=['created_at']),
            models.Index(fields=['pinched_user', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.pinch_user.username} pinched {self.pinched_user.username}"

    @classmethod
    def can_pinch(cls, pinch_user, pinched_user):
        """Check if pinch_user can pinch pinched_user (not self, not already today)"""
        if pinch_user == pinched_user:
            return False, "Cannot pinch yourself"
        
        from django.utils import timezone
        today = timezone.now().date()
        
        if cls.objects.filter(
            pinch_user=pinch_user,
            pinched_user=pinched_user,
            created_at__date=today
        ).exists():
            return False, "Already pinched today"
        
        return True, None


class DeviceAccount(models.Model):
    """Tracks accounts that have been used on a specific device"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_accounts', db_index=True)
    device_id = models.CharField(max_length=255, db_index=True)
    last_used = models.DateTimeField(auto_now=True, db_index=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'device_id')
        ordering = ['-last_used']
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['device_id', 'last_used']),
        ]

    def __str__(self):
        return f"{self.user.username} on device {self.device_id}"
