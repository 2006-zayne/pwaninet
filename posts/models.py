import uuid
from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db.models.fields.files import ImageFieldFile
import sys

# Spool uploaded raw videos to local disk to keep web request latency < 1s
# and prevent Cloudflare HTTP 524 timeouts. Celery handles HLS transcoding
# and uploads all HLS chunks + the raw video file to Cloudflare R2 asynchronously.
raw_video_storage = FileSystemStorage()


class SafeImageFieldFile(ImageFieldFile):
    """FieldFile that returns empty string instead of raising ValueError when no file is associated."""
    @property
    def url(self):
        try:
            if not self.name:
                return ''
            return super().url
        except (ValueError, Exception):
            return ''


class SafeImageField(models.ImageField):
    """ImageField using SafeImageFieldFile to prevent template crashes when file is missing."""
    attr_class = SafeImageFieldFile

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, 'django.db.models.ImageField', args, kwargs


GRADIENT_CHOICES = [
    ('none', 'Standard (No Gradient)'),
    ('grad-ocean', 'Ocean Blue'),
    ('grad-forest', 'Forest Green'),
    ('grad-magma', 'Magma Red'),
    ('grad-midnight', 'Midnight Purple'),
    ('grad-desert', 'Desert Storm'),
    ('grad-stealth', 'Night Ops (Stealth)'),
    ('bg-cosmic-stars', 'Cosmic Stars'),
    ('bg-spring-flora', 'Spring Flora'),
    ('bg-playful-doodles', 'Playful Doodles'),
    ('bg-magic-sparkles', 'Magic Sparkles'),
    ('bg-username-pattern', 'Signature Pattern'),
    ('bg-geometric-dots', 'Geometric Dots'),
    ('bg-diagonal-lines', 'Diagonal Lines'),
    ('bg-hexagon-mesh', 'Hexagon Mesh'),
    ('bg-circuit-board', 'Circuit Board'),
    ('bg-matrix-rain', 'Matrix Rain'),
]


