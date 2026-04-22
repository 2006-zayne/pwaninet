# Clean View Refactor Notes (Alpha Stage)

This document explains the exact modification made to move query/business logic out of the Django view layer, so views stay clean and focused.

## What You Asked For

You wanted:

- views that mainly accept requests and return pages
- query logic removed from views
- a clean architecture direction while still in local alpha

That is exactly what was implemented for the `home` feed flow first.

---

## What Was Changed

### 1) New Query Layer

Created: `core/queries/feed_queries.py`

Purpose:

- hold ORM-heavy read logic for the feed
- isolate SQL/query concerns from view/controller logic

Functions moved here:

- `get_following_ids(user)`
- `get_user_group_ids(user)`
- `get_prioritized_feed_posts(user, following_ids, user_group_ids, limit=15)`
- `get_liked_post_ids_for_user(user, post_ids)`
- `get_suggested_groups(user, following_ids, limit=5)`
- `get_user_suggestions_from_groups(user, limit=5)`

Result:

- feed query details are now centralized in one place
- easy to optimize indexing/query strategies later

---

### 2) New Service Layer

Created: `core/services/feed_service.py`

Purpose:

- orchestrate the use-case ("build context for home feed")
- combine query functions into one reusable service call

Main function:

- `build_home_feed_context(user)`

What it does:

1. loads following IDs and joined group IDs
2. fetches ranked feed posts
3. resolves liked-post state for current user
4. fetches suggested groups and user suggestions
5. returns a ready-to-render context dictionary

Result:

- business orchestration removed from views
- easier unit testing at service level

---

### 3) View Simplification

Updated: `core/views.py`

`home_view` changed from a large query-heavy function to:

1. call `build_home_feed_context(request.user)`
2. return `render(request, "home.html", context)`

Also removed the now-redundant local utility `get_suggestions(request)` from `views.py`, because it now belongs in the query layer.

Result:

- cleaner, smaller, easier-to-read view
- view now behaves as a true request/response controller

---

### 4) Package Setup

Added package markers:

- `core/queries/__init__.py`
- `core/services/__init__.py`

Purpose:

- keeps architecture modules organized
- supports clean imports across app modules

---

## Why This Is Better (Especially in Alpha)

1. **Safer iteration**  
   You can tune queries without touching request handling code.
2. **Faster debugging**  
   Problems are easier to isolate: view issue vs query issue.
3. **Better testability**  
   You can unit-test service/query logic without full request objects.
4. **Scales with team size**  
   One person can optimize data access while another works on templates/views.
5. **Production readiness**  
   This separation makes future caching, read-replica routing, and performance profiling easier.

---

## How to Continue This Pattern

Use the same 3-layer split for each complex endpoint:

1. **View**: receive request, validate simple input, return response
2. **Service**: use-case orchestration
3. **Query module**: ORM/database operations

Recommended next targets (in order):

1. notifications flow (`notifications_list`, unread counters)
2. search flow (`search_results`)
3. group dashboard/detail aggregations
4. profile analytics counts

---

## Example Template for Future Refactors

For any endpoint:

1. create `core/queries/<feature>_queries.py`
2. create `core/services/<feature>_service.py`
3. move ORM code into query functions
4. move orchestration into service function
5. keep view to 3-10 lines
6. add tests for service behavior

---

## Final Note

This was intentionally done as an incremental refactor (not a full rewrite), which is the right strategy before hosting.  
You now have a concrete clean-view pattern in production code (`home_view`) that can be repeated safely across the rest of the app.

---

## Additional Refactor Applied: Search Flow

To prove the procedure is repeatable, the same pattern has now also been applied to `search_results`.

### Files added

- `core/queries/search_queries.py`
- `core/services/search_service.py`

### View updated

- `core/views.py` (`search_results`)

### What moved out of the view

1. user search ORM filters
2. group search ORM filters
3. following IDs query
4. joined groups query
5. context assembly

Now the view only:

1. accepts request query input
2. calls `build_search_context(...)`
3. chooses partial vs full template response

---

## The Procedure (Reusable Checklist)

Use this exact checklist for each future endpoint:

1. Identify all ORM queries and business decisions in the view.
2. Move pure data fetches to `core/queries/<feature>_queries.py`.
3. Move orchestration/context construction to `core/services/<feature>_service.py`.
4. Replace view body with:
   - parse input
   - call service
   - return `render(...)` or response
5. Remove obsolete helper methods from `views.py`.
6. Run lints/tests and verify templates still receive the same context keys.
7. Commit small, endpoint-scoped changes (easy rollback).

