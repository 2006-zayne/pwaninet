# Pwaninet Architecture Guide

## Overview
This project has been restructured for scalability using domain-driven design principles.

## Project Structure

```
pwaninet/
├── pwaninet/
│   ├── settings/
│   │   ├── __init__.py      # Settings loader
│   │   ├── base.py          # Base settings
│   │   ├── local.py         # Development settings
│   │   └── production.py    # Production settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── courses/                 # Course management domain
│   ├── models.py            # Course, Year, Unit
│   ├── services/            # Business logic
│   ├── queries/             # Database queries
│   └── migrations/
├── users/                   # User management domain
│   ├── models.py            # User, Follow
│   ├── services/            # Business logic
│   ├── queries/             # Database queries
│   └── migrations/
├── posts/                   # Posts domain
│   ├── models.py            # Post, Like, Comment, CommentLike
│   ├── services/            # Business logic
│   ├── queries/             # Database queries
│   └── migrations/
├── groups/                  # Groups domain
│   ├── models.py            # Groups
│   ├── services/            # Business logic
│   ├── queries/             # Database queries
│   └── migrations/
├── notifications/           # Notifications domain
│   ├── models.py            # Notifications
│   ├── services/            # Business logic
│   ├── queries/             # Database queries
│   └── migrations/
├── core/                    # Legacy app (to be deprecated)
│   ├── models.py            # Old models
│   ├── views.py             # Old views
│   ├── services/            # Old services
│   └── queries/             # Old queries
├── static/
├── media/
├── logs/
└── manage.py
```

## Domain Boundaries

### Courses Domain
- **Models**: Course, Year, Unit
- **Responsibilities**: Academic structure management
- **Dependencies**: None

### Users Domain
- **Models**: User, Follow
- **Responsibilities**: User authentication, profiles, relationships
- **Dependencies**: courses (for year/course relationships)

### Posts Domain
- **Models**: Post, Like, Comment, CommentLike
- **Responsibilities**: Content creation, engagement
- **Dependencies**: users, groups, courses

### Groups Domain
- **Models**: Groups
- **Responsibilities**: Community management
- **Dependencies**: users

### Notifications Domain
- **Models**: Notifications
- **Responsibilities**: User notifications
- **Dependencies**: users, posts, groups

## Migration Strategy

### Phase 1: Setup (Complete)
- ✓ Created environment-based settings
- ✓ Created domain-driven app structure
- ✓ Updated requirements.txt

### Phase 2: Data Migration
1. Create migrations for new apps
2. Migrate data from core models to new domain models
3. Update foreign keys and relationships
4. Test data integrity

### Phase 3: Code Migration
1. Move services to respective domain apps
2. Move queries to respective domain apps
3. Update views to use new models
4. Update URLs to point to new views
5. Update templates

### Phase 4: Cleanup
1. Remove core app
2. Remove old migrations
3. Update documentation

## Environment Configuration

### Development
```bash
cp .env.example .env
# Edit .env with your settings
export DJANGO_SETTINGS_MODULE=pwaninet.settings.local
```

### Production
```bash
# Set environment variables
export DJANGO_SETTINGS_MODULE=pwaninet.settings.production
export SECRET_KEY=your-production-secret-key
export DB_NAME=your-db-name
export DB_USER=your-db-user
export DB_PASSWORD=your-db-password
export DB_HOST=your-db-host
export DB_PORT=5432
```

## Scalability Features

### Database
- **Development**: SQLite
- **Production**: PostgreSQL (configured in production.py)

### Caching
- Redis configured for caching (add to base.py when ready)

### Background Tasks
- Celery configured for async processing (add to base.py when ready)

### API Layer
- Django REST Framework installed for future API endpoints

### Logging
- Production logging configured in production.py

## Next Steps

1. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create and apply migrations**:
   ```bash
   python manage.py makemigrations courses users posts groups notifications
   python manage.py migrate
   ```

4. **Move services and queries** to respective domain apps

5. **Update views** to use new models

6. **Test thoroughly** before removing core app

## Best Practices

- Each domain app should be independently testable
- Services contain business logic
- Queries contain database access logic
- Views orchestrate services and queries
- Models only contain data definitions and basic methods
- Use environment variables for all configuration
