# Pre-Reels Implementation Checklist

## Overview
This document outlines all prerequisites and preparations needed before implementing the Reels feature. Complete these items to ensure a smooth implementation and avoid system issues.

---

## Phase 1: Infrastructure Prerequisites

### 1.1 Docker Configuration Updates

**Task**: Add FFmpeg to Dockerfile for video processing

**Current Dockerfile**: `/home/zayne/projects/pwaninet/Dockerfile`

**Required Change**:
```dockerfile
# Add FFmpeg to system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

**Verification**:
```bash
# After rebuilding Docker image
docker exec -it <container_id> ffmpeg -version
```

**Status**: ⬜ Not Started

---

### 1.2 Storage Capacity Assessment

**Task**: Ensure sufficient disk space for video storage

**Check Current Usage**:
```bash
# Check disk space
df -h

# Check current media directory size
du -sh /home/zayne/projects/pwaninet/media/
```

**Minimum Requirements for MVP**:
- 20GB free space for 200 videos (50MB each)
- 50GB recommended for buffer

**Action Items**:
- [ ] Verify current disk space >30GB
- [ ] Set up disk space monitoring alerts
- [ ] Plan storage cleanup strategy if needed

**Status**: ⬜ Not Started

---

### 1.3 Celery Worker Capacity

**Task**: Ensure Celery can handle video processing load

**Current Setup**:
- 1 Celery worker configured in docker-compose.yml
- Redis broker already configured

**Assessment**:
- Current worker: Sufficient for MVP (10-20 videos/day)
- Monitor queue length during testing

**Action Items**:
- [ ] Test Celery with video processing tasks
- [ ] Set up Celery queue monitoring
- [ ] Plan to add workers if queue >50 tasks consistently

**Status**: ⬜ Not Started

---

### 1.4 Redis Configuration

**Task**: Verify Redis is properly configured for caching

**Current Setup**:
- Redis 7-alpine in docker-compose
- Already configured in base.py

**Action Items**:
- [ ] Verify Redis connection is stable
- [ ] Test cache operations
- [ ] Set up Redis monitoring

**Status**: ⬜ Not Started

---

## Phase 2: Codebase Prerequisites

### 2.1 Complete Domain Migration

**Task**: Finish migrating views and forms from core app to domain apps

**Current Status**: In progress (per FEATURES.md)

**Action Items**:
- [ ] Move remaining views from core to domain apps
- [ ] Move remaining forms from core to domain apps
- [ ] Update URL references
- [ ] Test all migrated functionality
- [ ] Remove core app after verification

**Files to Check**:
- `/home/zayne/projects/pwaninet/core/views.py`
- `/home/zayne/projects/pwaninet/core/forms.py`
- `/home/zayne/projects/pwaninet/core/urls.py`

**Status**: ⬜ Not Started

---

### 2.2 Add REST API Layer

**Task**: Implement Django REST Framework endpoints

**Why**: Reels will need API endpoints for mobile/future use

**Action Items**:
- [ ] Create serializers for existing models
- [ ] Create viewsets for posts, users, groups
- [ ] Set up API authentication (JWT or session)
- [ ] Add API documentation (Swagger/DRF docs)
- [ ] Test API endpoints

**Priority**: HIGH - Do this before reels

**Status**: ⬜ Not Started

---

### 2.3 Database Indexing Review

**Task**: Ensure existing tables have proper indexes

**Check**:
```sql
-- Check indexes on posts table
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'posts_post';

