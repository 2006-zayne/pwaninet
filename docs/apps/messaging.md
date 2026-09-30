# Messaging app (frozen)

## Current status

Direct messaging is frozen until further notice and is excluded from the agreed launch scope. The repository retains its models, migrations, templates, WebSocket consumers, and APIs so the work is not lost.

Current project and group URL flows include a `messaging_frozen` gate for disabled routes. The app URL configuration includes a catch-all frozen response before conversation patterns. Verify all production entry points remain gated before launch; do not infer that the feature is available because its code is present.

## Code areas

`messaging/` contains conversations, members, messages, attachments, reactions, themes, views, serializers, API routes, and Channels consumers. `messaging.frozen/` is a separate historical/frozen code snapshot and is not the active installed app.

## Re-enabling later

Do not remove the gate as a documentation-only change. Re-enabling messaging requires a separate product decision and review of authentication, authorization, attachment access, WebSocket routing, notifications, privacy/retention, and client flows. Update this guide and the public privacy notice before launch of the feature.
