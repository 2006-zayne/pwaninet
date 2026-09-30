# Posts app

## Purpose

`posts` provides the social feed and user-generated post experience, including media, comments, reactions, reposts, sharing, and content reports.

## Main data

Important models include `Post`, `PostImage`, `Comment`, `Like`, `CommentLike`, `PostImageLike`, `PostImageComment`, `Repost`, `SharedPost`, `HiddenPost`, `AuthorPreference`, and `Report`.

## Main journeys

Authenticated users create posts and attach media. Other users can interact with content according to its visibility, follow relationships, and group context. The app also supports sharing/reposting and report/moderation signals. Larger media processing and preview generation can be delegated to Celery tasks.

## Routes and entry points

Posts are mounted at the site root through `posts/urls.py`. The app also exposes API routes in `posts/api_urls.py`. Core code is in `posts/models.py`, `posts/views.py`, `posts/forms.py`, `posts/services/`, `posts/queries/`, `posts/tasks.py`, and `posts/templates/`.

## Developer notes

- Media fields use Django storage; the active storage backend is selected by project settings. Local development uses `media/`; production should use the configured object-storage/CDN setup.
- Avoid bypassing visibility checks in views, APIs, feeds, shared content, and thumbnails.
- Post and image content is user content. Keep upload authorization, attribution, privacy, and report/removal handling in mind when changing this app.
- Task routing and retries are configured in app task decorators and project Celery settings.
