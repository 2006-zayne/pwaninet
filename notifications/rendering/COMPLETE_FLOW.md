# Complete Notification Flow: Event to Rendered Notification

This document traces the complete chain from event emission to the final rendered notification card.

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EVENT EMISSION                                      │
│                    (Platform Module emits event)                             │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EVENT ENGINE                                          │
│  • Records event with: event_id, actor, action, target, context, timestamp │
│  • Event is immutable and versioned                                         │
│  • Example: social.post.liked                                               │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION RULES ENGINE                                 │
│  • Evaluates event against notification rules                               │
│  • Determines: should notify? who? priority? delivery timing?               │
│  • Creates NotificationObject if rules match                                │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PREFERENCE ENGINE                                         │
│  • Evaluates recipient's notification preferences                            │
│  • Applies: muted workspaces, muted users, quiet hours, category settings  │
│  • Determines if notification is permitted for recipient                     │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGGREGATION ENGINE                                       │
│  • Combines related notifications to reduce noise                           │
│  • Aggregates based on: scope, window, rule                                │
│  • Updates notification with multiple actors                                │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION OBJECT CREATED                                │
│  • Stored in database with lifecycle state                                   │
│  • Contains: type, recipient, actors, context, resource, metadata           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PAYLOAD ADAPTER                                          │
│  • Converts NotificationObject to NotificationPayload                        │
│  • Maps database fields to Payload Contract structure                        │
│  • Adds: version, identity, intent, profile, components, navigation, etc.    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              NOTIFICATION PAYLOAD (Contract v1.0)                            │
│  {                                                                           │
│    version: "1.0",                                                          │
│    identity: { notification_id, recipient_id, event_id },                    │
│    type: "POST_LIKE",                                                       │
│    intent: "activity",                                                      │
│    lifecycle: { state: "LIVE", terminal: false },                            │
│    profile: { id: "POST_LIKE", version: "1.0" },                            │
│    actors: [{ id, name, username, avatar, verified }],                      │
│    context: { type, id, name, icon },                                       │
│    resource: { type, id, url, title },                                      │
│    message: { template, state, variables },                                 │
│    components: { context_header, actor_stack, content, preview, ... },      │
│    preview: { enabled, type, resource_id },                                 │
│    metadata: { read, priority, pinned, aggregated },                        │
│    actions: [{ id, label, style, enabled, url, method }],                 │
│    navigation: { primary, secondary },                                      │
│    permissions: { can_expand, can_reply, can_dismiss, ... },               │
│    analytics: { aggregation_count, view_count, interaction_count },         │
│    timestamps: { created_at, updated_at, read_at, completed_at },           │
│    raw_data: { ... },                                                        │
│    capabilities: { expandable, aggregatable, actionable, ... }              │
│  }                                                                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              RENDERING PROFILE RESOLVER                                      │
│  • Input: NotificationPayload                                               │
│  • Validates notification type                                               │
│  • Locates correct Rendering Profile from registry                           │
│  • Caches profile for performance                                            │
│  • Fallback to GENERIC profile for unknown types                             │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              RENDERING PROFILE (POST_LIKE)                                    │
│  {                                                                           │
│    id: "POST_LIKE",                                                         │
│    category: "social",                                                      │
│    intent: "activity",                                                      │
│    message_strategy: { template: "POST_LIKE", supported_states: [...] },     │
│    component_visibility: {                                                  │
│      context_header: false,                                                  │
│      actor_stack: true,                                                     │
│      content: true,                                                         │
│      preview: true,                                                         │
│      metadata: true,                                                        │
│      action_bar: false,                                                     │
│      status: false                                                          │
│    },                                                                       │
│    preview_strategy: { enabled: true, type: "POST", component: "..." },    │
│    action_strategy: { available: ["VIEW_POST"], primary: ["VIEW_POST"] },  │
│    status_strategy: { display: false },                                     │
│    interaction_strategy: {                                                  │
│      card: "OPEN_PRIMARY_RESOURCE",                                         │
│      actor_avatar: "OPEN_PROFILE",                                           │
│      preview: "OPEN_PREVIEW_RESOURCE"                                       │
│    },                                                                       │
│    navigation_strategy: {                                                    │
│      primary: { target: "POST_DETAIL", resource_id_field: "resource.id" }   │
│    },                                                                       │
│    aggregation_strategy: { enabled: true, scope: "PER_POST", window: "1h" }, │
│    expansion_strategy: { expandable: true, data_source: "actors" }           │
│  }                                                                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              NOTIFICATION MESSAGE ENGINE                                     │
│  • Input: NotificationPayload                                                │
│  • Uses: lifecycle, aggregation, actor count, templates, localization        │
│  • Determines message state: SINGLE, DUAL, FEW, MANY, HISTORICAL            │
│  • Selects template based on type and state                                 │
│  • Builds context variables: actor names, context, resource, etc.           │
│  • Generates final message: "Brian, Kevin and 18 others liked your post."   │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              COMPONENT VISIBILITY RESOLVER                                   │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves which components are visible                                     │
│  • Output: { context_header: false, actor_stack: true, preview: true, ... } │
│  • Renderer simply obeys - no conditional logic                             │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PREVIEW RESOLVER                                               │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves preview configuration                                            │
│  • Output: { enabled: true, type: "POST", component: "post_preview", ... }  │
│  • Reuses existing preview components                                       │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              ACTION RESOLVER                                                 │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves available actions based on lifecycle state                       │
│  • Handles terminal state actions (APPROVED, REJECTED, etc.)                 │
│  • Output: [{ id: "VIEW_POST", label: "View Post", style: "primary", ... }] │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              STATUS RESOLVER                                                 │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves status display based on lifecycle state                          │
│  • Uses profile's status_mapping                                            │
│  • Output: { display: false, text: null, state: "LIVE" }                     │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              INTERACTION RESOLVER                                            │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves interaction behavior for each region                            │
│  • Output: { card: "OPEN_PRIMARY_RESOURCE", actor_avatar: "OPEN_PROFILE", ... }│
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              NAVIGATION RESOLVER                                              │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves canonical navigation destinations                               │
│  • Extracts resource_id from payload using field path                       │
│  • Output: { primary: { target: "POST_DETAIL", resource_id: 42 }, ... }     │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              EXPANSION RESOLVER                                              │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves expansion behavior                                             │
│  • Output: { expandable: true, collapsed_layout: "actor_summary", ... }     │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              AGGREGATION RESOLVER                                            │
│  • Input: RenderingProfile, NotificationPayload                              │
│  • Resolves aggregation configuration                                       │
│  • Output: { enabled: true, scope: "PER_POST", window: "1h", rule: "ACTORS" }│
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PROFILE-DRIVEN RENDERER                                         │
│  • Orchestrates all resolvers in sequence                                   │
│  • Assembles complete rendering context                                      │
│  • No notification-specific conditionals                                    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              RENDERING CONTEXT (Complete)                                    │
│  {                                                                           │
│    payload: { ... },              // Original payload                         │
│    profile: { ... },              // Profile information                      │
│    message: "Brian, Kevin and 18 others liked your post.",                  │
│    components: { ... },           // Component visibility                     │
│    preview: { ... },              // Preview configuration                    │
│    actions: [                     // Available actions                        │
│      { id: "VIEW_POST", label: "View Post", style: "primary", ... }        │
│    ],                                                                        │
│    status: { ... },               // Status configuration                     │
│    interactions: { ... },         // Interaction behaviors                   │
│    navigation: {                  // Navigation targets                       │
│      primary: { target: "POST_DETAIL", resource_id: 42 }                     │
│    },                                                                        │
│    expansion: { ... },            // Expansion configuration                 │
│    aggregation: { ... }           // Aggregation configuration                │
│  }                                                                           │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              API RESPONSE (JSON)                                             │
│  • Rendering context serialized to JSON                                    │
│  • Sent to frontend via API endpoint                                         │
│  • Endpoint: /api/rendering/render/                                        │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              FRONTEND NOTIFICATION CARD RENDERER                             │
│  • Receives rendering context                                                │
│  • Renders components based on visibility flags                              │
│  • Displays message from Message Engine                                     │
│  • Shows preview using specified component                                  │
│  • Renders actions based on action configuration                            │
│  • Applies interactions based on interaction behavior                       │
│  • Handles navigation using navigation targets                               │
│  • Supports expansion based on expansion configuration                       │
│  • NO notification-specific conditionals - purely profile-driven            │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              FINAL RENDERED NOTIFICATION CARD                                │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ○○○ +18                    Brian, Kevin and 18 others liked your post│  │
│  │  [Post Preview Thumbnail]                                   2m ago    │  │
│  │                                                        [View Post]   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Integration Points

