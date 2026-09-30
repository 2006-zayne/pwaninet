# Search app

## Purpose

`search` provides site-wide search pages, query suggestions, and recent-search behavior. Other apps may also implement their own narrower search experiences.

## Main implementation

The app is service/view based and does not define a primary `models.py`. Search views are in `search/views.py`; URL patterns are in `search/urls.py`; indexing and query helpers live in `search/indexing.py` and `search/services/`.

## Routes

Mounted at `/search/`, with the main search page, suggestions, and recent-search clearing endpoints.

## Developer notes

- Search results must apply the same privacy, visibility, blocking, and membership filters as the source app.
- Search queries and recent-search state may be personal data; check what is stored, logged, or retained when changing search behavior.
- Keep indexing changes synchronized with model changes in the source apps.
