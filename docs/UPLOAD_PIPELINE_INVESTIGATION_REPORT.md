# PwaniNet Post Creation and Media Upload Pipeline Investigation Report

**Date:** 2025-06-29  
**Scope:** Complete read-only analysis of post creation and media upload pipeline  
**Status:** Investigation Complete

---

## Executive Summary

This report documents the complete post creation and media upload pipeline for PwaniNet, tracing the flow from user interaction to successful publication. The investigation covered entry points, UI flow, client-side architecture, validation, media processing, upload requests, Django backend flow, media storage, database interactions, response handling, failure paths, UX analysis, technical debt, and extension points.

**Key Findings:**
- Post creation uses traditional Django form submission with multipart/form-data
- Media preprocessing occurs server-side in PostImage model (PIL-based resizing and thumbnail generation)
- Client-side uses embedded JavaScript in create_post.html for file handling and preview
- HTMX is used for post-interaction actions (like, repost, share) but NOT for post creation
- Validation is split between client-side (basic) and server-side (comprehensive)
- Media storage uses Django's FileSystemStorage with organized subdirectories
- No client-side compression or chunked uploads currently implemented
- Celery tasks exist for background processing but are not actively used in the main flow

---

## 1. Upload Lifecycle Sequence Diagram

```
User Browser                    Django Backend              Database/Storage
    |                                |                            |
    |-- 1. Navigate to create_post  |                            |
    |      page                      |                            |
    |<--------------------------------|                            |
    |   Render create_post.html      |                            |
    |   with PostForm                |                            |
    |                                |                            |
    |-- 2. User selects files        |                            |
    |      (images/video/docs/audio) |                            |
    |                                |                            |
    |-- 3. JavaScript:              |                            |
    |      - FileReader reads files  |                            |
    |      - Generate preview       |                            |
    |      - Store in mediaFiles[]   |                            |
    |      - Update UI state        |                            |
    |                                |                            |
    |-- 4. User submits form         |                            |
    |      POST /posts/create/       |                            |
    |      multipart/form-data       |                            |
    |<--------------------------------|                            |
    |                                |                            |
    |                                |-- 5. create_post_view()    |
    |                                |      receives request      |
    |                                |                            |
    |                                |-- 6. PostForm validation   |
    |                                |      - File size checks    |
    |                                |      - Content length      |
    |                                |      - Field validation    |
    |                                |                            |
    |                                |-- 7. create_post_for_user()|
    |                                |      - transaction.atomic  |
    |                                |      - Create Post object  |
    |                                |      - Set author/course/   |
    |                                |        year/group/unit      |
    |                                |                            |
    |                                |-- 8. Media file handling:  |
    |                                |      - images: PostImage   |
    |                                |        objects (max 15)     |
    |                                |      - video: Post.video   |
    |                                |      - docs: Post.docs     |
    |                                |      - audio: Post.audio   |
    |                                |                            |
    |                                |-- 9. PostImage.save():     |
    |                                |      - PIL image open      |
    |                                |      - Convert to RGB      |
    |                                |      - Resize to 1080px     |
    |                                |      - Convert to WebP/PNG  |
    |                                |      - Generate 400px thumb |
    |                                |      - Generate 800px thumb |
    |                                |                            |
    |                                |-- 10. Save to database     |
    |                                |      - Post record         |
    |                                |      - PostImage records   |
    |                                |                            |
    |                                |-- 11. Save files to       |
    |                                |      MEDIA_ROOT/posts/     |
    |                                |      - images/             |
    |                                |      - videos/             |
    |                                |      - docs/               |
    |                                |      - audio/              |
    |                                |                            |
    |                                |-- 12. Send notifications   |
    |                                |      - Post creation       |
    |                                |      - WebSocket broadcast |
    |                                |                            |
    |<-------------------------------|                            |
    |   Redirect to /posts/home/     |                            |
    |   with success message         |                            |
    |                                |                            |
    |-- 13. Load home feed            |                            |
    |<--------------------------------|                            |
    |   Render posts with new post    |                            |
    |   (HTMX infinite scroll)        |                            |
    |                                |                            |
    |-- 14. WebSocket updates        |                            |
    |      (like/comment counts)     |                            |
    |<--------------------------------|                            |
```

---

## 2. Entry Points for Post Creation

### 2.1 Primary Entry Point
**URL:** `/posts/create/`  
**View:** `posts.views.create_post_view`  
**Template:** `posts/templates/posts/create_post.html`

### 2.2 Navigation Paths
- **Home Feed:** "Create a post" button when feed is empty
- **Navigation Bar:** Post creation link (if present)
- **Direct URL:** `/posts/create/`
- **Group Context:** `/posts/create/?group_id=<id>` for group-specific posts