### 1. Event Engine → Notification Rules
- **File**: `notifications/event_processor.py`
- **Function**: Processes incoming platform events
- **Output**: Creates NotificationObject if rules match

### 2. NotificationObject → Payload Adapter
- **File**: `notifications/rendering/adapters.py` (existing, needs update)
- **Function**: Converts database models to NotificationPayload
- **Output**: NotificationPayload instance

### 3. Payload → Profile Resolver
- **File**: `notifications/rendering/profile_resolver.py`
- **Function**: Resolves RenderingProfile from registry
- **Output**: RenderingProfile instance

### 4. Profile + Payload → Resolvers
- **Files**: 
  - `notifications/rendering/message_engine.py`
  - `notifications/rendering/resolvers.py`
- **Function**: Each resolver processes specific aspect
- **Output**: Resolved configuration for each aspect

### 5. All Resolvers → Profile-Driven Renderer
- **File**: `notifications/rendering/profile_driven_renderer.py`
- **Function**: Orchestrates all resolvers
- **Output**: Complete rendering context

### 6. Renderer → API
- **File**: `notifications/rendering/api_views.py`
- **Function**: Exposes rendering via REST API
- **Output**: JSON response with rendering context

### 7. API → Frontend
- **Endpoint**: `/api/rendering/render/`
- **Method**: POST
- **Payload**: Notification data
- **Response**: Rendering context

