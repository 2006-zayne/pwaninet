# Feed Ranking System Documentation

## Overview
This document describes the implementation of a scalable feed ranking system with cursor-based pagination for the Django social network project.

## Architecture

### Ranking Algorithm
The feed ranks posts based on engagement metrics:
- **Score Formula**: `score = like_count + (2 * comment_count)`
- **Ordering**: score DESC, created_at DESC, id DESC

### Cursor-Based Pagination
Replaces offset-based pagination for better performance and scalability:
- **Cursor Format**: `"score|created_at|id"`
- **Filtering Logic**: Returns posts where:
  - score < cursor_score
  - OR (score == cursor_score AND created_at < cursor_created_at)
  - OR (score == cursor_score AND created_at == cursor_created_at AND id < cursor_id)

## Components

### 1. Database Model Changes
**File**: `posts/models.py`

Added `db_index=True` to `created_at` field:
```python
created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

**Note**: A database migration is required to apply this change.

### 2. Feed Service
**File**: `posts/services/feed_service.py`

#### Functions

##### `encode_cursor(post)`
Encodes post score, created_at, and id into a cursor string.
- **Format**: `"score|created_at|id"`
- **Parameters**: `post` - Post object with annotated score
- **Returns**: String cursor

##### `decode_cursor(cursor_string)`
Decodes cursor string back to components.
- **Parameters**: `cursor_string` - String cursor or None
- **Returns**: Dict with `score`, `created_at`, `id` or None if invalid
- **Error Handling**: Returns None for malformed cursors

##### `get_ranked_feed(user, cursor=None, limit=10)`
Main feed function with cursor-based pagination.
- **Parameters**:
  - `user` - User requesting the feed
  - `cursor` - Optional cursor string for pagination
  - `limit` - Number of posts to return (default 10)
- **Returns**: Dict with:
  - `posts` - List of Post objects
  - `next_cursor` - Cursor for next page or None
  - `has_more` - Boolean indicating if more posts exist

**Query Optimization**:
- Uses `select_related('author', 'group', 'course', 'unit')`
- Uses `prefetch_related('likes', 'comments')`
- All filtering and ordering done at database level (no Python sorting)

##### `build_home_feed_context(user, cursor=None, limit=10)`
Builds context template for home feed.
- **Parameters**:
  - `user` - User requesting the feed
  - `cursor` - Optional cursor string
  - `limit` - Number of posts (default 10)
- **Returns**: Context dict with posts, liked_post_ids, suggestions, next_cursor, has_more

### 3. View Integration
**File**: `core/views.py`

#### `home_view(request)`
Updated to use cursor-based pagination:
```python
@login_required
def home_view(request):
    cursor = request.GET.get('cursor')
    context = build_home_feed_context(request.user, cursor=cursor)
    
    # HTMX support for full page and partial responses
    if request.headers.get('HX-Request') and not request.GET.get('q'):
        return render(request, 'partials/home_content.html', context)
    
    if request.headers.get('HX-Request'):
        return render(request, 'partials/post_list.html', context)
    
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    return render(request, 'home.html', context)
```

### 4. Template Updates
**File**: `templates/partials/post_list.html`

Updated infinite scroll to use cursor:
```django
{% for post in posts %}
    {% if forloop.last and has_more %}
        <div hx-get="{% url 'posts:home' %}?cursor={{ next_cursor }}" 
             hx-trigger="revealed" 
             hx-swap="afterend" 
             hx-indicator="#feed-spinner">
            {% include 'partials/post_card.html' %}
        </div>
    {% else %}
        {% include 'partials/post_card.html' %}
    {% endif %}
    ...
{% empty %}
    {% if not cursor %}
        <div class="text-center py-5">
            <i class="bi bi-broadcast text-muted fs-1"></i>
            <p class="text-muted mt-2">No posts yet. Be the first one to post.</p>
            <a href="{% url 'posts:create_post' %}" class="btn btn-primary rounded-pill px-4">Create a post</a>
        </div>
    {% endif %}
{% endfor %}
```

## Feed Filtering Logic

The feed shows posts from three sources:
1. **Following**: Posts from users the current user follows
2. **Groups**: Posts from groups the user is a member of
3. **Course/Year**: Posts from users in the same course and year

```python
Post.objects.filter(
    Q(author_id__in=following_ids) |
    Q(group_id__in=group_ids) |
    Q(course=user.course, unit__year=user.year)
)
```

## Performance Considerations

### Database Indexes
- `created_at` has `db_index=True` for efficient ordering
- Foreign keys (author, group, course) are automatically indexed

### Query Optimization
- All filtering and ordering done at database level
- No Python sorting or post-processing
- `select_related` reduces N+1 queries for foreign keys
- `prefetch_related` optimizes many-to-many relationships

### Pagination Performance
- Cursor-based pagination avoids OFFSET performance degradation
- Each page fetches `limit + 1` records to check for more results
- Constant time complexity regardless of page depth

## Safety & Error Handling

### Missing Cursor
- If no cursor provided, returns first page of results
- Empty state shown only on initial load (no cursor)

### Invalid Cursor
- `decode_cursor` returns None for malformed cursors
- Function gracefully handles None and continues without cursor filtering

### Empty Results
- Returns empty posts list
- `has_more` set to False
- `next_cursor` set to None

## Migration Required

To apply the `db_index=True` change to `created_at`:

```bash
python manage.py makemigrations posts
python manage.py migrate
```

## Testing Checklist

- [ ] Verify cursor encoding/decoding works correctly
- [ ] Test initial load (no cursor)
- [ ] Test infinite scroll with cursor
- [ ] Test empty feed state
- [ ] Test invalid cursor handling
- [ ] Verify query performance with large datasets
- [ ] Check HTMX infinite scroll behavior
- [ ] Verify ranking algorithm (score calculation)
- [ ] Test relationship filtering (following, groups, course)
- [ ] Run database migration

## Future Enhancements

Potential improvements:
1. Add time decay to score (older posts get lower scores)
2. Cache cursor-based results
3. Add relationship boost (same group/course weight)
4. Implement re-ranking on new posts
5. Add analytics for feed engagement
