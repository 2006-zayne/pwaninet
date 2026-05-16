# Project Migration & Setup Guide

## Overview

This document describes the migration from a monolithic `core` app to a domain-driven architecture and provides setup instructions for Docker and the new application structure.

## Architecture Changes

### Old Structure
```
pwaninet/
├── core/
│   ├── models.py (all models)
│   ├── services/ (all services)
│   ├── queries/ (all queries)
│   ├── views.py
│   ├── urls.py
│   └── forms.py
├── pwaninet/
│   └── settings.py (monolithic settings)
```

### New Structure
```
pwaninet/
├── courses/          # Course, Year, Unit models
├── users/            # User, Follow models + services/queries
├── posts/            # Post, Like, Comment, CommentLike models + services/queries
├── groups/           # Groups model + services/queries
├── notifications/    # Notifications model + services/queries
├── core/             # Legacy app (forms, views, urls - to be refactored)
├── pwaninet/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py       # Common settings
│   │   ├── local.py      # Development settings (SQLite)
│   │   └── production.py # Production settings (PostgreSQL)
│   ├── celery.py
│   └── urls.py
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Domain Boundaries

### Users App (`users/`)
- **Models**: User, Follow
- **Responsibilities**: User authentication, profile management, follow relationships
- **Services**: profile_service, friend_suggestion_service, search_service
- **Queries**: profile_queries

### Posts App (`posts/`)
- **Models**: Post, Like, Comment, CommentLike
- **Responsibilities**: Content creation, engagement (likes, comments)
- **Services**: post_service, comment_service, feed_service
- **Queries**: feed_queries, comment_queries, search_queries

### Groups App (`groups/`)
- **Models**: Groups
- **Responsibilities**: Group management, membership
- **Services**: group_service
- **Queries**: group_queries

### Notifications App (`notifications/`)
- **Models**: Notifications
- **Responsibilities**: Notification delivery, read/unread tracking
- **Services**: notification_service
- **Queries**: notification_queries

### Courses App (`courses/`)
- **Models**: Course, Year, Unit
- **Responsibilities**: Academic structure management
- **Services**: (to be added)
- **Queries**: (to be added)

## Environment-Based Settings

### Development (local.py)
```python
DEBUG = True
DATABASE = SQLite (db.sqlite3)
ALLOWED_HOSTS = localhost, 127.0.0.1, 0.0.0.0
```

### Production (production.py)
```python
DEBUG = False
DATABASE = PostgreSQL
ALLOWED_HOSTS = from environment variable
Security: SSL, HSTS, secure cookies enabled
Logging: File-based logging to logs/django.log
```

## Docker Setup

### Prerequisites
- Docker installed
- Docker Compose installed

### Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL for production)
DB_NAME=pwaninet
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

# Redis (for caching)
REDIS_URL=redis://localhost:6379/1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Docker Compose Services

The `docker-compose.yml` includes:

1. **web**: Django application
   - Port: 8000
   - Depends on: db, redis
   - Volumes: code, media, static

2. **db**: PostgreSQL database
   - Port: 5432
   - Environment: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
   - Volume: postgres_data

3. **redis**: Redis server
   - Port: 6379
   - Volume: redis_data

4. **celery**: Celery worker
   - Command: celery -A pwaninet worker -l info
   - Depends on: db, redis

5. **celery-beat**: Celery beat scheduler
   - Command: celery -A pwaninet beat -l info
   - Depends on: db, redis

### Running with Docker

#### Build and start all services:
```bash
docker-compose up --build
```

#### Start services in detached mode:
```bash
docker-compose up -d
```

#### Stop services:
```bash
docker-compose down
```

#### View logs:
```bash
docker-compose logs -f
```

#### Run Django management commands:
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
```

## Local Development Setup (without Docker)

### Prerequisites
- Python 3.12+
- Virtual environment

### Setup Steps

1. **Create and activate virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Run migrations:**
```bash
python manage.py migrate
```

5. **Create superuser:**
```bash
python manage.py createsuperuser
```

6. **Start development server:**
```bash
python manage.py runserver
```

7. **Start Celery worker (optional):**
```bash
celery -A pwaninet worker -l info
```

8. **Start Celery beat (optional):**
```bash
celery -A pwaninet beat -l info
```

## Database Migration Notes

### Fresh Installation
For new installations, the database will use the new domain-driven schema automatically when migrations are run.

### Data Migration from Old Schema
The project includes a data migration script (`migrate_data.py`) to copy data from the old `core` models to the new domain models. However, due to the User model change from `core.User` to `users.User`, a fresh database setup is recommended.

If you need to migrate existing data:

1. Backup your current database:
```bash
cp db.sqlite3 db.sqlite3.backup
```

2. Restore the backup:
```bash
cp db.sqlite3.backup db.sqlite3
```

3. Run the migration script:
```bash
python migrate_data.py
```

Note: Data migration may require manual adjustments depending on your specific data and relationships.

## Technology Stack

- **Django 6.0.3**: Web framework
- **PostgreSQL**: Production database
- **SQLite**: Development database
- **Redis**: Caching and Celery broker
- **Celery**: Asynchronous task processing
- **Django REST Framework**: API layer
- **django-cors-headers**: CORS handling
- **Whitenoise**: Static file serving
- **Docker**: Containerization

## Security Considerations

### Production Checklist
- [ ] Set `DEBUG = False` in production settings
- [ ] Set a strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Use HTTPS with SSL
- [ ] Set secure cookie flags
- [ ] Configure PostgreSQL with strong password
- [ ] Restrict Redis access
- [ ] Set up proper logging
- [ ] Configure firewall rules
- [ ] Regular database backups

## Troubleshooting

### Migration Errors
If you encounter migration conflicts:
```bash
# Delete database and start fresh
rm db.sqlite3
python manage.py migrate
```

### Docker Issues
```bash
# Rebuild containers
docker-compose down
docker-compose up --build

# Check logs
docker-compose logs web
docker-compose logs db
docker-compose logs redis
```

### Celery Issues
```bash
# Check if Redis is running
docker-compose logs redis

# Restart Celery worker
docker-compose restart celery
```

## Next Steps

1. **Refactor core app**: Move remaining views and forms to appropriate domain apps
2. **Create admin interfaces**: Add admin.py for each domain app
3. **Add API endpoints**: Create DRF serializers and viewsets for each domain
4. **Add tests**: Write unit and integration tests for domain apps
5. **Set up CI/CD**: Configure automated testing and deployment
6. **Performance monitoring**: Add logging and monitoring tools

## Support

For issues or questions about this migration, refer to the `ARCHITECTURE.md` file for detailed architectural decisions.
