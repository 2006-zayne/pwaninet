# Architecture Analysis Post-View Migration

**Date:** April 25, 2026
**Status:** Views migrated to domain apps - Phase 1 Complete
**Last Updated:** April 25, 2026 - Microservices Implementation Plan Added

---

## Executive Summary

The view migration from `core.views` to domain apps has been successfully completed. Django system check passes with no issues. However, several architectural bottlenecks remain that need to be addressed to achieve true domain-driven design.

---

## Current Architecture State

### ✅ Completed

1. **View Migration** - All Django views moved to domain apps:
   - `users/views.py`: register_view, profile_view, update_profile_view, toggle_follow, get_suggestions
   - `posts/views.py`: home_view, create_post_view, post_detail_view, add_comment, toggle_comment_like, toggle_like, post_likers_list, unit_posts_view, search_view
   - `groups/views.py`: groups_dashboard, groups_detail_view, create_group_view, toggle_group_membership, edit_group, invite_to_group, respond_to_invite
   - `notifications/views.py`: notifications_list, unread_notification_count, mark_notification_as_read, mark_all_as_read
   - `courses/views.py`: load_years

2. **URL Configuration** - All domain apps now have their own URL configurations with proper imports.

3. **No Circular Dependencies** - Dependency graph is clean.

---

## 🔴 Critical Issues (Must Fix)

### 1. Broken Import in users/services/notification_service.py

**Location:** `/home/zayne/projects/pwaninet/users/services/notification_service.py:5`

**Issue:**
```python
from core.queries.notification_queries import get_notification_for_user, get_notifications_for_user, get_unread_count, mark_user_notifications_as_read
```

**Problem:** `core.queries.notification_queries` does not exist. The actual file is at `notifications/queries/notification_queries.py`.

**Impact:** This will cause an ImportError at runtime.

**Fix Required:**
```python
from notifications.queries.notification_queries import get_notification_for_user, get_notifications_for_user, get_unread_count, mark_user_notifications_as_read
```

**Priority:** CRITICAL - This is a broken import that will crash the application.

---

## 🟡 High Priority Bottlenecks

### 2. Forms Still in Core App

**Location:** `/home/zayne/projects/pwaninet/core/forms.py`

**Issue:** All domain-specific forms remain in the core app, creating tight coupling.

**Current State:**
- `PwaniSignupForm` (User-related) → Should be in `users/forms.py`
- `PostForm` (Post-related) → Should be in `posts/forms.py`
- `ProfileUpdateForm` (User-related) → Should be in `users/forms.py`
- `GroupForm` (Group-related) → Should be in `groups/forms.py`

**Current Dependencies:**
- `users/views.py` imports from `core.forms`
- `groups/views.py` imports from `core.forms`
- `posts/views.py` imports from `core.forms`

**Impact:** Violates domain boundaries. Core app still contains business logic.

**Migration Plan:**
1. Create `users/forms.py` with PwaniSignupForm and ProfileUpdateForm
2. Create `posts/forms.py` with PostForm
3. Create `groups/forms.py` with GroupForm
4. Update imports in all view files
5. Delete `core/forms.py` (or leave only shared utilities if any)

**Priority:** HIGH - Core should not contain domain-specific forms.

---

### 3. Templates Still in Core App

**Location:** `/home/zayne/projects/pwaninet/core/templates/`

**Issue:** All domain-specific templates remain in core/templates directory.

**Current Template Distribution:**
```
core/templates/
├── base.html (shared - should stay in core)
├── register.html (user-related → users/templates/)
├── logout.html (shared - should stay in core)
├── home.html (post-related → posts/templates/)
├── create_post.html (post-related → posts/templates/)
├── post_detail.html (post-related → posts/templates/)
├── profile.html (user-related → users/templates/)
├── update_profile.html (user-related → users/templates/)
├── notifications.html (notification-related → notifications/templates/)
├── groups_dashboard.html (group-related → groups/templates/)
├── groups_detail.html (group-related → groups/templates/)
├── create_group.html (group-related → groups/templates/)
├── search_results.html (post-related → posts/templates/)
├── unit_detail.html (course-related → courses/templates/)
└── partials/ (mixed - needs distribution)
```

