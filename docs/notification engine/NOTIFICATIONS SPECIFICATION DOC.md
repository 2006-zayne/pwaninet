PwaniNet Notification Engine Specification
Version 1.0 (Draft)
Document Status: Draft
Classification: Platform Architecture Specification
Subsystem: Notification Engine
Platform: PwaniNet
Author: Engineer
Product Architect: Architect
Version: 1.0
Last Updated: August 2026
Chapter 1 — Introduction
1.1 Purpose
The Notification Engine is a platform subsystem responsible for transforming meaningful platform events into timely, relevant, and user-controlled notifications.
Unlike traditional notification systems that are tightly coupled to individual application features, the PwaniNet Notification Engine is designed as a reusable platform service capable of supporting every present and future subsystem within PwaniNet.
The engine is intended to serve not only the Social Platform but also future platform modules including:
·	Academic Course Workspaces
·	Study Groups
·	Collaboration Workspaces
·	Document Repository
·	AI Services
·	Meetings
·	Whiteboards
·	Video Calls
·	Future Mobile Applications
The Notification Engine shall operate independently from any individual feature and shall instead consume platform events generated throughout the system.
1.2 Vision
The Notification Engine shall provide a centralized, scalable, extensible, and user-centric notification platform capable of delivering meaningful information through multiple delivery channels while minimizing notification fatigue.
The engine shall ensure that users receive:
·	the right information,
·	at the right time,
·	through the appropriate channel,
·	according to their personal preferences.
1.3 Scope
This specification defines the architecture, principles, processing rules, and implementation requirements of the Notification Engine.
This document covers:
·	Event consumption
·	Notification generation
·	Notification aggregation
·	User preferences
·	Delivery architecture
·	Lifecycle management
·	Extension mechanisms
·	Integration with other platform services
1.4 Objectives
The Notification Engine is designed to achieve the following objectives.
Objective 1 — Centralization
Provide a single notification platform for every subsystem within PwaniNet.
Objective 2 — Decoupling
Ensure that application modules never communicate directly with notification delivery mechanisms.
Application modules shall emit events only.
The Notification Engine shall determine whether notifications are required.
Objective 3 — Scalability
Support future platform growth without requiring architectural redesign.
The addition of new modules shall not require modification of existing notification logic.
Objective 4 — User Control
Allow every user to determine:
·	which notifications they receive,
·	how they receive them,
·	when they receive them.
Objective 5 — Extensibility
Support future delivery mechanisms including:
·	Web Push
·	Mobile Push
·	Email
·	SMS
·	Additional channels without architectural changes.
Objective 6 — Low Coupling
Subsystems shall remain unaware of:
·	Firebase
·	Email Services
·	WebSockets
·	HTMX
·	Delivery mechanisms
Subsystems shall communicate only through events.
1.5 Design Philosophy
The Notification Engine is based upon six architectural principles.
Principle 1
Events represent facts.
Events describe things that happened.
Events do not decide whether users should be notified.
Principle 2
Notifications are derived from events.
Notifications do not exist independently.
Every notification originates from one or more platform events.
Principle 3
Delivery is independent.
Creating a notification and delivering a notification are separate responsibilities.
Failure to deliver shall never invalidate the notification itself.
Principle 4
User attention is limited.
Reducing unnecessary notifications is considered a primary design objective.
Aggregation, filtering and preferences shall be preferred over excessive notification delivery.
Principle 5
The platform is extensible.
Future platform modules shall integrate by emitting events.
The Notification Engine shall not require feature-specific modifications.
Principle 6
Users own their attention.
The platform recommends.
The user decides.
Every notification must respect user preferences.
1.6 Non-Goals
The Notification Engine is not responsible for:
·	generating application events
·	business logic of application modules
·	authentication
·	authorization
·	rendering notification UI
·	message formatting inside application features
These responsibilities belong to their respective platform services.
1.7 Expected Platform Consumers
The following platform modules are expected to consume Notification Engine services.
Module	Supported
Social Feed	✅
Course Workspaces	✅
Study Groups	✅
Collaboration Workspaces	✅
Project Management	✅
Meetings	✅
Whiteboards	✅
Group Chat	✅
Document Repository	✅
AI Assistant	✅
Mobile Applications	✅
Administrative Dashboard	✅
1.8 Architectural Position
                        PwaniNet Platform

     Users ─────────────────────────────────────────── Users

                         Presentation Layer
──────────────────────────────────────────────────────────────────

      Web UI        Mobile App        Future Clients

──────────────────────────────────────────────────────────────────

                       Platform Services

 Notification Engine     Workspace Engine     Search Engine

 Permission Engine       AI Engine            Document Engine

──────────────────────────────────────────────────────────────────

                           Core Services

       Event Engine      Identity      Storage      Database

──────────────────────────────────────────────────────────────────
The Notification Engine occupies the Platform Services layer. It consumes events from the Core Services layer and provides notification capabilities to presentation clients without embedding feature-specific business logic.
End of Chapter 1

Chapter 2 — Architectural Principles
2.1 Purpose
This chapter defines the fundamental architectural principles that govern the design, implementation, and evolution of the PwaniNet Notification Engine.
These principles are mandatory for all implementations of the Notification Engine. Future features, integrations, and extensions shall conform to these principles to ensure consistency, maintainability, and long-term scalability.
2.2 Architectural Philosophy
The Notification Engine shall be designed as an independent platform service rather than a feature-specific component.
The engine shall not contain business logic belonging to Social, Academic, Workspace, or Collaboration modules.
Instead, it shall consume platform events and determine how, when, and whether notifications should be delivered.
This architecture allows new platform modules to integrate with the Notification Engine without modifying its core implementation.
2.3 Core Concepts
The Notification Engine is built around the following concepts.
Event
An Event is a meaningful occurrence within PwaniNet that represents a state change or action performed by a user, the system, or an AI service.
Examples include:
·	A student uploads a document.
·	A lecturer publishes an assignment.
·	A user comments on a post.
·	A workspace member completes a task.
·	An AI assistant summarizes a meeting.
Events represent facts.
Events are not notifications.
Notification
A Notification is a user-facing message generated from one or more events.
Notifications exist solely to inform users about relevant events.
A notification shall always reference at least one originating event.
Rules Engine
The Rules Engine evaluates incoming events and determines:
·	whether notifications should be created,
·	who should receive them,
·	their importance,
·	applicable delivery channels,
·	aggregation eligibility.
Aggregation Engine
The Aggregation Engine reduces notification noise by combining related notifications into a single user-facing notification.
Aggregation shall never modify the underlying events.
Preference Engine
The Preference Engine evaluates user-specific notification preferences before delivery.
The Preference Engine determines whether a notification is permitted for a particular recipient.
Delivery Engine
The Delivery Engine is responsible for delivering notifications through one or more communication channels.
The Delivery Engine shall not generate notifications.
It shall only deliver notifications already created by the Rules Engine.
2.4 High-Level Architecture
The Notification Engine shall follow the architecture shown below.
                      Platform Event
                            │
                            ▼
                    Notification Rules
                            │
                            ▼
                  Notification Created
                            │
                            ▼
                  Preference Evaluation
                            │
                            ▼
                 Notification Aggregation
                            │
                            ▼
                   Delivery Scheduling
                            │
                            ▼
                     Delivery Engine
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      In-App         Web Push       Email
       Adapter        Adapter       Adapter
Each component has a single responsibility.
2.5 Architectural Layers
The Notification Engine is divided into five logical layers.
Layer 1 — Event Layer
Responsibilities:
·	Receive platform events.
·	Validate event integrity.
·	Forward events to the Rules Engine.
This layer does not create notifications.
Layer 2 — Decision Layer
Responsibilities:
·	Evaluate notification rules.
·	Determine recipients.
·	Determine notification priority.
·	Select delivery timing.
·	Determine grouping eligibility.
This layer creates Notification Objects.
Layer 3 — Preference Layer
Responsibilities:
·	Evaluate recipient preferences.
·	Apply muted workspaces.
·	Apply muted users.
·	Apply quiet hours.
·	Apply notification category settings.
Layer 4 — Processing Layer
Responsibilities:
·	Aggregate notifications.
·	Schedule delayed notifications.
·	Manage notification lifecycle.
·	Queue notifications for delivery.
Layer 5 — Delivery Layer
Responsibilities:
·	Deliver notifications.
·	Retry failed deliveries.
·	Track delivery status.
·	Support multiple delivery channels.
2.6 Separation of Responsibilities
Each component shall have one clearly defined responsibility.
Component	Responsibility
Event Engine	Produce events
Rules Engine	Create notifications
Preference Engine	Decide whether recipients should receive notifications
Aggregation Engine	Combine related notifications
Delivery Engine	Deliver notifications
Presentation Layer	Display notifications
No component shall assume responsibilities belonging to another component.
2.7 Dependency Rule
Dependencies shall flow in one direction only.
Events

↓

Rules

↓

Preferences

↓

Aggregation

↓

Delivery

↓

