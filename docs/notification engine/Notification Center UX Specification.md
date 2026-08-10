Notification Center UX Specification
Chapter 1 — Design Principles
1.1 Goals
The Notification Center should feel like a modern Activity Center rather than a simple list of notifications.
It must:
·	Scale from 10 notifications to 50,000.
·	Support every feature of the new Notification Engine.
·	Work equally well on desktop and mobile.
·	Require minimal clicks.
·	Encourage quick actions.
·	Never overwhelm the user.
1.2 Keep Existing Design Language
Do NOT redesign:
·	Page title
·	Navigation
·	Sidebar
·	Theme
·	Typography
·	Buttons
·	Colors
·	Existing responsive breakpoints
The Notification Center must appear as a natural evolution of the existing PwaniNet interface.
1.3 Layout Philosophy
Current:
Header

↓

Notification

Notification

Notification

Notification
New:
Header

↓

Toolbar

↓

Smart Feed

↓

Cards

↓

Actions
The feed becomes richer while remaining familiar.
1.4 Information Hierarchy
Every notification card should answer these questions, in order:
Who?

↓

What happened?

↓

Where?

↓

When?

↓

What can I do?
That order should remain consistent for all notification types.
1.5 Notification Card Anatomy
Every notification card consists of six logical regions.
┌────────────────────────────────────────────┐

① Actors

② Notification Content

③ Context

④ Timestamp

⑤ Actions

⑥ Status

└────────────────────────────────────────────┘
This structure remains consistent regardless of notification type.
1.6 Density
Notifications should be compact enough to allow scanning, but spacious enough to support inline actions.
Target height:
·	Standard: ~88–110px
·	Rich notifications: dynamic height
·	Expanded notifications: auto height
Avoid oversized cards unless content requires it.
1.7 Progressive Disclosure
The user should not see every detail immediately.
Collapsed notification:
Brian commented on your post.

2 min ago

Reply
Expanded:
Brian commented

Full comment

Replies

Related notifications

View discussion
Only reveal complexity when requested.
1.8 Consistency
Every notification must follow the same interaction rules.
Example:
Clicking the card:
→ Opens detail drawer.
Clicking an action:
→ Executes the action directly.
Clicking the context chip:
→ Opens the related object.
The behavior should never depend on notification type.
1.9 Accessibility
The Notification Center shall support:
·	Keyboard navigation
·	Screen readers
·	Focus indicators
·	High-contrast themes
·	Reduced-motion preferences
Unread state must never rely solely on color.
1.10 Mobile First
The Notification Center should work naturally on phones.
Cards become vertically stacked.
Action buttons wrap if necessary.
The detail view opens as a full-screen sheet instead of a side drawer.
1.11 Real-Time Updates
Incoming notifications should never abruptly reorder the interface while the user is reading.
Instead:
──────────────

3 New Notifications

──────────────
appears at the top.
The feed refreshes only when the user taps it or scrolls to the top.
This prevents the page from "jumping."
1.12 Empty State
Instead of showing:
No notifications
Show something more useful.
🎉

You're all caught up.

We'll notify you when something new happens.
Optionally provide a shortcut to notification preferences.
1.13 Loading State
Never show blank pages.
Use skeleton placeholders matching the shape of notification cards.
Avoid loading spinners for the main feed.
1.14 Error State
If notifications cannot be loaded:
Unable to load notifications.

Retry
Do not clear previously loaded notifications unless the data is invalid.
1.15 Future Compatibility
The UI must be able to support without redesign:
·	AI summaries
·	Semantic aggregation
·	Push notification history
·	Workspace notifications
·	Video meeting invitations
·	Live collaboration updates
·	Voice messages
·	Whiteboard session invitations
·	Future delivery channels
These features should extend the interface rather than replace it.
Engineer's Notes
Architect, I want to establish one rule that will guide every chapter after this:
The UI should reflect the Notification Engine, not hide it.
For example, if the engine knows that a notification is:
·	aggregated,
·	actionable,
·	tied to a workspace,
·	high priority,
·	or generated from multiple events,
the UI should expose those capabilities in a clear way instead of flattening everything into identical rows.
That principle will make the Notification Center feel more intelligent while staying consistent with PwaniNet's existing design language.


Chapter 2 — Notification Card Component
2.1 Purpose
The Notification Card is the primary UI component used to present a Notification Object within the Notification Center.
Every notification, regardless of origin, shall be rendered using this component.
Specialized notification types may extend the component but shall not replace its core structure.
2.2 Design Goals
The Notification Card shall:
·	Present information clearly.
·	Support aggregation.
·	Support inline actions.
·	Be compact.
·	Scale to desktop and mobile.
·	Support future notification types without redesign.
2.3 Card Layout
The card is divided into seven regions.
┌──────────────────────────────────────────────────────────────┐

① Actor Region

② Content Region

③ Context Region

④ Metadata Region

⑤ Action Region

⑥ Status Indicators

⑦ Expandable Details (Optional)

└──────────────────────────────────────────────────────────────┘
Every notification follows this structure.
2.4 Actor Region
The left side contains the actor(s) responsible for the notification.
Single actor
○

Brian
Aggregated notification
○○○ +12
Rules
·	Display up to 3 overlapping avatars.
·	Remaining actors shown as "+N".
·	Avatar click opens the user's profile.
·	If an actor has no profile photo, use initials.
2.5 Content Region
The content region is the primary message.
Structure
Actor(s)

↓

Action

↓

Target
Examples
Brian liked your post.
Kevin mentioned you in CSC221.
15 students commented on your assignment.
Important words such as usernames, document names, workspace names, and course names should be visually emphasized using the existing typography rules rather than introducing new styles.
2.6 Context Region
Every notification belongs somewhere.
Display a compact context chip beneath the main content.
Examples
[CSC221]
[Project Alpha]
[Document Repository]
[Study Group]
Rules
·	Chip is clickable.
·	Uses existing badge/chip styling.
·	Hidden if no meaningful context exists.
2.7 Metadata Region
The upper-right corner displays metadata.
Example
2m

Today

Yesterday

Jul 28
Future enhancements may include priority indicators without changing the layout.
2.8 Status Indicators
Unread
●
Read
No indicator.
High Priority
!
Critical
🔴
These indicators should be subtle and must not dominate the card.
2.9 Action Region
Inline actions are displayed only when the notification supports them.
Examples
Group Join Request
Approve

Reject

View Profile
Workspace Invitation
Accept

Decline

Open
Document Notification
Open

Bookmark

Download
Meeting Reminder
Join

Agenda

Dismiss
Actions must not require leaving the Notification Center unless necessary.
2.10 Expandable Region
Some notifications contain additional information.
Collapsed
Brian commented on your post.
Expanded
Brian commented

"This solution works much better..."

Replies

Related Activity

View Discussion
Expansion should animate smoothly and preserve the user's scroll position.
2.11 Aggregated Cards
Aggregated notifications display a summary.
Collapsed
○○○ +18

21 students liked your document.

View Details
Expanded
Brian

Kevin

Alice

Mary

John

...

View All
The Aggregation Engine supplies the actor list; the UI controls presentation.
2.12 Rich Notifications
Certain notifications may include previews.
Document
📄

Operating Systems Notes.pdf
Image
🖼

Photo Preview
Meeting
📹

Project Meeting

Starts in 10 minutes
Workspace
📁

Backend API Sprint
Rich previews should use existing card styling and not introduce separate layouts.
2.13 Interaction Model
Clicking different areas of the card should have consistent behavior.
Area	Action
Card body	Open detail drawer
Avatar	Open profile
Context chip	Open related context
Action button	Execute action
Timestamp	No action
Expand control	Expand/collapse details
2.14 Hover Behavior (Desktop)
On hover:
·	Slight elevation.
·	Background tint using the existing theme.
·	Action buttons become more prominent.
·	Cursor changes only on interactive elements.
Avoid excessive animations.
2.15 Mobile Behavior
On mobile:
·	Cards occupy full width.
·	Action buttons wrap to a second line if needed.
·	Expanded content pushes downward instead of opening a side panel.
·	Swipe gestures are reserved for quick actions (future enhancement).
2.16 Visual States
Each card supports the following states:
Unread

Read

Hovered

Focused

Expanded

Loading

Disabled

Action Pending
Transitions between states should be smooth but unobtrusive.
2.17 Notification-Type Icons
Each notification category may include a small leading icon alongside the content.
Examples:
Type	Icon
Like	❤️
Comment	💬
Mention	@
Follow	👤
Assignment	📚
Document	📄
Meeting	📹
Workspace	📁
Group	👥
System	⚙️
Security	🛡️
These icons complement, but do not replace, actor avatars.
2.18 Animation Rules
Animations should communicate state changes, not decorate the interface.
Examples:
·	New notification fades and slides into the feed.
·	Aggregated notification updates its actor stack smoothly.
·	Action buttons show loading feedback while processing.
·	Unread indicator fades after the notification becomes read.
Animation durations should match the existing PwaniNet motion system.
2.19 Performance Guidelines
To keep the Notification Center responsive:
·	Lazy-load rich previews.
·	Virtualize very long notification lists.
·	Avoid rerendering unchanged cards.
·	Update only affected cards during real-time events.
Engineer's Recommendation
I think one feature could become a signature element of PwaniNet:
Live Updating Cards
Instead of removing and recreating a notification when it changes, update the existing card in place.
Example:
Brian liked your post.
Two seconds later:
Brian and Kevin liked your post.
Then:
○○○ +12

15 students liked your post.
The card evolves smoothly without moving or flashing. Users keep their reading position, and the Notification Center feels alive rather than constantly refreshing.
2.20 Resource Preview Region (New)
Every notification may optionally include a preview of the object it references.
Updated card anatomy:
┌────────────────────────────────────────────────────────────────────────────┐

① Actor Region

② Content Region

③ Context Region

④ Metadata Region

⑤ Action Region

⑥ Status Indicators

⑦ Resource Preview

⑧ Expandable Details