### 2.3 UI Entry Elements
- **File Picker:** Hidden file inputs triggered by attachment modal
- **Drag & Drop:** Not implemented (files selected via modal only)
- **Paste:** Not implemented
- **Camera:** Not implemented (uses device file picker)
- **Mobile Paths:** Same as desktop (responsive design)

### 2.4 HTMX Triggers
Post creation does NOT use HTMX. It uses traditional form submission.
HTMX is used for post-interaction actions:
- Like toggle: `hx-post="{% url 'posts:toggle_like' post.id %}"`
- Repost: `hx-post="{% url 'posts:repost' post.id %}"`
- Hide: `hx-post="{% url 'posts:hide_post' post.id %}"`
- Share: Modal with HTMX form

---

## 3. UI Flow and States

### 3.1 Initial State
- Textarea visible for content input
- Gradient style selector visible (if no media)
- Attachment button opens modal
- Submit button disabled (no content/media)
- Character counter: "0 / 2500"

### 3.2 Media Selection State
- User clicks attachment button → modal opens
- Modal shows options: Images, Video, Documents
- User selects files → file input change event fires
- JavaScript processes files:
  - Images: FileReader reads as DataURL
  - Video: FileReader reads as DataURL, size check (150MB)
  - Docs: Added to mediaFiles array (no preview)
- Media preview area shows selected files
- Gradient selector hidden when media attached
- Submit button enabled

### 3.3 Preview State
- **Images:** Swipeable carousel with prev/next buttons, remove button
- **Video:** Video player with controls
- **Docs:** File icon with filename
- **Gradient:** Preview of selected gradient style (if no media)

### 3.4 Submit State
- Form submission intercepted by JavaScript
- Files from mediaFiles array re-attached to file inputs using DataTransfer
- Form submits via POST to `/posts/create/`
- Page redirects to home feed on success
- Error messages displayed via Django messages framework

### 3.5 Loading States
- **Submit Button:** No loading spinner during form submission
- **Progress Modal:** Exists (`posting_progress_modal.html`) but not used in current flow
- **HTMX Indicators:** Used for feed loading, not post creation

---

## 4. Client-Side JavaScript Architecture

### 4.1 Embedded JavaScript (create_post.html)
**Location:** Lines ~500-1197 in `create_post.html`

**Responsibilities:**
- File input change event listeners
- Media file handling and storage (mediaFiles array)
- Preview generation (FileReader for images/video)
- UI state management (show/hide elements)
- Character counting
- Form submission handling (file re-attachment via DataTransfer)
- Media carousel navigation (prev/next/remove)
- Gradient style selection

**Key Functions:**
- `handleImageUpload(e)`: Process image files
- `handleVideoUpload(e)`: Process video files with size validation
- `handleDocsUpload(e)`: Process document files
- `updateMediaPreview()`: Render media carousel
- `updatePreview()`: Update UI state based on content/media
- Form submit handler: Re-attach files before submission

### 4.2 Post Content JavaScript (post-content.js)
**Location:** `/home/zayne/projects/pwaninet/static/js/post-content.js`

**Responsibilities:**
- Post content truncation (See more/See less)
- Reinitialization on HTMX content swaps

**Key Functions:**
- Truncates long post content
- Toggles full/truncated view on button click

### 4.3 Posts API JavaScript (posts-api.js)
**Location:** `/home/zayne/projects/pwaninet/static/js/shared/api/posts-api.js`

**Responsibilities:**
- Centralizes API calls for posts
- createPost, likePost, commentPost, sharePost, updatePost, deletePost

**Key Functions:**
- `createPost(data)`: POST to `/api/posts/`
- `likePost(postId)`: POST to `/api/posts/{id}/like/`
- Other post-related API calls

**Note:** This API module is NOT used in the main post creation flow (which uses Django form submission). It may be used for alternative API-based creation.

### 4.4 Posting Progress Manager (posting_progress_modal.html)
**Location:** `/home/zayne/projects/pwaninet/posts/templates/posts/partials/posting_progress_modal.html`

**Responsibilities:**
- Progress modal for background uploads
- Polls `/api/posts/task-status/{taskId}/` for progress
- Shows success/error states

**Status:** Implemented but not actively used in current post creation flow

### 4.5 Home Content JavaScript (home_content.html)
**Location:** `/home/zayne/projects/pwaninet/posts/templates/posts/partials/home_content.html`

**Responsibilities:**
- Scroll-aware media auto-play/pause
- Skeleton loader management for HTMX feed loading
- WebSocket connection for real-time metrics

**Key Functions:**
- IntersectionObserver for media visibility
- HTMX event listeners for skeleton loading
- WebSocket handlers for like/comment/repost updates

