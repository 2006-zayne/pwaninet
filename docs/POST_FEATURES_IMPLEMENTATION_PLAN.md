# Post Features Implementation Plan

## Overview
This document outlines the implementation plan for the following post features:
1. **Repost Post** - Allow users to repost content to their profile or groups
2. **Hide Post** - Allow users to hide specific posts from their feed
3. **See Less From Author** - Allow users to reduce visibility of posts from specific authors
4. **Share to Profile** - Allow users to share posts to another user's profile
5. **Delete Post** - Enhanced delete permissions (author, admin, moderator)

---

## Current State Analysis

### Existing Models
- `Post` - Main post model with author, group, course, unit, content, media
- `Like` - User likes on posts
- `Comment` - Comments on posts
- `Report` - Post reports
- `User` - Has global roles: PRESIDENT, DELEGATE, VERIFIED, NORMAL
- `Follow` - User follow relationships

### Existing Permissions
- `CanDeletePost` - Author OR group admin can delete
- `CanEditPost` - Only author can edit
- `IsPostAuthorOrReadOnly` - Read for approved members, write for author

### Existing API Endpoints
- `/posts/{id}/` - CRUD operations
- `/posts/{id}/like/` - Toggle like
- `/posts/{id}/report/` - Report post
- `/posts/{id}/comments/` - List comments

---

## Feature 1: Repost Post

### Database Changes
**New Model: `Repost`**
```python
class Repost(models.Model):
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reposts')
    reposter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reposts')
    group = models.ForeignKey('groups.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='reposts')
    content = models.TextField(blank=True, null=True)  # Optional comment with repost
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        unique_together = ('original_post', 'reposter', 'group')
        ordering = ['-created_at']
```

**Post Model Addition**
```python
# Add to Post model
@property
def repost_count(self):
    return self.reposts.count()

def is_reposted_by(self, user):
    if user.is_authenticated:
        return self.reposts.filter(reposter=user).exists()
    return False
```

### API Endpoints
- `POST /posts/{id}/repost/` - Repost a post
  - Request body: `{ "group_id": optional, "content": optional }`
  - Response: Repost details
- `DELETE /posts/{id}/repost/` - Undo repost
- `GET /posts/{id}/reposts/` - List all reposts of a post

### Permissions
- User must be authenticated
- User must be approved member of the target group (if reposting to group)
- Cannot repost own post
- Cannot repost same post twice to same location

### Services
- `posts/services/repost_service.py`
  - `create_repost(user, post, group=None, content=None)`
  - `delete_repost(user, post, group=None)`
  - `get_post_reposts(post)`

### Frontend Considerations
- Repost button on post cards
- Repost modal with optional comment
- Group selector for repost destination
- Show repost count and who reposted
- Distinguish original posts from reposts in feed

---

## Feature 2: Hide Post

### Database Changes
**New Model: `HiddenPost`**
```python
class HiddenPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hidden_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='hidden_by')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        unique_together = ('user', 'post')
```

### API Endpoints
- `POST /posts/{id}/hide/` - Hide a post from feed
- `DELETE /posts/{id}/hide/` - Unhide a post
- `GET /posts/hidden/` - List hidden posts

### Permissions
- User must be authenticated
- Users can only hide/unhide their own hidden posts

### Services
- `posts/services/hide_service.py`
  - `hide_post(user, post)`
  - `unhide_post(user, post)`
  - `is_post_hidden(user, post)`
  - `get_hidden_posts(user)`

### Feed Integration
- Modify `posts/queries/feed_queries.py` to exclude hidden posts
- Add hidden post filter to `build_home_feed_context`

### Frontend Considerations
- Hide option in post menu (three dots)
- Hidden posts section in user settings
- Option to unhide posts
- Hidden posts should not appear in any feed

---

## Feature 3: See Less From Author

### Database Changes
**New Model: `AuthorPreference`**
```python
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
```

### API Endpoints
- `POST /users/{id}/preference/` - Set preference for author
  - Request body: `{ "preference": "less" | "none" }`
- `GET /users/{id}/preference/` - Get current preference
- `GET /users/preferences/` - List all author preferences

### Permissions
- User must be authenticated
- Users can only set their own preferences
- Cannot set preference for self

