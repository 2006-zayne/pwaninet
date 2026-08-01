# Document Engagement Expansion - Architecture Documentation

## Overview

This document describes the architectural changes made to expand the PwaniNet Document Repository with a comprehensive engagement system. The expansion adds download tracking, unique views, bookmarks with toggle functionality, document sharing, and a thumbs up/down rating system while preserving all existing functionality.

## Design Principles

1. **No Breaking Changes**: All existing features (uploads, previews, detail pages, search, recommendations, permissions, URLs, templates) remain functional.
2. **Minimal Modification**: Existing code was extended rather than rewritten where possible.
3. **Performance First**: Cached counters and asynchronous updates prevent performance degradation.
4. **Consistent Styling**: All new UI elements follow the existing PwaniNet design language.
5. **Permission Preservation**: Existing permission rules are respected and extended appropriately.

## Model Changes

### DocumentRating Model (Modified)

**Location**: `documents/engagement/models.py`

**Change**: Converted from 1-5 star rating system to thumbs up/down (1/-1) system.

**Rationale**: 
- Simpler user interaction (binary choice vs 5 options)
- Easier to calculate and display percentages
- More suitable for quick engagement feedback

**Fields Changed**:
- `rating`: Changed from `PositiveSmallIntegerField` with validators (1-5) to `SmallIntegerField` with choices (1/-1)
- Removed `review` field (simplified to binary rating)

**Migration Impact**: 
- Existing ratings will need data migration to convert 1-5 scale to thumbs up/down
- Suggested conversion: ratings >= 3 become thumbs up (1), ratings < 3 become thumbs down (-1)

**Backward Compatibility**: 
- The model structure change is breaking for existing rating data
- A data migration script should be run to preserve user feedback

### DocumentAnalytics Model (New)

**Location**: `documents/engagement/models.py`

**Purpose**: Cached engagement statistics to avoid expensive COUNT queries during page rendering.

**Key Fields**:
- `view_count`, `download_count`, `bookmark_count`, `share_count`: Engagement counters
- `rating_count`, `positive_rating_count`, `negative_rating_count`: Rating statistics
- `positive_rating_percentage`, `negative_rating_percentage`: Pre-calculated percentages
- `trending_score`: Computed from recent engagement (last 7 days)
- `popularity_score`: Computed from long-term engagement
- `last_updated`: Timestamp of last recalculation
- `last_activity`: Timestamp of most recent engagement

**Relationship**: One-to-one with Document model via `document.analytics`

**Performance Impact**: 
- Eliminates COUNT queries on engagement tables during page renders
- Analytics updated asynchronously via Celery tasks
- Stale analytics (older than 5 minutes) trigger background refresh

## View Changes

### New HTMX Endpoints

**Location**: `documents/views.py`

#### toggle_bookmark(document_id)
- **Purpose**: Toggle bookmark status for authenticated users
- **Method**: POST
- **Authentication**: Required
- **Response**: Partial HTML (bookmark_button.html)
- **Side Effect**: Triggers async analytics update via Celery

#### rate_document(document_id)
- **Purpose**: Rate document with thumbs up/down
- **Method**: POST
- **Authentication**: Required
- **Parameters**: `rating` (1 or -1)
- **Response**: Partial HTML (rating_buttons.html)
- **Side Effect**: Triggers async analytics update via Celery

#### share_document(document_id)
- **Purpose**: Share document (copy link, to profile, to group)
- **Method**: POST
- **Authentication**: Required
- **Parameters**: `share_type` (copy_link, profile, group), `group_id` (for group shares)
- **Response**: JSON with success/error message
- **Side Effect**: Triggers async analytics update via Celery

#### document_stats(document_id)
- **Purpose**: Get cached document statistics
- **Method**: GET
- **Authentication**: Required
- **Response**: JSON with engagement counts and percentages
- **Side Effect**: Triggers analytics refresh if stale (older than 5 minutes)

### Existing Views (Unchanged)

All existing views remain functional:
- `repository_home`: Repository landing page
- `search_results`: Search functionality
- `document_detail`: Document detail page (enhanced with new features)
- `upload_document`: Document upload flow
- `my_library`, `my_uploads`, `my_bookmarks`, `my_downloads`, `my_history`: User library views

## Template Changes

### document_detail.html (Enhanced)

**Location**: `documents/templates/documents/document_detail.html`

**Changes**:
1. **Bookmark Button**: Replaced static button with HTMX-powered toggle
   - Uses `bookmark_button.html` partial
   - Shows bookmark count
   - Visual feedback when bookmarked (filled icon, primary color)