└────────────────────────────────────────────────────────────────────────────┘
Posts
If the notification references a post, show a compact rounded-square preview (about 56–64 px).
Text-only post
┌──────┐
│ Aa   │
└──────┘
Display the post's gradient/theme or first few words so the user immediately recognizes it.
Image post
┌──────┐
│ 🖼️   │
└──────┘
Show the first image thumbnail.
If multiple images:
┌──────┐
│ 🖼️ +4│
└──────┘
Video post
┌──────┐
│ ▶️    │
└──────┘
Use the generated video thumbnail with a play icon overlay.
Document Repository
┌──────┐
│ 📄   │
└──────┘
or a miniature first-page preview if available.
Groups
Instead of a content preview, display the group avatar.
┌──────┐
│ CSC  │
└──────┘
or
┌──────┐
│ 👥   │
└──────┘
if the group has no custom avatar.
Workspaces
Exactly as you suggested.
Display the workspace logo or icon.
┌──────┐
│ 📁   │
└──────┘
or
┌──────┐
│ Alpha│
└──────┘
if the workspace has branding.
This instantly tells users which workspace generated the activity.
Study Groups
┌──────┐
│ 📚   │
└──────┘
or the study group's avatar.
Courses
Display the course icon or generated badge.
┌──────┐
│ CSC221│
└──────┘
This helps distinguish notifications from different courses at a glance.
Preview Priority
If multiple resources are associated with a notification, display the most relevant one.
Priority order:
1.	Post media thumbnail
2.	Document preview
3.	Workspace avatar
4.	Group avatar
5.	Course badge
6.	Generic notification icon
This keeps the preview meaningful.
Interactive Behavior
The preview should be clickable independently of the card.
Examples:
·	Click the thumbnail → Open the post or media viewer.
·	Click the workspace icon → Open the workspace.
·	Click the document preview → Open the document viewer.
·	Click the group avatar → Open the group.
The rest of the card still opens the notification detail drawer.
Performance
To avoid slowing down the feed:
·	Reuse cached thumbnails.
·	Lazy-load previews as cards enter the viewport.
·	Use low-resolution thumbnails in the feed.
·	Upgrade to high resolution only when opening the detail drawer.
One More Idea
I think we can make the Notification Center even more recognizable by using context accent bars.
A thin 3–4 px colored bar on the left edge of the card indicates the notification's domain.
For example:
·	🔵 Academic
·	🟢 Workspace
·	🟣 Groups
·	🟠 Documents
·	❤️ Social
·	🔴 Security
·	⚙️ System
The bar is subtle but gives users instant visual categorization before they even read the text.
Imagine a feed where you can immediately spot:
·	Blue cards → course activity.
·	Green cards → project work.
·	Purple cards → group discussions.
·	Orange cards → document repository updates.
Combined with actor avatars on the left and resource previews on the right, each notification card becomes identifiable in a fraction of a second while still fitting naturally into PwaniNet's existing design language.


Chapter 3 — Notification Feed
3.1 Purpose
The Notification Feed is the primary container that presents Notification Cards to the user.
It is responsible for organizing notifications into a logical, chronological, and context-aware activity stream while supporting filtering, grouping, searching, and real-time updates.
The feed shall remain responsive regardless of the number of notifications stored.
3.2 Design Goals
The Notification Feed shall:
·	Present notifications chronologically.
·	Minimize information overload.
·	Highlight unread activity.
·	Support aggregation naturally.
·	Scale efficiently.
·	Preserve user context during updates.
3.3 Feed Structure
The Notification Center consists of:
Page Header

↓

Toolbar

↓

Filter Bar

↓

Feed Sections

↓

Notification Cards

↓

Load More / Infinite Scroll
The Notification Feed occupies the primary content area while preserving the existing PwaniNet page layout.
3.4 Timeline Organization
Notifications shall be grouped by time rather than displayed as one continuous list.
Default sections:
Now

Earlier Today

Yesterday

This Week

Last Week

Earlier
Benefits:
·	Easier scanning.
·	Reduced cognitive load.
·	Better orientation.
The section headers remain visible while scrolling until the next section begins.
3.5 Unread Section
Unread notifications should always appear before read notifications within the same timeline section.
Example:
Earlier Today

● Brian mentioned you

● Kevin commented

● Assignment uploaded

────────────

Read Earlier Today

Brian liked your post

Mary followed you
The separation should be subtle rather than creating two completely independent lists.
3.6 Intelligent Grouping
The feed should visually group related notifications.
Example:
CSC221

Assignment uploaded

Document added

Meeting announced
instead of scattering them across the feed.
This is a presentation enhancement only.
The underlying Notification Objects remain independent.
3.7 Real-Time Insertions
When new notifications arrive while the user is viewing the feed:
Do not automatically insert them into the list.
Instead display:
────────────────────────

3 New Notifications

View

────────────────────────
Selecting "View" inserts the new notifications at the appropriate position.
This prevents sudden layout shifts.
3.8 Infinite Scrolling
The Notification Feed shall use cursor-based pagination with infinite scrolling.
Behavior:
·	Load the initial page.
·	Fetch additional notifications as the user nears the bottom.
·	Display loading placeholders while fetching.
·	Preserve scroll position.
Avoid traditional numbered pagination.
3.9 Search
The Notification Center shall support instant search.
Search should match:
·	User names.
·	Workspace names.
·	Group names.
·	Course names.
·	Document names.
·	Notification content.
Example:
Searching:
Operating Systems
returns notifications related to that document, assignment, or course.
3.10 Filter Bar
The Filter Bar appears directly below the toolbar.
Suggested filters:
All

Unread

Academic

Workspace

Groups

Social

Documents

Mentions

System
Filters should reuse the existing chip/button styling already used elsewhere in PwaniNet.
Only one primary filter is active at a time.
3.11 Advanced Filters
A secondary filter menu provides more granular filtering.
Examples:
Priority:
High

Normal

Low
Status:
Unread

Read

Dismissed

Archived
Date:
Today

This Week

This Month
Context:
CSC221

Project Alpha

Study Group 5
These filters are optional and remain hidden until requested.
3.12 Sorting
Default sorting:
Newest first.
Future options:
·	Oldest first.
·	Priority.
·	Workspace.
·	Academic.
·	Unread first.
The default should remain unchanged for consistency.
3.13 Feed Density
The Notification Feed supports two display modes.
Comfortable
Large cards

More spacing

Rich previews
Compact
Smaller spacing

Reduced metadata

More notifications visible
This preference should be stored per user.
3.14 Empty Feed
When no notifications exist:
🎉

You're all caught up.

We'll notify you when something new happens.

[Notification Preferences]
The page should never feel broken or unfinished.
3.15 Loading State
While loading:
·	Show skeleton cards.
·	Preserve page structure.
·	Avoid layout shifts.
Do not use a centered loading spinner for the entire feed.
3.16 Error Recovery
If loading fails:
Unable to load notifications.

Retry
Previously loaded notifications remain visible.
3.17 Sticky Toolbar
On desktop:
The toolbar and filter bar remain visible while scrolling.
Only the notification list scrolls.
On mobile:
The toolbar scrolls away naturally to maximize available space.
3.18 Live Synchronization
When a notification changes:
Examples:
·	Aggregation count increases.
·	Action completed.
·	Notification marked read elsewhere.
·	Join request approved.
Only the affected card updates.
The feed must not rerender completely.
3.19 Cross-Device Synchronization
If the same user has multiple sessions:
Example:
Laptop:
Brian mentioned you.

Unread.
Phone:
User opens notification.
↓
Laptop immediately updates:
Brian mentioned you.

Read.
Synchronization should occur through the existing WebSocket infrastructure.
3.20 Performance Targets
The feed should remain responsive with:
·	100,000+ stored notifications.
·	Thousands of active users.
·	Continuous real-time updates.
To achieve this:
·	Cursor pagination.
·	Virtualized rendering (when needed).
·	Incremental updates.
·	Cached unread counts.
·	Lazy loading.
3.21 Future Extensions
The feed layout should support without redesign:
·	AI summaries.
·	Daily digest sections.
·	Workspace activity feeds.
·	Meeting recordings.
·	Voice messages.
·	Whiteboard session updates.
·	Video call invitations.
These additions should integrate into the existing feed rather than requiring new layouts.
Engineer's Recommendation
I think there's one feature that could make the Notification Center feel unique:
Focus Mode
Instead of showing every notification equally, users could switch to a focused view.
Example:
Focus

• Mentions

• Assignments

• Workspace Tasks

• Meeting Invitations
Everything else is temporarily hidden, not deleted.
This would be especially valuable during exams or when working on a project, allowing users to concentrate on actionable notifications while filtering out lower-priority activity such as likes or follows.
One Enhancement I'd Make
I'd also add a "Today Summary" card at the very top whenever there has been significant activity.
Example:
Today

━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Activity Summary

• 18 new notifications

• 5 assignments published

• 3 workspace updates

• 12 students interacted with your content

━━━━━━━━━━━━━━━━━━━━━━━━━━
This is not a notification. It's a feed component generated from the Notification Engine that helps users quickly understand what happened before diving into individual cards.



Chapter 4 — Notification Detail Experience
4.1 Purpose
The Notification Detail Experience provides users with additional context and actions without unnecessarily leaving the Notification Center.
Whenever possible, users should complete their intended action directly from the Notification Center.
4.2 Design Philosophy
The notification feed should remain visible.
Instead of replacing the page:
Feed

↓

New Page
Use a split experience.
Desktop
┌───────────────────────┬─────────────────────────────┐
│                       │                             │
│ Notification Feed     │ Notification Details        │
│                       │                             │
│ ○ Brian liked...      │ Full notification           │
│ ○ Kevin replied...    │                             │
│ ○ Assignment...       │ Comments                    │
│                       │                             │
│                       │ Actions                     │
│                       │                             │
└───────────────────────┴─────────────────────────────┘
The feed never disappears.
4.3 Mobile Experience
Mobile cannot support a permanent split view.
Instead
Notification Feed

↓

Bottom Sheet

or

Fullscreen Sheet
The transition should preserve the user's position.
4.4 Detail Layout
The detail panel contains:
Header

↓

Actors

↓

Timeline

↓

Referenced Content

↓

Actions

↓

Related Notifications

↓

Metadata
4.5 Header
Contains
← Back

Notification Type

•••
The three-dot menu includes:
·	Mark unread
·	Archive
·	Copy link
·	Report (if applicable)
4.6 Actors Section
Display every participant.
Example
Brian

Kevin

Alice

+12 Others
Each actor:
·	Avatar
·	Name
·	Profile link
·	Role (optional)
4.7 Timeline
Every notification should explain how it evolved.
Example
10:32

Brian liked your post.

↓

10:34

Kevin liked your post.

↓

10:38

Alice liked your post.

↓

10:42

Notification aggregated.
This works beautifully with the engine you designed because aggregation already keeps the source events.
4.8 Referenced Content
Instead of saying
Brian commented on your post
Show the actual post.
Example
Your Post

──────────────────────

Building the notification engine...

──────────────────────

Brian

"This architecture is clean."
The user immediately understands the context.
4.9 Workspace Example
Workspace

Project Atlas

Backend Sprint