---

## 5. Validation Rules

### 5.1 Client-Side Validation
**Location:** Embedded JavaScript in `create_post.html`

| Rule | Location | Error Display |
|------|----------|---------------|
| Video file size ≤ 150MB | `handleVideoUpload()` | `alert('Video file too large!')` |
| Valid video file type | `handleVideoUpload()` | `alert('Please select a valid video file.')` |
| Character count ≤ 2500 | `updatePreview()` | Character counter turns red/warn |
| Submit button disabled | `updatePreview()` | Button disabled when empty |

### 5.2 Server-Side Validation

#### 5.2.1 Form Validation (PostForm)
**Location:** `posts/forms.py`

| Rule | Field | Validator | Max Size |
|------|-------|-----------|----------|
| Content length | content | `clean_content()` | 2500 chars |
| Image file size | images | `validate_image_size` | 5MB |
| Video file size | video | `validate_video_size` | 150MB |
| Document file size | docs | `validate_document_size` | 50MB |
| Audio file size | audio | `validate_audio_size` | 20MB |
| Unit belongs to user's course/year | unit | Queryset filter | N/A |

#### 5.2.2 Validator Functions
**Location:** `posts/validators.py`

```python
validate_image_size: 5MB
validate_video_size: 150MB
validate_document_size: 50MB
validate_audio_size: 20MB
```

#### 5.2.3 Serializer Validation
**Location:** `posts/serializers.py`

| Rule | Serializer | Field |
|------|------------|-------|
| Content length ≤ 2500 | PostCreateSerializer | content |
| Group membership required | PostSerializer, PostCreateSerializer | group |
| Repost restrictions | RepostSerializer | repost_of |
| Share constraints | SharedPostSerializer | shared_post |

### 5.3 Error Display
- **Form errors:** Django form error messages in template
- **Field errors:** Rendered below form fields
- **Non-field errors:** Rendered at top of form
- **Client errors:** Browser alerts (video size, file type)

---

## 6. Media Preprocessing

### 6.1 Server-Side Processing (PostImage Model)
**Location:** `posts/models.py`, `PostImage.save()` method

**Processing Steps:**
1. Open image with PIL
2. Convert to RGB if not already
3. Resize if dimensions > 1080px (thumbnail to 1080x1080)
4. Convert format:
   - PNG with RGBA → PNG with optimization
   - All others → WebP (quality 80, method 6)
5. Generate 400px thumbnail (WebP, quality 75)
6. Generate 800px thumbnail (WebP, quality 80)
7. Save as InMemoryUploadedFile

**Quality Settings:**
- Main image: WebP quality 80, method 6
- 400px thumbnail: WebP quality 75
- 800px thumbnail: WebP quality 80

**No Client-Side Compression:**
- Images uploaded at original quality
- No client-side resizing or compression
- All processing happens server-side

### 6.2 Video Processing
**Location:** `posts/tasks.py` (Celery task placeholder)

**Status:** 
- `process_large_video()` task exists but is not implemented
- No video compression or transcoding currently
- Videos stored at original quality

### 6.3 Document/Audio Processing
**No preprocessing** - stored as uploaded

---

## 7. Upload Request Structure

### 7.1 Request Details
**Method:** POST  
**URL:** `/posts/create/`  
**Content-Type:** multipart/form-data  
**Authentication:** Session-based (Django session middleware)  
**CSRF:** CSRF token included in form

