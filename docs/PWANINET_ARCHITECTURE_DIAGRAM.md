# PwaniNet Domain Communication Architecture

## 1. Overall System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser[Web Browser]
        PWA[PWA Application]
        Mobile[Mobile Browser]
    end
    
    subgraph "Web Server Layer"
        Nginx[Nginx Reverse Proxy]
        Daphne[Daphne ASGI Server]
    end
    
    subgraph "Application Layer - Django"
        subgraph "Core Domain"
            Core[pwaninet core]
            Settings[Settings/Config]
            Middleware[Custom Middleware]
            Routing[URL Routing]
        end
        
        subgraph "Users Domain"
            UsersApp[users app]
            UserModels[User Models]
            UserViews[User Views]
            UserSerializers[User Serializers]
        end
        
        subgraph "Posts Domain"
            PostsApp[posts app]
            PostModels[Post Models]
            PostViews[Post Views]
            PostSerializers[Post Serializers]
        end
        
        subgraph "Messaging Domain"
            MessagingApp[messaging app]
            MessageModels[Message Models]
            MessageConsumers[WebSocket Consumers]
            MessageViews[Message Views]
        end
        
        subgraph "Groups Domain"
            GroupsApp[groups app]
            GroupModels[Group Models]
            GroupViews[Group Views]
        end
        
        subgraph "Notifications Domain"
            NotificationsApp[notifications app]
            NotificationModels[Notification Models]
            NotificationViews[Notification Views]
            PushService[Web Push Service]
        end
        
        subgraph "Courses Domain"
            CoursesApp[courses app]
            CourseModels[Course Models]
            CourseViews[Course Views]
        end
        
        subgraph "Realtime Domain"
            RealtimeApp[realtime app]
            RealtimeConsumers[Real-time Consumers]
        end
    end
    
    subgraph "Data Layer"
        PostgreSQL[(PostgreSQL Database)]
        Redis[(Redis Cache & Pub/Sub)]
        FileSystem[File Storage]
    end
    
    subgraph "Background Jobs"
        Celery[Celery Workers]
        CeleryBeat[Celery Beat Scheduler]
    end
    
    subgraph "External Services"
        VAPID[VAPID Push Service]
        LinkFetcher[Link Metadata Fetcher]
    end
    
    Browser -->|HTTP/HTTPS| Nginx
    PWA -->|HTTP/HTTPS| Nginx
    Mobile -->|HTTP/HTTPS| Nginx
    
    Nginx --> Daphne
    
    Daphne --> Core
    Core --> Settings
    Core --> Middleware
    Core --> Routing
    
    Routing --> UsersApp
    Routing --> PostsApp
    Routing --> MessagingApp
    Routing --> GroupsApp
    Routing --> NotificationsApp
    Routing --> CoursesApp
    Routing --> RealtimeApp
    
    UsersApp --> UserModels
    UsersApp --> UserViews
    UsersApp --> UserSerializers
    
    PostsApp --> PostModels
    PostsApp --> PostViews
    PostsApp --> PostSerializers
    
    MessagingApp --> MessageModels
    MessagingApp --> MessageConsumers
    MessagingApp --> MessageViews
    
    GroupsApp --> GroupModels
    GroupsApp --> GroupViews
    
    NotificationsApp --> NotificationModels
    NotificationsApp --> NotificationViews
    NotificationsApp --> PushService
    
    CoursesApp --> CourseModels
    CoursesApp --> CourseViews
    
    RealtimeApp --> RealtimeConsumers
    
    UserModels --> PostgreSQL
    PostModels --> PostgreSQL
    MessageModels --> PostgreSQL
    GroupModels --> PostgreSQL
    NotificationModels --> PostgreSQL
    CourseModels --> PostgreSQL
    
    UserViews --> Redis
    PostViews --> Redis
    MessageConsumers --> Redis
    NotificationViews --> Redis
    RealtimeConsumers --> Redis
    
    PostViews --> FileSystem
    MessageViews --> FileSystem
    UserViews --> FileSystem
    
    Core --> Celery
    Celery --> Redis
    CeleryBeat --> Celery
    
    PushService --> VAPID
    PostViews --> LinkFetcher
    
    style Browser fill:#e1f5ff
    style PWA fill:#e1f5ff
    style Mobile fill:#e1f5ff
    style PostgreSQL fill:#e1ffe1
    style Redis fill:#ffe1e1
    style VAPID fill:#fff4e1
    style LinkFetcher fill:#fff4e1
