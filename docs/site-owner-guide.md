# Understanding PwaniNet and Pwanimate

This is a reading guide for understanding the whole product, even when you usually work on one feature at a time. It explains the current code in this repository. The code and settings are the final source of truth when behavior changes.

## 1. The short version

PwaniNet is one Django application for student profiles, social activity, groups, academic resources, notifications, and related site features. Pwanimate is the AI assistant inside that application. It is a Django app that uses PwaniNet's accounts, academic records, groups, posts, documents, and notifications as sources of context through explicit tools and retrieval services.

The main request path is:

```text
Browser or Android app
        │ HTTP/API requests
        ▼
Django site (templates, views, APIs, app services)
        ├── PostgreSQL: accounts, posts, groups, resources, assistant history
        ├── Redis: Channels, Celery broker/results, configured cache
        ├── Celery workers: media, notifications, ingestion, embeddings
        └── External services when configured: object storage, push, AI providers
```

The Android application is a Capacitor wrapper around the web experience. It does not have a separate copy of the core PwaniNet business logic.

## 2. Find the main pieces

| Folder or file | What it is for |
| --- | --- |
| `pwaninet/` | Django project configuration: settings, root URLs, ASGI/WSGI entry points, and Celery setup. |
| `users/`, `posts/`, `groups/`, `documents/`, `notifications/` | Main student-facing product areas. Each owns its models, views, URLs, and services. |
| `pwanimate/` | Assistant UI/API, conversation records, context assembly, tool calls, retrieval, AI provider adapters, and document ingestion. |
| `realtime/` | Shared Channels routing and WebSocket consumers. |
| `templates/` and each app's `templates/` | Django-rendered pages and partials. |
| `static/` | Source CSS, JavaScript, fonts, icons, and local vendor libraries. `staticfiles/` is generated deployment output. |
| `android/` and `capacitor.config.json` | Native Android wrapper project and Capacitor configuration. |
| `requirements.txt` / `package.json` | Python and JavaScript dependency declarations. `requirements.txt` also pins many transitive packages. |
| `docs/apps/` | Maintained technical guide for each first-party Django app. |

`messaging/` contains a large direct-message feature but its current URL flows are frozen behind a gate. Its code being present does not mean it is enabled for users. `messaging.frozen/` is a historical code snapshot.

## 3. How PwaniNet works

### A normal page request

The browser requests a URL. The root URL configuration (`pwaninet/urls.py`) sends the request to an app such as `posts`, `users`, `groups`, or `documents`. A view checks the logged-in user and relevant visibility rules, loads or changes database records through Django's ORM, and returns a template or JSON response. Most pages are rendered by Django templates. HTMX is used in many screens to fetch and replace part of a page without a full reload; JavaScript handles interactions that need richer client-side behavior.

The app folder is usually the best starting point: read its `urls.py`, then follow the view, service/query module, and models it calls. Shared concerns such as authentication, project middleware, settings, and URL mounts live in `pwaninet/`.

### The major product areas

- **Users** owns the custom account model, academic profile, profile and privacy preferences, relationships (follow, block, and related discovery controls), onboarding, login, account recovery, and two-factor authentication.
- **Posts** owns the feed, media posts, comments, reactions, reposts, visibility, and content reports.
- **Groups** owns group discovery, membership and roles, invitations, announcements, attachments, and group-level academic relationships. Group message endpoints are gated with messaging.
- **Documents** owns the academic-resource repository: its academic classifications, document metadata and versions, upload/download access, collections, requests, search, and moderation.
- **Courses** contains a separate, partly legacy course catalogue. Before changing academic classifications, check whether the relevant feature uses `courses` or the newer `documents/academic/` models.
- **Notifications** turns platform events into in-app notifications and, when configured, browser Web Push or Android Firebase push.
- **Search and recommendations** help discover people and content, but neither should grant access. The underlying app must still enforce privacy and visibility.
- **Pwanimate** is explained in detail below.

### Real-time work and background jobs

Django Channels handles the ASGI/WebSocket path. Daphne is the server started by the repository Dockerfile. Celery runs work outside the web request, including media processing, notification delivery, Pwanimate ingestion and embedding, and reconciliation. Redis is configured for the Channels layer and Celery broker/results; local settings can disable Django's general cache backend.

The checked-in Compose file starts PostgreSQL and Redis only. It does not start the Django server, Daphne, Celery worker, or Celery Beat. See the [developer guide](developer-guide.md) for the local startup steps.

## 4. How Pwanimate works

Pwanimate is not a separate server in the current application. Its pages are mounted at `/pwanimate/` and its API is mounted at `/api/pwanimate/`. Its orchestration, retrieval, provider, and tool code is implemented directly in `pwanimate/`.

### When a student sends a message