Presentation
Reverse dependencies are prohibited.
For example:
·	Delivery shall not create notifications.
·	Presentation shall not modify events.
·	Aggregation shall not change event data.
2.8 Single Responsibility Principle
Each engine shall solve exactly one problem.
Event Engine
Produces events.
Rules Engine
Determines notification eligibility.
Preference Engine
Determines recipient preferences.
Aggregation Engine
Reduces notification noise.
Delivery Engine
Transmits notifications.
Presentation Layer
Displays notifications.
2.9 Open/Closed Principle
The Notification Engine shall be open for extension but closed for modification.
Adding a new delivery mechanism shall not require changes to existing delivery implementations.
Example:
Current

In-App Adapter

Future

In-App Adapter

Push Adapter

Email Adapter

SMS Adapter
The Delivery Engine remains unchanged.
2.10 Feature Independence
Platform modules shall never send notifications directly.
Instead, modules shall emit events.
Example:
Document Repository

↓

Document Uploaded Event
NOT
Document Repository

↓

Create Notification
This rule applies to all current and future modules.
2.11 Event Immutability
Platform events are immutable.
Once created, an event shall never be modified or deleted.
Changes in system state shall generate new events.
Example:
Task Created

↓

Task Updated

↓

Task Completed
These represent three independent events.
2.12 Notification Mutability
Unlike events, notifications are mutable.
Notifications may be updated when aggregation occurs.
Example:
Initial Notification
Brian liked your post.
After aggregation
Brian and Kevin liked your post.
The underlying Like Events remain unchanged.
2.13 Delivery Independence
Notification creation and notification delivery are independent operations.
Failure to deliver shall not invalidate the notification.
Example:
Notification Created

↓

Push Failed

↓

Notification remains available In-App
2.14 User Attention Principle
User attention is a limited resource.
The Notification Engine shall prioritize relevance over volume.
The engine shall reduce notification fatigue through:
·	aggregation,
·	prioritization,
·	user preferences,
·	quiet hours,
·	delivery scheduling.
2.15 Extensibility
Future platform capabilities shall integrate through events.
Examples include:
·	AI Assistants
·	Video Meetings
·	Whiteboards
·	Live Collaboration
·	Real-Time Code Editing
·	Virtual Classrooms
·	External Integrations
No architectural redesign shall be required to support additional platform modules.
2.16 Architectural Decision Records (ADRs)
The following Architectural Decision Records are adopted by this specification.
ADR-001 — Events Are Immutable
Events represent historical facts and shall never be modified after creation.
ADR-002 — Notifications Are Derived From Events
Notifications shall only exist as representations of platform events.
Notifications shall never exist independently.
ADR-003 — Notification Delivery Is Independent
Notification creation and delivery are separate responsibilities.
ADR-004 — Users Control Their Attention
User preferences shall override default notification behavior except for explicitly defined critical system events.
ADR-005 — Modules Emit Events, Not Notifications
Application modules shall communicate with the Notification Engine exclusively through platform events.
Direct notification generation from feature modules is prohibited.
ADR-006 — Engines Have Single Responsibilities
Each engine shall solve one architectural concern.
Business logic shall not span multiple engines.
2.17 Summary
The architectural principles defined in this chapter establish the foundation for every subsequent chapter of this specification.
The Notification Engine is designed around:
·	Event-driven communication.
·	Independent processing stages.
·	Clear separation of responsibilities.
·	User-controlled attention management.
·	Extensibility through adapters and engines.
·	Low coupling between platform modules.
All future implementations shall comply with these principles unless superseded by a newer version of this specification.
End of Chapter 2

Chapter 3 — Event Engine
3.1 Purpose
The Event Engine is the foundational platform service responsible for recording meaningful occurrences within PwaniNet.
The Event Engine provides a standardized mechanism through which platform modules communicate state changes without directly interacting with one another.
Rather than allowing modules to call one another directly, modules emit events describing what occurred. Interested platform services consume those events independently.
The Event Engine forms the communication backbone of the PwaniNet platform.
3.2 Objectives
The Event Engine shall:
·	Provide a single mechanism for publishing platform events.
·	Decouple platform modules from one another.
·	Preserve a historical record of meaningful system activities.
·	Support multiple event consumers.
·	Enable future platform capabilities without modifying existing modules.
3.3 Architectural Position
                        PwaniNet Platform

                    ┌────────────────────┐
                    │   Social Module    │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Document Repository│
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Workspace Platform │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Academic Platform │
                    └─────────┬──────────┘
                              │
                     Emit Platform Events
                              │
                              ▼
                    ┌────────────────────┐
                    │    Event Engine    │
                    └─────────┬──────────┘
                              │
          ┌──────────┬────────┼──────────┬──────────┐
          ▼          ▼        ▼          ▼          ▼
 Notification   Activity   AI Memory   Analytics  Audit Log
    Engine       Feed
The Event Engine does not know who consumes events.
Consumers subscribe independently.
3.4 Design Principles
The Event Engine shall follow the following principles.
Principle 1 — Events describe facts.
Events represent something that happened.
Example:
Brian commented on Post #245.
NOT
Notify Ramsey.
Principle 2 — Events are immutable.
Once recorded, an event shall never be modified.
Subsequent changes shall generate new events.
Principle 3 — Events are generic.
The Event Engine shall not understand:
·	posts
·	workspaces
·	meetings
·	AI
It stores standardized event objects.
Principle 4 — Events are reusable.
A single event may be consumed by:
·	Notification Engine
·	Activity Feed
·	Analytics
·	AI Memory
·	Audit Log
simultaneously.
3.5 Event Definition
A Platform Event is defined as:
A meaningful occurrence representing a completed action or state transition performed by a user, the system, or an AI service.
An event is complete at the moment it is published.
Events shall never represent intentions.
Correct:
Document Uploaded
Incorrect:
Uploading Document
3.6 Event Producers
Any platform module may produce events.
Expected producers include:
Producer	Supported
Social Platform	✓
Document Repository	✓
Course Workspace	✓
Study Groups	✓
Collaboration Workspace	✓
Group Chat	✓
Video Meetings	✓
Whiteboard	✓
AI Assistant	✓
Administrative Console	✓
Authentication System	✓
3.7 Event Consumers
The following platform services consume events.
Consumer	Purpose
Notification Engine	Notify users
Activity Feed	Timeline generation
AI Context Engine	Workspace memory
Analytics Engine	Statistics
Audit Service	Historical records
Recommendation Engine	Future suggestions
Additional consumers may be added without modifying producers.
3.8 Event Categories
Events are classified according to their origin.
User Events
Generated directly by user actions.
Examples:
·	Post Created
·	Comment Added
·	Followed User
·	Uploaded Document
·	Joined Workspace
System Events
Generated automatically.
Examples:
·	Semester Changed
·	Assignment Deadline Reached
·	Document Indexed
·	Storage Optimized
AI Events
Generated by AI services.
Examples:
·	Meeting Summarized
·	Project Insights Generated
·	Duplicate Document Detected
Administrative Events
Generated by administrators.
Examples:
·	Announcement Published
·	Course Created
·	Workspace Archived
·	User Suspended
3.9 Event Structure
Every Platform Event shall contain the following conceptual fields.
Field	Description
Event ID	Unique event identifier
Event Type	Classification of event
Actor	Originator of the event
Action	Action performed
Target	Object acted upon
Context	Environment where event occurred
Audience	Intended recipients (if applicable)
Metadata	Additional event-specific information
Timestamp	Time of occurrence
Version	Event schema version
The exact database representation is defined in a later chapter.
3.10 Event Lifecycle
Every event progresses through the following lifecycle.
Action Occurs
      │
      ▼
Event Created
      │
      ▼
Event Validated
      │
      ▼
Event Published
      │
      ▼
Consumers Process Event
      │
      ▼
Event Archived
Once published, the Event Engine performs no further processing.
3.11 Event Publishing
Platform modules shall publish events only after the originating action has completed successfully.
Example:
Correct sequence:
Comment saved

↓

CommentCreated Event published
Incorrect sequence:
Publish Event

↓

Comment save fails
Publishing failed actions is prohibited.
3.12 Event Versioning
Event schemas shall support versioning.
Future schema changes shall not invalidate historical events.
Consumers shall process events according to their declared version.
3.13 Event Ordering
Events shall preserve chronological order based on their creation timestamp.
Consumers shall not assume that processing order is identical to publication order in distributed or asynchronous environments.
Where ordering is critical, consumers shall use timestamps and event identifiers to resolve sequence.
3.14 Event Reliability
Publishing an event shall not depend on the availability of downstream consumers.
If the Notification Engine, Analytics Engine, or AI Context Engine is unavailable, the event shall still be recorded successfully.
Consumers process events independently.
3.15 Error Handling
Invalid events shall be rejected before publication.
Examples include:
·	Missing actor.
·	Missing action.
·	Invalid target reference.
·	Unsupported event version.
Validation failures shall not propagate partial events.
3.16 Architectural Decision Records (ADRs)
ADR-007 — Events Are Platform Contracts
Events are the official communication mechanism between platform modules.
Direct feature-to-feature communication shall be avoided where an event can express the interaction.
ADR-008 — Publish After Success
Events shall only be published after the originating operation has completed successfully.
ADR-009 — Multiple Consumers
A platform event may be consumed by any number of independent services.
The Event Engine shall remain unaware of consumer implementations.
ADR-010 — Event Schemas Are Versioned
Platform events shall support schema evolution without breaking historical compatibility.
3.17 Summary
The Event Engine establishes a shared language for every subsystem in PwaniNet.
Rather than coupling modules through direct service calls, the platform communicates through immutable, versioned events.
This architecture enables independent evolution of:
·	Notification Engine
·	Workspace Platform
·	AI Context Engine
·	Analytics
·	Activity Feed
·	Future platform services
without introducing unnecessary dependencies.
Chapter 3.18 — Event Taxonomy
Purpose
The Event Taxonomy defines the official naming convention for all platform events.
Its objectives are to:
·	Ensure consistency across all platform modules.
·	Simplify event discovery.
·	Support analytics and debugging.
·	Reduce ambiguity.
·	Allow future services to subscribe to event families.
3.18.1 Naming Convention
Every event shall follow this pattern:
<domain>.<resource>.<action>
Examples
social.post.created