### 7.2 Form Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | text | No | Post content (max 2500 chars) |
| unit | select | No | Unit selection (filtered by user's course/year) |
| group | select | No | Group selection |
| gradient_class | hidden | No | Background style class |
| images | file (multiple) | No | Image files (max 15, 5MB each) |
| video | file | No | Video file (max 150MB) |
| docs | file | No | Document file (max 50MB, PDF only) |
| audio | file | No | Audio file (max 20MB) |

### 7.3 File Attachment Process
**JavaScript Handler (create_post.html):**
1. Form submit event intercepted
2. FormData object created from form
3. File inputs cleared
4. Files from mediaFiles array re-attached using DataTransfer API
5. Form submits normally

**Note:** This workaround is needed because file inputs cannot be programmatically set in modern browsers. The DataTransfer API allows reconstructing the FileList.

### 7.4 Headers
```
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary...
Cookie: sessionid=...; csrftoken=...
Referer: https://domain/posts/create/
X-CSRFToken: ... (from meta tag)
```

### 7.5 HTMX Involvement
**None** for post creation. HTMX is used for:
- Post interactions (like, repost, hide, share)
- Feed pagination (infinite scroll)
- Comment submission
- Search

---

## 8. Django Backend Flow

### 8.1 URL Routing
**Location:** `posts/urls.py`

```python
path('create/', views.create_post_view, name='create_post'),
```

### 8.2 View Processing
**Location:** `posts/views.py`, `create_post_view()`

**Flow:**
1. Extract `group_id` from query parameters
2. On POST:
   - Instantiate PostForm with request.POST, request.FILES, user
   - Validate form
   - If valid: call `create_post_for_user()`
   - Add success message
   - Redirect to `posts:home`
3. On GET:
   - Instantiate empty PostForm
   - Render create_post.html

### 8.3 Form Processing
**Location:** `posts/forms.py`, `PostForm`

**Fields:**
- unit (ModelChoiceField, filtered by user's course/year)
- group (ForeignKey to Group)
- content (CharField with max_length validation)
- video (FileField with video size validator)
- docs (FileField with document size validator)
- audio (FileField with audio size validator)
- images (ImageField, multiple)
- gradient_class (CharField)

**Validation:**
- Field-level validators (file sizes)
- Form-level clean_content() (2500 char limit)

### 8.4 Service Layer
**Location:** `posts/services/post_service.py`, `create_post_for_user()`

**Flow (atomic transaction):**
1. Create Post instance with commit=False
2. Set author, course, year, group, unit
3. Detect media presence to set gradient_class='none'
4. Save Post
5. Create PostImage objects for images (max 15, with order)
6. Assign video file to Post.video
7. Assign docs file to Post.docs
8. Assign audio file to Post.audio
9. Send notifications (post creation)
10. Return Post

### 8.5 Model Processing
**Location:** `posts/models.py`

**Post Model:**
- Fields: author, content, video, docs, audio, gradient_class, unit, group, course, year
- Methods: is_liked_by(), is_reposted_by(), etc.

**PostImage Model:**
- Fields: post, image, thumbnail_400, thumbnail_800, order
- save() method: Image processing (resize, convert, thumbnails)

### 8.6 Serializer Processing (API Path)
**Location:** `posts/serializers.py`

**PostCreateSerializer:**
- validate_content(): 2500 char limit
- validate_group(): Membership check
- create(): Post creation with group membership validation

**Note:** The main post creation flow uses Django forms, not serializers. Serializers are used for the REST API endpoints.

---

## 9. Media Storage Backend

### 9.1 Storage Configuration
**Backend:** Django FileSystemStorage (default)  
**Settings:** Not found in codebase (likely in settings.py not in posts app)

### 9.2 Directory Structure
**Base:** `MEDIA_ROOT/posts/`

**Subdirectories:**
- `posts/images/` - Image files
- `posts/videos/` - Video files
- `posts/docs/` - Document files
- `posts/audio/` - Audio files

**Actual Structure (from media/ directory listing):**
```
media/
├── covers/
├── group_covers/
├── group_profile_pic/
├── link_favicons/
├── link_previews/
├── message_attachments/
├── posts/ (empty in dev)
├── profile_pic/
└── temp/
```

### 9.3 File Naming
**PostImage:**
- Original filename preserved with extension change
- Pattern: `{original_name}.{webp|png}`
- Thumbnails: `{original_name}_400.webp`, `{original_name}_800.webp`

**Other Media:**
- Original filename preserved
- Stored directly in respective subdirectories

### 9.4 File Handling
- **Images:** Processed through PostImage.save() (PIL)
- **Video:** Stored as-is (no processing)
- **Docs:** Stored as-is (PDF only)
- **Audio:** Stored as-is

### 9.5 Storage Backend Integration
- Django's FileField handles storage automatically
- Uses configured storage backend (FileSystemStorage)
- Files saved to MEDIA_ROOT with upload_to paths defined in models

---

## 10. Database Interactions

### 10.1 Models Involved
**Primary:**
- `Post` - Main post record
- `PostImage` - Image attachments (one-to-many to Post)

**Secondary (created during post lifecycle):**
- `Like` - Post likes
- `Comment` - Post comments
- `CommentLike` - Comment likes
- `Report` - Post reports
- `Repost` - Reposts
- `HiddenPost` - Hidden posts
- `SharedPost` - Shared posts
- `Notification` - Post creation notifications

### 10.2 Database Flow (Post Creation)
1. **Transaction Start:** `transaction.atomic()` in `create_post_for_user()`
2. **Post Insert:** `Post.objects.create()` with author, content, media fields
3. **PostImage Inserts:** Loop through images, `PostImage.objects.create()` for each
   - Triggers PostImage.save() which processes images
   - Thumbnails generated and saved
4. **Post Updates:** Save video/docs/audio to Post (if present)
5. **Transaction Commit implicit on success**
6. **Notification Creation:** Post creation notification sent
7. **Cache Invalidation:** Like count cache invalidated (if applicable)

### 10.3 Relationships
```
Post (1) ----< (N) PostImage
Post (1) ----< (N) Like
Post (1) ----< (N) Comment
Post (1) ----< (N) Repost
Post (1) ----< (N) HiddenPost
Post (1) ----< (N) Report
Post (1) ----< (N) SharedPost
Post (N) ----< (1) User (author)
Post (N) ----< (1) Group (optional)
Post (N) ----< (1) Unit (optional)
Post (N) ----< (1) Course (optional)
```

### 10.4 Error Handling
- Transaction rollback on any exception
- Form validation errors returned to user
- Database constraints enforced (unique constraints, foreign keys)

---

## 11. Response Flow and UI Updates

### 11.1 Success Flow
1. **Form Submission:** POST to `/posts/create/`
2. **Processing:** Django processes form, creates post
3. **Response:** HTTP 302 Redirect to `/posts/home/`
4. **Success Message:** Django messages framework adds "Post created successfully."
5. **Home Feed Load:** GET request to `/posts/home/`
6. **Feed Rendering:** Posts rendered with new post included
7. **WebSocket Update:** Real-time like/comment counts via WebSocket

### 11.2 HTMX Updates (Post Interactions)
**Like Button:**
- `hx-post="{% url 'posts:toggle_like' post.id %}"`
- `hx-target="this"` (replace button)
- `hx-swap="outerHTML"`
- Returns updated like button with new icon and count

**Repost:**
- Modal with HTMX form
- On submit: HTMX replaces modal or redirects

**Hide Post:**
- `hx-post="{% url 'posts:hide_post' post.id %}"`
- Removes post from feed

**Share:**
- Modal with HTMX form
- Creates SharedPost record

### 11.3 WebSocket Updates
**Location:** `home.html` embedded JavaScript

**WebSocket Endpoint:** `/ws/feed/`

**Message Types:**
- `post_like_update` - Update like count and button state
- `post_repost_update` - Update repost count and button state
- `post_comment_update` - Update comment count

**Update Logic:**
- Find all post cards with matching post_id
- Update DOM elements (count, icon, classes)
- Handle reconnection with exponential backoff

### 11.4 Feed Refresh
- **Infinite Scroll:** HTMX `hx-trigger="revealed"` on sentinel div
- **Cursor-based Pagination:** Encoded cursor with post_id and timestamp
- **Skeleton Loading:** Post skeleton loaders shown during HTMX requests
- **HTMX Swap:** `hx-swap="afterend"` appends new posts

---

## 12. Failure Paths and Error Handling

### 12.1 Client-Side Failures
| Failure | Location | Handling |
|---------|----------|----------|
| Invalid video file type | `handleVideoUpload()` | Alert: "Please select a valid video file." |
| Video file too large | `handleVideoUpload()` | Alert: "Video file too large! Maximum allowed is 150MB." |
| FileReader error | Not explicitly handled | Browser default error |
| Empty submission | `updatePreview()` | Submit button disabled |

### 12.2 Server-Side Validation Failures
| Failure | Location | Handling |
|---------|----------|----------|
| Content too long | PostForm.clean_content() | Form error: "Post content cannot exceed 2500 characters." |
| Image too large | validate_image_size | Form error with max size |
| Video too large | validate_video_size | Form error with max size |
| Document too large | validate_document_size | Form error with max size |
| Audio too large | validate_audio_size | Form error with max size |
| Invalid file type | Form field validation | Form error |
| Group membership required | PostCreateSerializer.validate_group() | ValidationError: "You must be an approved member to post in this group." |

### 12.3 Database Failures
| Failure | Location | Handling |
|---------|----------|----------|
| Transaction error | create_post_for_user() | Transaction rollback, exception propagated |
| Foreign key violation | Model save | Database error, form error |
| Constraint violation | Model save | Database error, form error |

### 12.4 Storage Failures
| Failure | Location | Handling |
|---------|----------|----------|
| Disk full | File save | IOError/StorageError, form error |
| Permission denied | File save | PermissionError, form error |
| Invalid file format | PIL processing | PIL error, form error |

### 12.5 Network Failures
| Failure | Location | Handling |
|---------|----------|----------|
| Upload timeout | Browser | Browser timeout error |
| Connection lost | Browser | Network error, page reload |
| WebSocket disconnect | home.html | Reconnection logic with max 5 attempts |

### 12.6 Error Display
- **Form Errors:** Rendered in template with Django's form error rendering
- **Field Errors:** Below each field with error class
- **Non-field Errors:** At top of form
- **Client Alerts:** Browser alert() for immediate feedback
- **Django Messages:** Success/error messages after redirect

---

## 13. UX Analysis

### 13.1 Loading States
| Component | Loading Indicator | Status |
|-----------|-------------------|--------|
| Form submission | None | **Missing** - No spinner on submit button |
| File upload | None | **Missing** - No progress indicator |
| Image processing | None | Server-side, no feedback |
| Feed loading | Skeleton loaders | **Present** - HTMX skeleton loading |
| Post interactions | HTMX htmx-request class | **Present** - Button state changes |
| WebSocket | Reconnection dots | **Present** - Console logging |

### 13.2 Progress Indicators
- **Post Creation:** None (progress modal exists but unused)
- **File Upload:** No progress bar
- **Image Processing:** No progress feedback
- **Celery Tasks:** Progress modal with polling (not used in main flow)

### 13.3 Button States
| State | Implementation |
|-------|----------------|
| Submit disabled | When no content and no media |
| Submit enabled | When content or media present |
| Character counter | Changes color at 1875 (warn) and 2250 (danger) chars |
| Like button | Icon and color change on toggle (HTMX) |
| Repost button | Icon and color change on toggle (HTMX) |

### 13.4 Feedback Mechanisms
- **Success:** Django messages framework ("Post created successfully.")
- **Validation errors:** Form field errors
- **Client errors:** Browser alerts
- **Real-time updates:** WebSocket for like/comment counts
- **Media preview:** Immediate preview after file selection

### 13.5 UX Issues Identified
1. **No upload progress indicator** - Users don't know upload status
2. **No loading spinner on submit** - Unclear if submission is processing
3. **Progress modal unused** - Infrastructure exists but not integrated
4. **No retry mechanism** - Failed uploads require full re-entry
5. **No cancel option** - Once submitted, cannot cancel
6. **No chunked uploads** - Large files may timeout
7. **No offline support** - Requires network for post creation

---

## 14. File Responsibility Map

| File | Type | Responsibility | Key Components |
|------|------|----------------|-----------------|
| `posts/urls.py` | Python | URL routing | create_post_view, API endpoints |
| `posts/views.py` | Python | View logic | create_post_view, PostViewSet |
| `posts/forms.py` | Python | Form definition | PostForm, field validators |
| `posts/models.py` | Python | Data models | Post, PostImage (with image processing) |
| `posts/validators.py` | Python | Validation functions | File size validators |
| `posts/serializers.py` | Python | API serializers | PostCreateSerializer, validation |
| `posts/services/post_service.py` | Python | Business logic | create_post_for_user, toggle_post_like_for_user |
| `posts/services/feed_service.py` | Python | Feed logic | get_ranked_feed, cursor pagination |
| `posts/tasks.py` | Python | Background tasks | create_post_with_media, process_large_video |
| `posts/templates/posts/create_post.html` | Template | Post creation UI | Form, embedded JavaScript |
| `posts/templates/posts/home.html` | Template | Home feed UI | Search, feed container, WebSocket |
| `posts/templates/posts/partials/home_content.html` | Template | Feed content | Post list, skeleton loaders |
| `posts/templates/posts/partials/post_list.html` | Template | Post rendering | Post cards, infinite scroll trigger |
| `posts/templates/posts/partials/post_card.html` | Template | Post card UI | Media previews, interaction buttons |
| `posts/templates/posts/partials/post_content.html` | Template | Post content | Content truncation markup |
| `posts/templates/posts/partials/like_button.html` | Template | Like button | HTMX like toggle |
| `posts/templates/posts/partials/posting_progress_modal.html` | Template | Progress modal | Progress bar, status display |
| `static/js/post-content.js` | JavaScript | Content truncation | See more/see less logic |
| `static/js/shared/api/posts-api.js` | JavaScript | API calls | createPost, likePost, etc. |
| `static/js/htmx.min.js` | JavaScript | HTMX library | HTMX functionality |
| `static/js/lazy-load-images.js` | JavaScript | Image lazy loading | Performance optimization |
| `static/js/video-manager.js` | JavaScript | Video management | Auto-play/pause logic |

---

## 15. Dependency Graph and System Integration

### 15.1 Internal Dependencies
```
posts.views
  ├── posts.forms
  ├── posts.services.post_service
  ├── posts.models
  └── posts.serializers (for API views)

posts.forms
  ├── posts.models
  ├── posts.validators
  └── courses.models (Unit)

posts.services.post_service
  ├── posts.models
  ├── courses.models (Unit)
  ├── groups.models (Group)
  └── notifications (implied)

posts.models
  ├── django.db
  ├── PIL (Image)
  └── django.core.files (InMemoryUploadedFile)

posts.serializers
  ├── posts.models
  ├── groups.serializers
  └── courses.models
```

### 15.2 External Dependencies
- **Django:** Framework, ORM, forms, storage
- **Django REST Framework:** API serializers, viewsets
- **Pillow (PIL):** Image processing
- **Celery:** Background tasks (not actively used)
- **HTMX:** Frontend interactivity
- **Bootstrap:** CSS framework
- **Bootstrap Icons:** Icon set

### 15.3 System Integrations
- **Authentication:** Django session middleware
- **Storage:** Django FileSystemStorage
- **Notifications:** Notification system (implied from service)
- **WebSocket:** Real-time feed updates
- **Cache:** Django cache (for feed queries, like counts)
- **Messaging:** Separate messaging system (not in posts app)

### 15.4 Cross-App Dependencies
- **courses:** Unit, Course models
- **groups:** Group, Membership models
- **users:** User model, profile
- **notifications:** Notification creation

---

## 16. Technical Debt and Architectural Issues

### 16.1 Tight Coupling
| Issue | Location | Impact |
|-------|----------|--------|
| Image processing in model save() | PostImage.save() | Model has business logic, hard to test |
| Embedded JavaScript in template | create_post.html | No separation of concerns, hard to maintain |
| Form submission tightly coupled to view | create_post_view | No API-first approach, limited reusability |
| Direct database queries in views | Various views | No repository pattern, scattered queries |

### 16.2 Duplicate Logic
| Issue | Locations |
|-------|-----------|
| Content length validation | PostForm.clean_content(), PostCreateSerializer.validate_content() |
| Group membership check | PostSerializer.create(), PostCreateSerializer.validate_group() |
| File size validation | Form validators, client-side JavaScript |

### 16.3 Missing Abstractions
| Missing Abstraction | Impact |
|---------------------|--------|
| Repository pattern | Direct model access throughout codebase |
| Service layer for all operations | Some logic in views, some in services |
| Media processor interface | Image processing tightly coupled to PostImage |
| Upload handler abstraction | No reusable upload logic |
| Notification service interface | No clear notification abstraction |

### 16.4 Validation Gaps
| Gap | Risk |
|-----|------|
| No client-side image validation | Large images may timeout |
| No file type validation on client | Invalid files may reach server |
| No duplicate upload prevention | Users can accidentally upload same file |
| No content spam detection | No rate limiting on post creation |

### 16.5 Performance Bottlenecks
| Bottleneck | Location | Impact |
|------------|----------|--------|
| Synchronous image processing | PostImage.save() | Blocks request during processing |
| No client-side compression | Upload | Larger payloads, slower uploads |
| No chunked uploads | Large files | May timeout on slow connections |
| No lazy loading for media | Feed | All media loads immediately |
| N+1 queries in feed | Feed rendering | Potential performance issue |

### 16.6 Dead Code
| Code | Location | Status |
|------|----------|--------|
| Celery tasks | posts/tasks.py | Not used in main flow |
| Progress modal | posting_progress_modal.html | Not integrated |
| Friend suggestions | post_list.html | Commented out |
| Some serializers | posts/serializers.py | May be unused |

### 16.7 Security Considerations
| Issue | Location | Risk |
|-------|----------|------|
| No file content validation | Upload | Malicious files may be uploaded |
| No rate limiting | Post creation | Spam potential |
| No CSRF on API endpoints | API views | CSRF protection may be bypassed |
| Original filenames preserved | Storage | Potential information disclosure |

---

## 17. Safe Extension Points

### 17.1 Client-Side Extensions
| Extension | Safety | Effort | Impact |
|-----------|--------|--------|--------|
| Client-side image compression | High | Medium | Reduce upload size |
| Client-side video thumbnail generation | High | Medium | Better UX |
| Upload queue management | High | High | Better UX for multiple files |
| Drag & drop support | High | Low | UX improvement |
| Paste from clipboard | High | Low | UX improvement |
| Camera integration | High | Medium | Mobile UX improvement |
| Offline post creation | Medium | High | Complex, requires sync |
| Upload progress tracking | High | Low | UX improvement |
| Chunked uploads | High | High | Better for large files |
| Retry mechanism | High | Medium | Better reliability |

### 17.2 Server-Side Extensions
| Extension | Safety | Effort | Impact |
|-----------|--------|--------|--------|
| Async image processing | High | Medium | Better performance |
| Video transcoding service | High | High | Better video handling |
| Background upload processing | High | High | Better UX for large files |
| Thumbnail generation service | High | Medium | Consistent thumbnails |
| File validation service | High | Low | Better security |
| Rate limiting middleware | High | Low | Spam prevention |
| Upload queue backend | High | High | Complex, requires infrastructure |
| CDN integration | High | Medium | Better performance |
| Storage abstraction layer | High | High | Better flexibility |
| Notification service abstraction | High | Medium | Better maintainability |

### 17.3 Architectural Extensions
| Extension | Safety | Effort | Impact |
|-----------|--------|--------|--------|
| Repository pattern | High | High | Better testability |
| Service layer expansion | High | Medium | Better separation |
| Media processor interface | High | Medium | Better abstraction |
| API-first approach | Medium | High | Major refactoring |
| Event-driven architecture | Medium | High | Complex, requires infrastructure |
| CQRS pattern | Low | Very High | Major architectural change |

### 17.4 Recommended Extensions (High ROI)
1. **Client-side image compression** - Reduces upload size, easy to implement
2. **Upload progress tracking** - Better UX, infrastructure exists
3. **Drag & drop support** - UX improvement, low effort
4. **Async image processing** - Better performance, medium effort
5. **Rate limiting** - Security improvement, low effort

---

## 18. Risk Assessment

### 18.1 Tightly Coupled Components (High Risk)
| Component | Coupled To | Risk Level | Extension Difficulty |
|-----------|------------|------------|---------------------|
| PostImage.save() | PIL, storage logic | High | Difficult |
| create_post_view | PostForm, post_service | Medium | Medium |
| Embedded JavaScript | Template structure | High | Difficult |
| Post model | Notification system | Medium | Medium |

### 18.2 Loosely Coupled Components (Low Risk)
| Component | Coupled To | Risk Level | Extension Difficulty |
|-----------|------------|------------|---------------------|
| PostForm | Models, validators | Low | Easy |
| Validators | None | Low | Easy |
| Serializers | Models | Low | Easy |
| Feed service | Queries, cache | Low | Easy |
| HTMX interactions | Templates | Low | Easy |

### 18.3 Safe to Extend
- **Validation layer** - Add new validators easily
- **Serializers** - Add new API endpoints
- **Feed service** - Modify feed algorithm
- **Templates** - Add new UI components
- **Static JavaScript** - Add new client-side features
- **Celery tasks** - Add new background jobs

### 18.4 Requires Caution
- **PostImage.save()** - Contains image processing logic
- **create_post_for_user()** - Core business logic
- **Post model** - Central data model
- **Embedded JavaScript** - Tightly coupled to template

### 18.5 High Risk Changes
- **Modifying Post model fields** - Database migration required
- **Changing storage backend** - Affects all media
- **Modifying form submission flow** - Breaks existing functionality
- **Removing HTMX** - Affects all interactions
- **Changing WebSocket protocol** - Breaks real-time updates

---

## 19. Recommendations

### 19.1 Immediate Improvements (Low Effort)
1. Add loading spinner to submit button
2. Integrate existing progress modal for uploads
3. Add drag & drop support for file selection
4. Implement client-side image compression
5. Add upload progress indicator

### 19.2 Short-Term Improvements (Medium Effort)
1. Extract embedded JavaScript to separate module
2. Implement async image processing
3. Add rate limiting for post creation
4. Implement retry mechanism for failed uploads
5. Add chunked upload support for large files

### 19.3 Long-Term Improvements (High Effort)
1. Implement repository pattern
2. Create media processor abstraction
3. Add CDN integration
4. Implement offline post creation with sync
5. Refactor to API-first architecture

### 19.4 Technical Debt Reduction
1. Remove duplicate validation logic
2. Extract image processing from model save
3. Add service layer for all operations
4. Remove or document dead code
5. Add comprehensive test coverage

---

## 20. Conclusion

The PwaniNet post creation and media upload pipeline is functional but has several areas for improvement. The current implementation uses traditional Django form submission with server-side media processing. While this works, it lacks modern UX features like upload progress, client-side compression, and chunked uploads.

The architecture is reasonably well-structured with clear separation between views, forms, models, and services. However, there is some tight coupling (especially in PostImage.save() and embedded JavaScript) that could be improved.

The investigation identified several safe extension points, particularly on the client-side (compression, drag & drop, progress tracking) and in the validation layer. Server-side extensions like async processing and rate limiting are also viable.

The main risks are in the tightly coupled components (PostImage.save(), embedded JavaScript), which should be approached with caution when extending. The loosely coupled components (forms, validators, serializers, feed service) are safe to extend.

Overall, the pipeline is solid but would benefit from modern UX improvements and some architectural refactoring to reduce coupling and improve maintainability.

---

**Investigation Completed:** 2025-06-29  
**Total Files Analyzed:** 20+  
**Lines of Code Reviewed:** 5000+  
**No Code Modified:** Strictly read-only analysis