## Data Flow Summary

1. **Event** → **NotificationObject** (database)
2. **NotificationObject** → **NotificationPayload** (adapter)
3. **NotificationPayload** → **RenderingProfile** (resolver)
4. **RenderingProfile** + **NotificationPayload** → **Resolvers** (8 parallel resolvers)
5. **All Resolver Outputs** → **Rendering Context** (renderer)
6. **Rendering Context** → **JSON Response** (API)
7. **JSON Response** → **Notification Card** (frontend)

## Critical Design Principles

1. **No Notification-Specific Conditionals**: Renderer only understands profiles
2. **Single Responsibility**: Each resolver handles one aspect
3. **Declarative Profiles**: Profiles contain configuration, not code
4. **Graceful Degradation**: Generic profile for unknown types
5. **Performance**: Profile caching, lazy loading support
6. **Extensibility**: Add new types by registering profiles only

## Missing Integration Points

To complete the chain, the following adapters need to be created/updated:

1. **Event → NotificationObject**: Already exists in `event_processor.py`
2. **NotificationObject → NotificationPayload**: Needs adapter in `adapters.py`
3. **NotificationPayload → API**: Helper function exists in `api_views.py`
4. **API → Frontend**: Frontend implementation needed

## Example: Complete Flow for POST_LIKE

```
1. Brian likes post #42
   ↓
2. Event: social.post.liked (actor: Brian, target: post#42)
   ↓
3. Rules Engine: Create notification for post owner
   ↓
4. Preference Engine: User allows like notifications
   ↓
5. Aggregation Engine: Check for existing like notifications on post#42
   ↓
6. NotificationObject created: type=LIKE, recipient=post_owner
   ↓
7. Payload Adapter: Convert to NotificationPayload
   {
     type: "POST_LIKE",
     actors: [{id: 25, name: "Brian", ...}],
     resource: {type: POST, id: 42},
     message: {template: "POST_LIKE", state: "FEW", variables: {actor_count: 9}}
   }
   ↓
8. Profile Resolver: Get POST_LIKE profile from registry
   ↓
9. Message Engine: Generate "Brian, Kevin and 7 others liked your post."
   ↓
10. Component Visibility: {actor_stack: true, preview: true, action_bar: false}
   ↓
11. Preview Resolver: {enabled: true, type: "POST", component: "post_preview"}
   ↓
12. Action Resolver: [{id: "VIEW_POST", label: "View Post"}]
   ↓
13. Status Resolver: {display: false}
   ↓
14. Interaction Resolver: {card: "OPEN_PRIMARY_RESOURCE", preview: "OPEN_PREVIEW_RESOURCE"}
   ↓
15. Navigation Resolver: {primary: {target: "POST_DETAIL", resource_id: 42}}
   ↓
16. Expansion Resolver: {expandable: true, data_source: "actors"}
   ↓
17. Aggregation Resolver: {enabled: true, scope: "PER_POST"}
   ↓
18. Profile-Driven Renderer: Assemble complete context
   ↓
19. API Response: JSON with rendering context
   ↓
20. Frontend: Render notification card with post preview, actor stack, "View Post" button
   ↓
21. Final Card: Brian, Kevin and 7 others liked your post. [Post Preview] [View Post]
```

This complete flow ensures that the renderer never contains notification-specific logic - it simply obeys the Rendering Profile.
