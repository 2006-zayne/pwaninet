# Group Unread Count Feature - Implementation Plan

## Overview
This feature adds unread notification badges next to groups in the group dashboard/list, showing users which groups have new activity.

## Requirements

### Functional Requirements
1. Display unread notification count badge next to each group in group list
2. Badge should show the count of unread notifications for that specific group
3. Badge should be styled consistently with existing notification badges
4. Clicking the badge should filter notifications to show only that group's notifications
5. Badge should update in real-time when notifications are read
6. Badge should be hidden when count is 0
7. Badge should work with existing pagination and filtering

### Technical Requirements
1. Add query function to count unread notifications per group for current user
2. Modify group list view to include unread counts
3. Update group list template to display badges
4. Add HTMX for real-time badge updates when notifications are read
5. Ensure performance with efficient database queries
6. Maintain backward compatibility with existing group views

## Implementation Steps

### Step 1: Database Query Layer
**File:** `notifications/queries/notification_queries.py`

- Add function `get_unread_count_by_group(user, group_id)`
- This function will count unread notifications filtered by group
- Should use efficient query with COUNT aggregation

**Potential Issues:**
- None expected - simple query addition

### Step 2: Service Layer
**File:** `notifications/services/notification_service.py`

- Add function `get_group_unread_counts(user)` that returns a dictionary
- Dictionary maps group_id -> unread_count
- Should cache results for performance (5-10 second cache)
- Invalidate cache when notifications are created/read/deleted

**Potential Issues:**
- Cache invalidation must be handled correctly
- If cache fails, should fallback to direct query
- Multiple groups could cause N+1 query problem if not optimized

### Step 3: Group Views
**File:** `groups/views.py`

- Modify group list view to call `get_group_unread_counts`
- Pass counts to template context
- Ensure counts are available for both group list and group detail views

**Potential Issues:**
- If group list is large, counting for all groups could be slow
- Need to consider pagination impact on performance

### Step 4: Template Updates
**File:** `groups/templates/groups/group_list.html` (or equivalent)

- Add badge element next to group name
- Style badge to match notification badge design
- Add link to filtered notification view with group parameter
- Use conditional to hide badge when count is 0

**Potential Issues:**
- Template syntax errors if context variable not passed
- CSS conflicts with existing styles

### Step 5: Notification View Enhancement
**File:** `notifications/views.py`

- Ensure notification list view can filter by group_id
- Already implemented via `notification_type` parameter
- May need to add explicit group filtering if not already present

**Potential Issues:**
- None expected - filtering already exists

### Step 6: Real-time Updates
**File:** `notifications/templates/notifications/partials/notification_list.html`

- Add HTMX trigger to update group badges when notifications are read
- Use existing `updateUnreadCount` trigger or create new one
- Update badge counts via JavaScript fetch

**Potential Issues:**
- HTMX trigger timing issues
- JavaScript errors if DOM elements not found
- Performance if too many badges need updating

## System Impact Analysis

### Affected Components

**Positive Impact:**
1. **User Experience** - Users can quickly identify groups with new activity
2. **Engagement** - Likely to increase group participation
3. **Visibility** - Makes notification system more prominent

**Potential Negative Impact:**
1. **Performance** - Additional database queries for each group in list
2. **Cache Memory** - Group count cache will use additional memory
3. **Complexity** - Adds more logic to group views and templates

### Database Impact
- **Read Operations:** Additional COUNT queries for group notifications
- **Write Operations:** No direct impact, but cache invalidation on notification changes
- **Index Usage:** Should use existing indexes on `recipient` and `group` fields

### Performance Considerations
- **Small Group Lists (< 50 groups):** Minimal impact, acceptable
- **Large Group Lists (100+ groups):** Could be slow without caching
- **Solution:** Implement caching with 5-10 second TTL
- **Fallback:** If cache fails, show "!" indicator instead of count

### Backward Compatibility
- **Existing Views:** No breaking changes, only additive
- **Existing Templates:** New template variables are optional
- **Existing Data:** No migration required for existing data
- **API:** No API changes

## Risk Assessment

### High Risk
- None identified

### Medium Risk
1. **Performance degradation** on large group lists
   - **Mitigation:** Implement caching, add pagination limits
   - **Fallback:** Show "new" indicator instead of exact count

2. **Cache invalidation bugs** causing stale counts
   - **Mitigation:** Short cache TTL (5-10 seconds)
   - **Fallback:** Direct query if cache miss

### Low Risk
1. **Template rendering errors** if context not passed
   - **Mitigation:** Use `|default:0` filter in templates
   - **Testing:** Test with various view states

2. **CSS conflicts** with existing badge styles
   - **Mitigation:** Use specific CSS classes, test in different contexts
   - **Fallback:** Inline styles if needed

## Testing Strategy

### Unit Tests
1. Test `get_unread_count_by_group` with various states
2. Test `get_group_unread_counts` caching behavior
3. Test cache invalidation on notification create/read/delete

### Integration Tests
1. Test group list view with unread notifications
2. Test badge display and hiding logic
3. Test badge click navigation to filtered notifications
4. Test real-time badge updates via HTMX

### Edge Cases
1. User with no groups
2. User with groups but no notifications
3. User with 100+ groups (performance test)
4. Cache failure scenarios
5. Concurrent notification updates

## Rollback Plan

If issues arise after deployment:
1. Remove badge display from templates (simple revert)
2. Disable cache in service layer (fallback to direct query)
3. Remove unread count queries from views (performance issue)
4. Feature can be disabled without affecting core functionality

## Success Criteria
1. Badge displays correct unread count for each group
2. Badge updates when notifications are read
3. Badge links to filtered notification view
4. Performance impact is < 100ms for typical group lists
5. No errors in browser console
6. Works on mobile devices

## Timeline Estimate
- Implementation: 1-2 hours
- Testing: 30 minutes
- Total: 2-2.5 hours
