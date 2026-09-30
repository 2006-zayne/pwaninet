# Notifications app

## Purpose

`notifications` records platform events, creates in-app notification objects, stores user delivery preferences, and supports browser/native push subscriptions and delivery attempts.

## Main data

Important models include `PlatformEvent`, `NotificationObject`, `NotificationPreference`, `PushSubscription`, `DeliveryAttempt`, `EventArchive`, and `NotificationAction`.

## Main journeys

App signals or services create platform events; event processing generates user-facing notifications; users view, mark, delete, or act on notifications. Push subscription APIs store browser endpoints/keys or native device tokens when push is enabled.

## Routes and entry points

Mounted at `/notifications/`; push endpoints are also mounted at `/api/push/` in the project URL config. The app includes API routes, notification views, payload-rendering endpoints, tasks, delivery services, event processing, and rendering profiles.

## Developer notes

- Notification processing and Celery task behavior should be kept idempotent where retries are possible.
- Push endpoints and tokens are device-linked identifiers. Treat them as personal/security-sensitive data and remove them when subscriptions are revoked.
- Provider setup (VAPID, Firebase) is optional and depends on environment credentials; repository presence alone does not mean delivery is live.
- Keep preference handling consistent across notification creation and delivery.
