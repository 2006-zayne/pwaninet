# Pwaninet v0.97 Architecture

## Overview
Pwaninet v0.97 represents a clean, domain-driven architecture with complete separation of concerns. The legacy `core` app has been fully migrated and removed, resulting in a pure domain-based structure.

---

## Project Structure

```
pwaninet/
├── pwaninet/                    # Project configuration
│   ├── settings/
│   │   ├── __init__.py         # Settings loader
│   │   ├── base.py             # Base settings
│   │   ├── local.py            # Development settings
│   │   └── production.py       # Production settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI entry point
│   ├── asgi.py                 # ASGI entry point
│   ├── cache_backends.py       # Custom cache backends
│   └── celery.py               # Celery configuration
│
├── courses/                     # Courses domain
│   ├── __init__.py
│   ├── admin.py                # Admin configuration
│   ├── apps.py                 # App configuration
│   ├── models.py               # Course, Year, Unit models
│   ├── urls.py                 # Course URLs
│   ├── views.py                # Course views
│   ├── migrations/             # Database migrations
│   └── templates/              # Course templates
│
├── users/                       # Users domain
│   ├── __init__.py
│   ├── admin.py                # User admin configuration
│   ├── apps.py                 # App configuration (imports signals)
│   ├── forms.py                # User forms
│   ├── models.py               # User, Follow, DeviceAccount models
│   ├── urls.py                 # User URLs (register, logout, profile)
│   ├── views.py                # User views
│   ├── signals.py              # User signals (login, logout, auto-join)
│   ├── migrations/             # Database migrations
│   ├── queries/                # User database queries
│   │   ├── __init__.py
│   │   └── user_queries.py
│   ├── services/               # User business logic
│   │   ├── __init__.py
│   │   ├── device_service.py
│   │   ├── feed_service.py
│   │   ├── friend_suggestion_service.py
│   │   ├── notification_preferences_service.py
│   │   ├── profile_service.py
│   │   └── search_service.py
│   └── templates/              # User templates
│
├── posts/                       # Posts domain
│   ├── __init__.py
│   ├── admin.py                # Post admin configuration
│   ├── apps.py                 # App configuration
│   ├── forms.py                # Post forms
│   ├── models.py               # Post, Like, Comment, Repost models
│   ├── urls.py                 # Post URLs
│   ├── views.py                # Post views
│   ├── validators.py           # File size validators
│   ├── permissions.py          # Post permissions
│   ├── serializers.py          # DRF serializers
│   ├── migrations/             # Database migrations
│   ├── queries/                # Post database queries
│   │   ├── __init__.py
│   │   ├── post_queries.py
│   │   └── feed_queries.py
│   ├── services/               # Post business logic
│   │   ├── __init__.py
│   │   ├── author_preference_service.py
│   │   ├── feed_service.py
│   │   ├── hide_service.py
│   │   ├── post_service.py
│   │   ├── repost_service.py
│   │   └── share_service.py
│   └── templates/              # Post templates
│
├── groups/                      # Groups domain
│   ├── __init__.py
│   ├── admin.py                # Group admin configuration
│   ├── apps.py                 # App configuration
│   ├── forms.py                # Group forms
│   ├── models.py               # Group, Membership models
│   ├── urls.py                 # Group URLs
│   ├── views.py                # Group views
│   ├── permissions.py          # Group permissions
│   ├── serializers.py          # DRF serializers
│   ├── migrations/             # Database migrations
│   ├── queries/                # Group database queries
│   │   ├── __init__.py
│   │   └── group_queries.py
│   ├── services/               # Group business logic
│   │   ├── __init__.py
│   │   ├── group_notification_service.py
│   │   └── group_service.py
│   ├── templatetags/           # Template tags
│   │   ├── __init__.py
│   │   └── group_extras.py
│   └── templates/              # Group templates
│
├── notifications/               # Notifications domain
│   ├── __init__.py
│   ├── admin.py                # Notification admin configuration
│   ├── apps.py                 # App configuration
│   ├── context_processors.py   # Notification context processor
│   ├── models.py               # Notifications model
│   ├── urls.py                 # Notification URLs
│   ├── views.py                # Notification views
│   ├── signals.py              # Notification signals
│   ├── migrations/             # Database migrations
│   ├── queries/                # Notification database queries
│   │   ├── __init__.py
│   │   └── notification_queries.py
│   ├── services/               # Notification business logic
│   │   ├── __init__.py
│   │   └── notification_service.py
│   └── templates/              # Notification templates
│
├── templates/                   # Global templates
│   ├── base.html               # Base template
│   ├── logout.html             # Logout template
│   ├── partials/               # Partial templates
│   │   └── _form_field.html
│   └── registration/           # Registration templates
│       └── login.html
│
├── static/                      # Static files
│   ├── css/
│   ├── js/
│   └── images/
│
├── media/                       # User uploaded files
│   ├── profile_pic/
│   ├── covers/
│   ├── posts/
│   │   ├── images/
│   │   ├── videos/
│   │   └── docs/
│   └── group_profile_pic/
│
├── staticfiles/                 # Collected static files
├── logs/                        # Application logs
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── ARCHITECTURE_V0.97.md
│   ├── FEATURES.md
│   ├── PREREQUISITES_BEFORE_REELS.md
│   ├── REELS_IMPLEMENTATION_PLAN.md
│   └── ...
│
├── manage.py                    # Django management script
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
├── .env.example                 # Environment variables template
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose configuration
└── .gitignore                   # Git ignore rules
```

