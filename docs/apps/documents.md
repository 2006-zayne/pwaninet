# Documents app

## Purpose

`documents` powers the academic-resource repository: academic classifications, document metadata and files, uploads and versions, discovery, requests, bookmarks/downloads, moderation, and storage bookkeeping.

## Main data areas

- `documents/academic/`: academic years, levels, semesters, faculties, schools, departments, programmes, academic units, and programme-unit relations.
- `documents/documents/`: categories, tags, documents, versions, files, authors, and academic-unit links.
- `documents/requests/`: requests for resources and request voting.
- `documents/engagement/`: views, downloads, bookmarks, ratings, shares, analytics, and reports.
- `documents/collections/`: personal or shared collections and their items.
- `documents/moderation/`: review status and moderation queue.
- `documents/storage/`: backend metadata, checksums, and storage migration tracking.

## Main journeys

Users browse and search available resources, upload documents, manage versions and metadata, bookmark or download items, and request missing resources. Moderators review reported or queued material. Academic taxonomy supports course-related filtering and registration fields.

## Routes and entry points

Mounted at `/documents/`. `documents/urls.py` includes the web repository, document detail/upload/library actions, academic routes, and API routers. Main service code is divided into subpackages; `documents/views.py` is the main web entry point and `documents/api.py` contains API viewsets.

## Developer notes

- The app has both public and private file paths. Private resources must continue to use the controlled file-serving path and must not become publicly accessible through a CDN by accident.
- Storage backend settings are in `pwaninet/settings/base.py`; local `media/` storage is the default, and R2 is optional through environment settings.
- Past papers, lecture notes, and other academic materials can have third-party rights restrictions. Check provenance and permission before bulk-importing or exposing a file.
- Uploads, downloads, reports, and document search may create user activity records; preserve privacy and authorization filters.
