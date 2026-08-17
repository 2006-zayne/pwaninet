# PwaniNet Groups Announcements — Full Implementation

You are implementing the Groups Announcements feature in the existing PwaniNet Django application.

This is an existing production-oriented codebase. Do not redesign unrelated systems, introduce a new frontend framework, or duplicate infrastructure that already exists.

We have already completed two investigations:

1. A technical architecture audit of Groups, notifications, push delivery, permissions, posts, documents, uploads, and the existing announcement placeholder.
2. A visual/component investigation of the existing notification, post, and document-card systems.

The implementation must follow the existing architecture discovered in those audits.

============================================================
## CORE PRODUCT REQUIREMENT
============================================================

Every PwaniNet Group has its own independent Announcements page.

Example:

/groups/<group_id>/announcements/

Announcements belong to the Group.

An Announcement is NOT a Post.

An Announcement is NOT a Notification.

An Announcement MAY eventually trigger notifications/push delivery, but that integration is intentionally OUT OF SCOPE for this implementation pass.

The core relationship is:

Group
  └── Announcement
        ├── author
        ├── title
        ├── content
        ├── priority
        ├── pinned state
        └── attachments

Later:

Announcement
    ↓
Notification/Event system
    ↓
Push delivery

Do NOT implement the notification/push bridge yet.

============================================================
## IMPORTANT ARCHITECTURAL RULES
============================================================

Before editing anything:

1. Re-open and inspect the actual current implementation.
2. Verify all file paths, class names, functions, templates, permission classes, and existing utilities.
3. Do not rely blindly on the audit report if the current repository differs.
4. Reuse existing PwaniNet infrastructure wherever appropriate.
5. Do not introduce React, Vue, Alpine, or another frontend framework.
6. Use the existing Django templates + HTMX + vanilla JavaScript architecture.
7. Do not create duplicate notification, push, file-upload, document-preview, avatar, permission, or storage systems.
8. Do not refactor unrelated systems.
9. Keep the implementation modular and easy to extend.
10. Preserve existing Groups functionality.

If an audit recommendation conflicts with the actual repository, follow the repository and explain the discrepancy before proceeding.

============================================================
## PHASE 1 — ANNOUNCEMENT DOMAIN MODEL
============================================================

Create the announcement domain model using the project's existing model conventions.

Inspect existing models first for:

- primary-key conventions
- timestamps
- UUIDs
- foreign-key conventions
- related_name conventions
- indexes
- ordering
- deletion behavior
- user references
- validation patterns

Create an Announcement model associated with:

- Group
- Author/User

The MVP announcement should support at minimum:

- title
- content/body
- group
- author
- priority
- is_pinned
- created_at
- updated_at

Priority should support:

NORMAL
IMPORTANT
URGENT

Use the project's preferred implementation for enumerated choices.

Do NOT add speculative fields merely because they might be useful later.

Do not implement scheduling, expiration, read tracking, reactions, comments, or analytics in this phase unless existing architecture makes one of them technically necessary.

### Ordering

Announcements should have deterministic ordering.

Pinned announcements must appear before non-pinned announcements within the appropriate page section.

Within each group, newer announcements should normally appear before older announcements.

Use database-level ordering/indexing where appropriate rather than relying exclusively on Python sorting.

### Group isolation

An announcement must belong to exactly one group.

Do not allow an announcement to become visible in another group's announcement page.

============================================================
## PHASE 2 — PERMISSIONS
============================================================

Reuse the existing Groups membership and permission architecture.

Do NOT create a parallel role system.

The current Groups architecture includes group roles and existing permission mechanisms. Inspect the actual code and use them.

For the MVP:

### Viewing

Approved group members can view announcements belonging to that group.

Unauthorized users must not be able to access another group's announcements simply by manipulating the URL.

### Creating

Group ADMIN users can create announcements.

Do not automatically grant creation permission to every role unless the existing product architecture or current implementation explicitly requires it.

### Editing

Only authorized administrators should be able to edit announcements.

At minimum, follow the existing Groups admin authorization model.

### Deleting

Only authorized administrators should be able to delete announcements.

### Pinning

Only authorized administrators should be able to pin/unpin announcements.

The authorization must be enforced server-side.

Do not rely on hiding buttons in templates as the permission mechanism.