social.post.updated

social.post.deleted

social.comment.created

document.uploaded

document.updated

workspace.member.joined

workspace.member.left

meeting.started

meeting.ended
Notice something.
These names are descriptive, not implementation-specific.
Why three parts?
Let's decompose:
workspace.task.completed
Domain
workspace
Resource
task
Action
completed
Immediately understandable.
Domain
A domain represents a major subsystem.
Examples
social

document

workspace

meeting

chat

course

study

project

system

security

user

notification

ai
These shouldn't change often.
Resource
The object affected.
Examples
post

comment

document

member

task

assignment

meeting

message

whiteboard

role

workspace
Action
Always use past tense because an event represents something that already happened.
Approved actions:
created

updated

deleted

liked

commented

joined

left

completed

uploaded

downloaded

started

ended

published

assigned

submitted

approved

rejected

invited

accepted

declined
Notice what we avoid:
creating

uploading

processing
Those describe ongoing work.
Events describe completed facts.
Examples by Module
Social
social.post.created

social.post.deleted

social.post.liked

social.comment.created

social.comment.deleted

social.user.followed

social.user.unfollowed
Documents
document.uploaded

document.updated

document.deleted

document.reviewed

document.bookmarked

document.downloaded

document.indexed
Notice
indexed
That's a system event.
Workspace
workspace.created

workspace.archived

workspace.member.joined

workspace.member.left

workspace.member.removed

workspace.role.changed

workspace.task.created

workspace.task.completed
Course
course.assignment.published

course.assignment.submitted

course.assignment.graded

course.announcement.published
Study Groups
study.session.started

study.session.ended

study.member.joined

study.member.left
Collaboration
project.created

project.member.invited

project.member.joined

project.task.completed

project.milestone.completed
Chat
chat.message.sent

chat.message.edited

chat.message.deleted

chat.reaction.added
Meetings
meeting.started

meeting.ended

meeting.recording.ready

meeting.presentation.started

meeting.whiteboard.created
AI
ai.summary.generated

ai.document.tagged

ai.insight.generated

ai.recommendation.created
Notice
The AI is simply another event producer.
System
system.semester.changed

system.academic_year.changed

system.backup.completed

system.storage.cleaned
Security
security.login.detected

security.password.changed

security.device.added

security.account.locked
Event Families
One thing I'd like us to support from day one.
The Notification Engine may subscribe to:
workspace.*
Meaning
Everything under Workspace.
Or
document.*
Everything in Documents.
Or
*.created
Everything that was created.
This makes subscriptions incredibly flexible.
Reserved Domains
To avoid conflicts, these domains are reserved:
system

security

notification

event

user

ai
Modules should not redefine them.
ADR-011 — Canonical Event Naming
All platform events shall follow:
<domain>.<resource>.<action>
No exceptions.
This naming convention is mandatory for all present and future platform modules.
Engineer's Recommendation
Architect, I want to make one improvement that I think will save us from future headaches.
Instead of letting developers write event names as raw strings throughout the codebase:
publish_event("workspace.member.joined")
we should define a central Event Registry.
Conceptually:
EventTypes.WORKSPACE_MEMBER_JOINED
which resolves to:
workspace.member.joined
Why?
·	 No spelling mistakes (workspce.member.joined). 
·	IDE autocomplete.
·	Easy refactoring if naming changes.
·	One source of truth for every event.
·	Easier documentation and testing.
The registry itself will be an implementation detail that we cover later in the specification, but architecturally I think it's worth standardizing now.

End of Chapter 3
PwaniNet Notification Engine Specification
Chapter 4 — Event Schema
4.1 Purpose
This chapter defines the canonical structure of a Platform Event.
Every event emitted within PwaniNet shall conform to this schema regardless of the producing module.
The Event Schema establishes a common language between all platform services.
4.2 Design Goals
The schema is designed to be:
·	Generic
·	Extensible
·	Immutable
·	Versioned
·	Human-readable
·	Machine-readable
It should describe what happened, not how to process it.
4.3 Core Event Structure
Every event is composed of ten primary components.
Platform Event

├── Event Identity
├── Actor
├── Action
├── Target
├── Context
├── Audience
├── Metadata
├── Timestamp
├── Version
└── Correlation
Everything else is optional metadata.
4.4 Event Identity
Every event must have a globally unique identifier.
Purpose:
·	Traceability
·	Debugging
·	Analytics
·	Auditing
·	Deduplication
Example
Event ID

evt_019A7E4F3A12
This identifier never changes.
4.5 Actor
The Actor answers one question:
Who (or what) caused this event?
Actors are not limited to users.
Possible actors include:
Student

Lecturer

Administrator

AI Assistant

Notification Engine

System Scheduler
Examples
Actor

Brian
Actor

AI Assistant
Actor

System
One event always has exactly one primary actor.
4.6 Action
Action describes what occurred.
Actions are always expressed as completed verbs.
Examples
created

updated

deleted

joined

liked

uploaded

published

completed

approved

assigned

started

ended
Never use
creating

uploading

processing
Those describe processes, not facts.
4.7 Target
The Target is the object upon which the action occurred.
Examples
Post

Comment

Workspace

Task

Meeting

Document

Assignment

Whiteboard

User
Examples
Actor:
Brian

Action:
liked

Target:
Post #245
4.8 Context
Context answers:
Where did this happen?
This is one of the most powerful concepts in the architecture.
Examples
Public Feed

CSC221 Workspace

Project Alpha

Study Group 7

Document Repository

Meeting Room 12
Notice
The same action
message.sent
can occur inside:
·	Direct Chat
·	Study Group
·	Workspace
·	Meeting
Context distinguishes them.
4.9 Audience
Audience defines who may be interested in the event.
Important:
The audience is not the final notification recipients.
It is simply the intended scope.
Examples
Specific User

Workspace Members

Course Members

Followers

Administrators

Everyone

Custom Group
Later...
The Rules Engine decides exactly who receives notifications.
4.10 Metadata
Metadata contains event-specific information.
Unlike the previous fields, metadata is flexible.
Examples
Document Uploaded
File Name

Course

Semester

File Size
Task Completed
Completion %

Duration

Assigned By
Meeting Started
Meeting ID

Host

Recording Enabled
The Event Engine does not interpret metadata.
It merely stores and transports it.
4.11 Timestamp
Every event records the exact moment it occurred.
This timestamp represents:
The completion of the action.
Not
The beginning.
Not
The notification time.
4.12 Version
Every event declares the schema version used during creation.
Example
Version

1.0
Future versions remain backward compatible.
4.13 Correlation
Architect...
This is the field I deliberately saved for last.
I think this is what will make the Workspace Platform incredibly powerful.
Correlation answers:
Which larger activity does this event belong to?
Imagine
Brian creates Task

↓

Brian edits Task

↓

Brian uploads Document

↓

Brian starts Meeting

↓

Brian completes Task
Those are five independent events.
But they all belong to
Project Alpha
Correlation links them.
Another example
Student submits assignment.
Later
Lecturer grades assignment.
Later
Student downloads feedback.
Three events.
One academic workflow.
Correlation keeps them connected.
Why Correlation Matters
Without correlation:
Thousands of isolated events.
With correlation:
Project Timeline

Meeting Timeline

Assignment Timeline

Workspace Timeline

AI Memory Timeline
One field unlocks all of these.
4.14 Event Relationships
Events may reference previous events.
Example
Comment Created

↓

Comment Edited
The second event may reference the first.
This creates a chain of history without modifying existing events.
4.15 Event Example
Let's put everything together.
Event ID:
evt_019A7E4F3A12

Type:
workspace.task.completed

Actor:
Brian

Action:
completed

Target:
Task #81

Context:
Project Alpha

Audience:
Workspace Members

Metadata:
{
    duration: "4 hours",
    priority: "High"
}

Timestamp:
2026-08-03T14:52:00Z

Version:
1.0

