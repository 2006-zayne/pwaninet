# Change Log - 2026-04-22

## Scope

This update focuses on:

1. Feed refresh behavior and progressive loading.
2. Modal/script resilience for mobile usage.

## Implemented Changes

### 1) Feed pagination and infinite scroll

- Added a ranked feed queryset helper in `core/queries/feed_queries.py`:
  - `get_prioritized_feed_queryset(...)` now returns the ordered queryset.
  - Existing `get_prioritized_feed_posts(...)` remains as a compatibility wrapper.
- Updated `core/services/feed_service.py`:
  - `build_home_feed_context(user, page=1)` now supports page-based loading.
  - Added `FEED_PAGE_SIZE = 10`.
  - Added `has_next`, `next_page`, and `page` to the context.
  - Shortened page-1 cache timeout to improve refresh freshness.
- Added new feed page endpoint in `core/views.py`:
  - `home_feed_page(request)` returns a feed chunk partial for HTMX loading.
- Registered URL in `core/urls.py`:
  - `feed/page/` -> `home_feed_page`.
- Added template partial `core/templates/partials/feed_posts_page.html`:
  - Renders posts for one chunk.
  - Appends an HTMX sentinel using `hx-trigger="revealed"` to load next page.
- Updated `core/templates/home.html`:
  - Feed now renders via the new partial and progressively loads additional chunks.

### 2) Modal and script robustness

- Updated `core/templates/base.html`:
  - Added static-first script references for `htmx` and `bootstrap bundle`.
  - Kept CDN references as fallback.
  - Hardened modal reset script with null checks so missing elements do not crash JS.
- Updated `core/templates/groups_detail.html`:
  - Added `window.bootstrap` guard before calling `new bootstrap.Modal(...)`.

## Notes

- True offline mode (service worker + cache storage strategy) is not implemented yet in this change set.
- The current feed now supports progressive loading until the backend has no more posts to return.

## Notification Fixes (Follow-up)

### What was fixed

- Stopped auto-marking all notifications as read when opening the notifications page:
  - `core/views.py` now calls `build_notifications_context(..., mark_read=False)` in `notifications_list`.
  - `core/services/notification_service.py` default for `build_notifications_context` is now `mark_read=False`.
- Enforced HTTP method safety for read mutations:
  - `mark_notification_as_read` now returns `405` for non-POST requests.
  - `mark_all_as_read` now returns `405` for non-POST requests.
- Fixed and normalized notification list rendering:
  - `core/templates/notifications.html` now renders list rows via `partials/notification_list_items.html`.
  - `core/templates/partials/notification_list_items.html` now includes:
    - notification type badges
    - invite action buttons
    - icon column
    - proper empty state rendering
  - Removed invalid `group` template references from this partial that could break rendering.
- Added immediate badge refresh wiring for HTMX-triggered updates:
  - `core/templates/base.html` now listens for `notificationUpdate` and fetches fresh unread-count HTML into `#notification-badge-container`.

### Outcome

- Notifications no longer disappear from unread state just by visiting the page.
- "Mark as read" and "clear all" are now explicit actions.
- Navbar unread badge can refresh immediately after notification actions instead of waiting for the 30-second poll.

## Invite + Notification Routing Fixes

### What was fixed

- Fixed broken invite workflow where invited users were auto-added:
  - Removed duplicate `invite_to_group` behavior in `core/views.py` that directly added invited users to group membership.
  - `invite_to_group` now only creates an `INVITE` notification.
  - Membership now happens only via explicit accept in `respond_to_invite`.
- Enforced POST-only mutation paths for invite actions:
  - `invite_to_group` is now POST-only (`405` for non-POST).
  - `respond_to_invite` is now POST-only (`405` for non-POST).
  - Updated templates to submit invites/accept/decline via forms with CSRF tokens.
- Added notification "open event" redirection:
  - New endpoint `notifications/open/<notif_id>/` via `notification_redirect`.
  - Invite notifications open notifications page anchored to that invite card.
  - Like notifications open the related post detail page.
  - Follow notifications open the sender profile page.
  - Opening a notification marks it as read.
- Improved unread badge freshness:
  - Unread cache now invalidates on invite create, invite response, and notification-open read.
  - Signal-created LIKE/FOLLOW notifications now invalidate unread cache immediately.
- Removed duplicate LIKE notification creation path:
  - `toggle_like` no longer creates direct notifications in views.
  - LIKE notifications now come from a single source (`signals.py`) with post linkage.

### Outcome

- Users are no longer added to groups before accepting invite requests.
- Invite acceptance/decline is now explicit and secure.
- Notifications now behave like event links and send users to the exact related context.

## Notification Click Behavior Tweak

- Updated `core/templates/partials/notification_list_items.html` so clicking:
  - sender username
  - notification message text
  - right-side notification icon
  all route through `notification_redirect`.
- This makes click behavior consistent:
  - LIKE -> liked post detail
  - FOLLOW -> follower profile
  - INVITE -> notifications page anchored to invite card

## Load Simulation Toolkit (2,000 Students)

- Added `loadtesting/locustfile.py` with an exam-day student behavior profile:
  - login
  - home feed + paginated feed requests
  - groups, notifications, post detail, and search traffic
- Added staged load shape `ExamDayTwoThousandShape`:
  - ramps through 200 -> 500 -> 1,000 -> 1,500 -> 2,000 users
  - holds at 2,000 before ramping down
- Added `EXAM_LOAD_TEST_PLAN.md`:
  - setup instructions
  - run commands (UI and headless)
  - success thresholds
- Added `locust` dependency to `requirements.txt` for reproducible execution.