Task

API Authentication

Assigned by

Brian
Buttons
Open Workspace

Open Task

Reply
4.10 Document Example
Document

Operating Systems Notes

Uploaded by

Kevin

Course

CSC221
Buttons
Preview

Bookmark

Download
4.11 Assignment Example
Assignment

Operating Systems

Due

Tomorrow

Lecturer

Dr. Mwangi
Buttons
Open

Submit

Discussion
4.12 Actions Section
The Notification Engine already supports actions.
Display them prominently.
Examples
Join Request
Approve

Reject
Invitation
Accept

Decline
Meeting
Join

View Agenda
4.13 Related Notifications
This is one feature I think users will appreciate.
Instead of isolated notifications
Show
Related Activity

Kevin replied

Brian liked

Mary bookmarked

Workspace updated
All linked to the same resource.
It transforms notifications into an activity history.
4.14 Metadata
Collapse this section by default.
Display
Created

Delivered

Seen

Read

Priority

Notification ID

Event ID
Most users won't care, but developers and administrators will find it useful.
4.15 Keyboard Navigation
Desktop shortcuts:
↑ Previous notification

↓

Next notification

Enter

Open

Esc

Close detail panel

R

Reply

M

Mark read

D

Dismiss
4.16 Live Updates
Suppose the detail drawer is open.
Someone else comments.
Instead of closing and reopening:
Append
New Activity

Kevin commented.
Smoothly.
4.17 Transition Animation
Desktop
Feed

↓

Slide drawer

↓

Content fades in
Mobile
Bottom sheet rises

↓

Expandable to fullscreen
Avoid page reloads.
4.18 State Preservation
When the drawer closes:
Remember
·	Scroll position
·	Expanded cards
·	Applied filters
·	Search query
Users should never lose their place.
Engineer's Recommendation
I think there's one feature that could make PwaniNet stand out, especially once Workspaces are live.
Context Switch
Imagine opening a notification:
Brian assigned you

Backend Authentication

Workspace Alpha
Instead of simply opening the workspace:
A button says:
Continue in Workspace →
Selecting it doesn't just navigate.
It restores the exact context:
·	Opens Workspace Alpha.
·	Opens the Backend board.
·	Highlights the Authentication task.
·	Opens the task details.
The same idea applies elsewhere:
·	Posts: Open directly to the highlighted comment. 
·	Documents: Open to the referenced page in the document viewer. 
·	Group chats: Jump to the exact message. 
·	Video meetings (future): Join the meeting room immediately. 
·	Whiteboards (future): Open the active whiteboard session. 
The notification becomes a context restoration point, not just a link. That aligns perfectly with the event-driven architecture you've built and makes notifications genuinely useful rather than merely informative.

Chapter 5 — Notification Actions
This chapter is important because your Notification Engine already supports Notification Actions. The UI should make them feel like first-class interactions, not buttons bolted onto a notification.
5.1 Purpose
Notification Actions allow users to respond to events directly from the Notification Center without unnecessary navigation.
Actions shall execute securely, provide immediate feedback, and update the notification state in real time.
5.2 Design Principles
Actions should be:
·	Immediate
·	Context-aware
·	Non-destructive by default
·	Reversible where possible
·	Consistent across notification types
Users should complete common tasks from the Notification Center.
5.3 Action Placement
Every actionable notification reserves a dedicated action row.
Example:
┌─────────────────────────────────────────────┐

Brian invited you to Project Atlas

[ Accept ] [ Decline ]

└─────────────────────────────────────────────┘
Actions always appear at the bottom of the card.
5.4 Action Categories
Primary
The main action.
Examples:
·	Open
·	Accept
·	Approve
·	Join
·	View
Uses the existing primary button style.
Secondary
Supporting actions.
Examples:
·	Decline
·	Reject
·	Bookmark
·	Reply
Uses the existing secondary button style.
Passive
Utility actions.
Examples:
·	Dismiss
·	Mark Read
·	Copy Link
Displayed as text buttons or icons.
5.5 Immediate Feedback
After selecting an action:
Approve

↓

Button becomes disabled

↓

Loading indicator

↓

Success animation

↓

Card updates
The notification should not disappear immediately unless that behavior is intentional.
5.6 Optimistic Updates
For fast operations:
Example:
Mark Read
Update the UI immediately.
If the server fails:
Restore the previous state and show an error.
5.7 Confirmation Dialogs
Only destructive actions require confirmation.
Examples:
Delete Notification

Leave Workspace

Reject Join Request
Actions like Accept, Reply, and Open should execute immediately.
5.8 Multi-Step Actions
Some actions require additional input.
Example:
Reply
Instead of redirecting:
Reply

↓

Inline input

↓

Send
The user never leaves the Notification Center.
5.9 Action Progress
Long-running actions display progress.
Example:
Downloading...

██████████ 65%
Useful for:
·	Documents
·	Large media
·	Workspace exports (future)
5.10 Action Results
After success:
✓ Approved
The notification updates in place.
Example:
Before:
Approve

Reject
After:
Approved

View Member
No full page refresh.
5.11 Undo Support
Where appropriate:
Post bookmarked

Undo
Visible for a few seconds.
Applicable to:
·	Bookmark
·	Mark Read
·	Dismiss
·	Archive
Not applicable to security-sensitive actions.
5.12 Notification-Type Actions
Notification	Actions
Like	View Post
Comment	Reply, View Discussion
Follow	View Profile, Follow Back
Mention	Reply, View Context
Assignment	Open, Submit, Discuss
Document	Preview, Download, Bookmark
Group Invite	Join, Decline
Workspace Invite	Accept, Decline
Task Assignment	Open Task, Comment
Meeting	Join, Agenda
Security Alert	Review Activity, Secure Account
Every notification type defines its own valid actions.
5.13 Disabled Actions
If an action becomes unavailable:
Example:
Meeting Expired

[Join] (disabled)

Reason:

Meeting has ended.
Explain why instead of silently removing the action.
5.14 Multiple Actions
If a notification exposes many actions:
Display only the most important.
Example:
Open

Reply

•••
The overflow menu contains less common actions.
This keeps cards clean.
5.15 Action Permissions
The UI should never display actions the user cannot perform.
Example:
Only group administrators see:
Approve

Reject
Regular members see:
View Request
Permissions come from the backend; the frontend simply reflects them.
5.16 Action History
The detail drawer records completed actions.
Example:
Activity

────────────

Join Request Created

↓

Approved by You

↓

Member Joined

────────────
This creates a useful audit trail.
5.17 Accessibility
Actions must support:
·	Keyboard navigation
·	Screen readers
·	Focus indicators
·	Loading announcements
·	Disabled state announcements
5.18 Future Compatibility
The action framework should support future capabilities without redesign.
Examples:
·	Start Video Call
·	Join Whiteboard
·	Ask AI
·	Assign Task
·	Merge Workspace Changes
·	Review Pull Request
·	Generate Summary
These are simply new action types.
Engineer's Recommendation
This is where I think PwaniNet can feel different from most platforms.
Introduce Smart Action Chains.
Example:
A notification says:
Kevin uploaded Operating Systems Notes.
Instead of offering only:
Preview
Present a sequence of relevant actions:
Preview

↓

Bookmark

↓

Share

↓

Ask AI about this document (future)
Or for a workspace task:
Open Task

↓

Mark In Progress

↓

Comment

↓

Submit for Review
The Notification Center becomes a place where users complete work, not just read updates.

Chapter 6 — Notification Toolbar & Filters
6.1 Purpose
The Notification Toolbar provides centralized controls for navigating, filtering, searching, and managing notifications.
It serves as the command center for the Notification Center while preserving the existing PwaniNet page layout and styling.
6.2 Layout
The toolbar sits directly beneath the existing page header.
┌──────────────────────────────────────────────────────────────┐

Notifications                          🔍 Search

--------------------------------------------------------------

 All  Academic  Groups  Workspaces  Documents  Social  System

--------------------------------------------------------------

☑ Unread      Today ▼      Sort ▼            ⚙      ✓ Read All

└──────────────────────────────────────────────────────────────┘
The toolbar remains visually lightweight and uses existing PwaniNet buttons, chips, and dropdown styles.
6.3 Search
The search bar is always visible on desktop.
Placeholder:
Search notifications...
Search should match:
·	User names
·	Course names
·	Workspace names
·	Group names
·	Document titles
·	Assignment titles
·	Notification text
·	Tags
·	Context names
Example:
CSC221
returns every notification related to that course.
6.4 Primary Filters
Primary filters represent notification domains.
All

Academic

Groups

Workspaces

Documents

Social

System
Each filter displays a badge if unread notifications exist.
Example
Academic (5)

Groups (2)

Documents (1)
These counts update in real time.
6.5 Secondary Filters
Secondary filters refine the current domain.
Examples
Academic
Assignments

Announcements

Lecturers

Units

Study Groups
Workspace
Tasks

Meetings

Comments

Members

Files
Social
Likes

Comments

Mentions

Followers

Posts
These appear only after selecting the primary filter.
6.6 Quick Toggles
Frequently used toggles remain visible.
Examples
☑ Unread

☑ Action Required

☐ High Priority

☐ Mentioned Me
Users should be able to combine these with any filter.
6.7 Date Filter
A compact dropdown provides time filtering.
Today

Yesterday

Last 7 Days

Last 30 Days

This Semester

Custom Range
"This Semester" integrates naturally with PwaniNet's academic focus.
6.8 Sort Options
Default
Newest First
Additional options
Oldest First

Priority

Most Recent Activity

Unread First
Sorting should never alter grouping by timeline unless explicitly requested.
6.9 Bulk Actions
Visible when one or more notifications are selected.
Mark Read

Dismiss

Archive

Delete

Export (Future)
Bulk actions operate only on visible, selected notifications.
6.10 Selection Mode
Desktop
Checkbox appears on hover.
Mobile
Long press enters selection mode.
Header changes
12 Selected

Mark Read

Dismiss

Cancel
No navigation occurs while in selection mode.
6.11 Notification Preferences Shortcut
The toolbar includes a settings button.
Selecting it opens the Notification Preferences panel without leaving the Notification Center.
Users can immediately modify:
·	Delivery channels
·	Categories
·	Workspace preferences
·	Group preferences
·	Quiet hours (future)
·	Push notification settings (future)
6.12 Saved Views
Allow users to save frequently used filter combinations.
Examples
Assignments

Workspace Tasks

Unread Mentions

Project Atlas

CSC221
A saved view restores:
·	Filters
·	Sort order
·	Search text
·	Toggles
This is especially useful for students managing multiple courses and workspaces.
6.13 Filter Chips
Active filters appear beneath the toolbar.
Example
Academic