1. The Pwanimate UI posts a message to the chat API. The API validates the request and associates the conversation with the authenticated user.
2. `PwanimateOrchestrator` coordinates the response. Context services build a bounded package of relevant user/profile context and request intent.
3. The retrieval service can search ingested academic-resource chunks by vector similarity. The tool router may select domain tools for an explicit site lookup, such as academic data, a document, a group announcement, people, or notification context. The tool calls are app code that query PwaniNet data; they are not arbitrary shell or browser actions.
4. The AI gateway turns the prompt, context, and tool results into a provider request. Provider adapters normalize authentication, HTTP requests, errors, and responses. The configured provider chain/quota tracker can move to an eligible fallback on provider errors or rate limits.
5. The response and usage information are returned to the UI, and conversation/message records are persisted. The UI renders Markdown, math, and code with local browser libraries and sanitizes generated HTML before display.

The exact context, tool set, model, and providers vary with code paths and environment configuration. The presence of an adapter or API key setting alone does not prove a provider is active in deployment.

### How reference documents become searchable

The ingestion tasks read source files from PwaniNet's document storage. Format-specific extractors read PDF, Word, PowerPoint, and text-like files. The structure-aware chunker breaks extracted content into useful smaller pieces and keeps location/source metadata. The embedding factory sends chunk text to the configured embedding provider. PostgreSQL stores the vectors with `pgvector`; retrieval compares a query vector with stored vectors and applies source/availability filters. Celery runs long ingestion and embedding work asynchronously.

This is the basis of retrieval-augmented generation (RAG): search for source passages relevant to a question, then give those passages to the language model as evidence. It is separate from normal site-wide keyword search, and it does not mean that every site record or upload is automatically included in the assistant's knowledge base.

Pwanimate also accepts user attachments, processes their text asynchronously, tracks attachment chunks, and can generate downloadable resources. Private attachment/media/download routes and source ownership checks are important parts of this flow.

## 5. Libraries and services in plain language

The table focuses on libraries that shape how the site works. The Python requirements file also includes many lower-level dependencies pulled in by these packages, developer/test tools, and optional integrations. It is not useful to treat every transitive package as a separately designed site component.

### Site foundation

| Library or service | What it does here |
| --- | --- |
| **Django** | The web framework: URL routing, HTML templates, database models, authentication, forms, admin, and migrations. |
| **Django REST Framework (DRF)** | Builds authenticated JSON APIs using views, serializers, parsers, permissions, and response helpers. Pwanimate's chat and attachment APIs use it. |
| **drf-spectacular** | Generates the OpenAPI schema and interactive API documentation served from `/api/schema/`, `/api/docs/`, and `/api/redoc/`. |
| **django-filter** | Turns validated query parameters into model filters for API/search list views. |
| **django-axes** | Adds protection against repeated failed login attempts. |
| **django-cors-headers** | Applies Cross-Origin Resource Sharing rules to HTTP responses where configured. |
| **cryptography** | Encrypts sensitive values such as stored two-factor secrets and protects authenticated invite payloads. |
| **PostgreSQL + psycopg2** | The relational database and Python driver. Django stores application records here; PostgreSQL extensions also support full-text search and vector operations. |
| **pgvector** | Adds vector column/query support to PostgreSQL. Pwanimate stores embeddings and ranks similar document chunks; the database image must include the extension. |
| **PostgreSQL full-text search and `pg_trgm`** | Database-native search features used by site search fields and trigram similarity indexes; these are PostgreSQL capabilities/extensions, not separate hosted search engines. |

### Request, live updates, and jobs

| Library or service | What it does here |
| --- | --- |
| **Django Channels** | Extends Django's ASGI app to accept WebSocket connections and route them to consumers. |
| **Daphne** | ASGI web server used by the Dockerfile to serve the application, including Channels support. |
| **Redis / channels-redis** | Redis stores configured Celery broker/results and provides the Channels layer. It is an infrastructure service, not the primary database. |
| **Celery** | Runs slow or retryable tasks in separate worker processes: processing media, notifications, Pwanimate attachments, document ingestion, and embedding generation. |
| **Celery Beat** | Optional scheduler that enqueues periodic tasks; it must run as its own process when scheduled tasks are needed. |

### Storage, documents, and media

| Library or service | What it does here |
| --- | --- |
| **django-storages + Boto3** | Optional S3-compatible storage integration used for Cloudflare R2 when `USE_S3=1`; local filesystem storage is the default in settings. |
| **Pillow** | Opens, resizes, and creates images, profile/post thumbnails, and other image-based assets. |
| **PyMuPDF (`fitz`)** | Reads PDF pages and text and renders page previews/thumbnails. It is used by Pwanimate ingestion and the documents/media pipeline. |
| **python-docx** | Reads uploaded Word documents for extraction and creates generated Word resources. |
| **python-pptx** | Reads PowerPoint files for Pwanimate ingestion. |
| **ReportLab** | Creates PDF documents in generated-resource/reporting paths. |
| **CairoSVG** | Converts SVG artwork to raster output in image-generation workflows where used. |
| **Playwright** | Provides a headless browser used in some richer thumbnail/rendering paths; code may fall back to Pillow when it is unavailable. |

