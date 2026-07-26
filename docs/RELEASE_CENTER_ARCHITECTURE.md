# PwaniNet Release Center Architecture

## Overview

The PwaniNet Release Center is a comprehensive release management system designed to become the single authority for application versions. This architecture provides a clean, extensible foundation for version management, build numbers, release notes, changelog, deployment history, and future features like service worker versioning, cache versioning, update notifications, release channels, and rollbacks.

## Architecture Principles

1. **Separation of Concerns**: Business logic is separated from views through services layer
2. **Thin Views**: Views remain thin and delegate to services
3. **Reusable Utilities**: Common functionality extracted into utils
4. **Dedicated Permissions**: Custom permissions instead of relying solely on is_staff
5. **Audit Trail**: Comprehensive tracking of release operations
6. **Extensibility**: Architecture designed to support future growth without redesign

## File Tree

```
releases/
├── __init__.py
├── admin.py                    # Django admin interface
├── apps.py                     # App configuration
├── forms.py                    # Django forms for release management
├── migrations/                 # Database migrations
│   ├── 0001_initial.py
│   └── 0002_release_environment_snapshot_and_more.py
├── models.py                   # Data models (Release, ReleaseItem, UserReleaseView)
├── permissions.py              # Custom permissions for release operations
├── selectors.py                # Query selectors for releases
├── serializers.py              # DRF serializers for API
├── services.py                 # Business logic layer
├── signals.py                  # Audit trail signals
├── templates/                  # HTML templates
│   └── releases/
│       ├── create.html        # Create release form
│       ├── dashboard.html     # Release center dashboard
│       ├── detail.html        # Release details view
│       └── edit.html          # Edit release form
├── urls.py                     # URL routing
├── utils.py                    # Semantic version utilities
├── views.py                    # DRF API viewsets
└── web_views.py               # Web UI views
```

## Data Model

### Release Model

The Release model is the authoritative source for application versions.

**Fields:**

- **version** (CharField, unique): Semantic version (e.g., 1.0.0)
- **build_number** (PositiveIntegerField, unique): Incremental build number for ordering
- **release_title** (CharField): User-friendly title for this release
- **release_summary** (TextField): Brief summary of this release
- **release_type** (CharField): Type of release (MAJOR, MINOR, PATCH, HOTFIX)
- **status** (CharField): Current status (DRAFT, TESTING, PUBLISHED, ARCHIVED)
- **release_channel** (CharField): Release channel (DEVELOPMENT, ALPHA, BETA, RELEASE_CANDIDATE, STABLE)
- **is_current_release** (BooleanField): If True, this is the currently deployed release
- **mandatory_update** (BooleanField): If True, users must update to continue using the app
- **published** (BooleanField): If True, release is visible to users
- **minimum_supported_version** (CharField, nullable): Minimum version required for this update
- **environment_snapshot** (JSONField): Snapshot of environment configuration at release time
- **release_date** (DateTimeField): When this release was published
- **created_at** (DateTimeField): When this release was created
- **updated_at** (DateTimeField): When this release was last updated
- **published_at** (DateTimeField, nullable): When this release was published
- **created_by** (ForeignKey): Admin who created this release
- **published_by** (ForeignKey, nullable): Admin who published this release

**Constraints:**
- Unique constraint on version
- Unique constraint on build_number
- Unique constraint ensuring only one release can have is_current_release=True

**Indexes:**
- version, build_number, published, release_channel, status, is_current_release

### ReleaseItem Model

Individual items within a release (features, bug fixes, etc.).

**Fields:**

- **release** (ForeignKey): The release this item belongs to
- **category** (CharField): Category (FEATURE, IMPROVEMENT, BUG_FIX, SECURITY, KNOWN_ISSUE, DEPRECATION)
- **title** (CharField): Title of this item
- **description** (TextField): Detailed description of this item
- **display_order** (PositiveIntegerField): Order for displaying items within a release
- **created_at** (DateTimeField): When this item was created
- **updated_at** (DateTimeField): When this item was last updated

### UserReleaseView Model

Track which releases each user has viewed for the "What's New" experience.

**Fields:**

- **user** (ForeignKey): User who viewed this release
- **release** (ForeignKey): Release that was viewed
- **viewed_at** (DateTimeField): When the release was viewed
- **session_key** (CharField, nullable): Session key for anonymous users

## Permission Model

The Release Center uses dedicated permissions instead of relying solely on Django superuser access.

**Permissions:**

1. **releases.manage_release**: Create, edit, delete draft releases
2. **releases.publish_release**: Publish releases
3. **releases.view_release**: View releases (all authenticated users)
4. **releases.archive_release**: Archive releases