Correlation:
Project Alpha Sprint 2
Notice how easy it is to understand.
No code.
No Django.
Just facts.
4.16 Event Validation Rules
Every event must satisfy these requirements:
✅ Has Event ID
✅ Has Event Type
✅ Has Actor
✅ Has Action
✅ Has Target
✅ Has Timestamp
✅ Has Version
Context, Audience, Metadata, and Correlation may be optional depending on the event.
Invalid events shall not be published.
ADR-012 — Canonical Event Schema
All platform events shall conform to the Event Schema defined in this chapter.
No platform module shall introduce alternative event structures.
ADR-013 — Correlation Enables Workflows
Events participating in the same logical workflow should reference a common Correlation Identifier whenever applicable.
This enables:
·	Project timelines
·	Workspace history
·	AI reasoning
·	Analytics
·	Activity reconstruction
without coupling unrelated events.
Engineer's Review
Architect...
I think we've just crossed a major milestone.
Look at what we've actually designed.
This isn't a notification model.
It's not even an event model.
It's a Platform Event Standard.
I honestly think this schema shouldn't live under the Notification Engine forever.
I'd eventually extract it into its own document:
PwaniNet Platform Event Standard (PPES) v1.0
Then every subsystem—not just notifications—would officially depend on that standard.
One architectural improvement I'd make
There's one more field I'd like to introduce before we leave the Event Engine:
Source
Not the actor.
The source subsystem.
Example:
Source:
Document Repository
or
Source:
Workspace Platform
Why?
Imagine your AI Context Engine receives one million events.
Instead of inspecting every event type, it can immediately answer:
·	"Give me all events produced by the Workspace Platform."
·	"Show only Document Repository events."
·	"Ignore Social events."
That separation between Actor ("Brian"), Source ("Workspace Platform"), and Context ("Project Alpha") makes the event model even more expressive and keeps responsibilities distinct.
I would add that field now while the architecture is still young, rather than discovering we need it after thousands of events have already been recorded.
Revised Core Event Structure
Platform Event

├── Event Identity
├── Actor
├── Source
├── Action
├── Target
├── Context
├── Audience
├── Metadata
├── Timestamp
├── Version
└── Correlation
4.X Source
Purpose
The Source identifies the platform subsystem responsible for publishing the event.
While the Actor identifies who performed the action, the Source identifies which platform component generated the event.
These concepts are independent.
Examples
Actor:
Brian

Source:
Social Platform

Action:
created

Target:
Post #81
Actor:
System Scheduler

Source:
Academic Platform

Action:
changed

Target:
Semester
Actor:
AI Assistant

Source:
AI Platform

Action:
generated

Target:
Meeting Summary
Approved Sources
Initially, PwaniNet will define these canonical source subsystems:
Social Platform

Document Repository

Workspace Platform

Course Platform

Study Platform

Collaboration Platform

Meeting Platform

Chat Platform

AI Platform

Notification Engine

Authentication Service

Administrative Console

Academic Platform

Storage Service

System Scheduler
As the platform evolves, new sources may be added without changing the schema.
Why this field matters
Imagine the AI Context Engine receives these three events:
social.post.created

workspace.task.completed

document.uploaded
Without Source, it has to infer which subsystem produced them.
With Source, filtering becomes straightforward:
Source = Workspace Platform
or
Source = Document Repository
This is valuable for:
·	Analytics
·	AI context building
·	Audit logs
·	Debugging
·	Monitoring
·	Platform metrics
Engineer's Recommendation
I'd go one step further.
Let's make Source a controlled vocabulary.
Instead of developers writing arbitrary strings like:
Workspace
workspace
Projects Workspace
Collaboration
we define an official registry of source names. Every event must use one of those canonical identifiers.
That gives us consistency across logs, analytics, AI, and debugging.
One more idea
As we've refined the model, I think the canonical event schema should now be:
Platform Event

├── Event ID
├── Event Type
├── Actor
├── Source
├── Action
├── Target
├── Context
├── Audience
├── Metadata
├── Timestamp
├── Version
└── Correlation

Chapter 5 — Notification Rules Engine
5.1 Purpose
The Notification Rules Engine is responsible for transforming platform events into user notifications.
It evaluates every published event against a set of deterministic rules to decide:
·	Whether a notification should be created.
·	Who should receive it.
·	Its priority.
·	Its category.
·	Whether it can be aggregated.
·	Which delivery channels are permitted.
·	Whether delivery should occur immediately or later.
The Rules Engine is the decision-making component of the Notification Engine.
It does not deliver notifications.
It does not display notifications.
It only decides.
5.2 Responsibilities
The Rules Engine shall:
·	Consume platform events.
·	Evaluate notification rules.
·	Identify recipients.
·	Assign priorities.
·	Assign notification categories.
·	Determine aggregation eligibility.
·	Generate Notification Objects.
·	Pass notifications to downstream engines.
It shall not:
·	Deliver notifications.
·	Send push messages.
·	Send emails.
·	Render UI.
·	Store user preferences.
5.3 Position Within the Pipeline
             Platform Event
                    │
                    ▼
          Notification Rules Engine
                    │
                    ▼
         Notification Object Created
                    │
                    ▼
          Preference Engine
                    │
                    ▼
          Aggregation Engine
                    │
                    ▼
            Delivery Engine
5.4 Rule Evaluation
Every event shall pass through the Rules Engine exactly once.
The engine evaluates the event in the following order:
Receive Event
      │
      ▼
Validate Event
      │
      ▼
Find Matching Rules
      │
      ▼
Determine Recipients
      │
      ▼
Assign Priority
      │
      ▼
Assign Category
      │
      ▼
Determine Aggregation
      │
      ▼
Create Notification
5.5 Rule Structure
Every notification rule consists of seven logical parts.
Rule

├── Trigger
├── Conditions
├── Recipients
├── Priority
├── Category
├── Delivery Policy
└── Aggregation Policy
This makes every rule predictable and easy to reason about.
5.6 Trigger
A trigger specifies which event activates the rule.
Examples:
social.post.liked

social.comment.created

document.uploaded

workspace.task.completed

meeting.started
One trigger may activate multiple rules.
5.7 Conditions
Conditions determine whether the rule actually applies.
Example:
IF

comment author

≠

post owner

THEN

Create notification.
Without conditions:
You could receive notifications for liking your own post or commenting on your own content.
Conditions prevent meaningless notifications.
5.8 Recipients
Recipients specify who should receive the notification.
Examples:
Post Owner

Comment Author

Workspace Members

Mentioned Users

Course Students

Meeting Participants

Project Maintainers
A single event may generate notifications for multiple recipients.
5.9 Priority
Every notification shall receive a priority.
Initial priorities:
Priority	Meaning
Critical	Must never be missed
High	Requires prompt attention
Normal	Standard notification
Low	Informational only
Priority influences delivery behavior but does not override user preferences, except for explicitly defined critical system events.
5.10 Category
Every notification belongs to a category.
Initial categories:
Social

Academic

Workspace

Communication

Meeting

Project

Document

Security

System

AI
Categories simplify user preference management.
5.11 Delivery Policy
The Rules Engine determines the intended delivery strategy.
Examples:
Immediate

Delayed

Scheduled

Digest
It does not deliver the notification.
It simply expresses intent.
5.12 Aggregation Policy
The Rules Engine specifies whether similar notifications may be grouped.
Possible values:
Never

Allowed

Required
Examples:
Event	Aggregation
Post Likes	Allowed
Comments	Allowed
Assignment Published	Never
Security Login	Never
Workspace Join Requests	Allowed
5.13 Rule Examples
Example 1 — Like Notification
Trigger:
social.post.liked
Rule:
Recipient:
Post Owner

Priority:
Low

Category:
Social

Aggregation:
Allowed

Delivery:
Immediate
Example 2 — Assignment Published
Trigger:
course.assignment.published
Rule:
Recipients:
Course Members

Priority:
High

Category:
Academic

Aggregation:
Never

Delivery:
Immediate
Example 3 — Meeting Started
Trigger:
meeting.started
Rule:
Recipients:
Meeting Participants

Priority:
High

Category:
Meeting

Aggregation:
Never

Delivery:
Immediate
Example 4 — Document Uploaded
Trigger:
document.uploaded
Rule:
Recipients:
Followers of uploader
OR
Workspace Members

Priority:
Normal

Category:
Document

Aggregation:
Allowed
Notice that a single event may have multiple recipient groups.
5.14 Multiple Rule Execution
One event may satisfy multiple notification rules.
Example:
workspace.task.completed
May notify:
·	Task creator
·	Workspace owner
·	Assigned reviewer
Each notification is evaluated independently.
5.15 Rule Independence
Rules shall never depend on other rules.
Each rule evaluates an event independently.
This ensures predictable behavior and simplifies testing.
5.16 Rule Extensibility
Adding new event types shall require only the addition of new rules.
Existing rules shall not require modification.
This complies with the Open/Closed Principle established in Chapter 2.
5.17 Rule Failures
If a rule cannot be evaluated:
·	The failure shall be logged.
·	Other rules shall continue processing.
·	A single failing rule shall not block the entire event pipeline.
Architectural Decision Records
ADR-014 — Rules Decide, They Do Not Deliver
The Rules Engine shall determine notification intent only.
Delivery responsibilities belong exclusively to the Delivery Engine.
ADR-015 — One Event May Produce Many Notifications
A single event may legitimately result in multiple Notification Objects for different recipients.
ADR-016 — Rules Are Independent
Notification rules shall not invoke or depend upon one another.
Engineer's Review
Architect, this chapter is solid, but I want to make one architectural enhancement before we move on.
Right now, rules are treated as isolated decisions. As PwaniNet grows, you'll likely have hundreds of rules. We need a way to organize them.
I propose introducing Rule Sets.
For example:
Social Rules
├── Like Rules
├── Comment Rules
├── Mention Rules