### Pwanimate model calls and response display

| Library or service | What it does here |
| --- | --- |
| **`requests`** | Sends HTTP requests from the custom Pwanimate LLM and embedding adapters to provider APIs. Provider adapters are project code; no LangChain or OpenAI Python SDK is required for this runtime path. |
| **Gemini, Groq, OpenRouter** | Supported LLM service adapters. The gateway selects configured models and may use configured fallback candidates; credentials and deployment settings determine actual use. |
| **Gemini, Jina, Voyage, Cloudflare** | Supported embedding service adapters. These turn text into numeric vectors for semantic retrieval. A mock implementation supports tests/local flows. |
| **pgvector-backed RAG** | The retrieval technique and database support for finding semantically related source chunks to include as context for an LLM response. |
| **Marked** | Turns assistant Markdown into browser-renderable HTML. |
| **DOMPurify** | Cleans generated HTML before insertion into the page to reduce script/injection risk. |
| **KaTeX** | Renders mathematical notation in the response. |
| **Prism** | Highlights code blocks in the response. |

Pwanimate's current AI flow is custom Python code under `pwanimate/ai/`, `pwanimate/orchestrator/`, `pwanimate/context/`, `pwanimate/retrieval/`, and `pwanimate/tools/`. The cloned LangChain and OpenAI quickstart repositories under `pwanimate/repos/` are reference material, not imported runtime libraries. This distinction matters when reading the AI architecture or installing dependencies.

### Browser and mobile experience

| Library or service | What it does here |
| --- | --- |
| **HTMX** | Sends HTML-oriented requests from page elements and swaps returned fragments into the current page. It supports the site's partial-navigation pattern. |
| **Bootstrap 5** | Supplies common layout, responsive components, and JavaScript widgets such as modals/offcanvas. Site styling extends it with project CSS. |
| **Capacitor** | Wraps the web application in a native Android shell and bridges selected native capabilities. |
| **Capacitor App, Camera, Filesystem, Push Notifications, Share, Status Bar plugins** | Bridge app lifecycle, camera access, local files, native push, the share sheet, and Android status bar behavior when those flows call them. |
| **Service worker / Web App Manifest** | Provides the browser PWA install/offline and caching behavior. These are web platform features implemented in project files, not a separate backend framework. |
| **Chart.js** | Loaded from jsDelivr by the staff dashboard to draw activity charts. It is an optional dashboard visualization dependency. |

### Notifications and account security

| Library or service | What it does here |
| --- | --- |
| **pywebpush + VAPID** | Sends browser push messages to subscribed browsers when keys and delivery settings are configured. |
| **Firebase Admin SDK** | Sends native Android push messages through Firebase Cloud Messaging when Firebase credentials are configured. |
| **PyOTP** | Generates/verifies time-based one-time passwords for two-factor authentication. |
| **PyJWT / Simple JWT** | Token-related packages are present, but JWT authentication is currently commented out in the REST framework settings. Do not assume API access uses JWT; the normal site uses Django session authentication. |

## 6. Where to read next

1. Read [the site overview](site-overview.md) for product boundaries, current limitations, and the system map.
2. Read [the developer guide](developer-guide.md) to run the application locally.
3. Pick the feature guide from [the app index](apps/README.md), then trace that app's URL to its view/service/model.
4. For assistant changes, read [the Pwanimate app guide](apps/pwanimate.md), then start at `pwanimate/api/views.py` for API entry points and `pwanimate/orchestrator/service.py` for response coordination.
5. Check `pwaninet/settings/base.py` for the active configuration and the environment example for setting names. Secrets and live production values are not documented in this guide.

## 7. A few concepts to keep straight

- **An app is a code boundary**, not a separate deployed service. Most folders are Django apps in one project and one deployment.
- **A model is saved data; a service is behavior.** Models describe records and relationships. Services coordinate multi-step work; tasks move slow work to Celery.
- **A route is an entry point.** Root URLs decide which app receives a page/API request. WebSocket routes are configured through ASGI/Channels separately.
- **A provider is an external dependency.** Pwanimate can have adapter code for a provider without that provider being active. Check settings, credentials, and runtime environment.
- **A source document is not the same as an embedding.** Ingestion extracts and chunks content; embeddings are a searchable numeric representation of those chunks. Both still need access and source filters.
- **A configured integration is not proof of production use.** Verify production environment, process topology, and service credentials before making claims about live behavior.