### Services
- `posts/services/author_preference_service.py`
  - `set_author_preference(user, author, preference)`
  - `get_author_preference(user, author)`
  - `get_authors_to_see_less(user)`
  - `get_authors_to_hide(user)`

### Feed Integration
- Modify feed queries to:
  - Reduce frequency of "less" preferred authors (e.g., show 1 in 5 posts)
  - Completely exclude "none" preferred authors
- Add weighted randomization for "less" preference

### Frontend Considerations
- "See less from this author" option in post menu
- "See all posts from this author" option to reset
- Author preferences section in user settings
- Visual indicator when posts are filtered

---

## Feature 4: Share to Profile

### Database Changes
**New Model: `SharedPost`**
```python
class SharedPost(models.Model):
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    sharer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_posts')
    shared_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_shares')
    message = models.TextField(blank=True, null=True)  # Optional message with share
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_viewed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('original_post', 'sharer', 'shared_to')
        ordering = ['-created_at']
```

### API Endpoints
- `POST /posts/{id}/share/` - Share post to user's profile
  - Request body: `{ "shared_to_user_id": int, "message": optional }`
- `GET /posts/shared/` - List posts shared to current user
- `POST /posts/{id}/share/{share_id}/view/` - Mark share as viewed

### Permissions
- User must be authenticated
- Sharer must be able to view the original post
- Cannot share to self
- Cannot share same post to same user twice

### Services
- `posts/services/share_service.py`
  - `share_post(user, post, shared_to_user, message=None)`
  - `get_shared_posts(user)`
  - `mark_share_as_viewed(share_id)`
  - `get_post_shares(post)`

### Notifications
- Create notification when post is shared to user
- Notification type: `post_shared`
- Include sharer info and message

### Frontend Considerations
- Share option in post menu
- User search modal for selecting recipient
- Optional message input
- Shared posts section in notifications/feed
- Mark shares as read/viewed
- Show who shared the post

---

## Feature 5: Enhanced Delete Post

### Current State
- `CanDeletePost` allows: author OR group admin

### Required Changes
**Update `CanDeletePost` permission to include:**
- Post author
- Group admin (existing)
- Group moderator (new)
- Global admin (PRESIDENT, DELEGATE)

### Database Changes
**No schema changes needed** - MembershipRole already has MODERATOR

### Updated Permission Logic
```python
class CanDeletePost(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Author can delete their own post
        if obj.author == request.user:
            return True
        
        # Global admins can delete any post
        if request.user.global_role in [GlobalRole.PRESIDENT, GlobalRole.DELEGATE]:
            return True
        
        # Group admin/moderator can delete posts in their group
        if obj.group:
            from groups.models import Membership, MembershipRole, MembershipStatus
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=obj.group,
                    role__in=[MembershipRole.ADMIN, MembershipRole.MODERATOR],
                    status=MembershipStatus.APPROVED
                )
                return True
            except Membership.DoesNotExist:
                return False
        
        return False
```

### API Endpoints
- Existing: `DELETE /posts/{id}/` - No changes needed

### Services
- No new services needed
- Update existing delete logic if needed

### Frontend Considerations
- Show delete option for authorized users
- Confirm delete dialog
- Soft delete option (mark as deleted instead of actual delete)
- Audit log for admin/moderator deletions

---

## Implementation Order

### Phase 1: Foundation (Priority: High)
1. **Enhanced Delete Post** - Update permissions only
2. **Repost Post** - Core reposting functionality

### Phase 2: User Control (Priority: Medium)
3. **Hide Post** - Individual post hiding
4. **See Less From Author** - Author-level filtering

### Phase 3: Social Features (Priority: Medium)
5. **Share to Profile** - Post sharing with notifications

---

## Migration Plan

### Migration Files to Create
1. `posts/migrations/000X_add_repost_model.py`
2. `posts/migrations/000X_add_hidden_post_model.py`
3. `posts/migrations/000X_add_author_preference_model.py`
4. `posts/migrations/000X_add_shared_post_model.py`

### Data Migration Considerations
- No existing data to migrate
- All new models start empty

---

## Testing Strategy

### Unit Tests
- Test each model's constraints and methods
- Test permission classes for all scenarios
- Test service layer functions

### Integration Tests
- Test API endpoints with various user roles
- Test feed filtering with hidden posts and author preferences
- Test notification generation for shared posts

