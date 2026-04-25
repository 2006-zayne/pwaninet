# Project Structure

Complete file structure of the Pwaninet Django project after domain-driven architecture refactoring.

```
pwaninet/
│
├── .dockerignore              # Docker ignore file
├── .env                       # Environment variables (local)
├── .env.example               # Environment variables template
├── .git/                      # Git repository
├── .gitignore                 # Git ignore rules
├── ARCHITECTURE.md            # Architecture documentation
├── Dockerfile                 # Docker image configuration
├── MIGRATION_GUIDE.md         # Migration and setup guide
├── docker-compose.yml         # Docker Compose configuration
├── manage.py                  # Django management script
├── migrate_data.py            # Data migration script
├── requirements.txt           # Python dependencies
│
├── core/                      # Legacy app (views, forms, URLs)
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── context_processors.py
│   ├── forms.py               # All form classes
│   ├── models.py              # Legacy models (deprecated)
│   ├── projects.code-workspace
│   ├── signals.py
│   ├── urls.py                # Core URLs (register, logout)
│   ├── validators.py
│   ├── views.py               # All view functions
│   │
│   ├── management/            # Django management commands
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── populate_units.py
│   │       └── seed_social.py
│   │
│   ├── migrations/            # Database migrations (legacy)
│   │   ├── __init__.py
│   │   └── [migration files...]
│   │
│   ├── queries/               # Legacy queries (moved to domain apps)
│   │   ├── __init__.py
│   │   ├── comment_queries.py
│   │   ├── feed_queries.py
│   │   ├── group_queries.py
│   │   ├── notification_queries.py
│   │   ├── profile_queries.py
│   │   └── search_queries.py
│   │
│   ├── services/              # Legacy services (moved to domain apps)
│   │   ├── __init__.py
│   │   ├── comment_service.py
│   │   ├── feed_service.py
│   │   ├── friend_suggestion_service.py
│   │   ├── group_service.py
│   │   ├── notification_service.py
│   │   ├── post_service.py
│   │   ├── profile_service.py
│   │   └── search_service.py
│   │
│   └── __pycache__/           # Python cache files
│
├── users/                     # User domain app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # User, Follow models
│   ├── urls.py                # User-related URLs
│   │
│   ├── migrations/            # User app migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   └── __pycache__/
│   │
│   ├── queries/               # User query functions
│   │   ├── __init__.py
│   │   └── profile_queries.py
│   │
│   ├── services/              # User service functions
│   │   ├── __init__.py
│   │   ├── profile_service.py
│   │   ├── friend_suggestion_service.py
│   │   └── search_service.py
│   │
│   └── __pycache__/
│
├── posts/                     # Posts domain app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # Post, Like, Comment, CommentLike models
│   ├── urls.py                # Post-related URLs
│   │
│   ├── migrations/            # Posts app migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   └── __pycache__/
│   │
│   ├── queries/               # Post query functions
│   │   ├── __init__.py
│   │   ├── feed_queries.py
│   │   ├── comment_queries.py
│   │   └── search_queries.py
│   │
│   ├── services/              # Post service functions
│   │   ├── __init__.py
│   │   ├── post_service.py
│   │   ├── comment_service.py
│   │   └── feed_service.py
│   │
│   └── __pycache__/
│
├── groups/                    # Groups domain app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # Groups model
│   ├── urls.py                # Group-related URLs
│   │
│   ├── migrations/            # Groups app migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   └── __pycache__/
│   │
│   ├── queries/               # Group query functions
│   │   ├── __init__.py
│   │   └── group_queries.py
│   │
│   ├── services/              # Group service functions
│   │   ├── __init__.py
│   │   └── group_service.py
│   │
│   └── __pycache__/
│
├── notifications/             # Notifications domain app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # Notifications model
│   ├── urls.py                # Notification-related URLs
│   │
│   ├── migrations/            # Notifications app migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   ├── 0002_initial.py
│   │   ├── 0003_initial.py
│   │   └── __pycache__/
│   │
│   ├── queries/               # Notification query functions
│   │   ├── __init__.py
│   │   └── notification_queries.py
│   │
│   ├── services/              # Notification service functions
│   │   ├── __init__.py
│   │   └── notification_service.py
│   │
│   └── __pycache__/
│
├── courses/                   # Courses domain app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py              # Course, Year, Unit models
│   ├── urls.py                # Course-related URLs
│   │
│   ├── migrations/            # Courses app migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py
│   │   └── __pycache__/
│   │
│   ├── queries/               # Course query functions (to be added)
│   │   └── __init__.py
│   │
│   ├── services/              # Course service functions (to be added)
│   │   └── __init__.py
│   │
│   └── __pycache__/
│
├── pwaninet/                  # Project configuration
│   ├── __init__.py            # Celery app initialization
│   ├── asgi.py                # ASGI configuration
│   ├── celery.py              # Celery configuration
│   ├── settings.py            # Legacy settings file (deprecated)
│   ├── urls.py                # Main URL configuration
│   ├── wsgi.py                # WSGI configuration
│   │
│   ├── settings/              # Environment-based settings
│   │   ├── __init__.py        # Settings loader
│   │   ├── base.py            # Base/common settings
│   │   ├── local.py           # Development settings
│   │   └── production.py      # Production settings
│   │
│   └── __pycache__/
│
├── static/                    # Static files
│   ├── css/
│   ├── img/
│   ├── js/
│   └── vendor/
│
├── staticfiles/               # Collected static files
│   └── [collected static assets...]
│
├── media/                     # User-uploaded media files
├── logs/                      # Application logs directory
├── loadtesting/               # Load testing directory
│
├── db.sqlite3                 # SQLite database (development)
└── db.sqlite3.backup          # Database backup
```