-- Check indexes on users table
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users_user';
```

**Action Items**:
- [ ] Review indexes on all domain tables
- [ ] Add missing indexes on foreign keys
- [ ] Add indexes on frequently queried fields
- [ ] Test query performance with EXPLAIN ANALYZE

**Status**: ⬜ Not Started

---

### 2.4 Add Dependencies

**Task**: Install required packages for video processing

**File**: `/home/zayne/projects/pwaninet/requirements.txt`

**Add These Packages**:
```txt
ffmpeg-python==0.2.0
moviepy==1.0.3
pillow-heif==0.13.0
boto3==1.34.0              # For future S3 integration
django-storages==1.14.2    # For cloud storage
```

**Action Items**:
- [ ] Add packages to requirements.txt
- [ ] Rebuild Docker image
- [ ] Test imports in Python shell
- [ ] Verify FFmpeg-Python integration

**Status**: ⬜ Not Started

---

## Phase 3: Configuration Prerequisites

### 3.1 Add Reels Settings

**Task**: Add reels-specific configuration to settings

**File**: `/home/zayne/projects/pwaninet/pwaninet/settings/base.py`

**Add These Settings**:
```python
# Reels Configuration
REELS_MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
REELS_MAX_DURATION = 30  # 30 seconds
REELS_MAX_VIDEOS_PER_USER = 10
REELS_DAILY_UPLOAD_LIMIT = 3
REELS_AUTO_DELETE_DAYS = 90
REELS_ALLOWED_FORMATS = ['mp4', 'mov', 'webm']
REELS_VIDEO_QUALITY = 'high'  # high, medium, low
REELS_THUMBNAIL_SIZE = (1080, 1920)
```

**Action Items**:
- [ ] Add settings to base.py
- [ ] Add settings to local.py for testing
- [ ] Document each setting
- [ ] Test settings are accessible

**Status**: ⬜ Not Started

---

### 3.2 Update INSTALLED_APPS

**Task**: Add reels app to installed apps

**File**: `/home/zayne/projects/pwaninet/pwaninet/settings/base.py`

**Change**:
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'courses',
    'users',
    'posts',
    'groups',
    'notifications',
    'core',
    'reels',  # Add this line
]
```

**Status**: ⬜ Not Started (waiting for app creation)

---

### 3.3 Configure Media Storage

**Task**: Set up proper media file handling

**Current Setup**: Local storage in `/media/`

**For MVP**: Local storage is fine

**For Future**: Configure S3 when needed

**Action Items**:
- [ ] Verify MEDIA_ROOT and MEDIA_URL are set
- [ ] Ensure media directory has proper permissions
- [ ] Test file upload functionality
- [ ] Document S3 migration path

**Status**: ⬜ Not Started

---

## Phase 4: Monitoring & Logging

### 4.1 Set Up Disk Space Monitoring

**Task**: Monitor disk space to prevent filling up

**Implementation Options**:
```bash
# Simple cron job
*/5 * * * * df -h | grep -E '/$' | awk '{print $5}' | sed 's/%//' | awk '{if ($1 > 80) print "WARNING: Disk usage " $1 "%"}'

# Or use monitoring tool
# - Prometheus + Grafana
# - Datadog
# - New Relic
```

**Action Items**:
- [ ] Set up disk space monitoring
- [ ] Configure alerts at 70%, 80%, 90%
- [ ] Test alert notifications
- [ ] Document cleanup procedure

**Status**: ⬜ Not Started

---

### 4.2 Set Up Celery Monitoring

**Task**: Monitor Celery queue and worker health

**Tools**:
- Flower (Celery monitoring tool)
- Custom monitoring script

**Action Items**:
- [ ] Install Flower: `pip install flower`
- [ ] Add Flower to docker-compose.yml
- [ ] Configure Flower authentication
- [ ] Set up queue length alerts
- [ ] Test monitoring dashboard

**Status**: ⬜ Not Started

---

### 4.3 Set Up Application Logging

**Task**: Ensure proper logging for reels operations

**File**: `/home/zayne/projects/pwaninet/pwaninet/settings/base.py`