### Edge Cases to Cover
- Reposting own post (should fail)
- Reposting same post twice (should fail)
- Hiding already hidden post (should be idempotent)
- Setting preference for self (should fail)
- Sharing to self (should fail)
- Sharing same post to same user twice (should fail)
- Deleting post by non-author without permissions (should fail)

---

## Performance Considerations

### Database Indexes
- All foreign keys should have `db_index=True`
- Timestamps should have `db_index=True`
- Unique constraints on composite keys

### Query Optimization
- Use `select_related` for foreign keys
- Use `prefetch_related` for reverse relations
- Cache feed queries where possible
- Consider materialized views for complex feed filtering

### Caching Strategy
- Cache user author preferences
- Cache hidden post lists
- Cache repost counts
- Invalidate cache on mutations

---

## Security Considerations

### Authorization
- All endpoints require authentication
- Strict permission checks on all mutations
- Users can only modify their own data (preferences, hidden posts)

### Rate Limiting
- Consider rate limiting on:
  - Repost creation
  - Share creation
  - Preference updates

### Privacy
- Hidden posts should be truly hidden (no leaks in API)
- Author preferences are private to the user
- Shared posts only visible to recipient

---

## Frontend UI Components Needed

### Post Card Additions
- Repost button with count
- Share button in menu
- Hide option in menu
- "See less from author" option in menu
- Delete button (if authorized)

### New Pages/Modals
- Repost modal (group selector, optional comment)
- Share modal (user search, message input)
- Hidden posts page (settings)
- Author preferences page (settings)
- Shared posts page (notifications/feed)

### Feed Indicators
- Show when post is a repost
- Show original author
- Show reposting user
- Visual indicator for filtered content

---

## API Documentation Updates

### Endpoints to Document
- `POST /posts/{id}/repost/`
- `DELETE /posts/{id}/repost/`
- `GET /posts/{id}/reposts/`
- `POST /posts/{id}/hide/`
- `DELETE /posts/{id}/hide/`
- `GET /posts/hidden/`
- `POST /users/{id}/preference/`
- `GET /users/{id}/preference/`
- `GET /users/preferences/`
- `POST /posts/{id}/share/`
- `GET /posts/shared/`
- `POST /posts/{id}/share/{share_id}/view/`

### Permission Matrix
| Feature | Author | Admin | Moderator | Regular User |
|---------|--------|-------|-----------|--------------|
| Delete Post | ✅ | ✅ | ✅ | ❌ |
| Repost | ✅ | ✅ | ✅ | ✅ |
| Hide | N/A | N/A | N/A | ✅ |
| See Less | N/A | N/A | N/A | ✅ |
| Share | ✅ | ✅ | ✅ | ✅ |

---

## Dependencies

### Required Packages
- No new packages needed (uses existing Django REST Framework)

### External Services
- None required

---

## Rollout Plan

### Feature Flags
Consider adding feature flags for gradual rollout:
- `ENABLE_REPOSTS`
- `ENABLE_HIDE_POST`
- `ENABLE_AUTHOR_PREFERENCES`
- `ENABLE_POST_SHARING`

### Phased Rollout
1. Deploy database migrations
2. Deploy backend code with feature flags off
3. Enable feature flags for test users
4. Monitor for issues
5. Gradual rollout to all users

---

## Success Metrics

### Engagement Metrics
- Repost rate per active user
- Share rate per active user
- Hide post usage
- Author preference usage

### Quality Metrics
- Reduced spam complaints (from hide/see less)
- User satisfaction with feed relevance
- Report rate trends

---

## Open Questions

1. Should reposts appear in the original author's notifications?
2. Should there be a limit on how many times a post can be reposted?
3. Should "see less" be time-based (e.g., 30 days) or permanent?
4. Should shared posts expire after a certain time?
5. Should there be bulk operations (e.g., hide all posts from author)?

---

## Future Enhancements

### Potential Future Features
- Scheduled reposts
- Repost with comments as new post
- Share to multiple users at once
- Share to group (not just individual profile)
- Advanced feed filtering (keywords, topics)
- Undo repost within time window
- Share analytics (who viewed, etc.)

---

## Conclusion

This plan provides a comprehensive roadmap for implementing the requested post features. The implementation is divided into logical phases, with clear database models, API endpoints, permissions, and services defined for each feature. The plan also considers performance, security, testing, and user experience aspects.