CSC221

Unread

Today
Each chip includes a remove button.
A "Clear All" control removes every active filter.
6.14 Responsive Behavior
Desktop
Everything remains visible.
Tablet
Secondary controls collapse into dropdown menus.
Mobile
Toolbar becomes:
🔍

Filters

Sort

More
Search expands when tapped.
6.15 Keyboard Shortcuts
Desktop
Shortcut	Action
/	Focus search
F	Open filters
S	Open sort
Ctrl+A	Select visible notifications
Esc	Clear search or exit selection mode
6.16 Persistent State
When returning to the Notification Center, restore:
·	Search query
·	Selected filters
·	Sort order
·	Scroll position
·	Expanded cards
·	Active timeline section
Users should continue where they left off.
6.17 Smart Suggestions
When appropriate, display contextual suggestions above the feed.
Examples
You have 4 unread assignment notifications.
Project Atlas has 8 new updates.
CSC221 has new announcements.
These are informational and disappear when no longer relevant.
6.18 Notification Statistics
A compact statistics section may appear near the toolbar.
Example
Unread

12

Action Required

3

Today

27
Selecting a statistic applies the corresponding filter.
6.19 Future Extensions
The toolbar should support additional controls without redesign.
Examples:
·	AI Summary
·	Smart Filters
·	Voice Search
·	Natural-language search
·	Workspace-specific views
·	Academic calendar integration
These appear as optional additions rather than structural changes.
6.20 Performance
Toolbar interactions should feel instantaneous.
Guidelines:
·	Debounce search input.
·	Cache recent filter combinations.
·	Update unread counters incrementally.
·	Avoid full feed reloads when only filters change.
·	Keep filter state in the URL where practical, allowing bookmarked or shareable filtered views.
Engineer's Recommendation
Architect, I think one feature could become extremely valuable once PwaniNet grows.
Notification Perspectives
Instead of only filtering by category, let users switch between activity perspectives.
Example:
Everything

Student Life

Academic Focus

Workspace Focus

Documents

My Courses

My Projects

Action Required
These are curated combinations of filters rather than simple categories.
For example:
·	Academic Focus automatically shows assignments, lecturer announcements, study groups, and course documents while hiding likes and follows. 
·	Workspace Focus prioritizes tasks, mentions, meetings, approvals, and collaboration updates. 
·	Action Required surfaces only notifications that require a decision or response.

PwaniNet Notification Rendering Specification
Chapter 1 — Rendering Architecture
This specification sits between the Notification Engine and the Notification Center.
Event

↓

Notification Engine

↓

Notification Object

↓

Rendering Specification

↓

Notification Card

↓

Notification Detail

↓

Canonical Resource Viewer
The Rendering Specification tells the frontend how each notification should be presented.
1.1 Rendering Pipeline
Every notification passes through the same rendering pipeline.
Notification Object

↓

Determine Notification Type

↓

Resolve Rendering Profile

↓

Generate Notification Card

↓

Attach Available Actions

↓

Resolve Resource Preview

↓

Apply Accent Style

↓

Render Feed
No notification should bypass this process.
1.2 Rendering Profile
Every notification type has a Rendering Profile.
Example
COMMENT_CREATED

↓

Card Layout

↓

Comment Icon

↓

Post Thumbnail

↓

Reply Button

↓

Blue Accent

↓

Post Detail Drawer
The frontend never guesses how to display a notification.
1.3 Rendering Profile Fields
Each notification type defines:
Notification Type

Display Name

Category

Priority

Accent

Actor Layout

Preview Type

Aggregation

Supported Actions

Detail Drawer

Canonical Viewer

Deep Link

Push Eligible

Email Eligible
This profile is effectively a configuration contract between backend and frontend.
1.4 Canonical Viewer Rule
Every notification must resolve to exactly one canonical viewer.
Resource	Viewer
Post	Post Detail Viewer
Document	Document Viewer
Workspace	Workspace Viewer
Task	Task Detail Viewer
Assignment	Assignment Viewer
Group	Group Viewer
Study Group	Study Group Viewer
User	Profile Viewer
Course	Course Page
The Notification Center never creates alternative viewers.
1.5 Preview Resolution
Every notification determines the appropriate preview.
Priority:
Media Thumbnail

↓

Document Preview

↓

Workspace Avatar

↓

Group Avatar

↓

Course Badge

↓

User Avatar

↓

Generic Icon
Only one preview occupies the Resource Preview Region.
1.6 Actor Resolution
The renderer determines the actor layout.
Examples
Single actor
Brian
Two actors
Brian and Kevin
Multiple
Brian, Kevin and 13 others
Avatar stacking follows the design defined in Chapter 2.
1.7 Context Resolution
Every notification exposes its context.
Examples
CSC221
Project Atlas
Document Repository
Study Group 5
Context chips always navigate to their canonical destination.
1.8 Accent Resolution
Each notification category has an accent.
Not bright colors.
Subtle colors consistent with the current theme.
Example mapping
Academic

Blue

Workspace

Green

Groups

Purple

Documents

Orange

Social

Pink / Red

Security

Red

System

Gray
The accent appears as a thin left border and optional icon highlight.
1.9 Action Resolution
The Rendering Profile decides which actions appear.
Example
Notification Type

↓

Allowed Actions

↓

Permission Check

↓

Visible Actions
The renderer never shows actions the backend has not authorized.
1.10 Detail Resolution
Selecting a notification opens the appropriate detail experience.
Example
Comment

↓

Comment Drawer
Document Upload

↓

Document Viewer
Workspace Meeting

↓

Meeting Detail
The renderer does not decide the content; it routes to the appropriate component.
1.11 Aggregation Resolution
Aggregated notifications define:
·	aggregation title
·	actor stack
·	preview selection
·	action behavior
·	expansion content
Example
Collapsed
○○○ +18

21 students liked your document.
Expanded
Brian

Kevin

Alice

...

View All Activity
The renderer consumes the aggregation data provided by the Notification Engine.
1.12 State Resolution
Each notification may render differently depending on state.
Supported states:
Unread

Read

Pending Action

Completed

Expired

Dismissed

Archived
Example:
A meeting invitation that has expired should display an inactive "Join" action with an explanation rather than hiding it.
1.13 Rendering Priority
The renderer should prioritize information in this order:
1.	Actor(s)
2.	Event description
3.	Resource preview
4.	Context
5.	Available actions
6.	Metadata
7.	Status indicators
This ensures consistent scanning across all notification types.
Engineer's Recommendation
Architect, from this point onward I would stop talking about "notifications" in general.
Instead, we start defining Rendering Profiles one by one.
For example:
·	POST_LIKED
·	POST_COMMENTED
·	POST_MENTIONED
·	USER_FOLLOWED
·	DOCUMENT_UPLOADED
·	DOCUMENT_APPROVED
·	COURSE_ASSIGNMENT_PUBLISHED
·	GROUP_JOIN_REQUEST
·	GROUP_JOIN_APPROVED
·	WORKSPACE_INVITATION
·	WORKSPACE_TASK_ASSIGNED
·	WORKSPACE_MEETING_REMINDER
·	STUDY_GROUP_CREATED
Each profile will be a complete contract specifying:
·	Card appearance
·	Actor layout
·	Resource preview
·	Accent
·	Aggregation rules
·	Inline actions
·	Detail experience
·	Canonical viewer
·	Push notification eligibility
·	Future AI summary compatibility
Chapter 2 — Social Notification Rendering Profiles
These notifications originate from normal social interactions.
2.1 POST_LIKED
Purpose
Notify a user that another user liked one of their posts.
Category
Social
Priority
Low
Card
○

Brian liked your post.

2 minutes ago

                     ┌────────────┐
                     │ Thumbnail  │
                     └────────────┘

View Post
Actors
Supports aggregation.
Examples
Brian liked your post.
Brian and Kevin liked your post.
Brian, Kevin and 17 others liked your post.
Resource Preview
Uses the Post Preview component.
Priority
·	image
·	video
·	document attachment
·	text preview
·	post gradient
Never create a second preview implementation.
Context
Optional
If inside a group
[CSC221]
If inside Workspace
[Project Atlas]
Actions
View Post
Future
React
Aggregation
Yes.
Aggregate by
Post
Window
30 minutes
Detail Experience
Open Post Detail Viewer.
Highlight the likes section.
Push Eligible
Yes.
Email Eligible
No.
2.2 POST_COMMENTED
Priority
Medium
Card
○

Kevin commented on your post.

"The authentication flow..."

                     ┌────────────┐
                     │ Thumbnail  │
                     └────────────┘

Reply

View Discussion
Preview
Post Preview
Detail
Open
Post Detail Viewer
Automatically scroll to the comment.
Highlight the comment.
Actions
Reply

View Discussion
Aggregation
Yes.
Group by
Post
Example
Brian

Kevin

Mary

commented on your post.
Drawer
Displays
·	post
·	comment
·	replies
·	related comments
Push
Yes.
2.3 COMMENT_REPLY
Purpose
Someone replied to your comment.
Priority
Medium
Card
Brian replied to your comment.

"Exactly."

Reply

Open Thread
Viewer
Post Detail Viewer
Automatically expands the thread.
Aggregation
No.
Each reply deserves individual attention.
2.4 USER_MENTIONED
Priority
High
Card
Kevin mentioned you.

"@Zayne can you review..."

Reply

Open
Preview
Post Preview
Highlight
Mentioned username.
Viewer
Post Detail Viewer
Scroll directly to mention.
Aggregation
No.
Mentions are individual.
Push
Yes.
2.5 USER_FOLLOWED
Priority
Low
Card
○

Brian started following you.

View Profile

Follow Back
Preview
Actor Avatar
Viewer
Profile
Aggregation
Yes.
Brian, Kevin and 9 others started following you.
2.6 POST_SHARED
Priority
Medium
Card
Mary shared your post.

View Share

Open Post
Preview
Post Preview
Viewer
Post Detail Viewer
Aggregation
Yes.
2.7 POST_BOOKMARKED (Optional)
If bookmarks become visible to authors.
Priority
Low
Actions
View Analytics
Aggregation
Yes.
2.8 POST_REPORTED (Moderator Only)
Priority
Critical
Card
Your post was reported.

Reason

Spam

Review
Accent
Red
Viewer
Moderation Panel
Aggregation
No.
2.9 PROFILE_VERIFIED
Priority
High
Card
Your account has been verified.