**Permission Classes:**

- `CanViewRelease`: All authenticated users can view releases
- `CanManageRelease`: Users with manage_release permission or staff
- `CanPublishRelease`: Users with publish_release permission or staff
- `CanArchiveRelease`: Users with archive_release permission or staff
- `IsReleaseOwnerOrStaff`: Release creator or staff

## Release Workflow

### 1. Create Draft

```
User → Create Release Form → ReleaseService.create_draft() → Release (status=DRAFT)
```

- User fills out release form (title, summary, type, channel)
- ReleaseService automatically generates next version and build number
- Release is created with DRAFT status
- Release items can be added

### 2. Edit Draft

```
User → Edit Release Form → ReleaseForm → Update Release
```

- Only draft releases can be edited
- Users with manage_release permission can edit
- Release items can be added/removed

### 3. Publish Release

```
User → Publish Form → ReleaseService.publish_release() → Release (status=PUBLISHED)
```

- Only DRAFT or TESTING releases can be published
- User with publish_release permission required
- Sets published=True, status=PUBLISHED, published_at, published_by
- Option to set as current release
- Invalidates caches

### 4. Set Current Release

```
User → Set Current → ReleaseService.set_current_release() → Release (is_current_release=True)
```

- Only published releases can be marked as current
- Automatically unsets current flag from other releases
- Enforced at database level with unique constraint

### 5. Archive Release

```
User → Archive Form → ReleaseService.archive_release() → Release (status=ARCHIVED)
```
- Cannot archive current release
- Sets status=ARCHIVED, published=False
- Invalidates caches

## Service Layer

The `ReleaseService` class contains all business logic for release operations:

**Methods:**

- `create_draft()`: Create a new draft release with automatic version generation
- `publish_release()`: Publish a release
- `archive_release()`: Archive a release
- `set_current_release()`: Mark a release as current
- `get_current_release()`: Get the current release
- `get_latest_stable()`: Get the latest stable release
- `get_latest_beta()`: Get the latest beta release
- `get_latest_by_channel()`: Get the latest release for a specific channel
- `validate_release()`: Validate a release before publishing
- `generate_next_version()`: Generate the next version based on release type
- `generate_next_build()`: Generate the next build number
- `add_release_item()`: Add an item to a release
- `get_release_statistics()`: Get release statistics for dashboard

## Selector Layer

The `ReleaseSelector` and `ReleaseItemSelector` classes provide reusable query methods:

**ReleaseSelector Methods:**

- `all()`, `published()`, `drafts()`, `testing()`, `archived()`
- `by_status()`, `by_channel()`, `by_version()`, `by_build_number()`, `by_id()`
- `current()`, `latest()`, `latest_published()`, `latest_stable()`, `latest_beta()`, `latest_alpha()`
- `search()`, `by_created_by()`, `by_published_by()`
- `with_items()`, `with_item_count()`, `recent()`, `recent_published()`

## Utility Layer

The `utils.py` module provides semantic version helpers:

**Functions:**

- `parse_version()`: Parse version string into Version object
- `increment_version()`: Increment version based on release type
- `compare_versions()`: Compare two version strings
- `is_version_greater()`, `is_version_less()`: Version comparison helpers
- `validate_version()`: Validate version format
- `get_next_build_number()`: Get next build number
- `format_version_with_channel()`: Format version with channel tag
- `extract_base_version()`: Extract base version without prerelease

**Version Class:**

- Represents semantic version with optional prerelease and build metadata
- Supports comparison operators
- Provides increment method

## Routing

### API Routes

- `/api/releases/` - ReleaseViewSet (list, retrieve, latest, history, version_check)
- `/api/user-release-views/` - UserReleaseViewViewSet (track viewed releases)
- `/api/version/` - Current application version
- `/api/releases/create/` - Create release with auto-version increment

### UI Routes (/system/releases/)

- `/system/releases/` - Dashboard
- `/system/releases/create/` - Create release
- `/system/releases/<id>/edit/` - Edit release
- `/system/releases/<id>/` - Release details
- `/system/releases/<id>/publish/` - Publish release
- `/system/releases/<id>/archive/` - Archive release
- `/system/releases/<id>/set-current/` - Set as current release
- `/system/releases/<id>/add-item/` - Add release item
- `/system/releases/items/<id>/delete/` - Delete release item

## Audit Trail

The audit trail is implemented through Django signals:

**Signals:**

- `pre_save`: Track status changes before save
- `post_save`: Log creation, status changes, and publishing
- `pre_delete`: Log deletion before it happens