Academic Rules
├── Assignment Rules
├── Announcement Rules
├── Grade Rules

Workspace Rules
├── Membership Rules
├── Task Rules
├── Meeting Rules
The engine can then load and evaluate rule sets by domain instead of searching one giant collection of rules.

Chapter 6 — Notification Object
6.1 Purpose
The Notification Object is the canonical representation of information intended for one or more users.
It is created by the Notification Rules Engine after evaluating a platform event and subsequently processed by downstream components, including the Aggregation Engine, Preference Engine, and Delivery Engine.
Unlike Platform Events, Notification Objects are user-centric rather than system-centric.
6.2 Design Goals
The Notification Object shall be:
·	User-centric
·	Mutable
·	Aggregatable
·	Traceable to originating events
·	Delivery-independent
·	Presentation-independent
·	Extensible
A Notification Object describes what the user should know, not how it should be displayed.
6.3 Relationship to Platform Events
Every Notification Object originates from one or more Platform Events.
Platform Event(s)
        │
        ▼
 Notification Rules Engine
        │
        ▼
 Notification Object
Examples
Event

Brian liked your post.
becomes
Notification

Brian liked your post.
Later
Kevin liked your post.
does not create a second notification.
Instead
Brian and Kevin liked your post.
The notification changes.
The events never do.
6.4 Event vs Notification
Platform Event	Notification
Immutable	Mutable
Historical record	User message
System-centric	User-centric
Never changes	May be updated
May have many consumers	Belongs to recipient(s)
This distinction shall be maintained throughout the platform.
6.5 Notification Structure
Every Notification Object shall contain the following conceptual components.
Notification

├── Notification ID
├── Recipient
├── Source Event(s)
├── Type
├── Category
├── Priority
├── Title
├── Summary
├── Context
├── Status
├── Delivery Policy
├── Aggregation Data
├── Metadata
├── Created At
├── Updated At
└── Expiration
6.6 Notification Identity
Every notification shall have a globally unique identifier.
Example
ntf_019B8F4C72
This identifier remains constant throughout the notification lifecycle.
6.7 Recipient
Every Notification Object belongs to exactly one recipient.
Examples
Ramsey

Brian

Mary
If ten users should receive the same information, ten Notification Objects shall exist.
This enables:
·	independent read status
·	independent preferences
·	independent delivery history
ADR-017 — One Notification, One Recipient
A Notification Object shall never be shared across multiple users.
Recipient-specific state must remain isolated.
6.8 Source Events
A notification may reference one or more originating events.
Example
Event 1

Brian liked Post #20

Event 2

Kevin liked Post #20

Event 3

Alice liked Post #20
Notification
Brian, Kevin and Alice liked your post.
The Notification Object stores references to all three events.
6.9 Notification Type
The type identifies the semantic purpose of the notification.
Examples
Like

Comment

Mention

Assignment

Meeting

Workspace

Document

Security

System

AI
Type influences iconography and interaction but not business logic.
6.10 Category
Categories group related notification types for preference management.
Example
Category

Social

Type

Like
Category

Academic

Type

Assignment Published
Categories are broader than types.
6.11 Priority
Every notification shall be assigned one priority level.
Critical

High

Normal

Low
Priority influences:
·	delivery timing
·	quiet-hour behavior
·	presentation order
Priority does not determine visual styling directly.
6.12 Title
The Title is a concise human-readable headline.
Examples
New Assignment Available
Brian liked your post
Meeting starts in 10 minutes
The Rules Engine generates titles.
The UI displays them.
6.13 Summary
The Summary provides additional context.
Example
CSC221 Assignment 3
is due on Friday at 11:59 PM.
or
Three new members joined
Project Alpha today.
The Summary may evolve during aggregation.
6.14 Context
Context identifies where the notification belongs.
Examples
Course

CSC221
Workspace

Project Alpha
Document Repository
This enables context-aware filtering.
6.15 Status
Every notification progresses through a lifecycle.
Initial statuses:
Created

Queued

Delivered

Seen

Read

Archived

Expired
State transitions are defined in a later chapter.
6.16 Delivery Policy
The Rules Engine assigns an intended delivery policy.
Examples
Immediate

Scheduled

Delayed

Digest
The Delivery Engine executes the policy.
6.17 Aggregation Data
Aggregation information shall include:
·	Aggregation Key
·	Number of merged events
·	First event time
·	Latest event time
This allows notifications to grow over time without losing history.
6.18 Metadata
Metadata stores notification-specific information that does not belong in the core schema.
Examples
Avatar URLs

Deep Link

Thumbnail

Badge Count

Preview Image
The metadata structure is extensible.
6.19 Created At
Records when the Notification Object was first created.
This timestamp never changes.
6.20 Updated At
Records the last modification.
Aggregation updates this timestamp.
Preference evaluation does not.
6.21 Expiration
Some notifications become irrelevant.
Examples
Meeting Starts

Expires

After meeting ends.
Assignment Due

Expires

After submission deadline.
Expired notifications may be archived or hidden according to platform policy.
6.22 Notification Immutability Rules
Only the following fields may change after creation:
·	Summary
·	Aggregation Data
·	Status
·	Updated At
·	Metadata (where appropriate)
The following fields shall remain immutable:
·	Notification ID
·	Recipient
·	Source Events
·	Created At
·	Original Priority
This preserves traceability while allowing evolution.
6.23 Notification Example
Notification ID:
ntf_019B8F4C72

Recipient:
Ramsey

Source Events:
evt_101
evt_102
evt_103

Type:
Like

Category:
Social

Priority:
Low

Title:
Your post received new likes

Summary:
Brian, Kevin and Alice liked your post.

Context:
Public Feed

Status:
Delivered

Delivery Policy:
Immediate

Aggregation:
3 Events

Created:
10:00

Updated:
10:08

Expiration:
None
Architectural Decision Records
ADR-018 — Notifications Represent User Knowledge
A Notification Object represents information intended for a specific user rather than a historical system fact.
ADR-019 — Notifications Are Mutable
Notifications may evolve through aggregation and lifecycle state changes while maintaining references to their originating events.
ADR-020 — Presentation Independence
The Notification Object shall not contain UI-specific formatting, colors, layout instructions, or rendering logic.
Presentation is the responsibility of the client application.
Engineer's Review
Architect, this is the first chapter where I'd actually propose a significant enhancement before freezing the specification.
We're missing a concept that modern notification systems rely on:
Notification Actions
A notification shouldn't just inform; it should optionally offer an action.
For example:
·	Workspace Invitation
o	Accept
o	Decline
·	Meeting Reminder
o	Join
o	Snooze
·	Document Approval Request
o	Review
·	Assignment Published
o	Open Assignment
These actions are not part of the UI—they're part of the notification's semantic meaning. The web interface, PWA, and future Flutter app would all render them in their own style, but they'd be driven by the same underlying definition.
I recommend we introduce a dedicated Action Model in the next revision of this chapter instead of burying actions inside metadata. That keeps the Notification Object clean, expressive, and consistent across all clients.
6.24 Notification Actions
Rather than placing actions inside metadata, we define them as a first-class part of the Notification Object.
That gives us a consistent way to support:
·	Group join approvals
·	Workspace invitations
·	Friend/follow requests (if added)
·	Assignment review workflows
·	Document moderation
·	Event RSVPs
·	Meeting participation
·	Future AI approval flows
without redesigning the notification model later.
This is exactly the kind of capability that's expensive to bolt on later but straightforward to support when it's part of the architecture from the beginning. It also fits naturally with the Workspace Platform you're planning, where many notifications will represent workflows rather than simple alerts.


Chapter 7 — Aggregation Engine
7.1 Purpose
The Aggregation Engine is responsible for reducing notification fatigue by intelligently combining related Notification Objects into a single, coherent notification.
Aggregation improves the user experience by presenting multiple related events as one evolving notification while preserving references to all originating Platform Events.
The Aggregation Engine operates exclusively on Notification Objects.
It never modifies Platform Events.
7.2 Objectives
The Aggregation Engine shall:
·	Reduce notification noise.
·	Preserve important information.
·	Improve readability.
·	Maintain event traceability.
·	Support evolving notifications.
·	Minimize duplicate notifications.
7.3 Position Within Architecture
Platform Events
        │
        ▼
Notification Rules Engine
        │
        ▼
Notification Objects
        │
        ▼
Aggregation Engine
        │
        ▼
Preference Engine
        │
        ▼
Delivery Engine
Engineering Decision
I intentionally moved Aggregation before the Preference Engine.
Why?
If ten "like" notifications arrive within seconds, it is more efficient to aggregate them once and then evaluate preferences on the resulting notification rather than evaluating ten separate notifications.
This reduces processing and simplifies downstream logic.
ADR-021 — Aggregation precedes Preference Evaluation
7.4 Aggregation Philosophy
Aggregation shall answer one question:
"Would showing these separately provide additional value?"
If the answer is No, aggregate them.
If the answer is Yes, keep them separate.
Aggregation is therefore a semantic decision rather than merely a timing decision.
7.5 Aggregation Eligibility
A notification may only be aggregated if all mandatory conditions are satisfied.
Mandatory Conditions
The notifications must have the same:
·	Recipient
·	Notification Type
·	Category
·	Context
·	Aggregation Key
and must fall within the configured aggregation window.
If any mandatory condition differs, aggregation shall not occur.
7.6 Aggregation Key
The Aggregation Key uniquely identifies notifications that belong to the same logical conversation.
Example:
Like Notification