============================================================
## PHASE 3 — BACKEND CRUD
============================================================

Implement clean announcement CRUD using the architecture already used by the Groups application.

First inspect whether the current Groups application uses:

- traditional Django views
- DRF
- HTMX endpoints
- a combination

Follow the existing architecture.

Do not introduce an API solely because APIs are theoretically useful.

The feature should support:

- list announcements
- create announcement
- edit announcement
- delete announcement
- pin announcement
- unpin announcement

Use appropriate HTTP methods and existing project conventions.

If an AnnouncementViewSet is appropriate because the project already uses DRF for this kind of resource, use a dedicated Announcement resource rather than stuffing unrelated CRUD into GroupViewSet.

Prefer conceptual separation:

GroupViewSet
    → Groups

AnnouncementViewSet
    → Announcements

But follow the actual project's established API conventions.

============================================================
## PHASE 4 — EXISTING ANNOUNCEMENT PAGE
============================================================

Use the existing:

groups/templates/groups/group_announcements.html

and existing announcement URL/view infrastructure.

Do not create a second announcements page.

Transform the existing placeholder into the actual announcement interface.

The page should conceptually become:

------------------------------------------------------------

Announcements                         [+ Create Announcement]

📌 Pinned Announcements

[Announcement Card]

[Announcement Card]


All Announcements

[Announcement Card]

[Announcement Card]

------------------------------------------------------------

The Create Announcement control must only appear to authorized administrators.

If there are no pinned announcements:

- hide the entire pinned section.

If there are no announcements:

- show the appropriate announcement empty state.

Do not show an unnecessary empty pinned section.

============================================================
## PHASE 5 — ANNOUNCEMENT COMPONENT ARCHITECTURE
============================================================

Announcements must have their own reusable rendering/component structure.

Do NOT build one giant HTML block inside group_announcements.html.

Follow the existing Django template partial architecture.

A possible structure is:

groups/templates/groups/partials/
    announcement_list.html
    announcement_card.html
    announcement_header.html
    announcement_content.html
    announcement_attachments.html
    announcement_actions.html
    announcement_empty_state.html
    announcement_section_header.html

However:

DO NOT create these exact files blindly.

First inspect existing partial/component organization and adapt the structure to PwaniNet's conventions.

The important requirement is separation of responsibilities.

Conceptually:

Announcement Card
    ├── Header
    │     ├── Avatar
    │     ├── Author
    │     ├── Group role
    │     └── Timestamp
    │
    ├── Metadata
    │     └── Priority
    │
    ├── Content
    │     ├── Title
    │     ├── Preview
    │     └── Expanded body
    │
    ├── Attachments
    │
    └── Admin actions

Do not create a rendering service/filter merely for symmetry with notifications.

If simple Django template partials are sufficient, use them.

Only introduce an announcement rendering abstraction if the actual implementation demonstrates that it is useful.

============================================================
## PHASE 6 — ANNOUNCEMENT CARD
============================================================

The announcement card is the primary UI component.

It should visually belong to PwaniNet.

Reuse visual patterns from:

- notification cards
- post cards
- document cards

But do NOT couple the Announcement domain model to Post or Notification models.

### Card structure

Conceptually:

------------------------------------------------------------

[Avatar] Jane Wanjiku                         [⋮]

         Group Admin · 2 hours ago

[Important]

📌 Meeting Rescheduled

The department meeting has been rescheduled to
Thursday at 2pm in Room 304. Please...

                                      [⌄]

[Attachment] [Attachment]

------------------------------------------------------------

Expanded:

------------------------------------------------------------

[Avatar] Jane Wanjiku                         [⋮]

         Group Admin · 2 hours ago

[Important]

📌 Meeting Rescheduled

The department meeting has been rescheduled to Thursday
at 2pm in Room 304.

Please bring your laptops and relevant materials.

The agenda includes:

1. Q3 budget review
2. Project timeline updates
3. Team capacity planning

                                      [⌃]

[Attachment] [Attachment]

------------------------------------------------------------

### Important

Do NOT copy the post card literally.

Do NOT turn announcements into social posts.

The announcement card should be visually related to existing PwaniNet cards while remaining its own component.

============================================================
## PHASE 7 — AUTHOR IDENTITY
============================================================

Every announcement must clearly identify its author.

This is important because a group may have multiple administrators.

Display:

- user's avatar
- user's display name/name
- group role
- relative timestamp

Conceptually:

[avatar] Jane Wanjiku
         Group Admin · 2 hours ago

Reuse existing profile/avatar rendering patterns.

Do not create duplicate avatar/profile components.

Use the actual group membership role when displaying the role.

Do not hardcode "Admin" if the actual role system can provide the correct role.

The author identity must come from the Announcement.author relationship.

============================================================
## PHASE 8 — CONTENT PREVIEW + EXPANSION
============================================================

Announcements should be collapsed by default.

The collapsed card shows:

- title
- truncated content preview
- attachment previews

The full announcement body should not be rendered visibly in the initial collapsed state.

Use the existing PwaniNet expand/collapse interaction patterns.

The user expands the announcement using a proper button with a chevron.

Collapsed:

[⌄]

Expanded:

[⌃]

### Accessibility

The control MUST be a semantic button.

Use:

aria-expanded="false"
aria-controls="announcement-content-<id>"

and update the values when toggled.

The accessible label should change appropriately:

"Expand announcement"

"Collapse announcement"

Keyboard activation must work through the button naturally.

Do not use a clickable div.

### Animation

Reuse the existing PwaniNet animation approach where appropriate.

A vanilla JavaScript implementation is acceptable.

Do not introduce a new animation library.

Do not hardcode a fragile max-height such as:

max-height: 1000px;

Prefer the existing project pattern using measured scrollHeight or another robust implementation.

### Preview

Prefer line-based truncation where practical.

Target approximately 3–5 visible lines.

Inspect existing content truncation utilities before implementing a new one.

Do not duplicate truncation logic if PwaniNet already has a suitable utility.

============================================================
## PHASE 9 — PRIORITY
============================================================

Support:

NORMAL
IMPORTANT
URGENT

### NORMAL

Keep visually quiet.

No unnecessary badge if the design looks cleaner without one.

### IMPORTANT

Use the project's existing warning/status visual language.

### URGENT

Use the project's existing danger/alert visual language.

Do NOT introduce arbitrary hardcoded colors if existing CSS variables or Bootstrap semantic classes are available.

Priority should be visually understandable without relying exclusively on color.

Use appropriate icons/text where necessary.

Priority should appear close to the announcement title/content rather than competing with the author header.

============================================================
## PHASE 10 — PINNING
============================================================

Pinned announcements appear in a dedicated section above normal announcements.

The same Announcement object must not be duplicated in the database.

The page should simply partition the queryset into:

Pinned
Non-pinned

or use an equivalent clean approach.

Pinned cards should show a pin indicator.

Preferred visual treatment:

- pin icon near the title
- subtle distinction if necessary
- do not make the entire card visually loud

Pinned announcements retain their priority indicator.

Admin users should have a Pin/Unpin action.

The server must enforce authorization.

============================================================
## PHASE 11 — ATTACHMENTS
============================================================

Announcements should support attachments using the existing PwaniNet attachment/file infrastructure.

DO NOT create a parallel file-storage system.

Before implementing attachments:

Inspect:

- existing upload system
- document models
- post attachments
- document previews
- preview_path behavior
- file validation
- existing storage
- existing thumbnail/preview generation

Reuse existing infrastructure where compatible.

### Images

Use the existing post media visual language.

Expected behavior:

1 image:
    large preview

2 images:
    two-column layout

3+ images:
    existing PwaniNet multi-image pattern where possible
    +N overlay for additional images

Do not copy post-specific business logic into announcements.

Extract/reuse only the presentation behavior if the architecture allows it.

### Documents/PDFs

Use existing document preview patterns.

Display:

- preview thumbnail where available
- fallback file icon where not available
- file type badge
- filename
- appropriate metadata if existing component supports it

PDF should visually resemble the existing PwaniNet document preview rather than a generic download link.

### Attachment interaction

Follow existing PwaniNet document/image interaction conventions.

Do not invent a new viewer.

If an existing document viewer can handle the file, link into it.

If an existing download mechanism exists, reuse it.

### Collapsed cards

Attachment previews should remain visible in collapsed state.

The user should be able to understand that an announcement contains attached material without expanding the text.

============================================================
## PHASE 12 — ADMIN ACTIONS
============================================================

Do not clutter every card with:

[Edit] [Delete] [Pin]

