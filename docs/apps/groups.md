# Groups app

## Purpose

`groups` provides student communities, membership and role management, join requests, invitations, group announcements, and group-level media/resources.

## Main data

The central models are `Group`, `Membership`, `GroupJoinRequest`, `GroupInvitation`, `Announcement`, `AnnouncementAttachment`, and group-photo interaction models. Group-message and attachment models remain in the app, but message endpoints are currently gated/frozen.

## Main journeys

Users discover or create groups, request to join or accept invitations, and group managers approve members and assign roles. Members can participate in announcements and related activity subject to group membership and privacy rules.

## Routes and entry points

The app is mounted at `/groups/`. Views and API actions in `groups/urls.py` cover group management, membership, settings, invitations, announcements, and group APIs. Main implementation files include `groups/models.py`, `groups/views.py`, `groups/permissions.py`, `groups/services/`, `groups/tasks.py`, and `groups/templates/`.

## Developer notes

- Check role, membership, visibility, and join-policy enforcement in both page views and APIs.
- Group attachments and photos are user-uploaded content; use the configured storage backend and preserve authorization checks on file access.
- `groups/tasks.py` contains background work such as course-group joining and attachment thumbnail generation.
- Group messaging is not a launch feature while the messaging gate remains active.