Recipient:
Ramsey

Target:
Post #81

Aggregation Key:
like:post:81
All likes for Post #81 share the same key.
Comments
comment:post:81
Workspace Requests
workspace_join:csc221
Assignments
assignment:CSC221
ADR-022 — Aggregation by Logical Subject
Aggregation shall be based on logical subjects rather than event identifiers.
7.7 Aggregation Window
Aggregation occurs only during a configurable time window.
Example defaults:
Notification Type	Window
Likes	30 minutes
Comments	15 minutes
Followers	24 hours
Join Requests	Until reviewed
Assignment Publications	1 hour
Meeting Reminders	Never
Different notification types may define different windows.
7.8 Evolution of Notifications
Notifications shall evolve as additional events are aggregated.
Example:
Brian liked your post.
↓
Brian and Kevin liked your post.
↓
Brian, Kevin and Alice liked your post.
↓
15 people liked your post.
The Notification ID remains unchanged.
7.9 Aggregation Thresholds
Different presentation strategies apply based on participant count.
Count	Presentation
1	Brian liked your post.
2	Brian and Kevin liked your post.
3	Brian, Kevin and Alice liked your post.
4–99	15 people liked your post.
100+	100+ people liked your post.
The UI may provide additional details when expanded.
7.10 Actor Collection
Each aggregated notification maintains a collection of contributing actors.
Example:
Actors

Brian

Kevin

Alice

Mary

John
This enables:
·	overlapping avatars
·	participant lists
·	AI summaries
·	analytics
The UI decides how many avatars to display.
7.11 Event Collection
The notification shall maintain references to every contributing Platform Event.
Example:
Events

evt101

evt102

evt103

evt104
Event history is never lost.
7.12 Aggregation Actions
Aggregated notifications may expose actions that operate on the group.
Example:
5 Join Requests

Actions

Review Requests
Instead of
Approve Brian

Approve Kevin

Approve Alice

Approve John

Approve Mary
The user enters a review interface where individual decisions are made.
This prevents oversized notifications.
7.13 Notifications That Shall Never Aggregate
Certain notifications are too important to merge.
Examples include:
·	Security alerts
·	Password changes
·	Login verification
·	Assignment deadline reminders
·	Meeting starting
·	Payment confirmations (future)
·	Account suspension
·	Moderator warnings
Each shall remain independent.
ADR-023 — Critical Notifications Are Never Aggregated
Notifications marked Critical shall bypass aggregation.
7.14 Smart Aggregation
Aggregation shall preserve meaning.
Incorrect:
Brian liked your post.

↓

Brian commented on your post.
These shall never merge.
Different actions represent different intentions.
Correct:
Brian liked

Kevin liked

Alice liked
↓
3 people liked your post.
7.15 Context Isolation
Aggregation shall never occur across contexts.
Example:
Project Alpha

Brian completed Task
shall never aggregate with
Project Beta

Kevin completed Task
Even though the event types match.
7.16 Read State
Reading an aggregated notification marks the notification as read.
It does not modify the underlying Platform Events.
Future events added after it has been read shall return the notification to an unread state.
Example:
Brian liked your post.

(Read)
Later
Kevin liked your post.
↓
Notification becomes unread again.
7.17 Expansion
Aggregated notifications shall support expansion.
Collapsed:
15 people liked your post.
Expanded:
Brian

Kevin

Alice

Mary

John

...

View All
Expansion is a presentation concern.
The Aggregation Engine only supplies the underlying data.
7.18 Performance Considerations
Aggregation shall avoid repeatedly rebuilding notifications from scratch.
Instead, existing Notification Objects should be incrementally updated with:
·	new actors
·	new event references
·	updated summary
·	updated timestamp
·	updated counters
This minimizes processing overhead.
7.19 Aggregation Metrics
Each aggregated notification shall maintain:
·	Event Count
·	Actor Count
·	First Event Time
·	Latest Event Time
·	Last Updated Time
These values support analytics and intelligent presentation.
Architectural Decision Records
ADR-021 — Aggregate Before Preference Evaluation
Aggregation shall occur before user preference evaluation.
ADR-022 — Aggregate by Logical Subject
Aggregation decisions are based on Aggregation Keys rather than event IDs.
ADR-023 — Critical Notifications Are Never Aggregated
Notifications classified as Critical shall bypass aggregation.
ADR-024 — Aggregation Preserves Event History
Aggregation shall never remove references to originating Platform Events.
Engineer's Review
Architect, I think this chapter is about 85% complete, but there's one capability that I believe would make PwaniNet stand out.
Semantic Aggregation
Instead of only grouping by identical actions, the engine should understand related workflows.
Imagine this sequence:
Brian requested to join CSC221.

Kevin requested to join CSC221.

Mary requested to join CSC221.
Instead of only saying:
3 new join requests
the notification could become:
3 students are waiting for approval in CSC221.
Or consider a project workspace:
Task completed

↓

Document uploaded

↓

Meeting scheduled
Rather than three unrelated notifications, the engine could produce:
Project Alpha has 3 new updates.
Expanding it would reveal the individual activities.
This isn't simple aggregation anymore—it's semantic aggregation, where the system summarizes a related set of activities while preserving every underlying even


Chapter 8 — Preference Engine
8.1 Purpose
The Preference Engine is responsible for determining whether a Notification Object should proceed to delivery based on user-defined notification preferences and platform policies.
The Preference Engine evaluates each notification independently after aggregation and before delivery.
It ensures that users receive notifications that are relevant to them while respecting mandatory system notifications.
8.2 Objectives
The Preference Engine shall:
·	Respect user notification preferences.
·	Support fine-grained notification controls.
·	Support per-channel preferences.
·	Enforce mandatory platform notifications.
·	Reduce unwanted notifications.
·	Preserve user autonomy.
8.3 Position Within Architecture
Platform Event
      │
      ▼
Notification Rules Engine
      │
      ▼
Aggregation Engine
      │
      ▼
Preference Engine
      │
      ▼
Delivery Engine
8.4 Responsibilities
The Preference Engine shall:
·	Load recipient preferences.
·	Evaluate notification eligibility.
·	Apply platform policies.
·	Determine allowed delivery channels.
·	Forward approved notifications.
The Preference Engine shall not:
·	Modify Platform Events.
·	Deliver notifications.
·	Aggregate notifications.
·	Generate notifications.
8.5 Preference Hierarchy
When determining whether a notification may be delivered, the engine evaluates preferences in the following order:
Platform Policy
        │
        ▼
User Account Settings
        │
        ▼
Notification Category
        │
        ▼
Notification Type
        │
        ▼
Delivery Channel
More specific preferences override broader ones unless prohibited by platform policy.
8.6 Preference Levels
Users may configure preferences at multiple levels.
Global
Example:
Disable all social notifications.
Category
Example:
Receive Academic notifications.

Mute Social notifications.
Notification Type
Example:
Receive Assignment notifications.

Mute Like notifications.

Receive Mentions.
Context
Preferences may apply to a specific context.
Examples:
Mute Project Alpha.

Mute CSC221 Group.

Mute Study Group 7.
This allows users to silence a noisy workspace without leaving it.
8.7 Channel Preferences
Users may configure different preferences for each delivery channel.
Example
Notification Type	In-App	Push	Email
Likes	✓	✗	✗
Mentions	✓	✓	✗
Assignment Published	✓	✓	✓
Security Alerts	✓	✓	✓
This allows users to receive all notifications inside PwaniNet while limiting interruptions outside the application.
8.8 Mandatory Notifications
Certain notifications shall bypass user preferences.
Examples include:
·	Password changes.
·	Security alerts.
·	Suspicious login activity.
·	Account suspension.
·	Critical platform announcements.
These notifications are required for platform integrity and user safety.
ADR-025 — Mandatory Notifications Cannot Be Disabled
Critical platform notifications shall always be delivered through at least one supported channel.
8.9 Quiet Hours
The Preference Engine shall support user-defined quiet hours.
Example:
22:00

↓

07:00
During quiet hours:
·	Low priority notifications may be delayed.
·	Normal notifications may be delayed.
·	High priority notifications may follow user preference.
·	Critical notifications bypass quiet hours.
8.10 Workspace Overrides
Workspace administrators may define recommended notification defaults for workspace members.
Users retain the ability to customize their own preferences unless the notification is designated as mandatory for workspace governance.
Example:
Project Alpha

Default

Task Updates

Enabled
A member may later choose:
Task Updates

Muted
unless project policy requires otherwise.
8.11 Temporary Muting
Users may temporarily mute notifications.
Examples:
Mute

1 Hour

8 Hours

24 Hours

Until Tomorrow

Custom Date
This is particularly useful during exams or focused work sessions.
8.12 Preference Evaluation
For every Notification Object:
Load Preferences

↓

Check Platform Policy

↓

Check Category

↓

Check Type

