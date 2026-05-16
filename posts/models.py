from django.db import models
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys


GRADIENT_CHOICES = [
    ('none', 'Standard (No Gradient)'),
    ('grad-ocean', 'Ocean Blue'),
    ('grad-forest', 'Forest Green'),
    ('grad-magma', 'Magma Red'),
    ('grad-midnight', 'Midnight Purple'),
    ('grad-desert', 'Desert Storm'),
    ('grad-stealth', 'Night Ops (Stealth)'),
]


class Post(models.Model):
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey('courses.Unit', on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    video = models.FileField(upload_to='posts/videos', blank=True, null=True)
    docs = models.FileField(upload_to='posts/docs', blank=True, null=True)
    audio = models.FileField(upload_to='posts/audio', blank=True, null=True, help_text='Attach music/audio to post')
    gradient_class = models.CharField(max_length=50, choices=GRADIENT_CHOICES, default='none', blank=True)
    repost_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='repost_children')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author} on {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def get_intel_file(self):
        if self.images.exists():
            return self.images.first().image
        if self.video:
            return self.video
        if self.docs:
            return self.docs
        return None
    
    def is_liked_by(self, user):
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False

    @property
    def like_count(self):
        # Cache the count on the instance to avoid repeated queries
        if not hasattr(self, '_like_count'):
            self._like_count = self.likes.count()
        return self._like_count

    @property
    def repost_count(self):
        if not hasattr(self, '_repost_count'):
            self._repost_count = self.repost_children.count()
        return self._repost_count

    def is_reposted_by(self, user):
        if user.is_authenticated:
            return self.repost_children.filter(author=user).exists()
        return False
    
    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts/images')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            if img.height > 1080 or img.width > 1080:
                img.thumbnail((1080, 1080))

            output = BytesIO()
            img.save(output, format='JPEG', quality=75)
            output.seek(0)

            file_name = self.image.name.split('.')[0]
            self.image = InMemoryUploadedFile(
                output, 'ImageField', f"{file_name}.jpg",
                'image/jpeg', sys.getsizeof(output), None
            )

        super(PostImage, self).save(*args, **kwargs)


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'post')


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments', db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"

    def is_liked_by(self, user):
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False


class CommentLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'comment')


class Report(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reports')
    reason = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('reporter', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.username} on post {self.post.id}"


class Repost(models.Model):
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reposts')
    reposter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reposts')
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='reposts')
    content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('original_post', 'reposter', 'group')
        ordering = ['-created_at']

    def __str__(self):
        return f"Repost by {self.reposter.username} of post {self.original_post.id}"


class HiddenPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hidden_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='hidden_by')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} hid post {self.post.id}"


class AuthorPreference(models.Model):
    PREFERENCE_CHOICES = [
        ('normal', 'Normal'),
        ('less', 'See Less'),
        ('none', 'See None'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='author_preferences')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='follower_preferences')
    preference = models.CharField(max_length=10, choices=PREFERENCE_CHOICES, default='normal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'author')

    def __str__(self):
        return f"{self.user.username} -> {self.author.username}: {self.preference}"


class SharedPost(models.Model):
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    sharer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_posts')
    shared_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_shares', null=True, blank=True)
    shared_to_group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, related_name='received_shares', null=True, blank=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_viewed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['original_post', 'sharer', 'shared_to'],
                condition=models.Q(shared_to__isnull=False),
                name='unique_user_share'
            ),
            models.UniqueConstraint(
                fields=['original_post', 'sharer', 'shared_to_group'],
                condition=models.Q(shared_to_group__isnull=False),
                name='unique_group_share'
            ),
            models.CheckConstraint(
                condition=models.Q(shared_to__isnull=False) | models.Q(shared_to_group__isnull=False),
                name='share_to_user_or_group'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        if self.shared_to:
            return f"{self.sharer.username} shared post {self.original_post.id} to {self.shared_to.username}"
        elif self.shared_to_group:
            return f"{self.sharer.username} shared post {self.original_post.id} to group {self.shared_to_group.name}"
        return f"{self.sharer.username} shared post {self.original_post.id}"