---

## Domain Boundaries

### Courses Domain
**Purpose**: Academic structure management

**Models**:
- `Course` - Academic programs (e.g., Computer Science, Business)
- `Year` - Academic years within courses (Year 1, Year 2, etc.)
- `Unit` - Specific subjects/units within course years

**Responsibilities**:
- Manage hierarchical academic structure
- Provide course/year/unit data to other domains
- No dependencies on other domains

**Key Files**:
- `models.py` - Data definitions
- `views.py` - Course listing views
- `admin.py` - Admin interface

---

### Users Domain
**Purpose**: User authentication, profiles, and relationships

**Models**:
- `User` - Custom user model (extends AbstractUser)
- `Follow` - User follow relationships
- `DeviceAccount` - Device tracking for multi-account support

**Responsibilities**:
- User registration and authentication
- Profile management
- Follow/unfollow functionality
- Device account tracking
- Auto-join course groups on registration
- User search and suggestions

**Key Files**:
- `models.py` - User, Follow, DeviceAccount models
- `views.py` - Profile, registration, authentication views
- `signals.py` - Login/logout tracking, auto-join groups
- `services/` - Business logic for user operations
- `queries/` - User database queries

**Dependencies**:
- `courses` - For course/year relationships
- `groups` - For auto-join functionality

---

### Posts Domain
**Purpose**: Content creation and engagement

**Models**:
- `Post` - Main post model
- `PostImage` - Post images
- `Like` - Post likes
- `Comment` - Post comments
- `CommentLike` - Comment likes
- `Repost` - Post reposts
- `Report` - Post reports
- `HiddenPost` - Hidden posts
- `AuthorPreference` - Author visibility preferences
- `SharedPost` - Shared posts between users

**Responsibilities**:
- Post creation (text, images, videos, documents)
- Engagement (likes, comments, shares)
- Feed generation and ranking
- Post visibility and preferences
- Content reporting

**Key Files**:
- `models.py` - All post-related models
- `views.py` - Post creation, feed, engagement views
- `services/` - Feed ranking, post operations
- `queries/` - Post database queries
- `validators.py` - File size validation
- `permissions.py` - Post permissions
- `serializers.py` - DRF serializers

**Dependencies**:
- `users` - Author relationships
- `groups` - Group posts
- `courses` - Course/unit tagging

---

### Groups Domain
**Purpose**: Community management

**Models**:
- `Group` - Group model
- `Membership` - Group membership

**Responsibilities**:
- Group creation and management
- Membership management (roles, status)
- Group content organization
- Group permissions
- Group notifications

**Key Files**:
- `models.py` - Group, Membership models
- `views.py` - Group CRUD, membership views
- `services/` - Group operations, notifications
- `queries/` - Group database queries
- `permissions.py` - Group permissions
- `serializers.py` - DRF serializers
- `templatetags/` - Template tags

**Dependencies**:
- `users` - Group members, creators
- `courses` - Course/year associations

---

### Notifications Domain
**Purpose**: User notifications

**Models**:
- `Notifications` - Notification model

**Responsibilities**:
- Notification creation and delivery
- Notification caching
- Unread count tracking
- Context processor for global notification count

**Key Files**:
- `models.py` - Notifications model
- `views.py` - Notification listing and marking
- `services/` - Notification operations
- `queries/` - Notification database queries
- `context_processors.py` - Global notification count
- `signals.py` - Notification triggers

**Dependencies**:
- `users` - Notification recipients
- `posts` - Post-related notifications
- `groups` - Group-related notifications

---

## Architecture Principles

### 1. Domain-Driven Design (DDD)
Each domain app represents a bounded context with:
- **Models** - Data definitions
- **Services** - Business logic
- **Queries** - Database access
- **Views** - HTTP handlers
- **URLs** - Route definitions
- **Templates** - UI components

### 2. Separation of Concerns
- **Models** contain only data definitions and basic methods
- **Services** contain business logic
- **Queries** contain database access logic
- **Views** orchestrate services and queries
- No cross-domain model imports (use foreign keys)