View Badge
Viewer
Profile
Aggregation
No.
2.10 PROFILE_UPDATED
System-generated.
Example
Your profile information has been updated.
Useful when changes occur from academic synchronization or administrative updates.
Social Notification Summary
Notification Type	Aggregate	Push	Preview	Viewer
POST_LIKED	✅	✅	Post	Post Viewer
POST_COMMENTED	✅	✅	Post	Post Viewer
COMMENT_REPLY	❌	✅	Post	Post Viewer
USER_MENTIONED	❌	✅	Post	Post Viewer
USER_FOLLOWED	✅	✅	Avatar	Profile
POST_SHARED	✅	✅	Post	Post Viewer
POST_BOOKMARKED	✅	Optional	Post	Analytics/Post
POST_REPORTED	❌	✅	Post	Moderation
PROFILE_VERIFIED	❌	✅	Avatar	Profile
PROFILE_UPDATED	❌	Optional	Avatar	Profile
Engineer's Recommendation
Architect, I'd make one addition that's quite uncommon but fits PwaniNet well.
Smart Conversation Notifications
Suppose five people comment on the same post over twenty minutes.
Instead of only showing:
5 people commented on your post.
The notification evolves into:
💬 Active Discussion

Brian asked a question.

Kevin replied to Brian.

Mary added another solution.

18 comments

Last activity: 2 minutes ago

──────────────

Continue Discussion →
This isn't just aggregation—it recognizes that the post has become an active conversation. Rather than treating comments as isolated events, the notification becomes a live gateway back into that discussion.
Chapter 3 — Academic Notification Rendering Profiles
3.1 COURSE_ANNOUNCEMENT
Category: Academic
Priority: High
Preview: Course Avatar / Badge
Accent: Blue
Card
📢

CSC221

Dr. Mwangi posted an announcement.

Quiz moved to Friday.

                      ┌──────────┐
                      │ CSC221   │
                      └──────────┘

Open Announcement
Aggregation: Yes (multiple announcements from same course)
Viewer: Course → Announcements Tab
Push: Yes
3.2 ASSIGNMENT_PUBLISHED
Priority
High
Card
📚

Operating Systems Assignment 3

Due Friday

                      ┌──────────┐
                      │ CSC221   │
                      └──────────┘

Open Assignment

Discussion
Preview
Course Badge
Actions
·	Open Assignment
·	Discussion
·	Bookmark
Viewer
Assignment Viewer
Push
Yes
3.3 ASSIGNMENT_DUE_SOON
Priority
Critical
Card
⏰

Assignment due tomorrow

Operating Systems

23 hours remaining

Open

Submit
Accent
Orange
Aggregation
No
Viewer
Assignment Viewer
3.4 ASSIGNMENT_OVERDUE
Priority
Critical
Accent
Red
Card
⚠

Assignment overdue

Operating Systems

Submitted: No

Open
3.5 LECTURE_SCHEDULE_UPDATED
Card
📅

CSC221 lecture moved.

Thursday

10:00 → 2:00 PM

View Timetable
Aggregation
Yes
Viewer
Course Timetable
3.6 UNIT_REGISTERED
Card
✅

You were registered for

Operating Systems

Open Course
Viewer
Course Page
3.7 UNIT_REMOVED
Priority
High
Card
⚠

Computer Graphics removed from your semester.

View Details
3.8 STUDY_GROUP_CREATED
Card
👥

Study Group

Assignment 2 Discussion

created for CSC221

Join
Preview
Study Group Avatar
Viewer
Study Group
Aggregation
No
3.9 STUDY_GROUP_INVITATION
Card
Brian invited you

CSC221 Study Group

Accept

Decline
Viewer
Study Group
Push
Yes
3.10 STUDY_GROUP_JOIN_REQUEST
(Admin)
Kevin requested to join

Assignment Group 5

Approve

Reject
Aggregation
Yes
3.11 STUDY_GROUP_JOIN_APPROVED
You joined

Assignment Group 5

Open Group
3.12 LECTURER_POSTED_RESOURCE
📄

Operating Systems Notes

uploaded by

Dr. Mwangi

                      ┌────────────┐
                      │ Doc Preview│
                      └────────────┘

Preview

Bookmark

Download
Preview
✅ Reuse the Document Viewer preview component, not a separate notification preview.
Viewer
Document Viewer
3.13 PAST_PAPER_UPLOADED
📄

CSC221 Past Paper

2025

                      ┌────────────┐
                      │ First Page │
                      └────────────┘

Preview

Download
Aggregation
Yes
3.14 COURSE_MATERIAL_UPDATED
📚

Operating Systems

Lecture Slides updated

Preview
Viewer
Document Viewer
3.15 EXAM_TIMETABLE_RELEASED
📝

Semester Exam Timetable

published.

View Timetable
Priority
High
3.16 COURSE_DISCUSSION_MENTION
@

Dr. Mwangi mentioned you

in CSC221 discussion.

Reply
Viewer
Discussion Thread
3.17 COURSE_ENROLLMENT_UPDATED
Generated automatically by your academic synchronization engine.
Semester Profile Updated

3 new units added

1 archived
Viewer
Academic Profile
Academic Summary
Notification	Aggregate	Push	Viewer
Course Announcement	✅	✅	Course
Assignment Published	❌	✅	Assignment
Assignment Due	❌	✅	Assignment
Assignment Overdue	❌	✅	Assignment
Timetable Updated	✅	✅	Timetable
Unit Registered	❌	Optional	Course
Unit Removed	❌	✅	Course
Study Group Created	❌	✅	Study Group
Study Group Invite	❌	✅	Study Group
Join Request	✅	✅	Study Group
Join Approved	❌	✅	Study Group
Lecturer Resource	✅	✅	Document Viewer
Past Paper	✅	✅	Document Viewer
Course Material Updated	✅	✅	Document Viewer
Exam Timetable	❌	✅	Timetable
Course Mention	❌	✅	Discussion
Enrollment Updated	❌	Optional	Academic Profile
Engineering Addition
Since PwaniNet already knows a student's semester, units, courses, and study groups, I would add Academic Digest Cards.
Instead of six separate notifications:
CSC221 Assignment

CSC221 Slides

CSC221 Announcement

CSC221 Study Group

CSC221 Notes

CSC221 Quiz
Generate:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📘 CSC221 Activity

• Assignment 3 published

• Lecture slides uploaded

• Quiz moved to Friday

• 12 new study group messages

• Notes updated

Last activity: 5 minutes ago

[Open Course]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is not aggregation—it's a course activity digest. It gives students a complete picture of everything happening in a course without forcing them to open multiple notifications. Because your Notification Engine is event-driven and your academic profile updates automatically each semester, generating these digests will be straightforward and will make the Academic perspective far more useful.
Chapter 4 — Document Repository Notification Rendering Profiles
4.1 DOCUMENT_UPLOADED
Purpose
Notify users when a new document matching their courses, interests, workspaces, or followed categories is uploaded.
Category
Documents
Priority
Medium
Card
📄

Operating Systems Notes

Uploaded by Kevin

CSC221

2 minutes ago

                          ┌──────────────┐
                          │ First Page   │
                          │ Preview      │
                          └──────────────┘

Preview   Bookmark   Download
Resource Preview
Mandatory
Reuse the Document Repository Preview Component.
Never implement another preview inside notifications.
Supported automatically:
·	PDF preview
·	DOCX preview
·	PPT/PPTX preview
·	TXT preview
·	Future formats
Viewer
Document Viewer
Actions
·	Preview
·	Bookmark
·	Download
·	Share
Future
·	Ask AI
Aggregation
Yes
Example
Kevin uploaded 5 new documents.

View Collection
Push
Optional
Only if user follows:
·	course
·	category
·	uploader
·	workspace
4.2 DOCUMENT_UPDATED
📄

Operating Systems Notes

updated.

Version 3

                         ┌──────────────┐
                         │ Updated Page │
                         └──────────────┘

Preview

Version History
Viewer
Document Viewer
Automatically opens Version History.
Aggregation
Yes
4.3 DOCUMENT_APPROVED
(Admin workflow)
📄

Your document has been approved.

View
Viewer
Document Viewer
4.4 DOCUMENT_REJECTED
Priority
High
⚠

Your document needs revision.

Reason:

Duplicate upload.

Edit

View Feedback
Accent
Red
4.5 DOCUMENT_COMMENTED
💬

Brian commented on

Operating Systems Notes

"Page 18 contains..."

                     ┌──────────────┐
                     │ Page Preview │
                     └──────────────┘

Reply

Open Discussion
Viewer
Document Viewer
Scroll directly to the referenced comment.
4.6 DOCUMENT_RATED
⭐

12 students rated

Operating Systems Notes

92% Helpful

View Analytics
Aggregation
Yes
4.7 DOCUMENT_BOOKMARK_RECOMMENDATION
Generated by recommendation engine.
✨

Because you bookmarked

Operating Systems Notes

You may also like

Computer Architecture Notes

Preview
Future
AI-powered recommendations.
4.8 DOCUMENT_TRENDING
🔥

Operating Systems Notes

is trending.

563 downloads today.

Preview

Analytics
Aggregation
No
4.9 DOCUMENT_DOWNLOAD_MILESTONE
Uploader notification.
🎉

Operating Systems Notes

reached

100 downloads.
Viewer
Document Analytics
4.10 DOCUMENT_FEATURED
⭐

Your document was featured.

View Collection
4.11 DOCUMENT_REPORTED
Moderator
🚨

Your document was reported.

Reason:

Incorrect content.

Review
Aggregation
No
4.12 OCR_COMPLETED
Future
🤖

OCR completed.

Search is now available.

Open Document
4.13 DOCUMENT_AI_SUMMARY_READY
Future
✨

AI Summary generated.

Operating Systems Notes

Read Summary
4.14 DOCUMENT_PROCESSING_FAILED
⚠

Preview generation failed.

Retry

View Details
4.15 DOCUMENT_PROCESSING_COMPLETED
✅

Preview generated.

Search indexed.

Ready to use.

Open Document
4.16 DOCUMENT_SHARED
Brian shared

Operating Systems Notes

with CSC221.

Preview
4.17 COLLECTION_UPDATED
Future
📚

Operating Systems Collection

updated.

4 new documents.