```

## 2. Domain Interactions and Communication

```mermaid
graph LR
    subgraph "Users Domain"
        Users[Users App]
        UserAuth[Authentication]
        UserProfile[Profile Management]
        UserRelations[User Relations]
    end
    
    subgraph "Posts Domain"
        Posts[Posts App]
        PostFeed[Feed Management]
        PostMedia[Media Processing]
        PostInteractions[Interactions]
    end
    
    subgraph "Messaging Domain"
        Messaging[Messaging App]
        Chat[Real-time Chat]
        MessageQueue[Message Queue]
        Encryption[E2E Encryption]
    end
    
    subgraph "Groups Domain"
        Groups[Groups App]
        GroupMembership[Membership]
        GroupContent[Group Content]
        GroupPermissions[Permissions]
    end
    
    subgraph "Notifications Domain"
        Notifications[Notifications App]
        InApp[In-App Notifications]
        Push[Push Notifications]
        WebSocket[WebSocket Push]
    end
    
    subgraph "Courses Domain"
        Courses[Courses App]
        Academic[Academic Structure]
        CourseLinking[Course Linking]
    end
    
    subgraph "Shared Services"
        Database[(Database)]
        Cache[(Redis Cache)]
        Storage[File Storage]
    end
    
    Users -->|User Data| Posts
    Users -->|Participants| Messaging
    Users -->|Members| Groups
    Users -->|Recipients| Notifications
    Users -->|Students| Courses
    
    Posts -->|Events| Notifications
    Posts -->|Group Posts| Groups
    Posts -->|Course Posts| Courses
    Posts -->|Author Info| Users
    
    Messaging -->|User Context| Users
    Messaging -->|Group Chats| Groups
    Messaging -->|Message Events| Notifications
    
    Groups -->|Member Info| Users
    Groups -->|Group Posts| Posts
    Groups -->|Group Chats| Messaging
    Groups -->|Group Events| Notifications
    Groups -->|Course Groups| Courses
    
    Notifications -->|User Preferences| Users
    Notifications -->|Post Events| Posts
    Notifications -->|Message Events| Messaging
    Notifications -->|Group Events| Groups
    
    Courses -->|Student Info| Users
    Courses -->|Course Posts| Posts
    Courses -->|Course Groups| Groups
    
    Users --> Database
    Posts --> Database
    Messaging --> Database
    Groups --> Database
    Notifications --> Database
    Courses --> Database
    
    Users --> Cache
    Posts --> Cache
    Messaging --> Cache
    Groups --> Cache
    Notifications --> Cache
    
    Posts --> Storage
    Messaging --> Storage
    Users --> Storage
    Groups --> Storage
    
    style Users fill:#e1f5ff
    style Posts fill:#ffe1f5
    style Messaging fill:#fff4e1
    style Groups fill:#e1ffe1
    style Notifications fill:#ffe1e1
    style Courses fill:#f5e1ff
    style Database fill:#e1ffe1
    style Cache fill:#ffe1e1