If you follow this sequence every time, you will keep the codebase clean while reducing refactor risk during alpha.

---

## Additional Refactor Applied: Profile, Notifications, and Groups

The same clean-view procedure has now been applied to the other heavy sections.

### A) Profile flow

Added:

- `core/queries/profile_queries.py`
- `core/services/profile_service.py`

Updated:

- `core/views.py` -> `profile_view`

Moved out of view:

1. follow-state lookup
2. total likes aggregation
3. followers/following counts
4. user posts retrieval

Result:

- `profile_view` now only resolves `profile_user`, calls service, and renders.

### B) Notifications flow

Added:

- `core/queries/notification_queries.py`
- `core/services/notification_service.py`

Updated:

- `core/views.py` -> `notifications_list`
- `core/views.py` -> `unread_notification_count`
- `core/views.py` -> `mark_notification_as_read`
- `core/views.py` -> `mark_all_as_read`

Moved out of view:

1. list and ordering queries
2. mark-as-read operations
3. unread count retrieval
4. unread badge HTML assembly logic

Result:

- notification views now behave as thin controllers.

### C) Groups flow

Added:

- `core/queries/group_queries.py`
- `core/services/group_service.py`

Updated:

- `core/views.py` -> `groups_dashboard`
- `core/views.py` -> `groups_detail_view`

Moved out of view:

1. dashboard group list queries
2. suggested groups by following graph
3. group posts + membership checks
4. invite-candidate search logic

Result:

- both group views are now request/response handlers with service orchestration.

---

## Current Clean-View Coverage

The following endpoints are now refactored to clean-view style:

1. `home_view`
2. `search_results`
3. `profile_view`
4. `notifications_list`
5. `unread_notification_count`
6. `mark_notification_as_read`
7. `mark_all_as_read`
8. `groups_dashboard`
9. `groups_detail_view`

---

## Procedure You Should Keep Using (Standard)

For each remaining heavy endpoint:

1. extract ORM reads/writes into `core/queries/<feature>_queries.py`
2. create `core/services/<feature>_service.py` for use-case orchestration
3. slim view to input parsing + service call + response
4. keep template context keys unchanged
5. verify with local runserver manual test
6. run lint/tests
7. document endpoint changes in this file

This gives you predictable refactoring without breaking UX while alpha testing locally.

---

## Query Reduction + Caching (No Paid Products)

You asked to reduce DB queries and enable caching while still pre-hosting/early production without subscribing to paid services.  
This has now been implemented using Django's built-in cache framework.

### What was implemented

1. **Built-in cache backend configured**
   - `pwaninet/settings.py` now has `CACHES` using `LocMemCache`
   - no external subscription needed
2. **Feed context caching**
   - `core/services/feed_service.py`
   - home feed context cached for short TTL (45s)
   - invalidation helper added for write actions
3. **Search context caching**
   - `core/services/search_service.py`
   - per-user, per-query cache (30s TTL)
4. **Notification unread-count caching**
   - `core/services/notification_service.py`
   - unread count cached (30s TTL)
   - count cache invalidated/reset on read operations
5. **Global navbar query reduction**
   - `core/context_processors.py` now uses cached unread count
   - removes repetitive unread-count DB query on every template render
6. **Group query optimization**
   - `core/queries/group_queries.py`
   - `get_group_posts` now uses `select_related/prefetch_related`
   - invite candidate exclusion now uses member IDs directly

### Cache invalidation wired into write flows

Home feed cache invalidation was added in:

- post creation (`create_post_view`)
- like/unlike (`toggle_like`)
- follow/unfollow (`toggle_follow`)
- group join/leave (`toggle_group_membership`)
- invite acceptance (`respond_to_invite`)

This keeps cache fast while preventing long stale windows.

---

## How to Run This Without Paid Infra

### Local + alpha

- keep `LocMemCache` (already configured)
- use short TTLs as currently set
- this is enough for development and single-instance pilots

### Early production with zero subscription

If you run multiple Gunicorn workers/instances and still avoid paid services:

1. switch cache backend from `LocMemCache` to `FileBasedCache`
2. use a shared disk path on the host
3. keep TTLs short for user-sensitive fragments

`FileBasedCache` is slower than Redis but still better than no cache and requires no subscription.

---

## Important Note

Built-in caching helps immediately, but for true high concurrency (exam-day scale), Redis remains the best long-term option.  
You can keep this exact architecture and only swap the cache backend later with minimal code changes.