class Post(models.Model):
    share_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True)
    unit = models.ForeignKey('courses.Unit', on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to='posts/videos', storage=raw_video_storage, max_length=500, blank=True, null=True)
    video_preview = models.FileField(upload_to='posts/videos/previews', max_length=500, blank=True, null=True)
    video_poster = models.ImageField(upload_to='posts/videos/posters', max_length=500, blank=True, null=True)

    # Async video processing state (populated by the process_large_video Celery task)
    VIDEO_STATUS_PENDING     = 'pending'
    VIDEO_STATUS_TRANSCODING = 'transcoding'
    VIDEO_STATUS_READY       = 'ready'
    VIDEO_STATUS_FAILED      = 'failed'
    VIDEO_STATUS_CHOICES = [
        (VIDEO_STATUS_PENDING,     'Pending'),
        (VIDEO_STATUS_TRANSCODING, 'Transcoding'),
        (VIDEO_STATUS_READY,       'Ready'),
        (VIDEO_STATUS_FAILED,      'Failed'),
    ]
    video_status = models.CharField(
        max_length=20,
        choices=VIDEO_STATUS_CHOICES,
        default=VIDEO_STATUS_PENDING,
        blank=True,
        db_index=True,
        help_text='Processing state of the uploaded video',
    )
    hls_playlist = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Relative path or CDN URL to the HLS master playlist (master.m3u8)',
    )
    video_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Duration of the video in seconds (populated by ffprobe)',
    )
    video_width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Width of the video in pixels',
    )
    video_height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Height of the video in pixels',
    )

    docs = models.FileField(upload_to='posts/docs', max_length=500, blank=True, null=True)
    audio = models.FileField(upload_to='posts/audio', max_length=500, blank=True, null=True, help_text='Attach music/audio to post')
    thumbnail = SafeImageField(upload_to='posts/thumbnails', max_length=500, blank=True, null=True, help_text='Thumbnail for gradient/text posts')
    gradient_class = models.CharField(max_length=50, choices=GRADIENT_CHOICES, default='grad-ocean', blank=True)
    has_signature = models.BooleanField(default=False)
    custom_gradient_text = models.CharField(max_length=100, blank=True, null=True, help_text='Custom text for gradient patterns')
    custom_gradient_color1 = models.CharField(max_length=7, blank=True, null=True, help_text='Custom gradient color 1 (hex)')
    custom_gradient_color2 = models.CharField(max_length=7, blank=True, null=True, help_text='Custom gradient color 2 (hex)')
    custom_gradient_text_color = models.CharField(max_length=7, blank=True, null=True, help_text='Custom text color (hex)')
    repost_of = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='repost_children')
    shared_document = models.ForeignKey('documents.Document', on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_in_posts')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    video_transcript = models.TextField(blank=True, default='')
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            GinIndex(fields=['search_vector'], name='post_search_vector_idx'),
        ]

    def update_search_vector(self):
        """Recompute search vector with field weights."""
        from django.contrib.postgres.search import SearchVector
        Post.objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector('content', weight='B') +
                SearchVector('video_transcript', weight='C')
            )
        )

    def __str__(self):
        return f"Post by {self.author} on {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def get_intel_file(self):
        if self.pk and self.images.exists():
            return self.images.first().image
        if self.video:
            return self.video
        if self.docs:
            return self.docs
        return None
    
    @property
    def thumbnail_url(self):
        """Safely retrieve thumbnail URL without raising ValueError if file is missing."""
        try:
            if self.thumbnail and hasattr(self.thumbnail, 'url'):
                url = self.thumbnail.url
                return url if url else None
        except (ValueError, Exception):
            return None
        return None

    @property
    def get_video_for_feed(self):
        """Get video preview for feed, fallback to original or parent repost."""
        if self.video_preview:
            return self.video_preview
        if self.video:
            return self.video
        if self.repost_of_id and self.repost_of:
            return self.repost_of.get_video_for_feed
        return None
    
    @property
    def get_video_poster(self):
        """Get video poster image, delegating to parent repost if needed."""
        if self.video_poster:
            try:
                return self.video_poster.url
            except ValueError:
                pass
        if self.video:
            try:
                return self.video.url + '#poster'
            except ValueError:
                pass
        if self.repost_of_id and self.repost_of:
            return self.repost_of.get_video_poster
        return None

    @property
    def get_hls_url(self):
        """Get full CDN or media URL for HLS master playlist, delegating to parent repost if needed."""
        playlist = self.hls_playlist
        if not playlist and self.repost_of_id and self.repost_of:
            playlist = self.repost_of.hls_playlist
        if not playlist:
            return None
        if playlist.startswith('http://') or playlist.startswith('https://'):
            return playlist
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        return f"{media_url.rstrip('/')}/{playlist.lstrip('/')}"

    @property
    def is_reel(self):
        """Check if post is a vertical portrait video / reel."""
        # 1. Dimension-based check if stored
        if self.video_width and self.video_height:
            return self.video_height > self.video_width

        # 2. Explicit post_type check if present
        if hasattr(self, 'post_type') and self.post_type == 'reel':
            return True

        # 3. Filename heuristics
        video_field = self.video or self.video_preview
        if video_field:
            try:
                name = video_field.name.lower()
                if any(k in name for k in ['reel', 'portrait', 'short', 'tiktok', 'story', '9_16', '9x16', 'vertical']):
                    return True
            except Exception:
                pass

        try:
            intel = self.get_intel_file
            if intel:
                name = intel.name.lower()
                if any(k in name for k in ['reel', 'portrait', 'short', 'tiktok', 'story', '9_16', '9x16', 'vertical']):
                    return True
        except Exception:
            pass

        if self.repost_of_id and self.repost_of:
            return self.repost_of.is_reel

        return False

    @property
    def get_intel_file_is_video(self):
        """Check if the post has a video file attached directly or via get_intel_file."""
        if self.video or self.video_preview:
            return True
        try:
            intel = self.get_intel_file
            if intel:
                url = intel.url.lower()
                return any(ext in url for ext in ['.mp4', '.mov', '.webm', '.m4v'])
        except Exception:
            pass
        if self.repost_of_id and self.repost_of:
            return self.repost_of.get_intel_file_is_video
        return False

    @property
    def original_author(self):
        """Return original post author, handling legacy repost_of if present."""
        if self.repost_of_id:
            try:
                if self.repost_of:
                    return self.repost_of.author
            except Exception:
                pass
        return self.author

    def is_liked_by(self, user):
        if not self.pk:
            return False
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False

    @property
    def like_count(self):
        if not self.pk:
            return 0
        # Cache the count on the instance to avoid repeated queries
        if not hasattr(self, '_like_count'):
            self._like_count = self.likes.count()
        return self._like_count


    @property
    def repost_count(self):
        if not hasattr(self, '_repost_count'):
            self._repost_count = self.reposts.count() + self.repost_children.count()
        return self._repost_count

    def is_reposted_by(self, user):
        if not self.pk or not user or not user.is_authenticated:
            return False
        return self.reposts.filter(reposter=user).exists() or self.repost_children.filter(author=user).exists()

    def get_repost_avatars(self, viewer=None, max_avatars=3):
        """
        Get avatar user objects for users who reposted this reel/post.
        Prioritizes:
        1. Current viewer (if viewer reposted)
        2. Users the viewer follows (social proof)
        3. Other reposters up to max_avatars
        """
        if not self.pk:
            return []

        reposters_list = []
        for r in self.reposts.select_related('reposter').all():
            if r.reposter:
                reposters_list.append(r.reposter)
        for rc in self.repost_children.select_related('author').all():
            if rc.author:
                reposters_list.append(rc.author)
        if getattr(self, 'repost_context', None) and isinstance(self.repost_context, dict):
            ctx_reposter = self.repost_context.get('reposter')
            if ctx_reposter:
                reposters_list.append(ctx_reposter)

        if not reposters_list:
            return []

        viewer_id = viewer.id if (viewer and viewer.is_authenticated) else None
        following_ids = set()
        if viewer and viewer.is_authenticated:
            try:
                from users.models import Follow
                following_ids = set(Follow.objects.filter(follower=viewer).values_list('followed_id', flat=True))
            except Exception:
                following_ids = set()

        self_users = []
        followed_users = []
        other_users = []

        for reposter in reposters_list:
            if viewer_id and reposter.id == viewer_id:
                self_users.append(reposter)
            elif reposter.id in following_ids:
                followed_users.append(reposter)
            else:
                other_users.append(reposter)

        seen_ids = set()
        result = []
        for u in (self_users + followed_users + other_users):
            if u.id not in seen_ids:
                seen_ids.add(u.id)
                result.append(u)
            if len(result) >= max_avatars:
                break
        return result

    def get_repost_header_info(self, viewer=None):
        """
        Determine top postcard header text ("reposted this") using Option A:
        Only show when the current viewer OR a friend the viewer follows reposted it
        (or if the post is a direct repost_of / has repost_context).
        """
        if not self.pk:
            return {'show': False}

        viewer_id = viewer.id if (viewer and viewer.is_authenticated) else None
        following_ids = set()
        if viewer and viewer.is_authenticated:
            try:
                from users.models import Follow
                following_ids = set(Follow.objects.filter(follower=viewer).values_list('followed_id', flat=True))
            except Exception:
                following_ids = set()

        entries = []
        seen_uids = set()

        for r in self.reposts.select_related('reposter').order_by('-created_at'):
            if r.reposter and r.reposter.id not in seen_uids:
                seen_uids.add(r.reposter.id)
                entries.append((r.reposter, r.created_at))

        for rc in self.repost_children.select_related('author').order_by('-created_at'):
            if rc.author and rc.author.id not in seen_uids:
                seen_uids.add(rc.author.id)
                entries.append((rc.author, rc.created_at))

        if getattr(self, 'repost_context', None) and isinstance(self.repost_context, dict):
            ctx_user = self.repost_context.get('reposter')
            ctx_time = self.repost_context.get('created_at') or self.created_at
            if ctx_user and ctx_user.id not in seen_uids:
                seen_uids.add(ctx_user.id)
                entries.append((ctx_user, ctx_time))

        if self.repost_of_id and self.author and self.author.id not in seen_uids:
            seen_uids.add(self.author.id)
            entries.append((self.author, self.created_at))

        total_count = max(self.repost_count, len(entries))
        if total_count == 0 or not entries:
            return {'show': False}

        self_entry = None
        followed_entries = []
        for u, dt in entries:
            if viewer_id and u.id == viewer_id:
                self_entry = (u, dt)
            elif u.id in following_ids:
                followed_entries.append((u, dt))

        if not self_entry and not followed_entries and not self.repost_of_id:
            return {'show': False}

        if self_entry and followed_entries:
            friend_user, friend_dt = followed_entries[0]
            others_count = max(0, total_count - 2)
            return {
                'show': True,
                'is_self': True,
                'self_user': self_entry[0],
                'primary_user': friend_user,
                'primary_name': friend_user.get_full_name() or friend_user.username,
                'primary_username': friend_user.username,
                'second_user': None,
                'others_count': others_count,
                'created_at': self_entry[1] or friend_dt,
            }
        elif self_entry:
            others_count = max(0, total_count - 1)
            return {
                'show': True,
                'is_self': True,
                'self_user': self_entry[0],
                'primary_user': None,
                'primary_name': '',
                'primary_username': '',
                'second_user': None,
                'others_count': others_count,
                'created_at': self_entry[1],
            }
        else:
            primary_user, primary_dt = followed_entries[0] if followed_entries else entries[0]
            second_user = followed_entries[1][0] if (len(followed_entries) >= 2 and total_count == 2) else None
            others_count = 0 if second_user else max(0, total_count - 1)
            return {
                'show': True,
                'is_self': False,
                'self_user': None,
                'primary_user': primary_user,
                'primary_name': primary_user.get_full_name() or primary_user.username,
                'primary_username': primary_user.username,
                'second_user': second_user,
                'second_name': (second_user.get_full_name() or second_user.username) if second_user else '',
                'second_username': second_user.username if second_user else '',
                'others_count': others_count,
                'created_at': primary_dt,
            }

    def get_repost_badge_data(self, viewer=None, max_avatars=3):
        """
        Structured metadata for front-end floating repost badge.
        """
        reposters = self.get_repost_avatars(viewer=viewer, max_avatars=max_avatars)
        total_count = self.repost_count
        is_reposted = self.is_reposted_by(viewer) if viewer else False
        header_info = self.get_repost_header_info(viewer=viewer)

        avatars = []
        for u in reposters:
            pic_url = '/static/images/default-avatar.png'
            try:
                if u.profile_pic and hasattr(u.profile_pic, 'url'):
                    pic_url = u.profile_pic.url
            except Exception:
                pass
            avatars.append({
                'id': u.id,
                'username': u.username,
                'name': u.get_full_name() or u.username,
                'avatar': pic_url,
                'is_self': viewer.id == u.id if (viewer and viewer.is_authenticated) else False,
            })

        followed_friend = None
        if header_info.get('primary_user'):
            followed_friend = {
                'name': header_info.get('primary_name', ''),
                'username': header_info.get('primary_username', ''),
            }

        return {
            'repost_count': total_count,
            'is_reposted': is_reposted,
            'avatars': avatars,
            'has_more': max(0, total_count - len(avatars)),
            'followed_friend': followed_friend,
        }
    
    def save(self, *args, **kwargs):
        super(Post, self).save(*args, **kwargs)


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='posts/images', max_length=500)
    thumbnail_400 = models.ImageField(upload_to='posts/images/thumbnails', max_length=500, blank=True, null=True)
    thumbnail_800 = models.ImageField(upload_to='posts/images/thumbnails', max_length=500, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def get_thumbnail_url(self, size='400'):
        """Get thumbnail URL for feed display"""
        if size == '400' and self.thumbnail_400:
            return self.thumbnail_400.url
        elif size == '800' and self.thumbnail_800:
            return self.thumbnail_800.url
        return self.image.url

    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            original_format = img.format
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize original if too large
            if img.height > 1080 or img.width > 1080:
                img.thumbnail((1080, 1080))

            # Save original as WebP if possible, otherwise JPEG
            output = BytesIO()
            if original_format == 'PNG' and img.mode == 'RGBA':
                # Keep PNG for transparency
                img.save(output, format='PNG', optimize=True)
                file_ext = 'png'
                mime_type = 'image/png'
            else:
                # Use WebP for better compression
                img.save(output, format='WEBP', quality=80, method=6)
                file_ext = 'webp'
                mime_type = 'image/webp'
            output.seek(0)

            file_name = self.image.name.split('.')[0]
            self.image = InMemoryUploadedFile(
                output, 'ImageField', f"{file_name}.{file_ext}",
                mime_type, sys.getsizeof(output), None
            )

            # Generate 400px thumbnail for feed
            img_400 = img.copy()
            img_400.thumbnail((400, 400))
            output_400 = BytesIO()
            img_400.save(output_400, format='WEBP', quality=75, method=6)
            output_400.seek(0)
            self.thumbnail_400 = InMemoryUploadedFile(
                output_400, 'ImageField', f"{file_name}_400.webp",
                'image/webp', sys.getsizeof(output_400), None
            )

            # Generate 800px thumbnail for larger displays
            img_800 = img.copy()
            img_800.thumbnail((800, 800))
            output_800 = BytesIO()
            img_800.save(output_800, format='WEBP', quality=80, method=6)
            output_800.seek(0)
            self.thumbnail_800 = InMemoryUploadedFile(
                output_800, 'ImageField', f"{file_name}_800.webp",
                'image/webp', sys.getsizeof(output_800), None
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
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', db_index=True)
    reply_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'parent_comment']),
            models.Index(fields=['parent_comment', 'created_at']),
        ]

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


class PostImageLike(models.Model):
    """Individual likes for post images"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True)
    post_image = models.ForeignKey(PostImage, on_delete=models.CASCADE, related_name='likes', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'post_image')

    def __str__(self):
        return f"{self.user.username} likes image {self.post_image.id}"


class PostImageComment(models.Model):
    """Individual comments for post images"""
    post_image = models.ForeignKey(PostImage, on_delete=models.CASCADE, related_name='comments', db_index=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='image_comments', db_index=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.author} on image {self.post_image.id}"


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