```

## 3. Request Flow Through Domains

```mermaid
sequenceDiagram
    participant Client
    participant Nginx
    participant Daphne
    participant Core
    participant Users
    participant Posts
    participant Notifications
    participant Database
    participant Redis
    participant WebSocket
    
    Client->>Nginx: HTTP Request
    Nginx->>Daphne: Forward Request
    Daphne->>Core: Route Request
    Core->>Core: Authenticate User
    
    alt Auth Required
        Core->>Users: Validate Session
        Users-->>Core: User Context
        Core->>Core: Check Permissions
    end
    
    alt Post Request
        Core->>Posts: Handle Post Request
        Posts->>Database: Save Post
        Database-->>Posts: Confirmation
        Posts->>Notifications: Trigger Notification
        Notifications->>Redis: Update Cache
        Notifications->>WebSocket: Push Update
        Posts-->>Core: Response
    else Message Request
        Core->>WebSocket: Establish Connection
        WebSocket->>Users: Validate User
        WebSocket-->>Client: Connected
        Client->>WebSocket: Send Message
        WebSocket->>Database: Save Message
        Database-->>WebSocket: Confirmation
        WebSocket->>Redis: Broadcast
        Redis->>WebSocket: Distribute
        WebSocket-->>Client: Message Delivered
    else Profile Request
        Core->>Users: Handle Profile Request
        Users->>Database: Fetch Profile
        Database-->>Users: Profile Data
        Users->>Redis: Cache Profile
        Users-->>Core: Response
    end
    
    Core-->>Daphne: HTTP Response
    Daphne-->>Nginx: Response
    Nginx-->>Client: Final Response
```

## 4. Domain Data Dependencies

```mermaid
graph TD
    subgraph "Users Domain (Core)"
        User[User Model]
        Follow[Follow Model]
        Block[Block Model]
        Device[DeviceAccount Model]
    end
    
    subgraph "Posts Domain"
        Post[Post Model]
        PostImage[PostImage Model]
        Like[Like Model]
        Comment[Comment Model]
        Repost[Repost Model]
    end
    
    subgraph "Messaging Domain"
        Conversation[Conversation Model]
        Message[Message Model]
        MessageAttachment[MessageAttachment Model]
        PendingMessage[PendingMessage Model]
    end
    
    subgraph "Groups Domain"
        Group[Group Model]
        Membership[Membership Model]
    end
    
    subgraph "Notifications Domain"
        Notification[Notifications Model]
        PushSubscription[PushSubscription Model]
    end
    
    subgraph "Courses Domain"
        Course[Course Model]
        Year[Year Model]
        Unit[Unit Model]
        School[School Model]
    end
    
    User -->|Foreign Key| Post
    User -->|Foreign Key| PostImage
    User -->|Foreign Key| Like
    User -->|Foreign Key| Comment
    User -->|Foreign Key| Repost
    User -->|Foreign Key| Conversation
    User -->|Foreign Key| Message
    User -->|Foreign Key| Group
    User -->|Foreign Key| Membership
    User -->|Foreign Key| Notification
    User -->|Foreign Key| PushSubscription
    User -->|Foreign Key| Course
    User -->|Foreign Key| Year
    
    Post -->|Foreign Key| Group
    Post -->|Foreign Key| Course
    Post -->|Foreign Key| Unit
    
    Group -->|Foreign Key| Course
    Group -->|Foreign Key| Year
    
    Membership -->|Foreign Key| User
    Membership -->|Foreign Key| Group
    
    Conversation -->|Many-to-Many| User
    Message -->|Foreign Key| Conversation
    Message -->|Foreign Key| User
    
    Notification -->|Foreign Key| User
    Notification -->|Foreign Key| Post
    Notification -->|Foreign Key| Group
    
    Course -->|Foreign Key| School
    Year -->|Foreign Key| Course
    Unit -->|Foreign Key| Course
    Unit -->|Foreign Key| Year
    
    style User fill:#e1f5ff
    style Post fill:#ffe1f5
    style Conversation fill:#fff4e1
    style Group fill:#e1ffe1
    style Notification fill:#ffe1e1
    style Course fill:#f5e1ff