## File Descriptions

### Root Configuration Files

- **.dockerignore**: Specifies files to exclude from Docker builds
- **.env**: Local environment variables (not committed to git)
- **.env.example**: Template for environment variables
- **.gitignore**: Git ignore patterns
- **ARCHITECTURE.md**: Documentation of the new domain-driven architecture
- **Dockerfile**: Docker image build instructions
- **MIGRATION_GUIDE.md**: Migration instructions and Docker setup guide
- **docker-compose.yml**: Multi-container Docker application configuration
- **manage.py**: Django's command-line utility
- **migrate_data.py**: Script to migrate data from old to new schema
- **requirements.txt**: Python package dependencies

### Domain Apps

#### users/
- **Purpose**: User authentication, profiles, and follow relationships
- **Models**: User, Follow
- **Services**: profile_service, friend_suggestion_service, search_service
- **Queries**: profile_queries
- **URLs**: profile, update_profile, toggle_follow

#### posts/
- **Purpose**: Content creation and engagement
- **Models**: Post, Like, Comment, CommentLike
- **Services**: post_service, comment_service, feed_service
- **Queries**: feed_queries, comment_queries, search_queries
- **URLs**: home, create_post, post_detail, toggle_like, add_comment, toggle_comment_like, post_likers_list, unit_detail, search

#### groups/
- **Purpose**: Group management and membership
- **Models**: Groups
- **Services**: group_service
- **Queries**: group_queries
- **URLs**: groups_dashboard, groups_detail, create_group, toggle_membership, edit_group, invite_to_group, respond_to_invite

#### notifications/
- **Purpose**: Notification delivery and tracking
- **Models**: Notifications
- **Services**: notification_service
- **Queries**: notification_queries
- **URLs**: notifications, unread_count, mark_as_read, mark_notification_as_read

#### courses/
- **Purpose**: Academic structure management
- **Models**: Course, Year, Unit
- **Services**: (to be added)
- **Queries**: (to be added)
- **URLs**: load_years

### Legacy App (core/)

Contains views, forms, and URLs that haven't been migrated to domain apps yet. This app will be gradually phased out as components are moved to their respective domain apps.

- **views.py**: All view functions (to be migrated to domain apps)
- **forms.py**: All form classes (to be migrated to domain apps)
- **urls.py**: Core URLs (register, logout)

### Project Configuration (pwaninet/)

- **settings/__init__.py**: Settings loader that imports base, then local/production
- **settings/base.py**: Common settings shared across environments
- **settings/local.py**: Development-specific settings (SQLite, DEBUG=True)
- **settings/production.py**: Production-specific settings (PostgreSQL, security, logging)
- **celery.py**: Celery application configuration
- **urls.py**: Main URL configuration including all domain app URLs

### Static and Media Files

- **static/**: Source static files (CSS, JS, images)
- **staticfiles/**: Collected static files for production
- **media/**: User-uploaded media files

### Database Files

- **db.sqlite3**: SQLite database for development
- **db.sqlite3.backup**: Backup of original database before migration

## Migration Status

### Completed
- ✅ Domain app structure created
- ✅ Models moved to domain apps
- ✅ Services moved to domain apps
- ✅ Queries moved to domain apps
- ✅ URLs reorganized by domain
- ✅ Environment-based settings implemented
- ✅ PostgreSQL and Redis configured
- ✅ Django REST Framework added
- ✅ Celery configured
- ✅ Docker setup completed

### Pending
- ⏳ Move views from core to domain apps
- ⏳ Move forms from core to domain apps
- ⏳ Remove core app after complete migration
- ⏳ Add admin.py for each domain app
- ⏳ Create DRF serializers and viewsets for APIs
- ⏳ Add tests for domain apps
