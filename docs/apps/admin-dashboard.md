# Admin dashboard app

## Purpose

`admin_dashboard` provides staff-facing operational metrics, feedback tickets, and staff review workflows.

## Main data

The core models are `FeedbackTicket`, `FeedbackReply`, and `UserDailyActivity`. Authenticated requests update a per-user daily activity record for online and daily-active metrics.

## Routes and entry points

Mounted at `/dashboard/`. Current routes cover the dashboard home, staff feedback inbox/detail, a user feedback view, and feedback submission. Students can submit feedback directly from the main Settings page; successful submissions create a ticket and an in-app notification for active staff/superusers. Main implementation is in `admin_dashboard/models.py`, `views.py`, `urls.py`, and the app's templates/partials.

## Developer notes

- Keep staff-only operations protected by explicit permission checks.
- Feedback submissions may include contact details or personal information; limit access and avoid putting sensitive values in logs.
- Daily activity data begins accumulating after the `UserDailyActivity` migration is deployed; it does not backfill historical daily activity.
- The activity table stores account-linked per-day records. Set and document a retention period before launch.
- The admin charts load Chart.js on demand so first-load and HTMX navigation do not depend on a CDN script race.
