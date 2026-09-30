# Releases app

## Purpose

`releases` manages in-app release notes, version/build information, user views, and release publication workflows. The project also has separate mobile APK download endpoints at the project URL level.

## Main data

Models include `Release`, `ReleaseItem`, `ReleaseItemImage`, and `UserReleaseView`.

## Main journeys and routes

Staff manage and publish releases through `/system/releases/`. API routes under the release app provide version information, release data, creation, and a GitHub release webhook.

## Developer notes

- Publishing/current-release selection can affect what the application reports as its active version; review permissions and state transitions.
- Webhook signing/configuration and APK download behavior are partly configured at project level, so inspect the root URL/settings when changing releases.
- Release artwork uses the configured storage backend; do not commit generated or user-uploaded release media.