↓

Check Context

↓

Check Channel

↓

Decision
Possible outcomes:
Allow

Suppress

Delay
8.13 Preference Changes
Changing preferences shall affect only future notifications.
Previously generated notifications shall remain unchanged.
8.14 Default Preferences
New users shall inherit platform default preferences.
These defaults should prioritize awareness without overwhelming the user.
Example:
Category	Default
Academic	Enabled
Workspace	Enabled
Meeting	Enabled
Security	Enabled
Social	Enabled
AI	Enabled
Marketing (future)	Disabled
8.15 Preference Synchronization
Preferences belong to the user account rather than a specific device.
Changes made on one device shall apply across:
·	Web
·	PWA
·	Future Flutter application
8.16 Auditability
Preference changes should be recorded for administrative auditing and troubleshooting.
The audit log should include:
·	User
·	Preference changed
·	Previous value
·	New value
·	Timestamp
Architectural Decision Records
ADR-025 — Mandatory Notifications Cannot Be Disabled
Critical platform notifications override user preferences.
ADR-026 — Preferences Are User-Centric
Preferences belong to the user account and are synchronized across devices.
ADR-027 — Preference Changes Are Prospective
Preference changes affect only notifications created after the change.
Engineer's Review
Architect, there's one capability I would reserve for the future because it aligns perfectly with the Workspace Platform and AI.
Adaptive Preferences
Instead of relying solely on manual settings, PwaniNet could learn from user behavior.
Examples:
·	A user always opens assignment notifications immediately → prioritize future academic notifications.
·	A user consistently dismisses "like" notifications without reading → suggest muting them.
·	A user is highly active in Project Alpha but ignores Project Beta → recommend different notification levels for each workspace.
The system would never change preferences automatically. It would only make recommendations such as:
"You've dismissed 95% of like notifications this month. Would you like to mute them?"
That preserves user control while making the notification system increasingly personalized over time.
With this chapter complete, the next chapter is Chapter 9 — Delivery Engine.
Chapter 9 — Delivery Engine
9.1 Purpose
The Delivery Engine is responsible for delivering approved Notification Objects through one or more supported communication channels.
The Delivery Engine is the final stage of the Notification Engine pipeline.
It receives notifications that have already passed rule evaluation, aggregation, and preference evaluation.
The Delivery Engine does not decide whether a notification should exist.
It only determines how and when it reaches the user.
9.2 Objectives
The Delivery Engine shall:
·	Deliver notifications through supported channels.
·	Support multiple simultaneous delivery channels.
·	Guarantee reliable delivery.
·	Retry transient failures.
·	Record delivery outcomes.
·	Remain independent of notification creation.
9.3 Position Within Architecture
Platform Event
      │
      ▼
Notification Rules Engine
      │
      ▼
Aggregation Engine
      │
      ▼
Preference Engine
      │
      ▼
Delivery Engine
      │
      ▼
Delivery Adapters
      │
      ▼
User
9.4 Responsibilities
The Delivery Engine shall:
·	Receive approved notifications.
·	Select delivery channels.
·	Queue deliveries.
·	Invoke delivery adapters.
·	Record delivery status.
·	Retry failed deliveries.
·	Handle temporary failures.
The Delivery Engine shall not:
·	Evaluate notification rules.
·	Aggregate notifications.
·	Manage preferences.
·	Render user interfaces.
9.5 Delivery Channels
The architecture supports multiple delivery channels.
Initial channels include:
Channel	v1.0	Future
In-App	✓	✓
Web Push (FCM)	—	✓
Email	—	✓
Mobile Push	—	✓
SMS	—	Optional
Only In-App is implemented initially.
The remaining channels use the same architecture.
9.6 Multi-Channel Delivery
One notification may be delivered through multiple channels.
Example
Assignment Published

↓

In-App

+

Web Push

+

Email
Each channel operates independently.
A failure in one channel shall not prevent delivery through another.
ADR-028 — Channels Are Independent
Failures in one delivery channel shall not block other channels.
9.7 Delivery Queue
The Delivery Engine shall process notifications asynchronously.
Notification Approved

↓

Delivery Queue

↓

Delivery Worker

↓

Adapter

↓

User
Asynchronous delivery prevents user-facing actions from waiting on external services.
9.8 Delivery Adapters
Each delivery channel shall expose a standardized adapter interface.
Examples:
In-App Adapter

Web Push Adapter

Email Adapter

SMS Adapter
The Delivery Engine communicates only with adapters.
It never communicates directly with Firebase, SMTP servers, or browser APIs.
9.9 Delivery Workflow
Every delivery follows the same lifecycle.
Notification Approved

↓

Queued

↓

Adapter Selected

↓

Delivery Attempt

↓

Success

or

Failure

↓

Retry (if applicable)
This workflow is identical for every delivery channel.
9.10 Delivery Status
Each delivery attempt shall have a status.
Possible statuses:
Pending

Queued

Sending

Delivered

Failed

Retry Scheduled

Cancelled

Expired
These statuses belong to the delivery attempt, not the notification itself.
9.11 Delivery Attempts
Each delivery channel maintains its own delivery history.
Example
Notification

↓

In-App

Delivered

↓

Web Push

Failed

↓

Email

Pending
This allows independent tracking for each channel.
9.12 Retry Policy
Temporary failures shall be retried automatically.
Example retry schedule:
Attempt	Delay
First Retry	30 seconds
Second Retry	2 minutes
Third Retry	10 minutes
Final Retry	30 minutes
Permanent failures shall not be retried.
ADR-029 — Exponential Backoff
Retries should use increasing delays to avoid overwhelming downstream services.
9.13 Delivery Expiration
Some notifications lose value over time.
Example:
Meeting starts in 5 minutes.
Delivering this notification after the meeting has ended provides no value.
Expired notifications shall not be delivered.
9.14 Channel Capability
Not every channel supports the same features.
Example:
Feature	In-App	Push	Email
Avatar	✓	✓*	✓
Action Buttons	✓	Limited	Links
Rich Images	✓	Limited	✓
Real-Time Updates	✓	✗	✗
The Delivery Engine remains channel-agnostic.
Adapters decide how to represent the notification.
9.15 Delivery Logging
Every delivery attempt shall be logged.
The log should include:
·	Notification ID
·	Recipient
·	Channel
·	Attempt Number
·	Timestamp
·	Status
·	Error (if applicable)
These logs support monitoring and troubleshooting.
9.16 Offline Delivery
When a user is offline:
·	In-App notifications remain stored.
·	Push notifications may be queued by the push provider.
·	Email follows normal delivery.
·	Once the user reconnects, unread notifications synchronize automatically.
9.17 Future Scalability
The Delivery Engine shall support the addition of new delivery channels without modifying existing channel implementations.
Adding a new adapter should require registration rather than architectural changes.
Architectural Decision Records
ADR-028 — Independent Delivery Channels
Each delivery channel operates independently of every other channel.
ADR-029 — Retry with Exponential Backoff
Transient delivery failures shall use increasing retry intervals.
ADR-030 — Adapter Pattern
All delivery channels shall implement a common adapter interface, allowing new channels to be added without modifying the Delivery Engine.
Engineer's Review
Architect, I'd like to introduce one additional concept before we move on:
Delivery Priority Queue
Not all notifications deserve equal treatment in the queue.
Instead of processing notifications strictly in creation order, the Delivery Engine should maintain priority-aware queues.
For example:
Critical Queue
├── Security alerts
├── Account recovery
├── Emergency announcements

High Queue
├── Assignment published
├── Meeting started
├── Workspace invitations

Normal Queue
├── Comments
├── Mentions
├── Document updates

Low Queue
├── Likes
├── New followers
Workers should always drain higher-priority queues first while ensuring lower-priority queues are not starved indefinitely.
This becomes especially important once PwaniNet supports FCM, email, and large numbers of concurrent users.
Next Chapter
With delivery defined, the next logical step is Chapter 10 — Notification Lifecycle.
Chapter 10 — Notification Lifecycle
10.1 Purpose
The Notification Lifecycle defines the complete journey of a notification from the moment a platform event occurs until the notification is archived or permanently removed.
The lifecycle provides a standardized model for notification creation, processing, delivery, user interaction, and retirement.
Every Notification Object shall follow this lifecycle regardless of its originating platform module.
10.2 Objectives
The Notification Lifecycle shall:
·	Provide predictable notification behavior.
·	Ensure consistent processing.
·	Define legal state transitions.
·	Improve traceability.
·	Support monitoring and debugging.
·	Standardize notification processing across the platform.
10.3 Lifecycle Overview
Every notification follows the same high-level journey.
Platform Event
        │
        ▼
Rules Evaluation
        │
        ▼
Notification Created
        │
        ▼
Aggregation
        │
        ▼
Preference Evaluation
        │
        ▼
Queued
        │
        ▼
Delivered
        │
        ▼
Seen
        │
        ▼
Read
        │
        ▼
Archived
        │
        ▼
Deleted (Optional)
This represents the canonical lifecycle.
Some notifications may skip certain stages depending on their behavior.
10.4 Stage 1 — Event Published
The lifecycle begins when a Platform Event is successfully published.
Example
workspace.member.joined
The Event Engine records the event.
No notification exists yet.
10.5 Stage 2 — Rule Evaluation
The Notification Rules Engine evaluates the event.
Possible outcomes:
Generate Notification