**Impact:** Templates are not co-located with their domain logic.

**Migration Plan:**
1. Move domain-specific templates to respective app template directories
2. Keep shared templates (base.html, logout.html) in core
3. Distribute partials based on domain ownership
4. Update template references in views

**Priority:** HIGH - Violates domain-driven design principles.

---

## 🟢 Medium Priority Improvements

### 4. Duplicate Notification Service

**Issue:** There are two notification service files:
- `users/services/notification_service.py` (appears to be decompiled/broken)
- `notifications/services/notification_service.py` (actual implementation)

**Recommendation:** Remove the duplicate in users/services and ensure all imports use the notifications version.

**Priority:** MEDIUM - Code duplication and potential confusion.

---

### 5. Core App Still Contains Business Logic

**Current Core App Contents:**
- `core/forms.py` - Domain-specific forms (should be moved)
- `core/templates/` - Domain-specific templates (should be moved)
- `core/models.py` - Check if contains domain models
- `core/signals.py` - Check if contains domain-specific signals

**Recommendation:** Core app should only contain:
- Shared utilities
- Base templates
- Cross-cutting concerns (logging, middleware, etc.)
- Configuration

**Priority:** MEDIUM - Architectural cleanliness.

---

## 📋 Recommended Action Plan

### Phase 1: Critical Fixes (Immediate)
1. Fix broken import in `users/services/notification_service.py`
2. Test application to ensure no runtime errors

### Phase 2: Form Migration (High Priority)
1. Create domain-specific forms directories
2. Move forms to respective apps
3. Update all imports
4. Test all forms

### Phase 3: Template Migration (High Priority)
1. Create domain-specific template directories
2. Move templates to respective apps
3. Update template references in views
4. Test all pages

### Phase 4: Cleanup (Medium Priority)
1. Remove duplicate notification service
2. Review core/models.py for domain models
3. Review core/signals.py for domain-specific signals
4. Document final architecture

---

## Dependency Graph

```
core
├── users (depends on core.forms ❌)
├── posts (depends on core.forms ❌)
├── groups (depends on core.forms ❌)
└── notifications (clean ✅)

Target State:
core (shared utilities only)
├── users (self-contained ✅)
├── posts (self-contained ✅)
├── groups (self-contained ✅)
└── notifications (self-contained ✅)
```

---

## Risk Assessment

| Issue | Risk Level | Impact | Effort |
|-------|-----------|--------|--------|
| Broken import in notification_service.py | CRITICAL | App crash | 5 min |
| Forms in core | HIGH | Coupling | 1-2 hours |
| Templates in core | HIGH | Coupling | 2-3 hours |
| Duplicate notification service | MEDIUM | Confusion | 30 min |
| Core business logic | MEDIUM | Maintainability | 1-2 hours |

---

## Success Criteria

- [x] All views migrated to domain apps
- [x] URL configurations updated
- [x] No circular dependencies
- [ ] No core dependencies in domain apps
- [ ] All forms in domain apps
- [ ] All templates in domain apps
- [ ] Core app contains only shared utilities
- [ ] All tests pass
- [ ] No broken imports

---

## Notes

- The view migration was successful and Django check passes
- The main bottleneck is that forms and templates remain in core
- The broken import in users/services/notification_service.py is critical and must be fixed immediately
- No circular dependencies detected - the architecture is sound at the import level
- HTMX endpoints are working correctly with the new view locations

---

## Microservices Implementation Plan

### Current Architecture (Monolithic)

The current system is a **monolithic Django application** where all domain apps (users, posts, groups, notifications, courses) run in a single process:

```
┌─────────────────────────────────────┐
│   Single Django Application         │
│   (pwaninet/wsgi.py)               │
│                                     │
│  ┌─────────┐ ┌─────────┐           │
│  │ users   │ │ posts   │           │
│  └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐           │
│  │ groups  │ │ notifs  │           │
│  └─────────┘ └─────────┘           │
│  ┌─────────┐                       │
│  │ courses │                       │
│  └─────────┘                       │
│                                     │
│  Shared: PostgreSQL, Redis          │
└─────────────────────────────────────┘
```

**Problem:** If one app crashes (e.g., unhandled exception in posts), the entire Django process fails, taking down all other services.

---

### Target Architecture (Microservices)

Transform each domain app into an independent service with its own process, database, and API:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  User Svc   │  │  Post Svc   │  │  Group Svc  │
│  :8001      │  │  :8002      │  │  :8003      │
└─────────────┘  └─────────────┘  └─────────────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Notif Svc  │  │ Course Svc  │  │  API Gateway│
│  :8004      │  │  :8005      │  │  :8000      │
└─────────────┘  └─────────────┘  └─────────────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         ┌────▼────┐          ┌────▼────┐
         │PostgreSQL│         │  Redis  │
         │(per DB) │         │  Shared │
         └─────────┘          └─────────┘
```

**Benefit:** If Post Service crashes, User Service, Group Service, and others continue running independently.

---

### Implementation Steps

#### Phase 1: Database Decoupling (Critical)

**Current State:** Single PostgreSQL database shared by all apps.

**Required Actions:**

1. **Create separate databases for each service:**
   ```sql
   CREATE DATABASE pwaninet_users;
   CREATE DATABASE pwaninet_posts;
   CREATE DATABASE pwaninet_groups;
   CREATE DATABASE pwaninet_notifications;
   CREATE DATABASE pwaninet_courses;
   ```

2. **Update database configurations:**
   - Each service gets its own `DATABASES` setting
   - Example for users service:
     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.postgresql',
             'NAME': 'pwaninet_users',
             'USER': os.environ.get('DB_USER'),
             'PASSWORD': os.environ.get('DB_PASSWORD'),
             'HOST': os.environ.get('DB_HOST'),
             'PORT': '5432',
         }
     }
     ```

3. **Migrate foreign keys to service boundaries:**
   - Replace direct foreign keys with service IDs (UUIDs)
   - Example: Instead of `Post.author = ForeignKey(User)`, use `Post.author_id = CharField()` storing user UUID
   - Add validation to ensure referenced entities exist via API calls

4. **Update docker-compose.yml:**
   ```yaml
   services:
     db-users:
       image: postgres:15-alpine
       environment:
         - POSTGRES_DB=pwaninet_users
     db-posts:
       image: postgres:15-alpine
       environment:
         - POSTGRES_DB=pwaninet_posts
     # ... repeat for each service
   ```

**Estimated Effort:** 2-3 weeks

---

#### Phase 2: Extract Services into Independent Projects

**Required Actions:**

1. **Create separate Django projects for each service:**
   ```
   /services/
     ├── users-service/
     │   ├── manage.py
     │   ├── users-service/
     │   │   ├── settings.py
     │   │   ├── urls.py
     │   │   └── wsgi.py
     │   └── users/  # domain app
     ├── posts-service/
     ├── groups-service/
     ├── notifications-service/
     └── courses-service/
   ```

2. **Move domain-specific code:**
   - Copy `users/` app to `users-service/`
   - Copy `posts/` app to `posts-service/`
   - Repeat for all services

3. **Create API interfaces:**
   - Expose REST APIs for each service using Django REST Framework
   - Example users service endpoints:
     ```
     GET    /api/users/{id}/
     POST   /api/users/
     PUT    /api/users/{id}/
     DELETE /api/users/{id}/
     ```

4. **Implement service-to-service communication:**
   - Use HTTP/REST for synchronous calls
   - Use Redis pub/sub or message queue (RabbitMQ) for async events
   - Add circuit breakers to prevent cascading failures