Instead, inspect the existing PwaniNet action-menu/dropdown pattern and use it where appropriate.

For authorized administrators, the menu should provide relevant actions:

- Edit
- Delete
- Pin / Unpin

For ordinary members:

- do not expose administrative actions.

Server-side permissions remain authoritative.

Use confirmation for destructive deletion if that is consistent with the existing application.

Do not add unnecessary social actions such as:

- Like
- Repost
- Share

Announcements are not posts.

============================================================
## PHASE 13 — CREATE ANNOUNCEMENT UI
============================================================

Use the existing Create Announcement entry point/modal if present.

Do not create a duplicate modal system.

The form should support at minimum:

- title
- content
- priority
- pin state if product/permission rules allow it
- attachments if the existing upload infrastructure can support them cleanly

The exact form implementation should follow existing PwaniNet form patterns.

Use existing validation conventions.

Server-side validation is required.

Do not trust client-side validation.

============================================================
## PHASE 14 — EDIT ANNOUNCEMENT
============================================================

Authorized admins should be able to edit:

- title
- content
- priority
- pin state
- supported attachments according to the existing attachment architecture

Reuse the create form where practical instead of creating two completely different forms.

Ensure editing an announcement does not accidentally change:

- author
- group
- ownership

unless explicitly intended.

============================================================
## PHASE 15 — DELETE ANNOUNCEMENT
============================================================

Implement deletion using the project's existing deletion conventions.

Before choosing hard delete vs soft delete:

Inspect existing PwaniNet domain models.

If the project has an established soft-delete pattern, follow it where appropriate.

Otherwise use the simplest safe behavior for the current MVP.

Do not invent a complicated recovery system.

Ensure deleted announcements no longer appear in normal group announcement listings.

============================================================
## PHASE 16 — RESPONSIVE DESIGN
============================================================

The page must work cleanly on:

- desktop
- tablet
- mobile

Reuse the project's existing breakpoints.

Do not automatically introduce a new 768px breakpoint if the project already has established breakpoints.

### Mobile

Ensure:

- card fits viewport
- no horizontal overflow
- author information remains readable
- title wraps correctly
- preview is readable
- expand button is touch-friendly
- attachment previews fit available width
- admin menu remains accessible

Do not shrink text excessively merely to fit content.

============================================================
## PHASE 17 — DARK MODE
============================================================

Announcements must support the existing PwaniNet dark mode.

Reuse existing CSS variables.

Inspect actual variable names before writing styles.

Do not hardcode white/black backgrounds if the existing theme system already provides semantic variables.

Verify:

- card background
- text
- secondary text
- borders
- badges
- attachment previews
- buttons
- menus
- empty states
- focus states

============================================================
## PHASE 18 — EMPTY STATES
============================================================

Use the existing empty-state component/pattern.

There should be an appropriate empty state when there are no announcements.

Do not show a separate empty pinned section when there are no pinned announcements.

If there are announcements but none are pinned:

Do:

All Announcements
[announcement cards]

Do NOT:

Pinned Announcements
"No pinned announcements"

unless the existing UX architecture strongly indicates otherwise.

============================================================
## PHASE 19 — HTMX / PARTIAL UPDATES
============================================================

Use HTMX where it fits existing PwaniNet patterns.

For example, appropriate operations may be:

- create announcement
- edit announcement
- delete announcement
- pin/unpin
- expand/collapse if the project already uses HTMX for similar content

However, do NOT use HTMX simply because it exists.

Expansion/collapse should remain client-side if no server request is needed.

Avoid unnecessary full-page reloads where the existing architecture supports partial updates cleanly.

After create/edit/delete/pin/unpin, the UI should update consistently with the project's established patterns.

============================================================
## PHASE 20 — CSS / JAVASCRIPT ORGANIZATION
============================================================

Follow the existing PwaniNet organization.

Do not automatically put everything into inline template styles.

If announcement-specific CSS becomes substantial, prefer a dedicated stylesheet such as:

static/css/groups/announcements.css

only if that matches the project's current static architecture.

Likewise, announcement interactions can live in:

static/js/groups/announcements.js

if that matches the project's organization.

Do not create a JavaScript framework.

Keep announcement JavaScript scoped.

Avoid global function pollution where practical.

============================================================
## PHASE 21 — SECURITY
============================================================