or

Ignore Event
Not every event results in a notification.
10.6 Stage 3 — Notification Creation
If a rule matches:
A Notification Object is created.
At this stage:
·	Recipient assigned
·	Priority assigned
·	Category assigned
·	Source events linked
·	Status initialized
Initial Status
Created
10.7 Stage 4 — Aggregation
The Aggregation Engine evaluates whether the notification should merge with an existing notification.
Possible outcomes:
Merge into Existing Notification
or
Remain Independent
Aggregation may update:
·	Summary
·	Actor collection
·	Event collection
·	Counters
·	Updated timestamp
The Notification ID remains unchanged when merged.
10.8 Stage 5 — Preference Evaluation
The Preference Engine evaluates:
·	User preferences
·	Category preferences
·	Context preferences
·	Platform policies
Possible outcomes:
Approved

Suppressed

Delayed
Suppressed notifications terminate their delivery journey but remain auditable if platform policy requires.
10.9 Stage 6 — Queueing
Approved notifications enter the Delivery Queue.
Status
Queued
The queue determines delivery order according to:
·	Priority
·	Channel
·	Retry state
10.10 Stage 7 — Delivery
The Delivery Engine invokes one or more delivery adapters.
Possible channels:
·	In-App
·	Web Push
·	Email
·	Future Mobile Push
Each channel records an independent delivery outcome.
Status
Delivered
or
Failed
10.11 Stage 8 — User Sees Notification
A notification becomes Seen when it is rendered in the user's notification interface.
Examples:
·	Notification dropdown opened.
·	Notification page loaded.
·	Real-time notification banner displayed.
Status
Seen
A seen notification is not necessarily read.
10.12 Stage 9 — User Reads Notification
A notification becomes Read when the user intentionally interacts with it.
Examples:
·	Opens the notification.
·	Navigates to the linked content.
·	Expands the notification.
Status
Read
This distinction allows more accurate engagement metrics.
10.13 Stage 10 — User Action
Some notifications contain actions.
Examples:
Approve

Reject

Accept

Decline

Join Meeting
Executing an action may:
·	Generate new Platform Events.
·	Update the notification.
·	Close the notification.
·	Disable available actions.
The lifecycle continues independently of the generated events.
10.14 Stage 11 — Archive
Notifications that are no longer active may be archived.
Archived notifications:
·	Remain searchable.
·	Preserve history.
·	Are excluded from active notification counts.
Archiving does not delete notification data.
10.15 Stage 12 — Expiration
Certain notifications expire automatically.
Examples:
·	Meeting reminders.
·	Deadline warnings.
·	Temporary announcements.
Expired notifications shall no longer be delivered or updated.
10.16 Stage 13 — Deletion
Deletion permanently removes the Notification Object according to platform retention policies.
Deletion may occur because of:
·	User request.
·	Retention policy.
·	Administrative action.
Platform Events remain unaffected.
10.17 Lifecycle State Diagram
Created
   │
   ▼
Aggregated
   │
   ▼
Preference Approved
   │
   ▼
Queued
   │
   ▼
Delivered
   │
   ▼
Seen
   │
   ▼
Read
   │
   ▼
Archived
   │
   ▼
Deleted
Alternative paths:
Created
   │
   ▼
Suppressed
or
Queued
   │
   ▼
Delivery Failed
   │
   ▼
Retry
10.18 Lifecycle Invariants
The following rules shall always hold:
·	A Platform Event cannot re-enter the lifecycle.
·	A Notification Object has exactly one lifecycle.
·	Aggregation never changes originating Platform Events.
·	Read notifications may still receive new aggregated events.
·	Archived notifications shall not become active again.
·	Deleting a notification never deletes Platform Events.
10.19 Lifecycle Metrics
The platform should record timestamps for major lifecycle transitions.
Recommended metrics:
·	Created At
·	Aggregated At
·	Approved At
·	Queued At
·	Delivered At
·	First Seen At
·	First Read At
·	Archived At
·	Deleted At
These metrics support:
·	Performance analysis.
·	User engagement.
·	Delivery latency measurement.
·	AI insights.
·	Platform monitoring.
Architectural Decision Records
ADR-031 — Notifications Have a Single Lifecycle
Every Notification Object follows one standardized lifecycle regardless of its source.
ADR-032 — User Interaction Is Part of the Lifecycle
"Seen", "Read", and notification actions are first-class lifecycle stages.
ADR-033 — Events Outlive Notifications
Platform Events are immutable historical records and shall persist independently of Notification Objects.
Engineer's Review
Architect, there's one lifecycle state I believe we should introduce before implementation:
Dismissed
Today we have:
Seen

↓

Read

↓

Archived
But users often want to clear a notification from their active list without deleting it.
I propose:
Delivered
     │
     ▼
Seen
     │
     ▼
Read
     │
     ▼
Dismissed
     │
     ▼
Archived
A Dismissed notification:
·	Is removed from the active notification view.
·	Does not count as unread.
·	Remains searchable in notification history.
·	Can still be referenced for auditing or AI context if needed.
This is distinct from Archived, which is a system-managed retention state, and Deleted, which permanently removes the Notification Object according to retention policy.
I think adding Dismissed now will better match the behavior users expect from modern notification systems while keeping the lifecycle explicit and consistent.
With Chapter 10 complete, we've finished the core behavioral architecture. The remaining chapters focus on implementation and persistence:
·	Chapter 11 — Notification State Machine
·	Chapter 12 — Delivery Adapters
·	Chapter 13 — Data Model
·	Chapter 14 — Service Architecture
·	Chapter 15 — Integration
·	Chapter 16 — Implementation Guidelines
·	Chapter 17 — Migration Strategy
The next chapter, the State Machine, formalizes which state transitions are valid and prevents impossible transitions such as Archived → Delivered or Deleted → Read. That will serve as the execution contract for the implementation.

Chapter 11 — Notification State Machine
Instead of a full standalone chapter, I'd make it a concise implementation contract.
Purpose
The Notification State Machine defines all valid state transitions for a Notification Object. It guarantees consistent behavior across the platform and prevents invalid transitions.
States
Created
Queued
Delivered
Seen
Read
Dismissed
Archived
Deleted
Failed
Expired
Suppressed
Valid Transitions
Created
 ├──► Suppressed
 ├──► Queued
 └──► Expired

Queued
 ├──► Delivered
 ├──► Failed
 └──► Expired

Failed
 ├──► Queued
 └──► Archived

Delivered
 ├──► Seen
 ├──► Expired
 └──► Archived

Seen
 ├──► Read
 ├──► Dismissed
 └──► Archived

Read
 ├──► Dismissed
 ├──► Archived
 └──► Deleted

Dismissed
 ├──► Archived
 └──► Deleted

Archived
 └──► Deleted

Expired
 └──► Archived
Invalid Transitions
The following transitions are prohibited:
Deleted → Any State

Archived → Delivered

Read → Queued

Seen → Created

Failed → Delivered

Suppressed → Delivered
State Invariants
·	 Every notification begins in Created. 
·	 Every notification ends in either Deleted or Archived. 
·	A deleted notification cannot be restored.
·	Aggregation does not change lifecycle state.
·	Delivery retries do not create new notifications.
I recommend combining the remaining chapters.
Instead of writing seven more chapters, merge them into one final implementation chapter.
Chapter 12 — Implementation Architecture
This chapter would contain:
12.1 Database Model
·	Notification
·	NotificationEvent
·	NotificationActor
·	NotificationDelivery
·	UserNotificationPreference
·	DeviceSubscription
·	NotificationAction
12.2 Django Services
notifications/

    services/

        event_engine.py

        rules_engine.py

        aggregation_engine.py

        preference_engine.py

        delivery_engine.py

        state_machine.py

        notification_service.py
12.3 Signals & Event Publishing
Define how Django signals or service methods publish events without coupling modules.
12.4 Background Workers
·	Celery Tasks
·	Retry workers
·	Scheduled digest jobs
·	Cleanup jobs
·	Expiration jobs
12.5 API Endpoints
GET    /notifications/

GET    /notifications/unread/

POST   /notifications/read/

POST   /notifications/read-all/

POST   /notifications/dismiss/

POST   /notifications/action/

GET    /notifications/preferences/

PUT    /notifications/preferences/
12.6 WebSocket Events
notification.created

notification.updated

notification.dismissed

notification.deleted

notification.read

badge.updated
12.7 Frontend Responsibilities
Desktop
·	Notification dropdown
·	Notification page
·	Badge updates
·	Toast notifications
PWA
·	Offline sync
·	Push notifications
·	Background sync
Flutter (future)
·	Native push
·	Local notifications
·	Deep links
12.8 Performance
·	Redis caching
·	Indexed queries
·	Cursor pagination
·	Lazy loading
·	Batch aggregation
12.9 Security
·	Permission validation
·	Action authorization
·	Notification ownership checks
·	Rate limiting
·	Audit logging
12.10 Future Extensions
·	Firebase Cloud Messaging
·	Email delivery
·	AI-generated notification summaries
·	Semantic aggregation
·	Notification digests
·	Workspace smart notifications

