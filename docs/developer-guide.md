# PwaniNet Developer Guide

This guide takes a new developer from a clean clone to a local development server. It also explains the main services and where application code lives. Commands assume a terminal opened at the repository root.

## 1. Technology stack

- **Python 3.11+** runs the Django application. Python packages are pinned or constrained in `requirements.txt`.
- **Django 5.2** handles routing, views, templates, ORM, authentication, and migrations.
- **PostgreSQL** is the primary database. The Docker Compose image is `pgvector/pgvector:pg15`.
- **Redis 7** supports configured caching, Django Channels, and Celery services.
- **Celery 5** runs background tasks. Celery Beat is used for scheduled jobs where configured.
- **Django Channels + Daphne** provide the ASGI/WebSocket path. The Dockerfile starts Daphne.
- **Gunicorn** is installed and can serve the WSGI entry point, but the repository does not currently use it in its Dockerfile. Confirm the live host's process command before describing it as the deployed server.
- **Django templates, JavaScript, CSS, HTMX, and Bootstrap** make up the web UI.
- **Django REST Framework and drf-spectacular** provide the JSON API layer and generated OpenAPI documentation.
- **Pwanimate's AI and retrieval code** uses `requests` for provider APIs, `pgvector` with PostgreSQL for semantic retrieval, and PyMuPDF/python-docx/python-pptx for reading uploaded reference files. It has custom provider adapters rather than a runtime LangChain/OpenAI SDK dependency.
- **Pwanimate's browser renderer** uses local Marked, DOMPurify, KaTeX, and Prism assets for Markdown, safe HTML, math, and code formatting.
- **Capacitor and Android Gradle** provide the Android wrapper.
- **Cloudflare R2/CDN** is an optional configured storage backend for uploads; actual production use depends on environment configuration.

## 2. Clone the repository

Use the repository URL and access method supplied by the project owner:

```bash
git clone <repository-url>
cd pwaninet
```

If the project is already cloned, change to its root directory. You should see `manage.py`, `requirements.txt`, `pwaninet/`, and app folders such as `users/` and `posts/`.

## 3. Prepare local tools

Install Python 3.11 or newer, Git, Docker with the Compose plugin, and Node.js only if you need to work with the Capacitor/Android wrapper. Android development also requires Android Studio and an Android SDK.

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Configure environment variables

Copy `.env.example` to `.env` and edit the local values. Keep `.env` private; it is ignored by Git. Do not paste production credentials into the example file or commit them.

For the local database container, Compose reads `DB_NAME`, `DB_USER`, and `DB_PASSWORD` from `.env` and uses safe local defaults if they are absent. The Django process runs on your host, so set `DB_HOST=127.0.0.1` (or `localhost`) and `DB_PORT=5432`. For local Redis, use `redis://127.0.0.1:6379/1` for the configured cache URL and `redis://127.0.0.1:6379/0` for Celery broker/result settings.

Generate a fresh local Django `SECRET_KEY`; never reuse a production key. Keep optional email, push, Firebase, R2, and AI credentials blank unless the feature is being developed and you have credentials for it. Local email defaults to Django's console backend in the settings.

`manage.py` defaults to `pwaninet.settings.base`. For normal local development, explicitly select the development module in each Django command:

```bash
python manage.py check --settings=pwaninet.settings.local
```

When starting Celery, set `DJANGO_SETTINGS_MODULE=pwaninet.settings.local` in that terminal or command environment. The Celery bootstrap otherwise defaults to local unless `DJANGO_ENV=production` is set.

## 5. Start PostgreSQL and Redis

The checked-in `docker-compose.yml` starts only PostgreSQL and Redis; it does not start Django or Celery services.

```bash
docker compose up -d db redis
```

To stop those local services:

```bash
docker compose down
```

The named PostgreSQL volume persists database data. Do not add `-v` unless you intentionally want to delete the local database volume.

## 6. Prepare the database and run the site

Apply migrations:

```bash
python manage.py migrate --settings=pwaninet.settings.local
```

Create a local admin account if needed:

```bash
python manage.py createsuperuser --settings=pwaninet.settings.local
```

Start Django:

```bash
python manage.py runserver 127.0.0.1:8000 --settings=pwaninet.settings.local
```

Open `http://127.0.0.1:8000/`. The admin site is at `/admin/`.

## 7. Background workers and real-time features

Celery tasks run outside the web process. Start a worker in another terminal after activating the virtual environment and setting local settings:

Linux/macOS:

```bash
export DJANGO_SETTINGS_MODULE=pwaninet.settings.local
celery -A pwaninet worker -l info
```

Windows PowerShell:

```powershell
$env:DJANGO_SETTINGS_MODULE = "pwaninet.settings.local"
celery -A pwaninet worker -l info
```

Some tasks are routed to named queues in `pwaninet/settings/base.py`; check that configuration when a task appears not to run. Scheduled jobs require Celery Beat, which is a separate process:

```bash
celery -A pwaninet beat -l info
```

The repository Dockerfile starts Daphne and the ASGI application, which routes HTTP through Django and WebSocket traffic through Channels. The compose file does not launch Daphne. For a simple local page workflow, `runserver` is sufficient; use the ASGI server when working on WebSocket behavior.

## 8. Static assets and uploaded media

- Edit source CSS, JavaScript, fonts, and interface images under `static/`. These source files are part of the app and should be version-controlled unless the project intentionally moves them to a separately managed asset pipeline.
- `STATIC_ROOT` is `staticfiles/`. `collectstatic` generates this deployable copy; do not edit it or commit it.
- The current Dockerfile runs `collectstatic` during image build, so the build needs access to the tracked `static/` source tree. If the decision is to keep all static source assets out of GitHub, configure and document an asset upload/CDN build step before untracking those files.
- `media/` is local upload storage and is ignored by Git. Do not add user uploads, generated previews, or database media to the repository.
- Settings support Cloudflare R2 via `django-storages` and Boto3 when `USE_S3=1`. The default is local filesystem storage. Confirm production variables, bucket permissions, CDN domain, and private-document settings before assuming uploads go to the CDN.
- The `private_media/` tree may contain non-public documents. Never commit it. Local private files should be ignored even when testing storage code.

## 9. Android wrapper

The Capacitor configuration is in `capacitor.config.json`; native Android project files are in `android/`. The project package scripts include `npm run cap:open` to open Android Studio (with a configured local Android Studio path). Android SDK files, Gradle caches, build output, signing keys, and local properties must not be committed. Follow the Android setup requirements from the installed Capacitor and Android tooling before building.

## 10. Useful commands

```bash
# Django system checks
python manage.py check --settings=pwaninet.settings.local

# Database migrations
python manage.py makemigrations --settings=pwaninet.settings.local
python manage.py migrate --settings=pwaninet.settings.local

# Gather static assets for a deployment build
python manage.py collectstatic --noinput --settings=pwaninet.settings.local

# Run the Django test suite when requested for a code change
python manage.py test --settings=pwaninet.settings.local
```

Run migrations only when you understand the schema change. Do not run commands against production without the deployment owner's process and authorization.

## 11. How to find your way around

- `pwaninet/`: project settings, top-level URLs, ASGI/WSGI, Channels routing, and Celery setup.
- Each first-party Django app has its own models, views, URLs, templates, and services. See [the app guide index](apps/README.md).
- `static/`: source frontend assets.
- `templates/`: shared Django templates.
- `android/`: Capacitor Android project.
- `docs/pre-launch/`: About and Privacy drafts plus an internal launch checklist.
- `scripts/`: maintained operational scripts and clearly labeled historical diagnostics/one-off edits.
- `tests/legacy/` and `tests/manual/`: older standalone checks and manual debug pages; these are not guaranteed to be part of the maintained app test suite.

## 12. Before opening a change

Keep changes within the responsible app, update migrations when models change, and update the relevant documentation when behavior or setup changes. Never commit local environment files, private uploads, logs, database dumps, generated static output, or signing keys. Do not assume that a feature is active in production just because its code or environment variables exist.
