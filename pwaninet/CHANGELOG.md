# Changelog

All notable changes to the project will be documented in this file.

## [Unreleased]

### Fixed - Group Management Bugs (2026-04-26)

#### Bug 1: Notification Not Disappearing After Approval/Rejection
- **Issue**: When admins approved or rejected group join requests from notifications, the notification remained in the list instead of being removed.
- **Root Cause**: The `approve_from_notification` and `reject_from_notification` views were not deleting the GROUP_REQUEST notification after processing.
- **Fix**: Added logic to find and delete the GROUP_REQUEST notification after approving or rejecting a membership request.
- **Files Modified**:
  - `groups/views.py` (lines 467-477, 517-527)

#### Bug 2: Incorrect Notification on Group Join Request
- **Issue**: Users requesting to join a group were receiving a `GROUP_REQUEST` notification themselves, when only admins should receive this notification type.
- **Root Cause**: In `toggle_group_membership` view, a confirmation notification was being sent to the requesting user with the wrong notification type (`GROUP_REQUEST` instead of a simple success message).
- **Fix**: Removed the incorrect notification to the requesting user. Now only admins receive `GROUP_REQUEST` notifications when someone requests to join. Users only see a success message indicating their request is pending approval.
- **Files Modified**:
  - `groups/views.py` (lines 401-412)

#### Bug 3: Edit Group Modal Form Issues
- **Issue**: When clicking "Edit Group" button, the modal form was not saving changes correctly and had incorrect field mappings.
- **Root Cause**: 
  - Modal form used `name="photo"` but the form expected `name="group_pic"`
  - Modal was missing the `join_policy` field entirely
- **Fix**: 
  - Changed field name from `photo` to `group_pic` to match the GroupForm
  - Added `join_policy` select field with proper selection logic to pre-select current policy
- **Files Modified**:
  - `groups/templates/groups/groups_detail.html` (lines 644-672)

#### Bug 4: Group Approval Not Working
- **Issue**: When admins approved group join requests from notifications, the approval was not working correctly.
- **Root Cause**: The membership role was not being explicitly set to `MEMBER` upon approval, and error messages lacked debugging information.
- **Fix**: 
  - Added explicit `membership.role = MembershipRole.MEMBER` when approving requests
  - Improved error messages to include `user_id` and `group.name` for easier debugging
- **Files Modified**:
  - `groups/views.py` (lines 505-506, 502)

### Refactored - Group Notification Service (2026-04-26)

#### Created Dedicated Notification Service
- **Change**: Centralized all group-related notification logic into a dedicated service module.
- **Rationale**: 
  - Separation of concerns - notification logic should not be scattered across views
  - Reusability - notification functions can be reused across different parts of the app
  - Maintainability - easier to update notification behavior in one place
  - Testability - isolated functions are easier to unit test
- **New File**: `groups/services/group_notification_service.py`
  - `send_group_join_request_notification()` - Notifies admins when users request to join
  - `send_group_approved_notification()` - Notifies users when their request is approved
  - `send_group_rejected_notification()` - Notifies users when their request is rejected
  - `send_group_welcome_notification()` - Welcomes users to open groups
  - `send_group_invite_notification()` - Sends group invite notifications

#### Updated Views to Use Notification Service
- **Change**: Replaced all direct `create_notification()` calls in group views with the new service functions.
- **Files Modified**:
  - `groups/views.py` - Updated imports and replaced notification calls in:
    - `GroupViewSet.join()` method
    - `GroupViewSet.approve()` method
    - `GroupViewSet.reject()` method
    - `toggle_group_membership()` view
    - `invite_to_group()` view
    - `approve_from_notification()` view
    - `reject_from_notification()` view

### Updated - Create/Edit Group Template (2026-04-26)

#### Enhanced Template for Edit Mode
- **Change**: Updated `create_group.html` template to properly handle both create and edit modes.
- **Improvements**:
  - Page title dynamically shows "Create a Group" or "Edit Group" based on context
  - Form fields pre-populate with existing data when editing
  - Join policy dropdown shows current selection when editing
  - Submit button shows "Create Group" or "Save Changes" appropriately
  - Cancel button redirects to appropriate page (dashboard for create, group detail for edit)
- **Files Modified**:
  - `groups/templates/groups/create_group.html` (lines 195-264)

---

## Previous Changes

See individual documentation files for earlier changes:
- `docs/GROUP_MEMBERSHIP_REFACTORING.md` - Group membership system refactoring
- `docs/REALTIME_NOTIFICATIONS_ARCHITECTURE.md` - Real-time notifications implementation
- `ARCHITECTURE_ANALYSIS.md` - Overall architecture analysis
