PwaniNet Notification Center
Developer Implementation Guide (DIG)

Version 1.0

1. Purpose

This document translates the Notification Engine Specification into an implementation plan for the existing PwaniNet codebase.

The implementation must:

preserve all existing notification functionality
migrate incrementally
reuse existing components
minimize duplicated logic
remain compatible with HTMX
remain compatible with Django templates
reuse canonical viewers

This guide complements—not replaces—the Notification Engine Specification.

2. Current Architecture Audit

Before changing any code, perform a complete audit.

Produce a report covering:

Backend
notification models
notification services
notification event creation
unread counters
notification preferences
notification serializers
HTMX endpoints
existing API endpoints
signals
Celery tasks
Frontend

Audit

notification dropdown
notification page
notification cards
notification JavaScript
HTMX partials
CSS
Bootstrap utilities
dark mode support
mobile layouts
Integration

Identify integrations with

Posts
Comments
Likes
Groups
Documents
Academic system
Profiles
Settings
Search

Output:

Notification Architecture Report

No implementation yet.

3. Migration Strategy

Never rewrite everything.

Use progressive replacement.

Stage 1

Keep

Existing Notification Engine

Replace

Notification UI

Stage 2

Replace rendering.

Stage 3

Replace interaction.

Stage 4

Remove obsolete code.

4. Folder Organization

Recommended

notifications/

    templates/

        notifications/

            center/

            cards/

            renderers/

            partials/

    static/

        notifications/

            js/

            css/

            renderers/

            animations/

            registry/


Never place rendering logic inside templates.

Templates remain declarative.

5. Backend Responsibilities

Backend owns

event generation
aggregation
permissions
priorities
notification payload
unread tracking
filtering
pagination

Backend never decides presentation.

6. Frontend Responsibilities

Frontend owns

rendering
animation
filtering UI
selection mode
optimistic updates
transitions
drawers
previews

Frontend never computes notification meaning.

7. Rendering Registry

Create

NotificationRegistry

Purpose

Map

Notification Type

↓

Renderer

Example

POST_LIKE

↓

SocialRenderer
DOCUMENT_SHARED

↓

DocumentRenderer
WORKSPACE_TASK

↓

WorkspaceRenderer

Never use

if(type=="LIKE")

if(type=="COMMENT")

if(type=="...")

The registry must be extensible.

8. Rendering Pipeline

Every notification follows the same path.

Notification

↓

Registry

↓

Renderer

↓

NotificationCard

↓

UI

Every notification.

Without exception.

9. Resource Rendering

Never duplicate viewers.

Instead

Notification

↓

Open Resource

↓

Canonical Viewer

Examples

Posts

↓

Post Viewer

Documents

↓

Document Viewer

Assignments

↓

Assignment Viewer

Workspace

↓

Workspace

Task

↓

Task Detail

Meeting

↓

Meeting Viewer

10. Existing Components To Reuse

Reuse whenever possible.

Examples

Profile Avatar

User Chips

Buttons

Dropdowns

Document Preview

Skeletons

Modal styles

Badges

Timestamp formatter

Dark mode variables

Never recreate existing UI.

11. Components To Build

Create

NotificationCard

ContextHeader

ActorStack

NotificationContent

ResourcePreview

MetadataRow

ActionBar

TimelineDivider

NotificationDrawer

NotificationToolbar

NotificationList

NotificationFilters

SelectionToolbar

Each component

One responsibility.

12. HTMX Integration

Use HTMX for

mark read
delete
archive
load more
filters
pagination
notification actions

Avoid unnecessary full-page reloads.

13. JavaScript Modules

Suggested modules

registry.js

renderer.js

notification-ui.js

notification-actions.js

selection.js

drawer.js

filters.js

aggregation.js

animations.js

live-updates.js

Each module should remain small and focused.

14. CSS Organization

Separate

layout.css

cards.css

toolbar.css

filters.css

drawer.css

animations.css

mobile.css

dark.css

Avoid a single large stylesheet.

15. Performance Rules

Never

rerender entire list
recreate cards
reload page

Always

update changed notification
reuse DOM
preserve scroll
lazy load previews
virtualize large lists when necessary
16. Accessibility

Must support

Keyboard

Screen Readers

Reduced Motion

ARIA labels

Visible Focus

Semantic HTML

17. Testing Checklist

After every implementation phase verify:

✓ unread count

✓ aggregation

✓ filters

✓ search

✓ mobile

✓ desktop

✓ dark mode

✓ HTMX updates

✓ optimistic updates

✓ notification preferences

✓ accessibility

18. Recommended Implementation Order

Do not implement by notification type.

Implement by infrastructure.

Step 1

Foundation

NotificationCard
NotificationList
Toolbar
Drawer
Step 2

Reusable Components

ContextHeader
ActorStack
Metadata
ActionBar
ResourcePreview
Step 3

Registry

Build

NotificationRegistry

Then

Renderer Interface
Step 4

Implement Renderers

Order:

Social

↓

Academic

↓

Documents

↓

Groups

↓

Study Groups

↓

Workspaces

↓

Security

↓

System

Each renderer should become operational before starting the next.

Step 5

Interaction

Implement:

Search
Filters
Bulk Selection
Drawer
Detail View
Keyboard Navigation
Step 6

Animations

Implement:

Arrival
Dismissal
Aggregation
Live Updates
Drawer
Badge Updates
Step 7

Optimization

Lazy loading
DOM reuse
Performance profiling
Accessibility audit
19. Rollback Strategy

Every implementation phase must remain reversible.

Use feature flags where practical so the legacy notification UI can coexist with the new one during migration.

20. Code Review Checklist

Before merging any notification-related change, verify:

No duplicated rendering logic.
No duplicated resource previews.
Registry updated for every new notification type.
Canonical viewers reused.
No business logic in UI components.
Components remain reusable.
Existing notification preferences continue to work.
Mobile and desktop layouts both verified.
21. Final Architecture
                    Notification Engine
                             │
                             ▼
                   Notification Service
                             │
                             ▼
                     Notification API
                             │
                             ▼
                 Notification Registry
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
        SocialRenderer  DocumentRenderer  WorkspaceRenderer
                │            │            │
                └────────────┼────────────┘
                             ▼
                     NotificationCard
                             │
      ┌──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼
 ContextHeader   ResourcePreview   ActionBar
      │              │              │
      └──────────────┴──────────────┘
                             ▼
                  Canonical Resource Viewer
My final recommendation

One additional document will save you a lot of implementation time:

Notification Payload Contract Specification

Up to now we've designed events, rendering, and UI. The missing piece is the exact JSON/data contract between the backend and frontend.

For every notification type, define:

{
  "id": "",
  "type": "WORKSPACE_TASK_ASSIGNED",
  "actor": {},
  "context": {},
  "resource": {},
  "metadata": {},
  "actions": [],
  "status": {},
  "rendering_hints": {}
}

If every notification conforms to the same payload contract, the frontend registry becomes almost trivial: each renderer simply consumes the standardized payload instead of handling custom data shapes. In my view, that payload contract is the final architectural piece before implementation begins.