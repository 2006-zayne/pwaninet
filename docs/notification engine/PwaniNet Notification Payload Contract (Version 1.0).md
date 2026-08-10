PwaniNet Notification Payload Contract (Version 1.0)
Chapter 1 — Introduction
1.1 Purpose

The Notification Payload Contract defines the canonical JSON structure exchanged between the Notification Engine and all notification consumers.

It provides a stable, versioned interface that allows the frontend to render notifications without relying on notification-specific conditional logic.

The payload SHALL describe what a notification represents, while the renderer determines how it is presented using the Notification Rendering Profiles.

1.2 Design Principles

The payload SHALL be:

Declarative
Self-describing
Versioned
Extensible
Renderer-independent
Backward compatible

The payload SHALL NOT contain HTML, CSS classes, rendered markup, or presentation-specific strings.

Chapter 2 — Canonical Payload Structure

Every notification SHALL conform to the following structure.

NotificationPayload
│
├── version
├── identity
├── type
├── intent
├── lifecycle
├── profile
├── actors
├── context
├── resource
├── message
├── components
├── preview
├── metadata
├── actions
├── navigation
├── permissions
├── analytics
├── timestamps
└── raw_data

No notification type may omit these top-level sections. Sections with no applicable data should be present with empty values or null where appropriate, keeping the contract stable.

Chapter 3 — Payload Sections
3.1 Version
{
    "version": "1.0"
}

Purpose

Allows future payload evolution without breaking existing renderers.

3.2 Identity
{
    "identity": {
        "notification_id": "uuid",
        "recipient_id": 15,
        "event_id": "uuid"
    }
}

Required

notification_id
recipient_id
event_id
3.3 Notification Type
{
    "type": "POST_LIKE"
}

Examples

POST_LIKE

POST_COMMENT

FOLLOW

GROUP_JOIN_REQUEST

DOCUMENT_APPROVED

NEW_DEVICE_LOGIN

The type identifies the Rendering Profile to load.

3.4 Intent

Intent describes behavioral class.

{
    "intent": "activity"
}

Supported values

activity

workflow

awareness

alert

announcement

reminder

Intent assists the renderer in selecting interaction patterns.

3.5 Lifecycle
{
    "lifecycle": {
        "state": "PENDING",
        "terminal": false
    }
}

Examples

LIVE

UPDATED

PENDING

APPROVED

REJECTED

EXPIRED

COMPLETED

HISTORICAL

The renderer SHALL always derive visual state from the lifecycle object.

3.6 Rendering Profile
{
    "profile": {
        "id": "GROUP_JOIN_REQUEST",
        "version": "1.0"
    }
}

The renderer SHALL load the corresponding Rendering Profile before rendering the notification.

Chapter 4 — Actors

Actors describe who initiated the notification.

{
    "actors": [
        {
            "id": 25,
            "name": "Brian",
            "username": "brian",
            "avatar": "/media/avatar.jpg",
            "verified": true
        }
    ]
}

Aggregation notifications simply contain multiple actors.

No additional payload format is required.

Chapter 5 — Context

Context identifies the surrounding entity.

Example

{
    "context": {
        "type": "GROUP",
        "id": 8,
        "name": "Developers Kenya",
        "icon": "/media/group.png"
    }
}

Supported contexts

GROUP
DOCUMENT_REPOSITORY
SYSTEM
SECURITY
POST
PROFILE
Chapter 6 — Resource

Represents the primary object.

Example

{
    "resource": {
        "type": "POST",
        "id": 42
    }
}

Examples

POST

DOCUMENT

COMMENT

GROUP

PROFILE

SYSTEM
Chapter 7 — Message

The payload SHALL provide structured variables.

Never a final message.

{
    "message": {
        "template": "POST_LIKE",
        "state": "FEW",
        "variables": {
            "actor_count": 9,
            "others": 7
        }
    }
}

The Notification Message Engine SHALL generate the final text.

Chapter 8 — Components

This is one of the most important sections.

{
    "components": {
        "context_header": true,
        "actor_stack": true,
        "content": true,
        "preview": true,
        "metadata": true,
        "action_bar": false,
        "status": false
    }
}

Notice

The renderer no longer decides.

It simply obeys.

Chapter 9 — Preview
{
    "preview": {
        "enabled": true,
        "type": "DOCUMENT",
        "resource_id": 92
    }
}

Supported

POST

DOCUMENT

GROUP

PROFILE

NONE

The renderer selects the reusable preview component.

Chapter 10 — Metadata
{
    "metadata": {
        "read": false,
        "priority": "NORMAL",
        "pinned": false,
        "aggregated": true
    }
}

This section contains rendering metadata rather than business data.

Chapter 11 — Actions

Only actionable notifications populate this section.

{
    "actions": [
        {
            "id": "approve",
            "label": "Approve",
            "style": "primary",
            "enabled": true
        },
        {
            "id": "reject",
            "label": "Reject",
            "style": "danger",
            "enabled": true
        }
    ]
}

Once the lifecycle reaches a terminal state, the backend SHALL update this section instead of expecting the frontend to infer available actions.

Chapter 12 — Navigation
{
    "navigation": {
        "primary": {
            "target": "POST_DETAIL",
            "resource_id": 42
        },
        "secondary": {
            "target": "USER_PROFILE",
            "resource_id": 25
        }
    }
}

The frontend SHALL navigate using this object rather than constructing routes itself.

Chapter 13 — Permissions

Permissions define what the current recipient is allowed to do.

{
    "permissions": {
        "can_expand": true,
        "can_reply": false,
        "can_dismiss": true,
        "can_execute_actions": true
    }
}

This prevents the renderer from making authorization decisions.

Chapter 14 — Analytics

Optional telemetry.

{
    "analytics": {
        "aggregation_count": 9,
        "view_count": 1,
        "interaction_count": 2
    }
}

Useful for debugging and future insights without affecting rendering.

Chapter 15 — Timestamps
{
    "timestamps": {
        "created_at": "...",
        "updated_at": "...",
        "read_at": null,
        "completed_at": null
    }
}

Every lifecycle transition updates the appropriate timestamp.

Chapter 16 — Raw Data

The backend may include source-specific information that is not interpreted by the generic renderer but can be used by specialized components.

{
    "raw_data": {
        "comment_id": 89,
        "reaction": "LIKE",
        "document_version": 3
    }
}

The generic renderer SHALL ignore unknown keys in this section.

Engineer's Final Refinement

I would add one final top-level section that elevates the architecture further:

{
    "capabilities": {
        "expandable": true,
        "aggregatable": true,
        "actionable": false,
        "previewable": true,
        "navigable": true,
        "dismissible": true,
        "shareable": false
    }
}