Browse Collection
Document Summary
Notification	Aggregate	Push	Viewer
Document Uploaded	✅	Optional	Document Viewer
Document Updated	✅	Optional	Document Viewer
Approved	❌	✅	Document Viewer
Rejected	❌	✅	Document Viewer
Comment	✅	✅	Document Viewer
Rating	✅	Optional	Analytics
Recommendation	❌	Optional	Document Viewer
Trending	❌	Optional	Analytics
Download Milestone	❌	Optional	Analytics
Featured	❌	✅	Document Viewer
Reported	❌	✅	Moderation
OCR Complete	❌	Optional	Document Viewer
AI Summary	❌	Optional	Document Viewer
Processing Failed	❌	✅	Processing
Processing Complete	❌	Optional	Document Viewer
Shared	✅	Optional	Document Viewer
Collection Updated	✅	Optional	Collection
🚀 Engineer's Recommendation
This is where I think PwaniNet can do something that I haven't seen done well on university platforms.
Interactive Document Notifications
Instead of only showing a preview thumbnail, embed a live mini-document card powered by the same Document Viewer.
Example:
📄 Operating Systems Notes

┌──────────────────────────────┐
│ Page 12                      │
│                              │
│ "...Deadlock occurs when..." │
│                              │
└──────────────────────────────┘

👁 1,284   ⬇ 563   ⭐ 94%

Preview   Bookmark   Download
That small card is not a screenshot. It is the same rendering engine used by the full Document Viewer, just configured in a compact mode.
If the document has multiple pages, the preview can even remember the page referenced by the notification. For example, if someone comments on page 18, the notification preview should display page 18 instead of page 1.
This follows the Universal Resource Architecture perfectly:
·	One document.
·	One rendering engine.
·	One viewer.
·	Multiple presentation sizes (thumbnail, compact preview, full viewer).

Perfect. This is one of my favorite chapters because Study Groups are not ordinary groups.

A Study Group is a temporary academic workspace centered around a specific assignment, lab, exam revision, or topic. In the future it will gain video calls, whiteboards, shared notes, AI assistance, and collaborative tools.

So we shouldn't design it as a chat group—we should design it as a micro-workspace.

PwaniNet Notification Rendering Specification
Chapter 6 — Study Group Notification Rendering Profiles
6.1 STUDY_GROUP_CREATED
Purpose

Notify students that a new study group relevant to their course has been created.

Category

Study Groups

Priority

Medium

Card

📚

Assignment 3 Discussion

CSC221

Created by Brian

                     ┌─────────────┐
                     │ Study Group │
                     │ Avatar      │
                     └─────────────┘

Join

View Details

Viewer

Study Group Home

Aggregation

No

Push

Optional

6.2 STUDY_GROUP_INVITATION

Priority

High

Brian invited you

Assignment 3 Discussion

CSC221

Accept

Decline

Viewer

Study Group

Push

Yes

6.3 STUDY_GROUP_JOIN_REQUEST

(Admin)

Kevin requested to join

Assignment 3 Discussion

Approve

Reject

Aggregation

Yes

6.4 STUDY_GROUP_JOIN_APPROVED
You joined

Assignment 3 Discussion

Open Study Group

Viewer

Study Group

6.5 STUDY_GROUP_ASSIGNMENT_UPDATED
📚

Assignment requirements updated.

Assignment 3

View Changes

Viewer

Assignment Viewer

6.6 STUDY_GROUP_NEW_RESOURCE
📄

Operating Systems Notes

shared with

Assignment 3 Discussion

                  ┌──────────────┐
                  │ Document     │
                  │ Preview      │
                  └──────────────┘

Preview

Bookmark

Uses the canonical Document Viewer.

6.7 STUDY_GROUP_MESSAGE
Brian sent a message

Assignment 3 Discussion

Open Chat

Aggregation

Yes

Instead of

18 new messages

Display

Assignment 3 Discussion

18 new messages

Last message

"Authentication is done..."

Open Chat
6.8 STUDY_GROUP_MENTION

Priority

High

@

Brian mentioned you

"...@Zayne check Question 4..."

Reply

Viewer

Jump directly to the message.

Aggregation

No.

6.9 STUDY_GROUP_TASK_ASSIGNED

Future

Brian assigned you

Research Scheduling Algorithms

Due Tomorrow

Open Task

Viewer

Task Detail

6.10 STUDY_GROUP_MEETING_CREATED

Future

📹

Revision Meeting

Tonight

8 PM

Join

View Agenda

Viewer

Meeting

6.11 STUDY_GROUP_MEETING_REMINDER
Meeting begins in

10 minutes

Join Now

Critical

6.12 STUDY_GROUP_WHITEBOARD_UPDATED

Future

📝

Brian updated

Whiteboard

Operating Systems

Open Whiteboard

Viewer

Whiteboard

6.13 STUDY_GROUP_AI_INSIGHT

Future

✨

AI found

3 unanswered questions

Review Suggestions

Viewer

Study Group AI Panel

6.14 STUDY_GROUP_GOAL_COMPLETED
🎉

Assignment 3 completed.

All tasks finished.

View Summary
6.15 STUDY_GROUP_ARCHIVED
Study Group archived.

Final Report available.

Open Archive
Study Group Summary
Notification	Aggregate	Push	Viewer
Study Group Created	❌	Optional	Study Group
Invitation	❌	✅	Study Group
Join Request	✅	✅	Members
Join Approved	❌	✅	Study Group
Assignment Updated	❌	✅	Assignment
Resource Shared	✅	Optional	Document Viewer
New Messages	✅	Optional	Chat
Mention	❌	✅	Chat
Task Assigned	❌	✅	Task
Meeting Created	❌	✅	Meeting
Meeting Reminder	❌	✅	Meeting
Whiteboard Updated	✅	Optional	Whiteboard
AI Insight	❌	Optional	AI Panel
Goal Completed	❌	Optional	Summary
Archived	❌	Optional	Archive
🚀 Engineer's Recommendation

Architect, this is where I think PwaniNet can introduce something I've never seen on educational platforms.

Study Progress Notifications

Instead of only notifying users about events, notify them about progress.

Imagine this card:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 Assignment 3 Progress

████████░░ 82%

Tasks Completed

14 / 17

Resources Reviewed

8

Meeting Tonight

8:00 PM

Continue Working →

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is not an event notification—it's a live progress notification.

As the study group works:

Task completion updates.
Shared resources increase.
Meeting countdown changes.
AI suggestions appear.
Whiteboard edits accumulate.

The notification evolves over time into a small dashboard rather than remaining a static message.
Chapter 7 — Workspace Notification Rendering Profiles
7.1 WORKSPACE_INVITATION
Category
Workspace
Priority

High

Card
📁

Brian invited you to

Library Management System

Role

Backend Developer

                    ┌──────────────┐
                    │ Workspace    │
                    │ Avatar       │
                    └──────────────┘

Accept

Decline

Viewer

Workspace Home

Push

Yes

7.2 WORKSPACE_MEMBER_JOINED
👋

Kevin joined

Library Management System

View Team

Aggregation

Yes

7.3 WORKSPACE_ROLE_CHANGED
🎖

Your role changed

Frontend Developer

→

Team Lead

View Permissions

Viewer

Members

7.4 WORKSPACE_TASK_ASSIGNED

Priority

Critical

✅

Task Assigned

Implement Authentication

Due Friday

Open Task

Comment

Viewer

Task Detail

Push

Yes

7.5 WORKSPACE_TASK_UPDATED
📝

Authentication Task

updated.

View Changes

Aggregation

Yes

7.6 WORKSPACE_TASK_COMPLETED
🎉

Brian completed

Authentication Module

View Progress

Viewer

Project Timeline

7.7 WORKSPACE_TASK_OVERDUE

Priority

Critical

Accent

Red

⚠

Task overdue.

Implement Authentication

2 days late.

Open Task
7.8 WORKSPACE_COMMENT
💬

Brian commented

on Authentication Task

Reply

Open Discussion

Viewer

Task Discussion

7.9 WORKSPACE_MENTION

Priority

High

@

Brian mentioned you.

"...@Zayne review middleware..."

Reply

Viewer

Jump directly to the message.

7.10 WORKSPACE_DOCUMENT_SHARED
📄

System Design.pdf

shared in

Library Management System

                 ┌──────────────┐
                 │ Document     │
                 │ Preview      │
                 └──────────────┘

Preview

Download

Bookmark

Uses the canonical Document Viewer.

7.11 WORKSPACE_DOCUMENT_UPDATED
📄

SRS Document

updated.

Version 6

Preview

View History
7.12 WORKSPACE_MILESTONE_COMPLETED
🏆

Milestone Complete

Authentication System

View Progress

Priority

High

7.13 WORKSPACE_MEETING_CREATED
📹

Sprint Planning

Tomorrow

7 PM

Join

Agenda

Viewer

Meeting

7.14 WORKSPACE_MEETING_REMINDER

Priority

Critical

Meeting starts

in 10 minutes

Join Now
7.15 WORKSPACE_PRESENTATION_READY

Future

🖥

Sprint Demo

Presentation prepared.

Present

Viewer

Presentation Mode

7.16 WORKSPACE_WHITEBOARD_UPDATED

Future

📝

Architecture Whiteboard

updated.

Open Whiteboard

Viewer

Whiteboard

Aggregation

Yes

7.17 WORKSPACE_AI_SUMMARY

Future

✨

AI summarized

today's progress.

Read Summary

Viewer

AI Assistant

7.18 WORKSPACE_BUILD_STATUS (Future CI/CD Integration)
🛠

Latest build

Succeeded

View Logs

or

❌

Latest build

Failed

Review Errors
7.19 WORKSPACE_APPROVAL_REQUEST
Brian submitted

Authentication Module

for review.

Approve

Request Changes

Viewer

Task Review

Push

Yes

7.20 WORKSPACE_APPROVAL_RESULT
✅

Authentication Module

Approved

Continue Sprint

or

⚠

Changes requested

Open Feedback
7.21 WORKSPACE_FILE_ACTIVITY
📂

5 project files updated.

View Changes

Aggregation

Yes

7.22 WORKSPACE_CHAT_ACTIVITY

Instead of:

42 new messages

Display:

💬

Library Management System

42 new messages

Latest

"We should normalize..."

Open Chat
7.23 WORKSPACE_GOAL_COMPLETED
🎉

Sprint Goal

Completed

100%

View Timeline
7.24 WORKSPACE_ARCHIVED
📦

Library Management System

archived.

