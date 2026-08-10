Excellent. This is the last architectural chapter before implementation. After this, we should stop writing specifications and start building.

This chapter describes how the renderer thinks.

Chapter 10 — Notification Rendering Decision Engine
10.1 Purpose

The Notification Rendering Decision Engine is responsible for transforming a structured notification payload into a fully rendered notification card.

It SHALL coordinate all rendering subsystems while remaining independent of notification-specific business logic.

The Decision Engine SHALL NOT contain hardcoded rules for individual notification types.

Instead, it SHALL construct notification cards using the Notification Rendering Profiles and supporting rendering services.

10.2 Rendering Pipeline

Every notification SHALL pass through the following pipeline.

                    Notification Payload
                            │
                            ▼
                Rendering Profile Resolver
                            │
                            ▼
                Notification Message Engine
                            │
                            ▼
                 Component Visibility Resolver
                            │
                            ▼
                  Preview Component Resolver
                            │
                            ▼
                   Action Behaviour Resolver
                            │
                            ▼
                    Interaction Resolver
                            │
                            ▼
                    Navigation Resolver
                            │
                            ▼
                 Notification Card Renderer
                            │
                            ▼
                  Fully Rendered Notification

Each stage has a single responsibility.

10.3 Rendering Profile Resolver
Purpose

Identify the correct Rendering Profile for the incoming notification.

Example

POST_LIKE

↓

POST_LIKE Rendering Profile

or

DOCUMENT_APPROVED

↓

DOCUMENT_APPROVED Rendering Profile

The renderer SHALL never switch on notification types directly.

Incorrect

if(type=="POST_LIKE")...

Correct

payload

↓

profile resolver

↓

profile

↓

renderer
10.4 Notification Message Engine

Uses

lifecycle
aggregation
actor count
templates
localization

to generate

Brian liked your post.

or

Brian, Kevin and 18 others liked your post.

The renderer SHALL never construct these strings itself.

10.5 Component Visibility Resolver

Responsible for deciding which reusable components appear.

Input

Context Header:
Hidden

Preview:
Visible

Action Bar:
Hidden

Output

Actor Stack

↓

Content

↓

Preview

↓

Metadata

Nothing more.

10.6 Preview Resolver

Responsible for selecting the correct reusable preview component.

Example

Payload

Preview Type

↓

POST

Result

Post Preview Component

Payload

DOCUMENT

Result

Rich Document Preview Component

Payload

GROUP

Result

Group Preview Component

No notification shall create its own preview implementation.

10.7 Action Resolver

Determines

available actions
disabled actions
completed actions

Example

Pending

Approve

Reject

Approved

View Member

Rejected

View Profile

The renderer SHALL replace obsolete actions.

10.8 Status Resolver

Responsible for displaying lifecycle status.

Example

Pending

🟡 Pending

Approved

🟢 Approved

Rejected

🔴 Rejected

Completed

✅ Completed

Historical

Archived

Status presentation SHALL remain consistent across the application.

10.9 Interaction Resolver

Determines the behaviour of every interactive region.

Example

Region	Behaviour
Card	Primary Navigation
Actor Avatar	Open Profile
Preview	Open Resource
Context Header	Open Context
Action Button	Execute Action
Status Indicator	None

This allows every component to remain reusable.

10.10 Navigation Resolver

Determines the canonical destination.

Example

POST

↓

Post Detail
DOCUMENT

↓

Document Viewer
GROUP

↓

Group Detail
SYSTEM

↓

Announcement Detail

Navigation SHALL always use canonical viewers.

10.11 Notification Card Assembly

Once every resolver has completed,

the renderer assembles the notification.

Notification Card

├── Context Header
├── Actor Stack
├── Notification Content
├── Preview
├── Metadata
├── Action Bar
└── Status

No additional components shall be introduced without updating this specification.

10.12 Rendering Decision Flow

The following decision sequence SHALL be executed for every notification.

Receive Notification
        │
        ▼
Resolve Rendering Profile
        │
        ▼
Resolve Lifecycle
        │
        ▼
Resolve Message
        │
        ▼
Resolve Visible Components
        │
        ▼
Resolve Preview
        │
        ▼
Resolve Actions
        │
        ▼
Resolve Status
        │
        ▼
Resolve Navigation
        │
        ▼
Assemble Notification Card
        │
        ▼
Render

This order SHALL remain deterministic to ensure consistent rendering.

10.13 Graceful Degradation

If required data is unavailable, the renderer SHALL degrade gracefully.

Examples:

Missing Data	Behaviour
Actor avatar	Display default avatar
Preview image	Display placeholder preview
Deleted resource	Show "This item is no longer available" and disable resource navigation
Missing actor	Display "Unknown user"
Missing context	Hide Context Header
Invalid navigation target	Disable navigation and log the error

The notification itself SHALL still render whenever possible.

10.14 Performance Guidelines

To keep the notification center responsive, the renderer should follow these principles:

Rendering Profiles should be loaded once and cached.
Preview components should be lazily initialized when they become visible.
Expanded content should be fetched or rendered only on demand.
Avatar images should be lazy-loaded.
Reusable components should be shared across notification types.
Rendering decisions should rely on the payload rather than additional network requests.
10.15 Architectural Principles

The Notification Rendering Decision Engine SHALL adhere to the following principles:

Profile-driven — Rendering behavior is defined by Notification Rendering Profiles, not by conditional code.
Component-based — Notification cards are assembled from reusable UI components.
Declarative — The payload describes what to render; the renderer decides how to render it.
Single Responsibility — Each resolver performs exactly one task.
Extensible — Adding a new notification type should require only:
a new Rendering Profile,
a new message template (if needed),
and payload support from the Notification Engine.

No changes to the renderer's core orchestration should be required.

Engineer's Assessment

I think we've reached the point where the architecture is complete.

You now have specifications for:

✅ Notification Engine
✅ Notification Lifecycle
✅ Notification Sources
✅ Delivery Engine
✅ Rendering Profiles
✅ Card Specification
✅ Message Engine
✅ Rendering Decision Engine
✅ Social Notifications
✅ Group Notifications
✅ Document Notifications
✅ Security Notifications
✅ System Notifications