```

## 5. Cross-Domain Event Flow

```mermaid
graph TD
    subgraph "Event Sources"
        PostEvent[Post Created/Liked/Commented]
        MessageEvent[Message Sent]
        FollowEvent[User Followed]
        GroupEvent[Group Join/Post]
        CourseEvent[Course Enrollment]
    end
    
    subgraph "Event Processing"
        EventRouter[Event Router]
        NotificationService[Notification Service]
        CacheService[Cache Service]
        WebSocketService[WebSocket Service]
    end
    
    subgraph "Event Consumers"
        UserDomain[Users Domain]
        PostDomain[Posts Domain]
        MessageDomain[Messaging Domain]
        GroupDomain[Groups Domain]
        NotificationDomain[Notifications Domain]
    end
    
    subgraph "External Delivery"
        PushNotification[Push Notification]
        EmailNotification[Email Notification]
        RealtimeUpdate[Real-time Update]
    end
    
    PostEvent --> EventRouter
    MessageEvent --> EventRouter
    FollowEvent --> EventRouter
    GroupEvent --> EventRouter
    CourseEvent --> EventRouter
    
    EventRouter --> NotificationService
    EventRouter --> CacheService
    EventRouter --> WebSocketService
    
    NotificationService --> NotificationDomain
    CacheService --> UserDomain
    CacheService --> PostDomain
    WebSocketService --> MessageDomain
    WebSocketService --> GroupDomain
    
    NotificationService --> PushNotification
    NotificationService --> EmailNotification
    WebSocketService --> RealtimeUpdate
    
    PushNotification --> UserDomain
    RealtimeUpdate --> UserDomain
    RealtimeUpdate --> PostDomain
    RealtimeUpdate --> MessageDomain
    
    style PostEvent fill:#e1f5ff
    style MessageEvent fill:#ffe1f5
    style FollowEvent fill:#fff4e1
    style GroupEvent fill:#e1ffe1
    style CourseEvent fill:#f5e1ff
```

## 6. API Endpoint Distribution by Domain

```mermaid
graph LR
    subgraph "Users Domain API"
        UsersAPI[users/]
        Profile[/users/&lt;username&gt;/]
        Register[/register/]
        UpdateProfile[/update-profile/]
        Follow[/users/&lt;id&gt;/follow/]
    end
    
    subgraph "Posts Domain API"
        PostsAPI[posts/]
        Home[/]
        PostDetail[/post/&lt;id&gt;/]
        CreatePost[/create/]
        Search[/search/]
        Like[/posts/&lt;id&gt;/like/]
    end
    
    subgraph "Messaging Domain API"
        MessagingAPI[messaging/]
        Conversations[/conversations/]
        ConversationDetail[/&lt;id&gt;/]
        Messages[/messages/]
        WebSocket[ws/chat/&lt;id&gt;/]
    end
    
    subgraph "Groups Domain API"
        GroupsAPI[groups/]
        GroupList[/]
        GroupDetail[/&lt;id&gt;/]
        CreateGroup[/create/]
        Join[/&lt;id&gt;/join/]
    end
    
    subgraph "Notifications Domain API"
        NotificationsAPI[notifications/]
        NotificationList[/]
        MarkRead[/&lt;id&gt;/mark_read/]
        PushSubscribe[/api/push/subscribe/]
        PushUnsubscribe[/api/push/unsubscribe/]
    end
    
    subgraph "Courses Domain API"
        CoursesAPI[courses/]
        CourseList[/]
        UnitDetail[/unit/&lt;id&gt;/]
    end
    
    subgraph "Shared API"
        APIHealth[/api/health/]
        APISchema[/api/schema/]
        APIDocs[/api/docs/]
    end
    
    style UsersAPI fill:#e1f5ff
    style PostsAPI fill:#ffe1f5
    style MessagingAPI fill:#fff4e1
    style GroupsAPI fill:#e1ffe1
    style NotificationsAPI fill:#ffe1e1
    style CoursesAPI fill:#f5e1ff
    style SharedAPI fill:#e1ffe1