Browse Archive
Workspace Summary
Notification	Aggregate	Push	Viewer
Invitation	❌	✅	Workspace
Member Joined	✅	Optional	Members
Role Changed	❌	✅	Members
Task Assigned	❌	✅	Task
Task Updated	✅	Optional	Task
Task Completed	✅	Optional	Timeline
Task Overdue	❌	✅	Task
Comment	✅	✅	Discussion
Mention	❌	✅	Chat
Document Shared	✅	Optional	Document Viewer
Document Updated	✅	Optional	Document Viewer
Milestone Completed	❌	✅	Timeline
Meeting Created	❌	✅	Meeting
Meeting Reminder	❌	✅	Meeting
Presentation Ready	❌	Optional	Presentation
Whiteboard Updated	✅	Optional	Whiteboard
AI Summary	❌	Optional	AI
Build Status	❌	Optional	Build
Approval Request	❌	✅	Review
Approval Result	❌	✅	Review
File Activity	✅	Optional	Files
Chat Activity	✅	Optional	Chat
Goal Completed	❌	Optional	Timeline
Archived	❌	Optional	Archive
🚀 Engineer's Recommendation

This is where I think PwaniNet can introduce its most distinctive notification type.

Workspace Dashboard Notification

Instead of individual project notifications, create a persistent, live project summary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Library Management System

Sprint 3

████████░░ 81%

👥 Online: 5/8

✅ Tasks Completed: 18/24

⚠ Due Today: 3

📄 Documents Updated: 2

💬 Messages: 34

📹 Meeting: Today • 8:00 PM

Open Workspace →

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This isn't a notification about a single event. It's a live workspace card that evolves as the project changes.

When the AI assistant is added, it can become:

AI Summary: "The backend is blocked waiting for the database schema. Three tasks are overdue. The sprint is 81% complete."

The notification becomes a continuously updated project briefing rather than a list of isolated events.
Chapter 8 — Security Notification Rendering Profiles

Security notifications are never aggregated. Every security event must be individually visible and auditable.

8.1 LOGIN_NEW_DEVICE
Category
Security
Priority

Critical

Accent

Red

Card
🛡

New login detected

Chrome • Windows

Nairobi, Kenya

2 minutes ago

Review

Secure Account
Viewer

Security → Active Sessions

Push

Yes

Email

Future

Yes

8.2 LOGIN_UNKNOWN_LOCATION
⚠

Suspicious login detected

Unknown Device

Mombasa

Was this you?

Yes

No

Viewer

Security Review

8.3 PASSWORD_CHANGED
🔑

Your password

was changed successfully.

Review Sessions

Viewer

Security Settings

8.4 EMAIL_CHANGED
✉

Your email address

has been updated.

Review
8.5 ACCOUNT_RECOVERY_REQUEST
⚠

Password reset requested.

Ignore

Continue
8.6 ACCOUNT_VERIFIED
✅

Your account

has been verified.

View Profile
8.7 MULTIPLE_FAILED_LOGINS
🚨

Several failed login attempts

were detected.

Review Activity
8.8 SESSION_EXPIRED
⌛

One of your sessions

expired.

View Devices
8.9 DEVICE_REMOVED
📱

A device was signed out.

View Devices
8.10 SECURITY_ALERT

Generic fallback.

🛡

Security Alert

Immediate attention required.

Review
Security Summary
Notification	Push	Aggregate
New Login	✅	❌
Unknown Location	✅	❌
Password Changed	✅	❌
Email Changed	✅	❌
Recovery Request	✅	❌
Account Verified	Optional	❌
Failed Logins	✅	❌
Session Expired	Optional	❌
Device Removed	Optional	❌
Security Alert	✅	❌
Chapter 9 — System Notification Rendering Profiles

System notifications communicate changes to the platform itself.

9.1 SYSTEM_ANNOUNCEMENT
📢

PwaniNet Update

Maintenance tonight

11:00 PM

Read More
9.2 FEATURE_RELEASED
✨

New Feature

Workspace Whiteboards

Try Now
9.3 MAINTENANCE_SCHEDULED
🛠

Scheduled Maintenance

Saturday

11 PM

View Details
9.4 MAINTENANCE_COMPLETED
✅

Maintenance Complete

Thanks for your patience.

Continue
9.5 STORAGE_LIMIT
💾

Storage almost full

92%

Manage Storage

Viewer

Settings → Storage

9.6 STORAGE_CLEANUP_COMPLETED
🧹

Cache cleaned

850 MB freed.

View Storage
9.7 BACKUP_COMPLETED (Future)
☁

Workspace backup completed.

View Backup
9.8 PLATFORM_STATUS
🌐

All services operational.

or

⚠

Document Repository

temporarily unavailable.
9.9 PROFILE_SYNC_COMPLETED

One of the most important notifications for PwaniNet.

🎓

Academic profile updated

2027 Academic Year

Semester II

2 new units added

Open Academic Profile

This integrates directly with your automatic academic synchronization engine.

9.10 PROFILE_SYNC_FAILED
⚠

Academic profile

could not be updated.

Retry
9.11 APP_UPDATE_AVAILABLE (PWA)
⬆

New PwaniNet version available.

Refresh

Later
9.12 OFFLINE_MODE
📶

You're offline.

Some features

may be unavailable.

Automatically disappears when the connection returns.

System Summary
Notification	Push	Aggregate
Announcement	Optional	❌
Feature Released	Optional	❌
Maintenance	✅	❌
Storage Warning	Optional	❌
Storage Cleanup	❌	❌
Backup Complete	Optional	❌
Platform Status	Optional	❌
Academic Sync	Optional	❌
Academic Sync Failed	✅	❌
App Update	Optional	❌
Offline Mode	❌	❌
🚀 Engineer's Recommendation

Architect, I'd introduce one final notification category that cuts across every feature:

Platform Health Notifications

Instead of only notifying users about individual events, occasionally summarize the health of their PwaniNet account.

Example:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 Platform Health

Academic Profile

✓ Up to date

Storage

74% used

Security

✓ No issues detected

Workspaces

3 active

Documents

14 bookmarked

Notifications

2 require action

Review Dashboard →

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This isn't an alert—it's a status dashboard. It gives users confidence that everything is functioning correctly and highlights anything that needs attention.
Chapter 10 — Animation & Micro-Interactions
10.1 Purpose

Animations provide visual feedback for notification lifecycle events while maintaining responsiveness.

Animations must:

Explain state changes
Preserve user context
Never block interaction
Respect reduced-motion accessibility settings
10.2 Motion Principles

Every animation should answer one question:

What just changed?

Avoid animations that exist purely for decoration.

Examples:

✔ New notification arrives

✔ Notification grouped

✔ Action completed

✔ Drawer opens

✖ Random bouncing

✖ Flashing cards

✖ Long fades

10.3 Notification Arrival

When a new notification arrives:

Desktop

↓

Card slides down slightly

↓

Opacity increases

↓

Unread indicator appears

↓

Unread counter increments

The feed should not jump if the user is reading older notifications.

Instead:

━━━━━━━━━━━━━━

3 New Notifications

━━━━━━━━━━━━━━

Tapping the banner inserts the new cards.

10.4 Unread Indicator

Unread notifications display a small colored indicator.

When opened:

●

↓

shrinks

↓

fades

↓

disappears

Not instantly removed.

10.5 Card Expansion

Grouped notifications expand smoothly.

3 Comments

↓

↓

Brian

Kevin

Mary

Expansion should preserve surrounding scroll position.

10.6 Card Collapse

Reverse of expansion.

No snapping.

10.7 Mark Read

When marking as read:

Unread Dot

↓

Fade

↓

Card background transitions

↓

Counter updates

No page refresh.

10.8 Delete / Dismiss
Card

↓

Slides horizontally

↓

Shrinks vertically

↓

Removed

↓

Remaining cards move upward

Undo Snackbar appears.

Notification dismissed.

Undo
10.9 Bulk Actions

Selecting notifications:

Checkbox

↓

Scale In

↓

Toolbar transforms

↓

Selection Counter appears

Deselection reverses the process.

10.10 Action Buttons

Example

Approve

Button

↓

Loading Spinner

↓

Checkmark

↓

Button changes to

Approved

Never leave users wondering if an action completed.

10.11 Resource Preview Loading

Preview loads independently.

Placeholder

┌────────────┐

██████████

██████████

└────────────┘

When ready

Cross-fade.

Do not resize the card.

10.12 Drawer Opening

Desktop

Drawer slides from the right.

Background remains visible.

Mobile

Bottom sheet expands.

If opening a canonical viewer (for example, the Document Viewer), transition directly into that experience without an intermediate flash.

10.13 Live Updates

Aggregated notifications update without recreating the card.

Example

Brian liked your post.

↓

Brian and Kevin liked your post.

↓

Brian, Kevin and 8 others liked your post.

Only the changed content animates.

10.14 Badge Animation

Unread count

12

↓

13

Small scale animation.

No bouncing.

10.15 Timeline Animation

When a new timeline section appears:

Yesterday

↓

Today

Fade in gently.

10.16 Search Results

Filtering

Old cards fade out.

Matching cards remain.

No full reload.

10.17 Empty States

If a filter produces no results:

No notifications found.

Clear Filters

Fade between content and empty state.

10.18 Error Feedback

Failed action

Approve

↓

Loading

↓

Error

↓

Retry

The notification should remain usable.

10.19 Offline Mode

If offline:

Offline

Queued

Will sync automatically

Queued actions receive a small sync indicator.

Once connected:

Queued

↓

Synced ✓
10.20 Reduced Motion

If the operating system requests reduced motion:

Replace movement with:

opacity transitions
instant layout updates
subtle fades

All interactions remain functional.

10.21 Performance Targets

Animation guidelines:

Begin within one frame of the triggering event.
Avoid animating expensive layout properties.
Prefer transform and opacity.
Prevent animation-induced layout shifts.
Keep animations interruptible if the user interacts again.
10.22 Animation Consistency

The same interaction should always animate the same way.

Examples:

Every drawer opens identically.
Every notification dismisses identically.
Every resource preview fades in identically.

Users should develop predictable expectations.

🚀 Engineer's Recommendation

Architect, I'd add one signature interaction that could become uniquely associated with PwaniNet.

Live Event Morphing

Instead of removing and recreating cards as events evolve, let the notification transform in place.

Example:

Brian liked your post.

↓

Brian and Kevin liked your post.

↓

Brian, Kevin and 8 others liked your post.

↓

Your post is trending.

184 reactions

52 comments

Notice what's happening.

The notification isn't disappearing and being replaced.

It evolves as the underlying event evolves.

The same could happen for workspaces:

Task Assigned

↓

Task In Progress

↓

Task Submitted for Review

↓

Task Approved

The user follows the lifecycle of a single entity instead of mentally stitching together four separate notifications. That fits perfectly with the event-driven architecture you've built and will make the Notification Center feel much more coherent.
hapter 11 — Frontend Component Architecture
11.1 Philosophy

The Notification Center shall be built from reusable UI components.

No notification type should introduce custom layouts unless absolutely necessary.