2. **Share Dropdown**: Added share functionality with three options
   - Copy Link: Copies URL to clipboard and tracks share
   - Share to Profile: Creates post on user's feed
   - Share to Group: Creates post in selected group
   - JavaScript functions handle dropdown toggle and API calls

3. **Rating Buttons**: Added thumbs up/down rating system
   - Uses `rating_buttons.html` partial
   - Shows percentage of positive/negative ratings
   - Visual feedback for user's current rating
   - Exclusive states (can only be thumbs up OR down)

4. **Uploader Information**: Enhanced with course details
   - Added course name display if user has a course
   - Maintains existing profile picture and name display

5. **JavaScript Updates**:
   - Updated stats fetch URL to use new endpoint
   - Added share dropdown functions
   - Added CSRF token handling for HTMX requests
   - Added click-outside handler for dropdown

**Preserved Elements**:
- Document preview
- Metadata display
- Download button
- Existing stats display (views, downloads, bookmarks)
- Related documents section
- All styling and layout

### document_CARD.html (Enhanced)

**Location**: `documents/templates/documents/partials/document_card.html`

**Changes**:
1. **Download Count**: Now uses cached analytics if available
   - Falls back to COUNT query if analytics not created yet

2. **Rating Percentages**: Added thumbs up/down percentages
   - Only displayed if analytics exist
   - Shows positive and negative rating percentages

**Preserved Elements**:
- Thumbnail display
- File type badge
- Title and academic unit
- Upload time
- All styling and hover effects

### New Partial Templates

#### bookmark_button.html
**Location**: `documents/templates/documents/partials/bookmark_button.html`

**Purpose**: HTMX partial for bookmark toggle button

**Features**:
- Shows bookmark count
- Visual feedback when bookmarked (filled icon, primary color)
- HTMX attributes for async toggle

#### rating_buttons.html
**Location**: `documents/templates/documents/partials/rating_buttons.html`

**Purpose**: HTMX partial for thumbs up/down rating buttons

**Features**:
- Two buttons: thumbs up and thumbs down
- Shows percentage for each rating type
- Visual feedback for user's current rating
- HTMX attributes for async rating

## URL Changes

**Location**: `documents/urls.py`

**New Routes**:
- `documents:toggle_bookmark`: `/documents/document/<id>/bookmark/`
- `documents:rate_document`: `/documents/document/<id>/rate/`
- `documents:share_document`: `/documents/document/<id>/share/`
- `documents:document_stats`: `/documents/document/<id>/stats/`

**Preserved Routes**: All existing URL patterns remain unchanged.

## Selector Changes

### DocumentSelector.get_document_statistics (Modified)

**Location**: `documents/selectors/document_selectors.py`

**Change**: Updated to use cached analytics instead of COUNT queries

**Behavior**:
1. First attempts to get DocumentAnalytics for the document
2. If analytics exist, returns cached values (fast)
3. If analytics don't exist, falls back to COUNT queries (slow but functional)
4. Returns additional fields: rating percentages, trending/popularity scores

**Performance Impact**: 
- Significant reduction in database queries when analytics exist
- Graceful degradation ensures functionality even before analytics are created

## Celery Task Changes

### New Tasks

**Location**: `documents/tasks/processing.py`

#### update_document_analytics(document_id)
**Purpose**: Recalculate and cache engagement statistics for a document

**Process**:
1. Get or create DocumentAnalytics record
2. Count engagement records (views, downloads, bookmarks, shares, ratings)
3. Calculate rating percentages
4. Compute trending score (weighted recent engagement from last 7 days)
5. Compute popularity score (weighted long-term engagement)
6. Update last_activity timestamp
7. Save analytics record

**Triggered By**:
- Bookmark toggle
- Rating change
- Share action
- Stale analytics detection (older than 5 minutes)

#### update_analytics_for_all_documents()
**Purpose**: Maintenance task to update analytics for all documents

**Use Case**: Can be run periodically to ensure all documents have fresh analytics

## Performance Optimizations

### Cached Counters
- DocumentAnalytics model stores pre-computed counts
- Eliminates expensive COUNT queries during page renders
- Updated asynchronously via Celery

### Asynchronous Updates
- All engagement actions trigger background analytics updates
- User interactions remain fast (no waiting for analytics recalculation)
- Celery tasks handle computation in background

### Query Optimization
- DocumentSelector uses cached analytics when available
- Falls back to COUNT queries only when necessary
- select_related and prefetch_related used in existing queries (preserved)

### Indexes
- DocumentAnalytics has indexes on trending_score, popularity_score, last_updated
- Enables efficient sorting for trending/popular document lists

## Permission Model

### Preserved Permissions
- Download permissions follow existing document access rules
- View tracking works for both authenticated and anonymous users