**Logged Events:**

- Release creation
- Status changes
- Publishing
- Deletion
- Release item creation

All audit entries are stored in Django's LogEntry model for review.

## Environment Snapshot

When a release is created, the system captures a snapshot of the environment:

```python
{
    'environment': 'development/production',
    'debug': True/False,
    'allowed_hosts': [...],
    'database_engine': '...',
}
```

This snapshot is stored in the `environment_snapshot` JSONField and can be used for:
- Future reporting
- Troubleshooting
- Rollback decisions
- Deployment history analysis

## Future Extension Points

### 1. Deployment Automation

The architecture is ready for deployment automation integration:

- **Service Worker Versioning**: Add service_worker_version field to Release model
- **Cache Versioning**: Add cache_version field to Release model
- **Docker Integration**: Add docker_image_tag field to Release model
- **Git Integration**: Add git_commit, git_branch fields to Release model

### 2. Update Notifications

The existing API endpoints support update notifications:

- `/api/releases/version_check/` - Lightweight endpoint for polling
- Returns current version, latest version, update status
- Can be extended with WebSocket support for real-time updates

### 3. Rollback Implementation

The architecture supports rollbacks:

- `is_current_release` flag allows easy rollback
- Environment snapshot provides deployment context
- Audit trail provides rollback history
- Can add rollback_reason field in future

### 4. Release Channels

The release_channel field supports staged rollouts:

- DEVELOPMENT, ALPHA, BETA, RELEASE_CANDIDATE, STABLE
- Can be extended with percentage-based rollouts
- Can add channel-specific user targeting

### 5. Version.py Generation

The Release model can become the authoritative source for version.py:

- Add management command to generate version.py from current release
- Remove dependency on manual version.py updates
- Ensure single source of truth

### 6. API Extensions

The existing DRF viewsets can be extended:

- Add rollback endpoint
- Add deployment endpoint
- Add webhook support for CI/CD integration
- Add GraphQL support

## Architectural Decisions

### 1. Separate Web Views and API Views

**Decision**: Created separate `web_views.py` for UI and kept `views.py` for API.

**Rationale**: 
- Clear separation of concerns
- API views can evolve independently
- Web views can use Django forms and templates
- Easier to maintain and test

### 2. Service Layer Pattern

**Decision**: All business logic in `ReleaseService`, views remain thin.

**Rationale**:
- Reusable business logic across different interfaces
- Easier to test business logic in isolation
- Views focus on HTTP concerns
- Follows Django best practices

### 3. Selector Pattern

**Decision**: Created `selectors.py` for query logic.

**Rationale**:
- Reusable query methods
- Centralized query logic
- Easier to optimize queries
- Clear separation between data access and business logic

### 4. Semantic Version Utilities

**Decision**: Created comprehensive semantic version utilities in `utils.py`.

**Rationale**:
- No manual string concatenation
- Reusable version comparison and parsing
- Supports pre-release and build metadata
- Follows semantic versioning specification

### 5. Dedicated Permissions

**Decision**: Created custom permissions instead of relying on is_staff.

**Rationale**:
- Granular access control
- Future developers can have release permissions without superuser access
- Follows principle of least privilege
- Easier to audit and manage

### 6. JSONField for Environment Snapshot

**Decision**: Used JSONField for environment_snapshot.

**Rationale**:
- Flexible schema for future additions
- No need for migrations when adding environment data
- Easy to query and filter
- Native Django support

### 7. Unique Constraint for Current Release

**Decision**: Database-level constraint ensuring only one current release.

**Rationale**:
- Data integrity enforced at database level
- No race conditions
- Application-level enforcement as backup

### 8. Audit Trail via Django Signals

**Decision**: Used Django signals for audit trail.

**Rationale**:
- Non-invasive to existing code
- Automatic logging without manual calls
- Leverages Django's built-in LogEntry model
- Easy to extend with additional events

## Code Quality

- **Type Hints**: Used throughout services and utilities
- **Docstrings**: Comprehensive docstrings for all classes and methods
- **No Magic Strings**: Constants defined in models
- **No Dead Code**: All code has a purpose
- **No Duplication**: Reusable utilities and services
- **Django Best Practices**: Follows Django conventions
- **Thin Views**: Views delegate to services
- **Business Logic in Services**: All business logic in service layer

## Summary

The PwaniNet Release Center architecture provides a clean, extensible foundation for release management. It separates concerns effectively, follows Django best practices, and is designed to support future features without requiring architectural redesign. The system is production-ready and capable of supporting deployment automation, update notifications, service worker versioning, cache versioning, and rollbacks.
