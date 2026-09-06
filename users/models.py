from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex, OpClass


class GlobalRole(models.TextChoices):
    PRESIDENT = 'PRESIDENT', 'President'
    DELEGATE = 'DELEGATE', 'Delegate'
    VERIFIED = 'VERIFIED', 'Verified'
    NORMAL = 'NORMAL', 'Normal'


class ThemePreference(models.TextChoices):
    LIGHT = 'light', 'Light'
    DARK = 'dark', 'Dark'
    SYSTEM = 'system', 'System Default'


class FontSizePreference(models.TextChoices):
    TINY = 'tiny', 'Tiny'
    SMALL = 'small', 'Small'
    MEDIUM = 'medium', 'Medium'
    LARGE = 'large', 'Large'


class LanguagePreference(models.TextChoices):
    ENGLISH = 'en', 'English'
    KISWAHILI = 'sw', 'Kiswahili'


class FontFamilyPreference(models.TextChoices):
    DEFAULT = 'default', 'Default (System)'
    INTER = 'inter', 'Inter'
    ROBOTO = 'roboto', 'Roboto'
    IBM_PLEX_SERIF = 'ibm_plex_serif', 'IBM Plex Serif'
    MANROPE = 'manrope', 'Manrope'
    PLAYFAIR_DISPLAY = 'playfair_display', 'Playfair Display'
    ROMANESCO = 'romanesco', 'Romanesco'
    STORY_SCRIPT = 'story_script', 'Story Script'
    POPPINS = 'poppins', 'Poppins'
    LORA = 'lora', 'Lora'
    MERRIWEATHER = 'merriweather', 'Merriweather'
    DANCING_SCRIPT = 'dancing_script', 'Dancing Script'
    GREAT_VIBES = 'great_vibes', 'Great Vibes'
    PARISIENNE = 'parisienne', 'Parisienne'
    SATISFY = 'satisfy', 'Satisfy'
    COOKIE = 'cookie', 'Cookie'
    ITALIANNO = 'italianno', 'Italianno'
    TANGERINE = 'tangerine', 'Tangerine'


class FontStylePreference(models.TextChoices):
    NORMAL = 'normal', 'Normal'
    ITALIC = 'italic', 'Italic'


class AudioPreference(models.TextChoices):
    MUTED = 'muted', 'Muted'
    UNMUTED = 'unmuted', 'Unmuted'


class PrivacyLevel(models.TextChoices):
    PUBLIC = 'PUBLIC', 'Everyone'
    AUTHENTICATED = 'AUTHENTICATED', 'PwaniNet Users'
    FOLLOWERS = 'FOLLOWERS', 'Followers Only'
    PRIVATE = 'PRIVATE', 'Only Me'


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
    
    # Legacy academic fields (for backward compatibility)
    year = models.ForeignKey('courses.Year', on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    
    # New academic profile fields
    programme = models.ForeignKey(
        'documents.Programme',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="Current academic programme"
    )
    academic_level = models.ForeignKey(
        'documents.AcademicLevel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="Current academic level (Year 1, Year 2, etc.)"
    )
    academic_year = models.ForeignKey(
        'documents.AcademicYear',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="Current academic year"
    )
    semester = models.ForeignKey(
        'documents.Semester',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        help_text="Current semester"
    )
    
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

    # Font size preference
    font_size_preference = models.CharField(
        max_length=10,
        choices=FontSizePreference.choices,
        default=FontSizePreference.MEDIUM
    )

    # Language preference
    language_preference = models.CharField(
        max_length=5,
        choices=LanguagePreference.choices,
        default=LanguagePreference.ENGLISH
    )

    # Font family preference
    font_family_preference = models.CharField(
        max_length=30,
        choices=FontFamilyPreference.choices,
        default=FontFamilyPreference.DEFAULT
    )

    # Font style preference
    font_style_preference = models.CharField(
        max_length=10,
        choices=FontStylePreference.choices,
        default=FontStylePreference.NORMAL
    )

    # Audio preference for video playback
    audio_preference = models.CharField(
        max_length=10,
        choices=AudioPreference.choices,
        default=AudioPreference.MUTED,
        help_text="Default audio state for video playback"
    )

    # Online status tracking
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)

    # Onboarding tracking
    has_completed_onboarding = models.BooleanField(default=False, help_text="Whether user has completed the onboarding tour")

    # Email verification
    email_verified = models.BooleanField(default=False, help_text="Whether the user's email address has been verified")

    # Privacy settings
    profile_privacy = models.CharField(
        max_length=20,
        choices=PrivacyLevel.choices,
        default=PrivacyLevel.PUBLIC,
        help_text="Who can view profile information"
    )
    post_privacy = models.CharField(
        max_length=20,
        choices=PrivacyLevel.choices,
        default=PrivacyLevel.PUBLIC,
        help_text="Default visibility for new posts"
    )
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            GinIndex(fields=['search_vector'], name='user_search_vector_idx'),
            GinIndex(
                OpClass('username', name='gin_trgm_ops'),
                name='user_username_trgm_idx',
            ),
            GinIndex(
                OpClass('first_name', name='gin_trgm_ops'),
                OpClass('last_name', name='gin_trgm_ops'),
                name='user_names_trgm_idx',
            ),
        ]

    def update_search_vector(self):
        """Recompute search vector with field weights."""
        from django.contrib.postgres.search import SearchVector
        User.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('username', weight='A') +
                SearchVector('first_name', weight='A') +
                SearchVector('last_name', weight='A') +
                SearchVector('headline', weight='B') +
                SearchVector('bio', weight='C')
            )
        )

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
        # Check new academic profile first
        if self.programme and self.academic_level:
            return True
        # Fallback to legacy fields for backward compatibility
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


class UserSession(models.Model):
    """Tracks active user sessions for device management"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_sessions', db_index=True)
    session_key = models.CharField(max_length=255, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=20, choices=[('mobile', 'Mobile'), ('tablet', 'Tablet'), ('desktop', 'Desktop')], default='desktop', blank=True)
    browser = models.CharField(max_length=100, blank=True)
    operating_system = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    login_time = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity = models.DateTimeField(auto_now=True, db_index=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['session_key']),
            models.Index(fields=['-last_activity']),
        ]

    def __str__(self):
        return f"{self.user.username} session on {self.device_name or 'Unknown Device'}"


class Block(models.Model):
    """Tracks blocked users"""
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_users', db_index=True)
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocked_by', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['blocker', '-created_at']),
            models.Index(fields=['blocked']),
        ]

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


class UserProfilePhotoLike(models.Model):
    """Likes for user profile and cover photos"""
    PHOTO_TYPE_CHOICES = [
        ('profile', 'Profile Photo'),
        ('cover', 'Cover Photo'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='photo_likes', db_index=True)
    profile_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_photo_likes', db_index=True)
    photo_type = models.CharField(max_length=10, choices=PHOTO_TYPE_CHOICES, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'profile_user', 'photo_type')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['profile_user', 'photo_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} likes {self.profile_user.username}'s {self.photo_type} photo"


class HiddenAuthor(models.Model):
    """Tracks authors whose posts are hidden from user's feed"""
    hider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_authors', db_index=True)
    hidden_author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_by', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('hider', 'hidden_author')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hider', '-created_at']),
            models.Index(fields=['hidden_author']),
        ]

    def __str__(self):
        return f"{self.hider.username} hid {self.hidden_author.username}"