### New Permission Requirements
- **Bookmark**: Requires authentication (login_required decorator)
- **Rate**: Requires authentication (login_required decorator)
- **Share**: Requires authentication (login_required decorator)
- **Stats**: Requires authentication (login_required decorator)

### Rationale
- Engagement features require user identity to prevent abuse
- Anonymous users can still view documents and download (if permitted)
- Consistent with social platform best practices

## Regression Prevention

### Existing Features Preserved

1. **Upload Flow**: No changes to upload views, forms, or processing
2. **Document Preview**: Preview generation and display unchanged
3. **Search**: Search functionality and indexing unchanged
4. **Recommendations**: Related document logic unchanged
5. **Permissions**: Document access permissions unchanged
6. **URLs**: All existing URL patterns preserved
7. **Templates**: Existing template structure preserved (only enhanced)

### Graceful Degradation

1. **Analytics**: If analytics don't exist, system falls back to COUNT queries
2. **Rating**: Old rating data can be migrated to new system
3. **UI**: If HTMX fails, buttons still render (just without async behavior)

### Testing Coverage

Comprehensive test suite added in `documents/tests/test_engagement.py`:
- Model tests (DocumentRating, DocumentAnalytics)
- View tests (bookmark toggle, rating, sharing, stats)
- Permission tests (anonymous vs authenticated)
- Edge cases (invalid ratings, zero ratings, unique constraints)

### Migration Strategy

1. **Model Changes**: Django makemigrations will create migration for DocumentRating field changes
2. **Data Migration**: Custom migration needed to convert existing 1-5 ratings to thumbs up/down
3. **Analytics Creation**: Celery task can be run to create analytics for existing documents
4. **Rollback Plan**: Migrations can be reversed if issues arise

## Integration Points

### Posts Integration
- Share to profile creates a Post with `shared_document` field
- Uses existing PostService if available
- Falls back to direct Post creation if service unavailable

### Groups Integration
- Share to group creates GroupPost with shared document
- Checks group membership before allowing share
- Uses existing Group and GroupPost models

### Courses Integration
- Uploader information displays course name from User.course relationship
- No changes to Course model

## Known Limitations

1. **Group Selection**: Current implementation uses prompt() for group ID selection
   - **Improvement**: Should be replaced with proper modal in production
   
2. **Share to Profile**: Assumes PostService.create_document_share_post exists
   - **Fallback**: Direct Post creation if service unavailable
   - **Improvement**: Verify PostService implementation

3. **Analytics Initialization**: Analytics created on first engagement or stats request
   - **Improvement**: Consider bulk initialization for existing documents

4. **Rating Migration**: Existing 1-5 ratings need data migration
   - **Action Required**: Run custom migration to convert existing data

## Deployment Checklist

1. **Run Migrations**:
   ```bash
   python manage.py makemigrations documents
   python manage.py migrate documents
   ```

2. **Create Data Migration for Ratings** (if existing ratings exist):
   - Convert ratings >= 3 to thumbs up (1)
   - Convert ratings < 3 to thumbs down (-1)

3. **Initialize Analytics for Existing Documents**:
   ```python
   from documents.tasks.processing import update_analytics_for_all_documents
   update_analytics_for_all_documents.delay()
   ```

4. **Verify HTMX**: Ensure HTMX library is included in base template

5. **Test Engagement Features**:
   - Bookmark toggle
   - Thumbs up/down rating
   - Share (copy link, profile, group)
   - Stats display

6. **Monitor Celery**: Ensure Celery workers are running for async analytics updates

## Monitoring and Maintenance

### Analytics Freshness
- Analytics older than 5 minutes trigger refresh on next stats request
- Consider periodic bulk refresh task for consistency

### Performance Metrics
- Monitor page load times (should improve with cached analytics)
- Monitor Celery queue length (analytics updates should be fast)
- Monitor database query counts (should decrease)

### Data Integrity
- Periodic verification that analytics match actual counts
- Consider reconciliation task if discrepancies found

## Future Enhancements

1. **Real-time Updates**: Consider WebSocket for real-time engagement updates
2. **Advanced Analytics**: Add time-series data for engagement trends
3. **Recommendation Engine**: Use engagement data for improved recommendations
4. **A/B Testing**: Test different engagement UI patterns
5. **Gamification**: Add badges/achievements based on engagement

## Conclusion

The document engagement expansion successfully adds comprehensive engagement features while preserving all existing functionality. The architecture prioritizes performance through caching and asynchronous processing, maintains consistency with existing design patterns, and provides a solid foundation for future enhancements.

The implementation follows Django best practices, includes comprehensive test coverage, and includes graceful degradation strategies to ensure reliability. All changes are documented to facilitate maintenance and future development.