```

## 7. Domain Responsibilities Summary

| Domain | Primary Responsibilities | Key Models | External Dependencies |
|--------|------------------------|------------|----------------------|
| **Users** | Authentication, profiles, user relationships | User, Follow, Block, DeviceAccount, UserSession | PostgreSQL, Redis, File Storage |
| **Posts** | Social feed, content creation, media handling | Post, PostImage, Like, Comment, Repost, SharedPost | PostgreSQL, Redis, File Storage, Link Fetcher |
| **Messaging** | Real-time chat, E2E encryption, attachments | Conversation, Message, MessageAttachment, PendingMessage, LinkPreview | PostgreSQL, Redis, WebSocket, File Storage |
| **Groups** | Community management, memberships, permissions | Group, Membership | PostgreSQL, Users Domain |
| **Notifications** | In-app alerts, push notifications, event handling | Notifications, PushSubscription | PostgreSQL, Redis, VAPID Service |
| **Courses** | Academic structure, course management | School, Course, Year, Unit | PostgreSQL, Users Domain |
| **Realtime** | WebSocket infrastructure, real-time features | N/A (consumers only) | Redis, Django Channels |

## 8. Communication Patterns

### Synchronous Communication (HTTP/HTTPS)
- **Client → Django**: Traditional HTTP requests for page loads, form submissions
- **Django → Database**: CRUD operations via Django ORM
- **Django → External APIs**: Link metadata fetching, push notifications

### Asynchronous Communication (WebSocket)
- **Client → Django**: Real-time messaging, live updates
- **Django → Redis**: Channel layer for message broadcasting
- **Redis → Django**: Pub/sub for real-time event distribution

### Background Processing (Celery)
- **Django → Celery**: Task queuing for heavy operations
- **Celery → Database**: Async data processing
- **Celery → Redis**: Task queue backend, result storage

### Cache Communication
- **Django → Redis**: Caching user sessions, notification counts, online status
- **Redis → Django**: Fast data retrieval for frequently accessed data
- **WebSocket → Redis**: Real-time state synchronization

## 9. Security Boundaries by Domain

```mermaid
graph TD
    subgraph "Public Layer"
        Public[Public Pages]
        Registration[Registration]
        Login[Login]
    end
    
    subgraph "Authenticated Layer"
        Authenticated[Authenticated Pages]
        UserProfile[User Profiles]
        PostFeed[Post Feed]
        GroupView[Group View]
    end
    
    subgraph "Domain-Specific Security"
        UserSecurity[User Domain Security]
        PostSecurity[Post Domain Security]
        MessageSecurity[Message Domain Security]
        GroupSecurity[Group Domain Security]
    end
    
    subgraph "Admin Layer"
        AdminPanel[Admin Panel]
        UserManagement[User Management]
        ContentModeration[Content Moderation]
    end
    
    Public --> Authenticated
    Authenticated --> UserSecurity
    Authenticated --> PostSecurity
    Authenticated --> MessageSecurity
    Authenticated --> GroupSecurity
    
    UserSecurity --> AdminPanel
    PostSecurity --> ContentModeration
    GroupSecurity --> ContentModeration
    
    AdminPanel --> UserManagement
    
    style Public fill:#e1f5ff
    style Authenticated fill:#ffe1f5
    style AdminPanel fill:#ffe1e1
```

## 10. Technology Stack by Domain

| Domain | Backend Tech | Frontend Tech | Database | Cache | Real-time |
|--------|--------------|---------------|----------|-------|-----------|
| **Users** | Django, DRF | Bootstrap, HTMX | PostgreSQL | Redis | - |
| **Posts** | Django, DRF | Bootstrap, HTMX, JS | PostgreSQL | Redis | WebSocket |
| **Messaging** | Django, Channels | Bootstrap, WebSocket | PostgreSQL | Redis | WebSocket |
| **Groups** | Django, DRF | Bootstrap, HTMX | PostgreSQL | Redis | - |
| **Notifications** | Django, DRF | Bootstrap, Web Push API | PostgreSQL | Redis | WebSocket |
| **Courses** | Django, DRF | Bootstrap, HTMX | PostgreSQL | Redis | - |
| **Realtime** | Django, Channels | - | - | Redis | WebSocket |
