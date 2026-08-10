PwaniNet Notification Engine Implementation Blueprint
Version 1.0
Mission Statement
Implement the Notification Engine incrementally while maintaining a fully functional PwaniNet application at every milestone. Each phase must be independently testable, minimize architectural debt, and preserve backward compatibility until the new engine fully replaces the legacy notification system.
Guiding Principles
1.	No Big Bang Rewrite
o	The existing notification system remains operational until its replacement is complete.
2.	Incremental Migration
o	Replace one responsibility at a time.
3.	One Source of Truth
o	All new notification generation must eventually flow through the Event Engine.
4.	Service-Oriented Design
o	Business logic belongs in services, not Django views or signals.
5.	Events First
o	Features publish events; they never create notifications directly.
Overall Roadmap
Phase 1  → Event Infrastructure
Phase 2  → Notification Models
Phase 3  → Rules Engine
Phase 4  → Aggregation Engine
Phase 5  → Preference Engine
Phase 6  → Delivery Engine (In-App)
Phase 7  → Frontend Integration
Phase 8  → Migration
Phase 9  → Optimization
Phase 10 → Future Extensions
Phase 1 — Event Infrastructure
Goal
Create the platform foundation.
Deliverables
·	Event model
·	Event publisher service
·	Event registry
·	Event types
·	Event validator
·	Event logging
Directory
notifications/

    events/

        registry.py

        publisher.py

        validator.py

        models.py

        schemas.py
Success Criteria
Instead of:
create_notification(...)
modules now do:
publish_event(...)
No notifications are generated yet.
Only events.
Phase 2 — Notification Models
Build the data layer.
Models
Notification

NotificationEvent

NotificationAction

NotificationDelivery

NotificationPreference

DeviceSubscription
Still no delivery.
Only persistence.
Phase 3 — Rules Engine
Now connect Events to Notifications.
Pipeline
Event

↓

Rules Engine

↓

Notification Object
Implement
Rule Registry

Rule Evaluator

Recipient Resolver

Priority Resolver

Category Resolver
At this stage
Notifications appear again.
Phase 4 — Aggregation Engine
Replace duplicate notifications.
Support
✓ Likes
✓ Comments
✓ Follows
✓ Join Requests
Not yet
AI summaries.
Phase 5 — Preference Engine
Implement
User Settings
↓
Context Settings
↓
Category Settings
↓
Type Settings
↓
Channel Settings
Initially
Only
In-App
Phase 6 — Delivery Engine
Since v1 only supports In-App
Only implement
InAppAdapter
Leave interfaces ready for
FCM
Email
Flutter
Phase 7 — Frontend
Desktop
Notification dropdown
Notification page
Badge counter
Real-time updates
Grouping
Overlapping avatars
Expand button
Actions
Approve
Reject
Accept
Decline
Read
Dismiss
Archive
Phase 8 — Migration
This phase replaces the legacy system.
Migration strategy
Old Notification Calls

↓

Publish Events

↓

Rules Engine

↓

New Notification Engine
Nothing else should create notifications.
Phase 9 — Performance
Introduce
Redis
Celery
Notification caching
Unread counters
Aggregation cache
Delivery queue
Background cleanup
Phase 10 — Future
Reserved
FCM
Email
Flutter
AI summaries
Semantic aggregation
Notification digest
Priority queues
Smart recommendations
Service Architecture
notifications/

    services/

        event_engine.py

        notification_service.py

        rules_engine.py

        aggregation_engine.py

        preference_engine.py

        delivery_engine.py

        state_machine.py
Database Layer
models.py

Notification

NotificationEvent

NotificationDelivery

NotificationPreference

NotificationAction

DeviceSubscription
API Layer
GET

/notifications/

GET

/notifications/unread/

POST

/notifications/read/

POST

/notifications/read-all/

POST

/notifications/action/

POST

/notifications/dismiss/

POST

/notifications/archive/

GET

/preferences/

PUT

/preferences/
WebSocket Layer
notification.created

notification.updated

notification.read

notification.dismissed

notification.deleted

badge.updated
Celery Tasks
Deliver Notification

Retry Delivery

Aggregate Notifications

Archive Old Notifications

Delete Expired Notifications

Send Digests
Testing Strategy
Every phase must end with four levels of testing:
Unit Tests
Each service independently.
Integration Tests
Entire pipeline.
UI Tests
Dropdown
Notification page
Badge
Grouping
Load Tests
Thousands of events
Hundreds of users
Redis
Celery
Definition of Done
A phase is complete only if:
·	Architecture matches the specification.
·	Unit tests pass.
·	Integration tests pass.
·	Existing features still work.
·	Performance remains acceptable.
·	Documentation is updated.
The Real Development Order
This is the sequence I would follow:
1. Audit current notification system

↓

2. Design new database models

↓

3. Build Event Engine

↓

4. Build Event Registry

↓

5. Publish first events

↓

6. Build Rules Engine

↓

7. Generate Notification Objects

↓

8. Build Aggregation

↓

9. Build Preferences

↓

10. Build Delivery

↓

11. Connect frontend

↓

12. Migrate legacy code

↓

13. Optimize