Every notification is composed from a common component hierarchy.

NotificationCard

├── ContextHeader
├── ActorStack
├── NotificationContent
├── ResourcePreview
├── MetadataRow
├── ActionBar
└── StatusIndicators

Instead of building 50 notification layouts,

we build about 10 reusable components.

11.2 NotificationCard

The root component.

Responsible for

spacing
elevation
unread styling
hover
focus
animation
expansion
selection

Every notification begins here.

NotificationCard

↓

Everything else
11.3 ContextHeader

Shows where the notification belongs.

Example

👥 Developers Kenya

📚 CSC221

📁 Library Workspace

📄 Document Repository

Contains

Context Avatar
Context Name
Context Badge
Context Type
11.4 ActorStack

Displays actors.

Supports

Single

Brian

Two

Brian

Kevin

Many

Brian

Kevin

Mary

+17

Uses overlapping avatars.

Future support

Animated online indicators.

11.5 NotificationContent

Responsible for

Title

Description

Highlighted words

Examples

Brian commented on your post.
Assignment due tomorrow.
Sprint completed.

Rich text supported.

Mentions.

Links.

Bold.

Emoji.

11.6 ResourcePreview

One of the most important components.

Never implement resource previews separately.

Supported resources

Post

Document

Assignment

Workspace

Task

Meeting

Whiteboard

Presentation

Video

Collection

The renderer simply asks

Render Preview(resource)

The ResourcePreview component chooses the correct renderer.

11.7 MetadataRow

Contains

2 minutes ago

Unread

Priority

Course Badge

Future

Read receipts.

11.8 ActionBar

Contains actions.

Example

Approve

Reject

or

Reply

Open

Supports

Loading

Disabled

Overflow Menu

Permissions

11.9 StatusIndicator

Shows

Unread

Pending

Completed

Failed

Expired

Queued

Offline

Never mixed with actions.

11.10 TimelineDivider

Reusable.

Today

Yesterday

Earlier

Supports

Auto collapsing.

11.11 NotificationGroup

Container

Brian

Kevin

Mary

liked your post.

Expandable.

Collapsible.

11.12 NotificationDrawer

Desktop

Slides from right.

Contains

Full notification

History

Related activity

Actions

Canonical Viewer launcher.

11.13 MobileBottomSheet

Equivalent of drawer.

Optimized for touch.

11.14 SearchBar

Shared component.

Supports

Debounced search.

Suggestions.

Recent searches.

11.15 FilterChip
Academic

Unread

Today

Removable.

Animated.

11.16 Toolbar

Contains

Search

Filters

Bulk Actions

Settings Shortcut

Statistics

Perspective Switcher

11.17 NotificationList

Responsible for

Sorting

Virtual scrolling

Grouping

Pagination

Live updates

Never renders notification content.

Only manages layout.

11.18 Skeleton Components

Every component has a loading state.

Examples

Notification Skeleton

Document Preview Skeleton

Avatar Skeleton

Action Skeleton

This prevents layout shifts.

11.19 Empty State Component

Shared everywhere.

Examples

No notifications.

No academic notifications.

Nothing matched your search.
11.20 Canonical Viewer Launcher

Perhaps the most important reusable component.

Every resource opens through this launcher.

Examples

Open Document

↓

Document Viewer
Open Task

↓

Task Viewer
Open Workspace

↓

Workspace

The Notification Center never decides how to display a resource.

It simply delegates.

11.21 Component Hierarchy
NotificationCenter

│

├── NotificationToolbar

├── TimelineSection

│

├── NotificationList

│

├── NotificationCard

│

├── ContextHeader

├── ActorStack

├── NotificationContent

├── ResourcePreview

├── MetadataRow

├── ActionBar

└── StatusIndicator

│

└── NotificationDrawer

Notice something?

Nothing here knows about

likes
comments
assignments
workspaces

Those are Rendering Profiles.

The components remain generic.

11.22 Component Reuse Matrix
Component	Used By
NotificationCard	Every notification
ContextHeader	Groups, Courses, Workspaces, Documents, Study Groups
ActorStack	Social, Groups, Workspaces
ResourcePreview	Posts, Documents, Tasks, Assignments, Meetings
ActionBar	Every actionable notification
MetadataRow	Every notification
TimelineDivider	Notification feed
NotificationDrawer	Desktop
BottomSheet	Mobile
Canonical Viewer Launcher	Every resource
🚀 Engineer's Recommendation

Architect...

I would make one final architectural improvement before implementation.

Component Registry

Instead of this:

if (notification.type === "POST_COMMENT") {
    ...
}

if (notification.type === "DOCUMENT") {
    ...
}

Create a registry.

Rendering Profile

↓

Component Registry

↓

NotificationCard

Example:

POST_COMMENT

↓

CommentRenderer

↓

NotificationCard
DOCUMENT_UPLOADED

↓

DocumentRenderer

↓

NotificationCard
WORKSPACE_TASK_ASSIGNED

↓

WorkspaceTaskRenderer

↓

NotificationCard

Now imagine two years from now.

You introduce

AI_CODE_REVIEW_COMPLETED

You don't touch existing notification code.

You simply register

AI_CODE_REVIEW_COMPLETED

↓

AICodeReviewRenderer

Done.
Chapter 12 — Implementation Blueprint
12.1 Objective

Implement the new Notification Center incrementally while maintaining compatibility with the existing Notification Engine.

The implementation must:

Avoid breaking existing notifications.
Reuse existing PwaniNet components where possible.
Support gradual rollout.
Keep the UI functional throughout development.
12.2 Implementation Strategy

Development should proceed in five phases.

Notification Engine
        │
        ▼
Rendering Layer
        │
        ▼
Notification Components
        │
        ▼
Notification Center
        │
        ▼
Live Updates

The backend already exists. The work now is primarily frontend integration.

Phase 1 — Foundation
Goal

Create the reusable infrastructure.

Tasks

Create NotificationCenter
Create NotificationCard
Create NotificationList
Create NotificationToolbar
Create TimelineSection
Create NotificationDrawer
Create MobileBottomSheet
Create EmptyState
Create Skeleton Components

Nothing should be notification-specific yet.

Deliverable:

A static Notification Center that can display placeholder notifications.

Phase 2 — Core Components

Build reusable components.

Implement

ContextHeader
ActorStack
NotificationContent
ResourcePreview
MetadataRow
ActionBar
StatusIndicator
TimelineDivider
Filter Chips

At the end of Phase 2, every notification can be composed from reusable pieces.

Phase 3 — Rendering System

Implement the Rendering Registry.

Example

Notification Type

↓

Renderer Registry

↓

Rendering Profile

↓

Notification Card

Create renderers for

Social
Academic
Documents
Groups
Study Groups
Workspaces
Security
System

No business logic belongs in the UI.

The renderer only interprets the notification payload.

Phase 4 — Advanced Features

Implement

Aggregation
Live notification updates
Search
Filters
Bulk actions
Selection mode
Detail drawer
Timeline grouping
Optimistic updates
Undo support

This transforms the UI from static to interactive.

Phase 5 — Polish

Implement

Animations
Keyboard shortcuts
Accessibility
Performance optimizations
Reduced motion
Virtual scrolling
Lazy preview loading
Error handling
Offline indicators

Only after functionality is complete.

12.3 Suggested Folder Structure
notifications/

    components/

        NotificationCard/

        NotificationToolbar/

        NotificationDrawer/

        Timeline/

        ResourcePreview/

        ActorStack/

        ActionBar/

        EmptyState/

        Skeletons/

    renderers/

        social/

        academic/

        documents/

        groups/

        study_groups/

        workspaces/

        security/

        system/

    registry/

        registry.js

        profiles.js

    services/

        notification-ui.js

        aggregation.js

        filters.js

        search.js

    styles/

        notifications.css

        animations.css

This separates rendering from presentation and keeps the codebase extensible.

12.4 Integration Points

The Notification Center consumes only the Notification Engine's output.

It does not:

Generate notifications
Aggregate events
Apply permissions
Make business decisions

It receives fully prepared notification objects and renders them.

12.5 Rendering Flow
Notification Engine

↓

Notification API

↓

Notification Registry

↓

Renderer

↓

NotificationCard

↓

User

This pipeline should remain stable even as new notification types are added.

12.6 Component Reuse Rules

The Notification Center must never duplicate existing viewers.

Instead:

Resource	Viewer
Post	Post Detail Viewer
Document	Document Viewer
Assignment	Assignment Viewer
Workspace	Workspace Home
Task	Task Detail
Meeting	Meeting Viewer
User	Profile
Group	Group Home
Study Group	Study Group Home

The Notification Center is an entry point, not a destination.

12.7 Performance Targets

The UI should:

Render incrementally.
Update only changed notifications.
Avoid full feed reloads.
Lazy-load previews.
Reuse DOM elements where practical.
Debounce search input.
Cache filter state.
Preserve scroll position after updates.
12.8 Testing Strategy
Unit Tests
Renderer selection
Aggregation rendering
Filter logic
Action execution
Registry lookups
Integration Tests
Notification API → UI
Live updates
HTMX partial updates
Drawer navigation
Deep linking
UI Tests
Mobile layouts
Desktop layouts
Keyboard navigation
Dark mode
Light mode
Reduced motion
Empty states
Regression Tests

Verify:

Existing notifications still render.
Old links continue working.
Notification preferences continue working through Settings → Notifications.
Unread counts remain correct.
Aggregation behaves consistently.
12.9 Rollout Plan

Deploy progressively.

Stage 1

Internal development.

Stage 2

Enable the new UI behind a feature flag for selected accounts.

Stage 3

Run both notification UIs temporarily.

Allow easy rollback if issues appear.

Stage 4

Make the new Notification Center the default.

Retain the old implementation only until stability is confirmed.

Stage 5

Remove legacy notification components and simplify the codebase.

12.10 Future Compatibility

The architecture should support future notification types without redesign.

Examples:

AI Assistant
Video Calls
Whiteboards
Shared Presentations
Collaborative Editing
Code Reviews
Calendar Events
Grade Releases
Git Integration
External Integrations

Adding a new notification should require only:

Define the backend event.
Add a rendering profile.
Register a renderer.

No existing renderer should need modification.

12.11 Definition of Done

The Notification Center is considered complete when:

All notification categories render through the registry.
Rendering profiles are fully implemented.
Existing platform viewers are reused.
Aggregation works correctly.
Search, filters, and bulk actions are functional.
Live updates work without page refreshes.
Notification preferences route to Settings → Notifications.
Accessibility requirements are met.
Performance targets are satisfied.
Legacy implementation has been retired.