### 3. Dependency Flow
```
courses (no dependencies)
    ↓
users (depends on courses)
    ↓
groups (depends on users, courses)
    ↓
posts (depends on users, groups, courses)
    ↓
notifications (depends on users, posts, groups)
```

### 4. Configuration Management
- Environment-based settings (local, production)
- Environment variables for sensitive data
- Centralized template directory
- Context processors for global data

---

## URL Structure

### Root URLs (`pwaninet/urls.py`)
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include(('posts.urls', 'posts'), namespace='posts')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('groups/', include(('groups.urls', 'groups'), namespace='groups')),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('courses/', include('courses.urls')),
]
```

### Domain URL Patterns

**Users**:
- `/users/register/` - User registration
- `/users/logout/` - User logout
- `/users/user/<username>/` - User profile
- `/users/profile/edit/` - Edit profile
- `/users/toggle-follow/<username>/` - Follow/unfollow
- `/users/notification-preferences/` - Notification settings
- `/users/accounts/switch/<id>/` - Switch accounts
- `/users/accounts/device-accounts/` - Device accounts
- `/users/accounts/remove/<id>/` - Remove account from device

**Posts**:
- `/` - Home feed
- `/posts/create/` - Create post
- `/posts/<id>/` - Post detail
- `/posts/<id>/like/` - Like/unlike post
- `/posts/<id>/comment/` - Comment on post
- `/posts/<id>/repost/` - Repost
- `/posts/<id>/hide/` - Hide post
- `/posts/<id>/report/` - Report post

**Groups**:
- `/groups/` - Group list
- `/groups/create/` - Create group
- `/groups/<id>/` - Group detail
- `/groups/<id>/join/` - Join group
- `/groups/<id>/leave/` - Leave group
- `/groups/<id>/members/` - Group members
- `/groups/<id>/posts/` - Group posts

**Notifications**:
- `/notifications/` - Notification list
- `/notifications/<id>/read/` - Mark as read
- `/notifications/read-all/` - Mark all as read

**Courses**:
- `/courses/` - Course list
- `/courses/<id>/` - Course detail
- `/courses/<id>/years/` - Course years
- `/courses/<id>/years/<year_id>/units/` - Year units

---

## Database Schema

### Users
- `users_user` - User accounts
- `users_follow` - Follow relationships
- `users_deviceaccount` - Device tracking

### Courses
- `courses_course` - Academic courses
- `courses_year` - Academic years
- `courses_unit` - Course units

### Posts
- `posts_post` - Posts
- `posts_postimage` - Post images
- `posts_like` - Post likes
- `posts_comment` - Post comments
- `posts_commentlike` - Comment likes
- `posts_repost` - Reposts
- `posts_report` - Post reports
- `posts_hiddenpost` - Hidden posts
- `posts_authorpreference` - Author preferences
- `posts_sharedpost` - Shared posts

### Groups
- `groups_group` - Groups
- `groups_membership` - Group memberships

### Notifications
- `notifications_notifications` - Notifications

---

## Technology Stack

### Backend
- **Framework**: Django 5.2.13
- **Language**: Python 3.11
- **Database**: PostgreSQL (production), SQLite (development)
- **Cache**: Redis 7
- **Task Queue**: Celery 5.3.4
- **API**: Django REST Framework 3.14.0

### Frontend
- **Templates**: Django Templates
- **CSS**: Bootstrap 5, Custom CSS
- **JavaScript**: HTMX, Vanilla JS
- **Icons**: Bootstrap Icons

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Web Server**: Gunicorn
- **Static Files**: WhiteNoise
- **Media Storage**: Local (development), S3 (planned)

---

## Settings Configuration

### Base Settings (`pwaninet/settings/base.py`)
- INSTALLED_APPS - Domain apps only (no core)
- TEMPLATES - Global templates directory
- Context processors - Notifications context processor
- Database - PostgreSQL configuration
- Cache - Redis with fallback
- REST Framework - Session authentication

### Local Settings (`pwaninet/settings/local.py`)
- DEBUG = True
- SQLite database
- Local Redis
- CORS for development

### Production Settings (`pwaninet/settings/production.py`)
- DEBUG = False
- PostgreSQL database
- Production Redis
- Security headers
- Logging configuration

---

## Signal Architecture

### Users Signals (`users/signals.py`)
- `user_logged_in` - Track device on login
- `user_logged_out` - Clear session on logout
- `post_save (User)` - Auto-join course groups

### Notifications Signals (`notifications/signals.py`)
- Post creation notifications
- Like notifications
- Comment notifications
- Follow notifications
- Group notifications

---

## Service Layer Architecture

### Users Services
- `device_service.py` - Device ID management
- `feed_service.py` - User feed generation
- `friend_suggestion_service.py` - Follow suggestions
- `notification_preferences_service.py` - Notification settings
- `profile_service.py` - Profile operations
- `search_service.py` - User search

### Posts Services
- `author_preference_service.py` - Author visibility
- `feed_service.py` - Post feed ranking
- `hide_service.py` - Hide posts
- `post_service.py` - Post operations
- `repost_service.py` - Repost operations
- `share_service.py` - Share posts

### Groups Services
- `group_service.py` - Group operations
- `group_notification_service.py` - Group notifications

### Notifications Services
- `notification_service.py` - Notification operations

---

## Query Layer Architecture

### Users Queries
- `user_queries.py` - User database queries

### Posts Queries
- `post_queries.py` - Post database queries
- `feed_queries.py` - Feed database queries

### Groups Queries
- `group_queries.py` - Group database queries

### Notifications Queries
- `notification_queries.py` - Notification database queries

---

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
- ✅ Feed ranking system with cursor-based pagination
- ✅ Core app fully migrated and removed
- ✅ Admin configurations distributed to domain apps
- ✅ Validators moved to posts domain
- ✅ Context processors moved to notifications domain
- ✅ Signals consolidated in users domain
- ✅ Templates moved to global directory

### No Legacy Code
- ❌ No core app
- ❌ No cross-domain imports
- ❌ No legacy views
- ❌ No legacy forms
- ❌ No legacy templates

---

## Performance Optimizations

### Database
- Indexed foreign keys
- Indexed created_at fields
- Indexed frequently queried fields
- select_related for foreign keys
- prefetch_related for many-to-many
- Cursor-based pagination for feeds

### Caching
- Redis for notification counts (30-second TTL)
- Redis for feed results (5-minute TTL)
- Fallback to local memory cache

### Background Tasks
- Celery for async operations
- Celery Beat for scheduled tasks

---

## Security Features

### Authentication
- Custom User model
- Session-based authentication
- Device account tracking
- CSRF protection

### Authorization
- Custom permissions per domain
- Role-based access (groups)
- Object-level permissions

### Data Validation
- File size validators
- Content type validation
- Form validation

### Headers
- CORS headers
- XSS protection
- Clickjacking protection

---

## Deployment Architecture

### Development
```yaml
Services:
  - db (PostgreSQL)
  - redis (Redis)
  - web (Django dev server)
  - celery (Celery worker)
  - celery-beat (Celery beat scheduler)