Before considering the implementation complete, verify:

1. A non-member cannot view another group's announcements.
2. A member cannot create an announcement unless authorized.
3. A member cannot edit another user's announcement unless authorized.
4. A member cannot delete announcements unless authorized.
5. A member cannot pin/unpin announcements unless authorized.
6. Group IDs cannot be manipulated to access another group's data.
7. Announcement IDs cannot be used to bypass group authorization.
8. Attachment access follows the existing file permission model.
9. Form validation is server-side.
10. CSRF protection remains enabled.
11. User-supplied announcement content is safely rendered.

Pay particular attention to rich text / HTML content.

Do not introduce unsafe `|safe` rendering unless the existing content sanitization pipeline guarantees safety.

============================================================
## PHASE 22 — DATABASE / PERFORMANCE
============================================================

Avoid N+1 queries.

The announcement list should efficiently retrieve:

- author
- group membership/role where needed
- attachments
- related data required by the card

Use:

select_related()

prefetch_related()

or the project's equivalent where appropriate.

Do not optimize blindly.

Inspect actual relationships first.

If useful, add appropriate database indexes for:

- group
- pinned state
- created_at

but only where justified by the query pattern.

============================================================
## PHASE 23 — TESTING
============================================================

Add tests following the existing PwaniNet testing conventions.

At minimum cover:

### Model

- announcement belongs to group
- author is recorded
- priority values
- pinned state
- ordering

### Permissions

- member can view
- non-member cannot view
- admin can create
- unauthorized member cannot create
- admin can edit
- unauthorized member cannot edit
- admin can delete
- unauthorized member cannot delete
- admin can pin/unpin
- unauthorized member cannot pin/unpin

### Views/API

- list announcements
- create
- edit
- delete
- pin/unpin
- invalid group access
- invalid announcement access

### Rendering

Verify:

- author identity appears
- role appears
- priority appears correctly
- pinned indicator appears
- collapsed preview appears
- expanded content is available
- admin actions are permission-aware
- attachments render using the intended components

### Security

Explicitly test object-level group isolation.

============================================================
## PHASE 24 — DO NOT IMPLEMENT YET
============================================================

Do NOT implement:

- push notifications
- notification-page integration
- PlatformEvent integration
- NotificationObject integration
- Web Push delivery
- scheduled announcements
- announcement expiration
- announcement read tracking
- announcement comments
- announcement reactions
- announcement analytics

These are future phases.

The only goal of this implementation is to establish a clean, stable Announcement domain and UI.

============================================================
## PHASE 25 — FINAL IMPLEMENTATION REVIEW
============================================================

Before finishing, inspect your own changes.

Check for:

- duplicated logic
- duplicated CSS
- unnecessary abstractions
- unused imports
- dead JavaScript
- permission gaps
- N+1 queries
- broken dark mode
- mobile overflow
- unsafe HTML rendering
- inconsistent naming
- missing CSRF protection
- missing tests
- accidental modifications to unrelated Groups functionality

Run the relevant test suite.

If the repository has linting/formatting/type checking, run the applicable existing checks.

Do not modify unrelated failing tests unless your changes caused the failure.

============================================================
## FINAL RESPONSE TO US
============================================================

When implementation is complete, report:

### 1. What was implemented

### 2. Files created

### 3. Files modified

### 4. Announcement model/data structure

### 5. Permission behavior

### 6. Routes/endpoints

### 7. Renderer/component structure

### 8. Create/edit/delete/pin behavior

### 9. Attachment implementation

### 10. Expand/collapse implementation

### 11. Responsive/dark-mode behavior

### 12. Tests added/run

### 13. Any known issues

### 14. Anything intentionally left for the notification/push phase

Do not claim something is implemented unless it actually exists and has been verified.

============================================================
## MOST IMPORTANT DESIGN PRINCIPLE
============================================================

The finished feature should feel like a native PwaniNet feature:

Existing Groups infrastructure
        +
Existing permission system
        +
Existing Django/HTMX architecture
        +
Existing notification visual language
        +
Existing post media patterns
        +
Existing document preview system
        +
New Announcement domain
        =
Clean PwaniNet Announcements

Do not build a parallel application inside PwaniNet.

Reuse existing infrastructure where appropriate, but keep the Announcement domain independent from Posts and Notifications.
