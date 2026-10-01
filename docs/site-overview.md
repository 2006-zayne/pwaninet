# PwaniNet Site Overview

## What PwaniNet is

PwaniNet is a student-focused web application built with Django. It brings together student profiles and connections, posts and groups, academic programme data, a document repository, notifications, and the Pwanimate assistant. The site also has a Progressive Web App experience and an Android wrapper built with Capacitor.

The project aims to address student updates and discussions being spread across separate channels, difficulty discovering relevant study resources, and difficulty connecting with peers around shared academic interests. These are the product's intended pain points and should be validated with student feedback before being presented as research findings.

The project is an independent personal project. It is not an official Pwani University service or assignment unless the University confirms such a relationship in writing. See the pre-launch About draft for the current proposed public wording.

## Main user journeys

1. A visitor registers with a username, password, programme, academic level, academic year, and semester. The form also allows optional name fields. Users sign in with Django session authentication.
2. An account can fill in a profile, choose visibility and display preferences, follow other users, and manage account security.
3. Users can publish posts, images, comments, reactions, and reposts, with visibility and group-related features governed by the app.
4. Users can find or share academic documents, browse academic classifications, request resources, bookmark and download available items, and report content.
5. Notifications surface social, group, document, and service events. Browser or native push is available when configured and enabled by the user.
6. Search and recommendation components help users find people and content. Pwanimate provides an assistant experience inside the same Django site. Its custom orchestration layer assembles student context, searches the document knowledge base, and can call site tools before requesting a response from a configured AI provider. Provider availability and data routing depend on environment settings.

Direct messaging code and data models remain in the repository, but direct messaging is frozen for now. URL gates return frozen/disabled behavior in current flows. Do not describe it as a launch feature unless that gate has been deliberately changed and reviewed.

## Technology and architecture

| Area | Technology and role |
| --- | --- |
| Web application | Django 5.2, Python, Django templates, JavaScript, CSS, HTMX, Bootstrap |
| Database | PostgreSQL; the supplied Compose database image includes pgvector |
| Real-time connections | Django Channels over ASGI; Daphne is used by the repository Dockerfile |
| Background work | Celery tasks; Redis is configured as broker/result backend |
| Cache and channel layer | Redis; local settings disable Django's cache backend but Channels/Celery still have Redis configuration |
| Media | Local filesystem by default; optional Cloudflare R2 object storage with a CDN domain when `USE_S3=1` |
| Static files | Source assets live in `static/`; `collectstatic` writes generated output to `staticfiles/` |
| Mobile wrapper | Capacitor Android project in `android/` |
| WSGI option | Gunicorn is in Python dependencies; confirm deployment command before treating it as the production server |

The project settings live in `pwaninet/settings/`. `pwaninet/asgi.py` routes HTTP requests to Django and WebSocket requests through Channels; the shared WebSocket consumers are in `realtime/`. `pwaninet/celery.py` configures task discovery. The root URL configuration mounts the installed apps and project-level endpoints. Much of the site navigation uses HTMX to fetch and swap page sections while Django templates remain the server-rendered source of content. Pwanimate uses a custom browser rendering layer for assistant responses.

## App map

- `users`: accounts, profiles, authentication, privacy, security, and social connections.
- `posts`: feed, media posts, comments, reactions, reposting, and moderation reports.
- `groups`: group membership, invitations, announcements, and group resources.
- `courses`: legacy/course catalogue structures; newer registration academic classifications also live under `documents/academic/`.
- `documents`: academic resource repository, metadata, engagement, requests, storage, and moderation.
- `notifications`: notification events, preferences, delivery, and push subscriptions.
- `search`: cross-site search views and suggestions.
- `recommendations`: recommendation and ranking services consumed by other experiences.
- `pwanimate`: assistant conversations, retrieval/chunks, attachments, and provider integrations.
- `releases`: release notes and version information.
- `admin_dashboard`: internal dashboard and feedback handling.
- `messaging`: frozen direct-messaging feature code; preserve it while the feature is disabled.
- `core` and `realtime`: project-level views/utilities and shared ASGI/Channels support; these are not listed as separate installed app guides.

See [the app guides](apps/README.md) for code locations and more detail.

For a learner-friendly walkthrough of the site boundaries, important dependencies, and the Pwanimate request lifecycle, start with the [site owner guide](site-owner-guide.md).

## Data and files

The database stores accounts, relationships, posts, group and document metadata, notification state, and other application records. Uploaded files use Django storage fields and related services. Settings support a local filesystem backend and Cloudflare R2 through `django-storages`/Boto3. Production is intended to keep user uploads in configured object storage/CDN; confirm the production environment has `USE_S3=1`, valid credentials, the right bucket, and private-resource handling before relying on that behavior.

Static source assets are not user uploads. The app loads CSS, JavaScript, fonts, and interface images from the tracked `static/` tree. The generated `staticfiles/` collection is ignored. Removing source assets would break the site unless an equivalent deployed asset source is configured.

The default profile avatar is tracked at `static/images/default_pic1.jpg`. `ProfilePictureStorage` maps the legacy default field name to that static asset, while actual profile-picture uploads continue using the configured media storage. No uploaded media belongs in Git.

## External services

The settings and code include optional integration points for email, Firebase/native push, Web Push, Cloudflare R2, and external AI/embedding providers. Repository configuration is not proof that an integration is enabled in production. Maintain the actual production provider inventory in the pre-launch checklist and privacy notice.

## Key operations

- Database schema changes are made through Django migrations.
- Background jobs are declared in app task modules and discovered by Celery.
- Django's admin site is available under `/admin/` for authorized staff.
- API schema and interactive API documentation are mounted at `/api/schema/` and `/api/docs/` in the root URL configuration.
- Release screens are under `/system/releases/`; API routes are under the release URL namespace.

## Current limitations and launch decisions

- Direct messaging is frozen.
- The repo's `docker-compose.yml` starts PostgreSQL and Redis only; it does not start Django, Celery workers, or Celery Beat.
- The Dockerfile collects static assets and starts Daphne. A production process topology and Gunicorn role must be documented from the actual hosting configuration.
- R2/CDN support is conditional on environment settings; verify the live deployment before stating that all uploads are CDN-backed.
- The privacy policy, University relationship, material permissions, support contact, and licence inventory are still being finalized.