```

### Production (Planned)
```yaml
Services:
  - db (PostgreSQL with read replicas)
  - redis (Redis Cluster)
  - web (Gunicorn with multiple workers)
  - celery (Multiple Celery workers)
  - celery-beat (Celery beat scheduler)
  - nginx (Reverse proxy and static file serving)
  - cdn (CloudFront for static/media)
  - s3 (S3 for media storage)
```

---

## Monitoring & Logging

### Logging
- Structured logging with log levels
- Separate log files per domain
- Log rotation

### Monitoring (Planned)
- Error tracking (Sentry)
- Performance monitoring (New Relic)
- Health checks
- Metrics collection

---

## API Layer (DRF)

### Serializers
- `posts/serializers.py` - Post serializers
- `groups/serializers.py` - Group serializers
- Planned: User, Notification, Course serializers

### Authentication
- Session authentication
- Basic authentication
- Planned: JWT authentication

### Permissions
- `posts/permissions.py` - Post permissions
- `groups/permissions.py` - Group permissions
- IsAuthenticated default

---

## Future Enhancements

### Planned Features
- REST API completion
- Real-time features (WebSockets)
- Messaging system
- Reels feature (documented in REELS_IMPLEMENTATION_PLAN.md)
- Enhanced search (Elasticsearch)
- Mobile app (React Native)

### Architecture Improvements
- Microservices migration (documented in MICROSERVICES_IMPLEMENTATION.md)
- Event-driven architecture
- API gateway
- Service mesh

---

## Version History

### v0.97 (Current)
- Removed core app completely
- Migrated all components to domain apps
- Clean domain-driven architecture
- No legacy code
- All domain apps have admin.py
- Validators in posts domain
- Context processors in notifications domain
- Signals in users domain
- Templates in global directory

### v0.96
- Partial core migration
- Some components still in core

### v0.95
- Initial domain structure
- Core app still present

---

## Conclusion

Pwaninet v0.97 represents a clean, mature architecture following domain-driven design principles. All legacy code has been removed, and the codebase is organized into clear domain boundaries with proper separation of concerns. The architecture is ready for scaling and future enhancements including the planned Reels feature.

**Key Achievements**:
- ✅ Pure domain-driven design
- ✅ No legacy code
- ✅ Clear separation of concerns
- ✅ Proper dependency flow
- ✅ Scalable architecture
- ✅ Ready for new features

**Next Steps**:
1. Complete REST API layer
2. Add comprehensive testing
3. Implement real-time features
4. Add Reels feature (per implementation plan)
