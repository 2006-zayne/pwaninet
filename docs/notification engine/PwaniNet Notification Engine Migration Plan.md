PwaniNet Notification Engine Migration Plan
Version 1.0
1. Purpose
This document defines the strategy for migrating PwaniNet from the current notification implementation to the new Event-Driven Notification Engine.
The migration shall:
·	Preserve all existing functionality.
·	Avoid service interruptions.
·	Minimize architectural debt.
·	Allow gradual adoption.
·	Support rollback if required.
2. Migration Principles
Principle 1 — No Big Bang Rewrite
The existing notification system shall remain operational until every major component of the new engine has been verified.
The old system is retired only after the new system proves stable.
Principle 2 — Feature Parity Before Feature Expansion
Do not implement FCM, email, AI summaries, or semantic aggregation until the new engine can reproduce every capability of the existing notification system.
Principle 3 — Dual Operation
During migration, both systems may coexist.
User Action
      │
      ▼
Publish Event
      │
      ├────────► Legacy Notification
      │
      └────────► New Notification Engine
Initially, only the legacy notification is shown to users while the new engine runs in parallel for validation.
3. Current System Audit
Before any code changes, document:
·	Notification models
·	Notification creation points
·	Django signals
·	Views
·	HTMX endpoints
·	AJAX endpoints
·	Channels/WebSocket consumers
·	Existing notification templates
·	Badge counter logic
·	Unread count calculation
·	Real-time update mechanism
Deliverable:
Notification System Inventory
This becomes the migration checklist.
4. Introduce the Event Layer
This is the first code change.
Do not replace notifications.
Instead:
create_notification(...)
becomes
publish_event(...)
create_notification(...)
The old notification still works.
The Event Engine simply records events.
This validates the event infrastructure without affecting users.
5. Validate Event Coverage
Every existing notification must now produce a corresponding Platform Event.
Create a coverage matrix.
Feature	Event Published	Verified
Like	✓	✓
Comment	✓	✓
Reply	✓	✓
Follow	✓	✓
Mention	✓	✓
Group Join	✓	✓
Assignment	✓	✓
Document Upload	✓	✓
No feature proceeds until every notification source publishes events.
6. Introduce Notification Objects
Next, enable the Rules Engine.
Pipeline becomes:
Platform Event

↓

Rules Engine

↓

Notification Object
The Notification Object is stored in the database.
Users still receive notifications from the legacy system.
The new Notification Objects exist only for comparison.
7. Parallel Validation
For every notification:
Legacy Result
↓
New Result
↓
Compare
Verify:
·	Recipient
·	Type
·	Priority
·	Context
·	Summary
·	Timestamp
Any mismatch is logged for investigation.
8. Replace Notification Creation
Once validation is complete:
Replace:
create_notification(...)
with:
publish_event(...)
The Rules Engine becomes the sole creator of Notification Objects.
This is the first major architectural transition.
9. Enable Aggregation
Aggregation remains disabled until the new engine is stable.
Then enable it gradually.
Recommended rollout:
Likes

↓

Comments

↓

Follows

↓

Group Requests

↓

Workspace Events
Each stage should be monitored independently.
10. Enable Preference Engine
Import existing user notification settings.
Verify:
·	Mute behavior
·	Category settings
·	Context settings
·	Read status
No user should lose their preferences during migration.
11. Replace Delivery
The Delivery Engine now becomes responsible for:
·	In-App notifications
·	Badge updates
·	Notification dropdown
·	Notification page
The legacy delivery mechanism is removed only after successful validation.
12. Frontend Migration
Replace frontend data sources incrementally.
Migration order:
1.	Badge counter
2.	Notification dropdown
3.	Notification page
4.	Notification actions
5.	Notification grouping
6.	Live updates
Avoid replacing multiple UI components simultaneously.
13. Legacy Removal
Only after all validation passes:
Remove:
·	Legacy notification service
·	Legacy helper functions
·	Obsolete signals
·	Unused models
·	Duplicate API endpoints
Archive the old implementation before deletion.
14. Rollback Strategy
Every migration phase must support rollback.
If a critical issue is detected:
Disable New Engine

↓

Enable Legacy Engine

↓

Investigate

↓

Retry Migration
No irreversible changes should occur during intermediate phases.
15. Success Criteria
The migration is complete when:
·	All notifications originate from Platform Events.
·	The Rules Engine is the only notification creator.
·	Aggregation is operational.
·	User preferences are respected.
·	The Delivery Engine handles all in-app notifications.
·	The legacy notification system has been removed.
·	Existing functionality remains intact.
·	Performance is equal to or better than the legacy implementation.
16. Risk Register
Risk	Mitigation
Duplicate notifications	Feature flags and dual-run validation
Missing events	Event coverage matrix and automated tests
Incorrect recipients	Parallel comparison with legacy outputs
Performance degradation	Incremental rollout and profiling
Data inconsistency	Database transactions and audit logs
User preference loss	Migrate preferences before switching delivery
17. Feature Flag Strategy
Introduce feature flags to control each subsystem independently.
Recommended flags:
EVENT_ENGINE_ENABLED

RULES_ENGINE_ENABLED

AGGREGATION_ENABLED

PREFERENCE_ENGINE_ENABLED

DELIVERY_ENGINE_ENABLED

LIVE_NOTIFICATIONS_ENABLED

NOTIFICATION_ACTIONS_ENABLED
This allows gradual activation and immediate rollback without redeploying the application.
18. Testing Gates
A phase cannot advance unless all of the following pass:
·	Unit tests
·	Integration tests
·	Notification parity tests (legacy vs. new)
·	UI tests
·	Load tests
·	Manual verification of representative user flows