**Estimated Effort:** 3-4 weeks

---

#### Phase 3: Implement API Gateway

**Required Actions:**

1. **Create API Gateway service:**
   - Use Django, FastAPI, or dedicated gateway (Kong, Traefik)
   - Routes requests to appropriate backend service
   - Handles authentication/authorization centrally

2. **Gateway routing configuration:**
   ```python
   # Example routing
   /api/users/*   → users-service:8001
   /api/posts/*   → posts-service:8002
   /api/groups/*  → groups-service:8003
   /api/notifs/*  → notifications-service:8004
   /api/courses/* → courses-service:8005
   ```

3. **Implement authentication:**
   - Move authentication to users service
   - Gateway validates JWT tokens from users service
   - Passes user context to downstream services

**Estimated Effort:** 2 weeks

---

#### Phase 4: Implement Fault Isolation

**Required Actions:**

1. **Service health checks:**
   ```python
   # Add to each service
   @api_view(['GET'])
   def health_check(request):
       return Response({'status': 'healthy'}, status=200)
   ```

2. **Circuit breakers:**
   - Use `pybreaker` or similar library
   - Prevent cascading failures when a service is down
   - Example:
     ```python
     from pybreaker import CircuitBreaker

     user_service_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)

     @user_service_breaker
     def get_user(user_id):
         # Call users service
         pass
     ```

3. **Retry logic with exponential backoff:**
   - Retry failed service calls with delays
   - Prevent overwhelming degraded services

4. **Bulkhead patterns:**
   - Limit concurrent calls to each service
   - Prevent resource exhaustion

5. **Graceful degradation:**
   - If posts service is down, show cached posts
   - If notifications service is down, queue notifications locally

**Estimated Effort:** 2 weeks

---

#### Phase 5: Data Consistency & Event-Driven Architecture

**Required Actions:**

1. **Implement event bus:**
   - Use Redis pub/sub or RabbitMQ
   - Services publish events for state changes
   - Example events:
     ```
     user.created
     user.updated
     post.created
     post.liked
     group.joined
     ```

2. **Event sourcing for cross-service data:**
   - Each service maintains its own data
   - Other services subscribe to relevant events
   - Example: When user updates profile, posts service updates author info

3. **Saga pattern for distributed transactions:**
   - Break complex operations into compensatable steps
   - Example: Creating a post with notification:
     ```
     1. Create post (posts service)
     2. Publish post.created event
     3. Notifications service receives event
     4. Create notification (notifications service)
     ```

**Estimated Effort:** 3-4 weeks

---

#### Phase 6: Independent Deployment

**Required Actions:**

1. **Containerize each service:**
   ```dockerfile
   # Dockerfile for users-service
   FROM python:3.12
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD gunicorn users-service.wsgi:application --bind 0.0.0.0:8001
   ```

2. **Update docker-compose.yml:**
   ```yaml
   services:
     users-service:
       build: ./services/users-service
       ports:
         - "8001:8001"
       depends_on:
         - db-users
         - redis
     posts-service:
       build: ./services/posts-service
       ports:
         - "8002:8002"
       depends_on:
         - db-posts
         - redis
     # ... repeat for all services
   ```

3. **Kubernetes deployment (optional):**
   - Create Helm charts for each service
   - Enable horizontal pod autoscaling
   - Implement rolling updates

**Estimated Effort:** 2 weeks

---

#### Phase 7: Monitoring & Observability

**Required Actions:**

1. **Centralized logging:**
   - Use ELK stack or Loki
   - All services send logs to central location
   - Add correlation IDs to trace requests across services

2. **Distributed tracing:**
   - Implement OpenTelemetry or Jaeger
   - Track requests across service boundaries
   - Identify performance bottlenecks

3. **Metrics collection:**
   - Use Prometheus + Grafana
   - Monitor service health, latency, error rates
   - Set up alerts for service failures