**Add Logging Configuration**:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/django.log',
        },
        'reels': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/reels.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'reels': {
            'handlers': ['reels'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

**Action Items**:
- [ ] Add logging configuration
- [ ] Create logs directory
- [ ] Test logging output
- [ ] Set up log rotation

**Status**: ⬜ Not Started

---

### 4.4 Set Up Error Tracking

**Task**: Implement error tracking for production

**Recommended Tools**:
- Sentry (recommended)
- Rollbar
- Bugsnag

**Action Items**:
- [ ] Sign up for Sentry account
- [ ] Install Sentry SDK
- [ ] Configure Sentry in settings
- [ ] Test error reporting
- [ ] Set up alert notifications

**Status**: ⬜ Not Started

---

## Phase 5: Testing Infrastructure

### 5.1 Set Up Test Database

**Task**: Ensure test database is configured

**Current Setup**: Uses SQLite for development

**Action Items**:
- [ ] Configure test database in settings
- [ ] Ensure test database is separate from production
- [ ] Test database migrations
- [ ] Set up test data fixtures

**Status**: ⬜ Not Started

---

### 5.2 Add Test Framework

**Task**: Set up testing framework

**Recommended**: pytest + pytest-django

**Add to requirements.txt**:
```txt
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
factory-boy==3.3.0
```

**Action Items**:
- [ ] Install test dependencies
- [ ] Create pytest configuration
- [ ] Set up test directory structure
- [ ] Write sample test
- [ ] Configure coverage reporting

**Status**: ⬜ Not Started

---

### 5.3 Set Up Load Testing

**Task**: Prepare for load testing reels endpoints

**Tools**:
- Locust (recommended)
- Apache Bench
- JMeter

**Action Items**:
- [ ] Install Locust
- [ ] Create basic load test script
- [ ] Test current system capacity
- [ ] Document baseline performance
- [ ] Plan load testing for reels

**Status**: ⬜ Not Started

---

## Phase 6: Security Prerequisites

### 6.1 Review File Upload Security

**Task**: Ensure secure file upload handling

**Security Checklist**:
- [ ] File type validation (whitelist, not blacklist)
- [ ] File size limits enforced
- [ ] File content validation (magic bytes)
- [ ] Sanitize file names
- [ ] Store files outside web root
- [ ] Rate limiting on uploads
- [ ] Virus scanning (optional but recommended)

**Implementation**:
```python
# Example validation
def validate_video_upload(file):
    # Check file extension
    ext = file.name.split('.')[-1].lower()
    if ext not in settings.REELS_ALLOWED_FORMATS:
        raise ValidationError("Invalid file format")
    
    # Check file size
    if file.size > settings.REELS_MAX_VIDEO_SIZE:
        raise ValidationError("File too large")
    
    # Check magic bytes
    file.seek(0)
    header = file.read(12)
    # Validate video header bytes
    file.seek(0)
```

**Status**: ⬜ Not Started

---

### 6.2 Set Up Rate Limiting

**Task**: Implement rate limiting for API endpoints

**Tools**:
- django-ratelimit
- DRF throttling

**Action Items**:
- [ ] Install django-ratelimit
- [ ] Configure rate limits for upload endpoints
- [ ] Configure rate limits for feed endpoints
- [ ] Test rate limiting
- [ ] Document rate limits

**Status**: ⬜ Not Started

---

### 6.3 Review Content Moderation

**Task**: Set up content moderation system

**Action Items**:
- [ ] Implement report system
- [ ] Create moderation queue
- [ ] Set up admin review process
- [ ] Document moderation policies
- [ ] Plan AI moderation (future)

**Status**: ⬜ Not Started

---

## Phase 7: Team & Process Prerequisites

### 7.1 Define Development Workflow

**Task**: Establish clear development process

**Action Items**:
- [ ] Create feature branch strategy
- [ ] Define code review process
- [ ] Set up CI/CD pipeline
- [ ] Define deployment process
- [ ] Document rollback procedure

**Status**: ⬜ Not Started

---

### 7.2 Allocate Resources

**Task**: Ensure sufficient team capacity

**Resource Requirements**:
- 1 backend developer (4-6 weeks for MVP)
- 1 frontend developer (if using React)
- DevOps support (for infrastructure)
- QA support (for testing)

**Action Items**:
- [ ] Confirm team availability
- [ ] Assign tasks to team members
- [ ] Set up communication channels
- [ ] Schedule regular check-ins

**Status**: ⬜ Not Started

---

### 7.3 Define Success Metrics

**Task**: Establish measurable goals

**Metrics to Track**:
- Upload success rate (>95%)
- Video processing time (<30s)
- Feed load time (<2s)
- User engagement rate
- Storage growth rate
- Error rates

**Action Items**:
- [ ] Define baseline metrics
- [ ] Set up metric collection
- [ ] Define success thresholds
- [ ] Plan metric review process

**Status**: ⬜ Not Started

---

## Phase 8: Documentation Prerequisites

### 8.1 Update API Documentation

**Task**: Prepare API documentation

**Action Items**:
- [ ] Set up Swagger/OpenAPI
- [ ] Document existing endpoints
- [ ] Prepare documentation for reels endpoints
- [ ] Set up API versioning strategy
- [ ] Document authentication methods

**Status**: ⬜ Not Started

---

### 8.2 Create Deployment Guide

**Task**: Document deployment process

**Action Items**:
- [ ] Document environment setup
- [ ] Document database migrations
- [ ] Document configuration changes
- [ ] Document rollback procedure
- [ ] Create troubleshooting guide

**Status**: ⬜ Not Started

---

### 8.3 Update User Documentation

**Task**: Prepare user-facing documentation

**Action Items**:
- [ ] Write user guide for reels
- [ ] Create FAQ
- [ ] Document privacy settings
- [ ] Create moderation guidelines
- [ ] Prepare release notes

**Status**: ⬜ Not Started

---

## Phase 9: Backup & Recovery

### 9.1 Set Up Database Backups

**Task**: Ensure regular database backups

**Current Setup**: PostgreSQL in docker-compose

**Action Items**:
- [ ] Set up automated backups
- [ ] Test backup restoration
- [ ] Document backup schedule
- [ ] Set up backup monitoring
- [ ] Store backups off-site

**Status**: ⬜ Not Started

---

### 9.2 Set Up Media Backups

**Task**: Back up video files

**Challenge**: Video files are large

**Options**:
- Sync to S3 (even if not serving from it)
- rsync to backup server
- Snapshot entire volume

**Action Items**:
- [ ] Choose backup strategy
- [ ] Implement backup solution
- [ ] Test restoration
- [ ] Document backup procedure

**Status**: ⬜ Not Started

---

### 9.3 Create Disaster Recovery Plan

**Task**: Plan for system failures

**Scenarios to Plan For**:
- Disk full
- Database corruption
- Video processing failure
- CDN outage (when using CDN)
- High traffic spikes

**Action Items**:
- [ ] Document each scenario
- [ ] Define response procedures
- [ ] Test recovery procedures
- [ ] Train team on procedures

**Status**: ⬜ Not Started

---

## Phase 10: Final Verification

### 10.1 Pre-Implementation Checklist

**Before Starting Reels Implementation**:

Infrastructure:
- [ ] FFmpeg installed and tested
- [ ] Disk space >30GB available
- [ ] Celery worker operational
- [ ] Redis connection stable
- [ ] Monitoring tools in place

Codebase:
- [ ] Domain migration complete
- [ ] REST API layer implemented
- [ ] Database indexes optimized
- [ ] Required dependencies installed
- [ ] Settings configured

Testing:
- [ ] Test database configured
- [ ] Test framework set up
- [ ] Load testing tools ready
- [ ] Baseline performance documented

Security:
- [ ] File upload security reviewed
- [ ] Rate limiting configured
- [ ] Content moderation planned

Documentation:
- [ ] API documentation prepared
- [ ] Deployment guide written
- [ ] User documentation drafted

Backup:
- [ ] Database backups automated
- [ ] Media backups configured
- [ ] Disaster recovery plan written

Team:
- [ ] Resources allocated
- [ ] Workflow defined
- [ ] Success metrics established

---

### 10.2 Go/No-Go Decision

**Go Criteria**:
- All critical items (Infrastructure, Codebase, Security) complete
- Team resources available
- Success metrics defined
- Backup systems operational

**No-Go Criteria**:
- Disk space insufficient
- Domain migration incomplete
- No team availability
- Monitoring not set up

**Decision Maker**: [Your Name/Team Lead]

**Decision Date**: [Date]

---

## Timeline Estimate

**Minimum Time to Complete Prerequisites**: 2-3 weeks

**Breakdown**:
- Phase 1 (Infrastructure): 2-3 days
- Phase 2 (Codebase): 5-7 days
- Phase 3 (Configuration): 1-2 days
- Phase 4 (Monitoring): 2-3 days
- Phase 5 (Testing): 2-3 days
- Phase 6 (Security): 2-3 days
- Phase 7 (Team): 1-2 days
- Phase 8 (Documentation): 2-3 days
- Phase 9 (Backup): 2-3 days
- Phase 10 (Verification): 1-2 days

---

## Dependencies

**These prerequisites depend on**:
- Current system stability
- Team availability
- Budget for monitoring tools
- Management approval

**These prerequisites block**:
- Reels implementation start
- Video processing development
- Reels API development
- Reels testing

---

## Next Steps After Completing Prerequisites

1. **Review this checklist** with team
2. **Assign owners** to each phase
3. **Set deadlines** for completion
4. **Schedule weekly check-ins**
5. **Update status** as items complete
6. **Hold Go/No-Go meeting** when all items complete
7. **Begin reels implementation** if approved

---

## Notes

- Some items can be done in parallel
- Some items are optional for MVP (marked as such)
- Adjust timeline based on team size and availability
- Document any deviations from this checklist
- Update this document as new requirements emerge

---

## Contact

**Questions about this checklist**: [Your Name/Team Lead]

**Last Updated**: [Date]

**Version**: 1.0
