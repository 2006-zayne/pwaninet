# Pwaninet Posts Implementation Analysis

## Overview
This document provides a comprehensive analysis of the posts implementation in the Pwaninet social networking platform, covering all post types, media handling, caching mechanisms, and social interactions.

## Table of Contents
1. [Post Types](#post-types)
2. [Data Models](#data-models)
3. [Media File Storage & Data Flow](#media-file-storage--data-flow)
4. [File Caching Mechanisms](#file-caching-mechanisms)
5. [Background Uploading & Sync](#background-uploading--sync)
6. [Media File Sharing Limits](#media-file-sharing-limits)
7. [Social Interactions](#social-interactions)
8. [Comments System](#comments-system)
9. [Feed Algorithm](#feed-algorithm)
10. [API Endpoints](#api-endpoints)

---

## Post Types

### 1. Regular Posts (Global Feed)
- **Model**: `Post` with `group=null`
- **Visibility**: Visible to users in same course/year or based on following relationships
- **Location**: Appears in home feed for relevant users
- **Creation**: Via `PostForm` or API through `PostCreateSerializer`

### 2. Group Posts
- **Model**: `Post` with `group` field populated
- **Visibility**: Only visible to approved group members
- **Location**: Appears in group feed and home feed for group members
- **Restrictions**: User must be approved member to post/comment/like
- **Creation**: Via `group_id` parameter in post creation

### 3. Reposts
- **Model**: Two implementations:
  - **Inline Reposts**: `Post.repost_of` field (self-referential FK)
  - **Dedicated Reposts**: `Repost` model with `original_post` FK
- **Visibility**: 
  - Personal reposts: Visible in reposter's feed
  - Group reposts: Visible in group feed
- **Behavior**: Creates new post with reference to original, copies media files
- **Restrictions**: Cannot repost own posts, one repost per location (user/group)

### 4. Shared Posts
- **Model**: `SharedPost` with tracking capabilities
- **Types**:
  - Direct user-to-user sharing
  - User-to-group sharing (creates repost in group)
- **Features**: View tracking, message attachment, notifications
- **Restrictions**: Cannot share to self, must be member of target group

---

## Data Models

### Core Post Model
```python
class Post(models.Model):
    group = models.ForeignKey('groups.Group', null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    course = models.ForeignKey('courses.Course', null=True, blank=True)
    unit = models.ForeignKey('courses.Unit', null=True, blank=True)
    content = models.TextField()
    video = models.FileField(upload_to='posts/videos', blank=True, null=True)
    docs = models.FileField(upload_to='posts/docs', blank=True, null=True)
    audio = models.FileField(upload_to='posts/audio', blank=True, null=True)
    gradient_class = models.CharField(max_length=50, choices=GRADIENT_CHOICES)
    repost_of = models.ForeignKey('self', null=True, blank=True, related_name='repost_children')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### PostImage Model
```python
class PostImage(models.Model):
    post = models.ForeignKey(Post, related_name='images')
    image = models.ImageField(upload_to='posts/images')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Social Interaction Models
- **Like**: `Like(user, post, created_at)` - unique per user-post
- **Comment**: `Comment(post, author, content, created_at)` - flat structure
- **CommentLike**: `CommentLike(user, comment, created_at)` - unique per user-comment
- **Repost**: `Repost(original_post, reposter, group, content, created_at)`
- **SharedPost**: `SharedPost(original_post, sharer, shared_to, shared_to_group, message, is_viewed)`

---

## Media File Storage & Data Flow

### Storage Configuration
- **Base Directory**: `MEDIA_ROOT = BASE_DIR / 'media'`
- **Media URL**: `/media/`
- **Storage Backend**: Django's default file system storage

### File Type Storage Paths
| File Type | Upload Path | Max Size | Processing |
|-----------|-------------|----------|------------|
| Images | `posts/images/` | 5MB | Resize to 1080x1080, convert to JPEG @ 75% quality |
| Videos | `posts/videos/` | 150MB | No processing |
| Documents | `posts/docs/` | 50MB | No processing |
| Audio | `posts/audio/` | 20MB | No processing |

### Data Flow for Post Creation

1. **Form Submission** (`PostForm`)
   - User submits post with content and optional media files
   - Form validates file sizes and types

2. **Post Creation Service** (`post_service.py:create_post_for_user`)
   ```python
   def create_post_for_user(form, user, files, group_id=None):
       with transaction.atomic():
           post = form.save(commit=False)
           post.author = user
           post.course = user.course
           post.year = user.year
           # Handle group assignment
           if group_id:
               post.group = get_object_or_404(Group, id=group_id)
           post.save()
           
           # Handle multiple image uploads
           if files and 'images' in files:
               images = files.getlist('images')
               for idx, image_file in enumerate(images[:15]):  # Max 15 images
                   PostImage.objects.create(
                       post=post,
                       image=image_file,
                       order=idx
                   )
           
           # Handle audio upload
           if files and 'audio' in files:
               audio_file = files.get('audio')
               if audio_file and hasattr(audio_file, 'name') and audio_file.name:
                   post.audio = audio_file
                   post.save()
   ```

3. **Image Processing** (`PostImage.save()`)
   - Opens image with PIL
   - Converts to RGB if necessary
   - Resizes if dimensions > 1080x1080
   - Saves as JPEG at 75% quality
   - Stores in memory before final save

4. **Database Storage**
   - Post record created in PostgreSQL
   - File paths stored in database
   - Actual files stored on filesystem

5. **Feed Invalidation**
   - Home feed cache invalidated for author
   - Notifications sent to relevant users

### File Access Flow
1. **Request**: Client requests media file via `/media/posts/images/...`
2. **Django**: Serves file through `django.views.static.serve`
3. **Whitenoise**: Middleware handles static/media file serving in production
4. **Response**: File returned to client

---

## File Caching Mechanisms

### Cache Configuration
```python
CACHES = {
    'default': {
        'BACKEND': 'pwaninet.cache_backends.FallbackRedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'TIMEOUT': 300,
        'KEY_PREFIX': 'pwaninet',
    },
    'fallback': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pwaninet-fallback-cache',
    }
}
```

### FallbackRedisCache Backend
- **Primary**: Redis cache for distributed caching
- **Fallback**: Local memory cache if Redis unavailable
- **Behavior**: Automatic failover with logging
- **Operations**: All cache operations (get, set, delete, etc.) have fallback logic

### Feed Caching
- **Home Feed Context**: Cached per user with cursor-based pagination
- **Invalidation**: Feed cache invalidated on:
  - Post creation
  - Post deletion
  - Like/unlike actions
  - Comment additions
  - Follow/unfollow actions

### Like Count Caching
```python
@property
def like_count(self):
    if not hasattr(self, '_like_count'):
        self._like_count = self.likes.count()
    return self._like_count
```
- Instance-level caching to avoid repeated database queries
- Reset on each request cycle

### Notification Count Caching
- **Function**: `get_cached_unread_count(request.user)`
- **Storage**: Cached in Redis with user-specific key
- **Invalidation**: Updated when notifications are created/read

---

## Background Uploading & Sync

### Current Status
**No background uploading or sync features are currently implemented for posts.**

### Celery Configuration
- **Status**: Celery is configured but not actively used for post operations
- **Configuration**: `pwaninet/celery.py` with autodiscovery enabled
- **Tasks**: No post-related background tasks found
- **Notifications**: Empty `notifications/tasks.py` file

### Current Processing Model
All media processing happens **synchronously** during post creation:
- Image resizing and conversion happens in the request thread
- File uploads block until complete
- No progress tracking for uploads
- No retry mechanism for failed uploads

### Recommendations for Background Processing
To implement background uploading/sync, consider:
1. **Celery Tasks** for:
   - Image processing (resize, convert)
   - Video transcoding
   - File validation
   - Thumbnail generation
2. **Progress Tracking**:
   - WebSocket updates for upload progress
   - Database status fields
3. **Retry Logic**:
   - Automatic retry for failed uploads
   - Dead letter queue for failed tasks

---

## Media File Sharing Limits

### Per-Post Limits
| Media Type | Max Count | Max Size per File | Total Max Size |
|------------|-----------|-------------------|----------------|
| Images | 15 | 5MB | 75MB |
| Videos | 1 | 150MB | 150MB |
| Documents | 1 | 50MB | 50MB |
| Audio | 1 | 20MB | 20MB |

### Validation Implementation
```python
# posts/validators.py
def validate_image_size(value):
    limit_mb = 5
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image too large! Maximum allowed is {limit_mb}MB.")

def validate_video_size(value):
    limit_mb = 150
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Video file exceeds mission parameters! Maximum allowed is {limit_mb}MB.")

def validate_document_size(value):
    limit_mb = 50
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Document too heavy! Maximum allowed is {limit_mb}MB.")

def validate_audio_size(value):
    limit_mb = 20
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Audio file too large! Maximum allowed is {limit_mb}MB.")
```

### Image Count Enforcement
```python
# posts/services/post_service.py
if files and 'images' in files:
    images = files.getlist('images')
    for idx, image_file in enumerate(images[:15]):  # Max 15 images
        PostImage.objects.create(
            post=post,
            image=image_file,
            order=idx
        )
```

### Storage Considerations
- **Filesystem Storage**: All files stored locally on server
- **No CDN Integration**: Files served directly from application server
- **No Compression**: Videos and documents stored as-is
- **Image Optimization**: Only basic resize and format conversion

---

## Social Interactions

### Likes

#### Implementation
- **Model**: `Like(user, post, created_at)`
- **Constraint**: Unique per user-post combination
- **API**: Toggle-based (like/unlike in single endpoint)
- **Caching**: Instance-level count caching

#### Like Flow
```python
def toggle_post_like_for_user(post, user):
    like_qs = Like.objects.filter(user=user, post=post)
    if like_qs.exists():
        like_qs.delete()
        is_liked = False
    else:
        Like.objects.create(user=user, post=post)
        is_liked = True
    invalidate_home_feed_context(user.id)
    if post.author_id != user.id:
        invalidate_home_feed_context(post.author_id)
    return {
        "post": post,
        "is_liked": is_liked,
        "like_count": post.likes.count()
    }
```

#### Permissions
- **Group Posts**: Must be approved group member to like
- **Global Posts**: No restrictions (authenticated users only)

### Reposts

#### Implementation
- **Two Models**: 
  - `Post.repost_of` (inline reposts)
  - `Repost` (dedicated repost tracking)
- **Behavior**: Creates new post with reference to original
- **Media Copying**: Images copied to new post, video/docs referenced

#### Repost Flow
```python
def create_repost(user, post, group=None, content=None):
    # Validation
    if post.author == user:
        raise ValidationError("You cannot repost your own post.")
    
    if Repost.objects.filter(original_post=post, reposter=user, group=group).exists():
        raise ValidationError("You have already reposted this post.")
    
    # Group membership check
    if group:
        # Verify membership...
    
    # Create repost
    repost = Repost.objects.create(
        original_post=post,
        reposter=user,
        group=group,
        content=content
    )
    return repost
```

#### API Repost Implementation
```python
# views.py - POST /posts/{id}/repost/
repost = Post.objects.create(
    author=request.user,
    content=content,
    group=original_post.group,
    course=original_post.course,
    unit=original_post.unit,
    video=original_post.video,
    docs=original_post.docs,
    gradient_class=original_post.gradient_class,
    repost_of=original_post
)

# Copy images
for image in original_post.images.all():
    PostImage.objects.create(post=repost, image=image.image)
```

### Sharing

#### Implementation
- **Model**: `SharedPost(original_post, sharer, shared_to, shared_to_group, message, is_viewed)`
- **Types**: User-to-user and user-to-group sharing
- **Tracking**: View status tracking for received shares
- **Notifications**: Automatic notification creation

#### Share Flow
```python
def share_post(user, post, shared_to_user=None, shared_to_group=None, message=None):
    # Validation
    if not shared_to_user and not shared_to_group:
        raise ValidationError("You must share to either a user or a group.")
    if shared_to_user and shared_to_group:
        raise ValidationError("You can only share to either a user or a group, not both.")
    
    # User sharing
    if shared_to_user:
        if shared_to_user == user:
            raise ValidationError("You cannot share posts to yourself.")
        
        shared_post = SharedPost.objects.create(
            original_post=post,
            sharer=user,
            shared_to=shared_to_user,
            message=message
        )
        # Create notification...
    
    # Group sharing
    elif shared_to_group:
        # Create repost in group
        repost = Post.objects.create(
            author=user,
            content=message or '',
            group=shared_to_group,
            video=post.video,
            docs=post.docs,
            gradient_class=post.gradient_class,
            repost_of=post
        )
        # Copy images...
        # Create SharedPost record...
        # Notify group admins...
```

#### Bulk Sharing
- **User Sharing**: Comma-separated usernames via `shared_to_usernames`
- **Group Sharing**: Comma-separated group IDs via `shared_to_group_ids`
- **Error Handling**: Partial success with error reporting

---

## Comments System

### Current Implementation
- **Model**: `Comment(post, author, content, created_at)`
- **Structure**: Flat structure (no parent/child relationships)
- **Ranking**: Comments ranked by likes and recency
- **Likes**: Comments can be liked via `CommentLike` model

### Comment Ranking Algorithm
```python
def get_ranked_comments_queryset(post):
    now = timezone.now()
    return post.comments.select_related('author').annotate(
        likes_count = Count('likes', distinct=True),
        recency_bonus = Case(
            When(created_at__gte=now - timedelta(hours=1), then=Value(3)),
            When(created_at__gte=now - timedelta(days=1), then=Value(2)),
            When(created_at__gte=now - timedelta(days=7), then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).order_by('-likes_count', '-recency_bonus', '-created_at')
```

### Comment Flow
```python
def add_comment_to_post(post, author, content):
    content = (content or '').strip()
    if not content:
        return None
    comment = Comment.objects.create(post=post, author=author, content=content)
    invalidate_home_feed_context(author.id)
    return comment
```

### Comment Likes
```python
def toggle_comment_like_for_user(comment, user):
    like_qs = CommentLike.objects.filter(user=user, comment=comment)
    if like_qs.exists():
        like_qs.delete()
    else:
        CommentLike.objects.create(user=user, comment=comment)
    return {
        'comment': comment,
        'liked_comment_ids': {comment.id}
    }
```

### Reply Support
**Current Status**: Comments do NOT support replies.

**To Add Reply Support**, you would need to:
1. **Add field to Comment model**:
   ```python
   parent = models.ForeignKey('self', null=True, blank=True, related_name='replies')
   ```

2. **Update serializers** to include nested replies
3. **Update ranking algorithm** to handle threaded discussions
4. **Add API endpoints** for creating replies
5. **Update UI** to display threaded comments
6. **Consider depth limits** (e.g., max 3 levels deep)

### Comment Display
- **Default**: Shows 3 top-ranked comments
- **Show All**: Option to display all comments
- **Pagination**: Not currently implemented (all comments loaded)

---

## Feed Algorithm

### Feed Prioritization
The feed uses a sophisticated ranking algorithm with multiple factors:

#### Priority Tiers
1. **Followed Users**: 100 points
2. **User's Groups**: 80 points
3. **Same Course & Year**: 70 points
4. **Same Course (any year)**: 50 points
5. **Same Year (any course)**: 40 points
6. **Default**: 20 points

#### Engagement Score
```python
engagement_score = (
    like_count * 1.0 +
    comment_count * 2.0 +
    repost_count * 3.0 +
    author_affinity +
    recency_score
)
```

#### Recency Score
- **< 6 hours**: 50 points
- **< 1 day**: 40 points
- **< 3 days**: 30 points
- **< 7 days**: 20 points
- **< 30 days**: 10 points
- **Older**: 5 points (minimum to ensure visibility)

#### Author Affinity
- **Followed authors**: 30 points boost
- **Others**: 0 points

### Feed Query
```python
def get_prioritized_feed_queryset(user, following_ids, user_group_ids):
    filters = Q(author_id__in=following_ids)
    
    if user_group_ids:
        filters |= Q(group_id__in=user_group_ids)
    if user.course:
        filters |= Q(course=user.course)
    if hasattr(user, 'year') and user.year:
        filters |= Q(unit__year=user.year)
    
    # Exclude hidden posts
    hidden_post_ids = HiddenPost.objects.filter(user=user).values_list('post_id', flat=True)
    if hidden_post_ids:
        filters &= ~Q(id__in=hidden_post_ids)
    
    return Post.objects.filter(filters).select_related('author', 'unit', 'group').prefetch_related('likes', 'comments').annotate(
        like_count_annotated=Count('likes', distinct=True),
        comment_count_annotated=Count('comments', distinct=True),
        repost_count_annotated=Count('repost_children', distinct=True),
        author_affinity=Case(...),
        priority_tier=Case(...),
        recency_score=Case(...)
    ).annotate(
        engagement_score=(...)
    ).distinct().order_by('-priority_tier', '-engagement_score', '-created_at', '-id')
```

### Pagination
- **Type**: Cursor-based pagination
- **Cursor Format**: `{post_id}|{created_at_timestamp}`
- **Page Size**: 10 posts per page
- **Benefits**: Efficient for large datasets, prevents duplicate/missing posts

---

## API Endpoints

### Post Endpoints

#### Create Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/`
- **Serializer**: `PostCreateSerializer`
- **Permissions**: `IsAuthenticated`
- **Validation**: Group membership check for group posts

#### List Posts
- **Method**: `GET`
- **Path**: `/api/v1/posts/`
- **Serializer**: `PostSerializer`
- **Queryset**: All posts with select_related/prefetch_related
- **Filters**: Django-filter backend enabled

#### Post Detail
- **Method**: `GET`
- **Path**: `/api/v1/posts/{id}/`
- **Serializer**: `PostSerializer`

#### Update Post
- **Method**: `PUT/PATCH`
- **Path**: `/api/v1/posts/{id}/`
- **Serializer**: `PostUpdateSerializer`
- **Permissions**: `IsAuthenticated`, `CanEditPost`

#### Delete Post
- **Method**: `DELETE`
- **Path**: `/api/v1/posts/{id}/`
- **Permissions**: `IsAuthenticated`, `CanDeletePost`

### Post Actions

#### Like/Unlike Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/{id}/like/`
- **Behavior**: Toggle like status
- **Validation**: Group membership check for group posts

#### Report Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/{id}/report/`
- **Serializer**: `ReportCreateSerializer`
- **Validation**: One report per user per post

#### Get Post Comments
- **Method**: `GET`
- **Path**: `/api/v1/posts/{id}/comments/`
- **Serializer**: `CommentSerializer`

#### Repost Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/{id}/repost/`
- **Behavior**: Creates new post with repost_of reference
- **Media**: Copies images from original post

#### Delete Repost
- **Method**: `DELETE`
- **Path**: `/api/v1/posts/{id}/repost/`
- **Validation**: Must be reposter and post must be a repost

#### Get Post Reposts
- **Method**: `GET`
- **Path**: `/api/v1/posts/{id}/reposts/`
- **Serializer**: `RepostSerializer`

#### Hide Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/{id}/hide/`
- **Behavior**: Creates HiddenPost record

#### Unhide Post
- **Method**: `DELETE`
- **Path**: `/api/v1/posts/{id}/hide/`
- **Behavior**: Removes HiddenPost record

#### Share Post
- **Method**: `POST`
- **Path**: `/api/v1/posts/{id}/share/`
- **Parameters**: 
  - `shared_to` (user ID)
  - `shared_to_group` (group ID)
  - `shared_to_usernames` (comma-separated usernames)
  - `shared_to_group_ids` (comma-separated group IDs)
  - `message` (optional message)

### Comment Endpoints

#### Create Comment
- **Method**: `POST`
- **Path**: `/api/v1/comments/`
- **Serializer**: `CommentCreateSerializer`
- **Validation**: Group membership check for group posts

#### List Comments
- **Method**: `GET`
- **Path**: `/api/v1/comments/`
- **Serializer**: `CommentSerializer`

#### Comment Detail
- **Method**: `GET`
- **Path**: `/api/v1/comments/{id}/`
- **Serializer**: `CommentSerializer`

### Web Views (Django Templates)

#### Home Feed
- **Path**: `/`
- **View**: `home_view`
- **Template**: `posts/home.html`
- **Pagination**: HTMX infinite scroll with cursor

#### Create Post
- **Path**: `/posts/create/`
- **View**: `create_post_view`
- **Template**: `posts/create_post.html`

#### Post Detail
- **Path**: `/posts/{post_id}/`
- **View**: `post_detail_view`
- **Template**: `posts/post_detail.html`

#### Add Comment
- **Path**: `/posts/{post_id}/comment/`
- **View**: `add_comment`
- **Method**: `POST`

#### Toggle Like
- **Path**: `/posts/{post_id}/like/`
- **View**: `toggle_like`
- **Method**: `POST`
- **Response**: HTMX partial

#### Toggle Comment Like
- **Path**: `/comments/{comment_id}/like/`
- **View**: `toggle_comment_like`
- **Method**: `POST`
- **Response**: HTMX partial

#### Share Post (Web)
- **Path**: `/posts/{post_id}/share/`
- **View**: `share_post_view`
- **Method**: `POST`
- **Response**: HTMX partial or redirect

#### Shared Posts
- **Path**: `/posts/shared/`
- **View**: `shared_posts_view`
- **Template**: `posts/shared_posts.html`

---

## Summary & Recommendations

### Current Strengths
1. **Flexible Post Types**: Supports regular, group, repost, and shared posts
2. **Comprehensive Social Features**: Likes, comments, reposts, sharing all implemented
3. **Smart Feed Algorithm**: Multi-factor ranking with engagement scoring
4. **Efficient Pagination**: Cursor-based for scalability
5. **Fallback Caching**: Redis with local memory fallback
6. **Media Processing**: Automatic image optimization

### Areas for Improvement
1. **Comment Replies**: Currently flat structure, could benefit from threading
2. **Background Processing**: No async media processing or upload tracking
3. **CDN Integration**: Files served from application server
4. **Video Optimization**: No transcoding or thumbnail generation
5. **Comment Pagination**: All comments loaded at once
6. **Upload Progress**: No real-time progress tracking
7. **Media Compression**: Videos and documents not compressed

### Scalability Considerations
1. **File Storage**: Consider cloud storage (S3, CloudFront) for better performance
2. **CDN**: Implement CDN for media file delivery
3. **Background Tasks**: Use Celery for heavy media processing
4. **Database**: Consider read replicas for feed queries
5. **Cache**: Implement more aggressive caching for popular posts

### Security Considerations
1. **File Validation**: Size limits enforced but could add type validation
2. **Access Control**: Group membership checks in place
3. **Rate Limiting**: DRF throttling configured
4. **CSRF Protection**: Enabled for web views

---

## File Locations Reference

### Models
- `posts/models.py` - All post-related models
- `posts/serializers.py` - DRF serializers
- `posts/forms.py` - Django forms

### Services
- `posts/services/post_service.py` - Post creation and likes
- `posts/services/comment_service.py` - Comment operations
- `posts/services/repost_service.py` - Repost operations
- `posts/services/share_service.py` - Share operations
- `posts/services/feed_service.py` - Feed building
- `posts/services/hide_service.py` - Post hiding
- `posts/services/author_preference_service.py` - Author preferences

### Queries
- `posts/queries/feed_queries.py` - Feed algorithm
- `posts/queries/comment_queries.py` - Comment ranking
- `posts/queries/search_queries.py` - Search functionality

### Views
- `posts/views.py` - API viewsets and web views

### Validation
- `posts/validators.py` - File size validators

### Configuration
- `pwaninet/settings/base.py` - Media and cache configuration
- `pwaninet/cache_backends.py` - Custom cache backend
- `pwaninet/celery.py` - Celery configuration

---

*Document generated on June 2, 2026*
*Pwaninet v0.99.06*