4. **Service dashboard:**
   - Real-time view of all service statuses
   - Quick identification of failing services

**Estimated Effort:** 2 weeks

---

### Service Communication Patterns

#### Synchronous Communication (HTTP/REST)

**Use when:** Immediate response required, data consistency critical

**Example:** Getting user profile
```python
# posts-service calls users-service
response = requests.get(
    'http://users-service:8001/api/users/{user_id}/',
    headers={'Authorization': f'Bearer {token}'}
)
user_data = response.json()
```

#### Asynchronous Communication (Message Queue)

**Use when:** Event notifications, eventual consistency acceptable

**Example:** Post created notification
```python
# posts-service publishes event
redis_client.publish('events', json.dumps({
    'event_type': 'post.created',
    'post_id': post.id,
    'author_id': post.author_id,
    'timestamp': now().isoformat()
}))

# notifications-service subscribes
pubsub = redis_client.pubsub()
pubsub.subscribe('events')
for message in pubsub.listen():
    event = json.loads(message['data'])
    if event['event_type'] == 'post.created':
        create_notification(event)
```

---

### Fault Isolation Strategies

#### 1. Database Isolation
- Each service has its own database
- One service's DB issues don't affect others
- Can scale databases independently

#### 2. Process Isolation
- Each service runs in separate process/container
- Memory leaks in one service don't affect others
- Can restart individual services

#### 3. Network Isolation
- Services communicate via well-defined APIs
- Network issues between services handled gracefully
- Can deploy services to different regions

#### 4. Resource Isolation
- CPU/memory limits per service (Kubernetes)
- One service can't starve others
- Cost optimization by scaling only needed services

---

### Rollout Strategy

#### Option A: Big Bang (Not Recommended)
- Migrate everything at once
- High risk, long downtime
- **Avoid this approach**

#### Option B: Strangler Fig Pattern (Recommended)
1. Start with least critical service (e.g., courses)
2. Extract and deploy as microservice
3. Route traffic through API gateway
4. Monitor and validate
5. Repeat for next service
6. Gradually decommission monolith

#### Option C: Hybrid Approach
- Keep monolith for core functionality
- Extract new features as microservices
- Gradual migration over time

---

### Summary of Required Changes

| Component | Current State | Target State | Effort |
|-----------|---------------|--------------|--------|
| Database | Single shared DB | Separate DB per service | 2-3 weeks |
| Code Structure | Single Django project | 5 independent projects | 3-4 weeks |
| Communication | Direct function calls | HTTP/REST + message queue | 2 weeks |
| Authentication | Django auth | JWT via users service | 1 week |
| Deployment | Single container | 5+ containers | 2 weeks |
| Monitoring | Basic logs | Distributed tracing | 2 weeks |
| Fault Tolerance | All-or-nothing | Circuit breakers, retries | 2 weeks |

**Total Estimated Effort:** 14-18 weeks

---

### Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Increased complexity | High | Start with 1-2 services, learn gradually |
| Data consistency issues | High | Implement event sourcing, sagas |
| Performance overhead | Medium | Use caching, optimize API calls |
| Operational overhead | High | Automate deployment, monitoring |
| Distributed debugging | High | Implement distributed tracing |

---

### Success Criteria for Microservices

- [ ] Each service can be deployed independently
- [ ] Failure of one service doesn't crash others
- [ ] Services communicate via well-defined APIs
- [ ] Authentication/authorization centralized
- [ ] Data consistency maintained via events
- [ ] Monitoring covers all services
- [ ] Deployment is automated
- [ ] Can scale services independently
- [ ] Circuit breakers prevent cascading failures
- [ ] Health checks detect service failures

---

### Recommendation

**Start with database decoupling** (Phase 1) as it's the foundation for everything else. Then extract the least critical service (courses) as a proof-of-concept before migrating core services (users, posts).

**Do not attempt full migration at once.** Use the strangler fig pattern to gradually replace the monolith while keeping the system operational.
