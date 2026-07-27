# PwaniNet Data Flow Diagrams (DFD)

## 1. Context Diagram (Level 0 DFD)

```mermaid
graph LR
    subgraph "External Entities"
        User[User]
        Admin[Administrator]
        ExternalAPI[External Services]
    end
    
    subgraph "PwaniNet System"
        System[PwaniNet Platform]
    end
    
    User -->|HTTP/HTTPS Requests| System
    User -->|WebSocket Connections| System
    System -->|HTML Responses| User
    System -->|Real-time Updates| User
    System -->|Push Notifications| User
    
    Admin -->|Admin Requests| System
    System -->|Admin Reports| Admin
    
    ExternalAPI -->|Link Metadata| System
    System -->|HTTP Requests| ExternalAPI
    
    style User fill:#e1f5ff
    style Admin fill:#ffe1f5
    style ExternalAPI fill:#fff4e1
    style System fill:#e1ffe1
```

## 2. Level 0 DFD - Main System Processes

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Admin[Admin]
        External[External Services]
    end
    
    subgraph "PwaniNet System"
        Auth[Authentication Process]
        Posts[Posts Management]
        Messaging[Messaging System]
        Groups[Groups Management]
        Users[User Management]
        Notifications[Notification System]
        Courses[Academic Courses]
        Storage[File Storage]
        Database[(Database)]
        Redis[(Redis Cache)]
    end
    
    User -->|Credentials| Auth
    Auth -->|Session Data| User
    Auth -->|User Data| Database
    Database -->|User Info| Auth
    
    User -->|Post Data| Posts
    Posts -->|Feed Content| User
    Posts -->|Post Records| Database
    Database -->|Post Data| Posts
    Posts -->|Media Files| Storage
    Storage -->|File URLs| Posts
    
    User -->|Messages| Messaging
    Messaging -->|Message Data| User
    Messaging -->|Conversation Data| Database
    Database -->|Message History| Messaging
    Messaging -->|Online Status| Redis
    Redis -->|User Status| Messaging
    
    User -->|Group Actions| Groups
    Groups -->|Group Info| User
    Groups -->|Membership Data| Database
    Database -->|Group Data| Groups
    
    User -->|Profile Updates| Users
    Users -->|Profile Data| User
    Users -->|User Records| Database
    Database -->|User Info| Users
    
    Posts -->|Events| Notifications
    Messaging -->|Events| Notifications
    Groups -->|Events| Notifications
    Users -->|Events| Notifications
    
    Notifications -->|Alerts| User
    Notifications -->|Notification Records| Database
    Database -->|Notification History| Notifications
    Notifications -->|Cache Updates| Redis
    
    User -->|Course Selection| Courses
    Courses -->|Course Info| User
    Courses -->|Academic Data| Database
    Database -->|Course Records| Courses
    
    Admin -->|Management| Database
    Database -->|Reports| Admin
    
    Posts -->|Link Requests| External
    External -->|Metadata| Posts
    
    style User fill:#e1f5ff
    style Admin fill:#ffe1f5
    style External fill:#fff4e1
    style Database fill:#e1ffe1
    style Redis fill:#ffe1e1
```

## 3. Level 1 DFD - Posts Management Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Storage[File Storage]
    end
    
    subgraph "Posts Process"
        Validate[Validate Input]
        ProcessMedia[Process Media]
        SavePost[Save Post to DB]
        CreateNotifications[Create Notifications]
        UpdateCache[Update Redis Cache]
        Broadcast[Broadcast via WebSocket]
        UpdateFeed[Update User Feeds]
    end
    
    subgraph "Data Stores"
        PostDB[(Post Database)]
        NotificationDB[(Notification Database)]
        RedisCache[(Redis Cache)]
    end
    
    User -->|Post Content + Media| Validate
    Validate -->|Validated Data| ProcessMedia
    ProcessMedia -->|Processed Media| SavePost
    ProcessMedia -->|Upload Files| Storage
    Storage -->|File URLs| ProcessMedia
    
    SavePost -->|Post Record| PostDB
    PostDB -->|Confirmation| SavePost
    
    SavePost -->|Trigger Events| CreateNotifications
    CreateNotifications -->|Notification Records| NotificationDB
    NotificationDB -->|Confirmation| CreateNotifications
    
    CreateNotifications -->|Cache Keys| UpdateCache
    UpdateCache -->|Cached Data| RedisCache
    RedisCache -->|Confirmation| UpdateCache
    
    UpdateCache -->|Broadcast Signal| Broadcast
    Broadcast -->|Real-time Updates| User
    
    Broadcast -->|Feed Update Signal| UpdateFeed
    UpdateFeed -->|Updated Feeds| User
    
    style User fill:#e1f5ff
    style Storage fill:#fff4e1
    style PostDB fill:#e1ffe1
    style NotificationDB fill:#e1ffe1
    style RedisCache fill:#ffe1e1
```

## 4. Level 1 DFD - Messaging System Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Storage[File Storage]
    end
    
    subgraph "Messaging Process"
        Authenticate[Authenticate User]
        EstablishConnection[Establish WebSocket]
        EncryptMessage[Encrypt Message]
        QueueMessage[Queue Message]
        UploadAttachments[Upload Attachments]
        SaveMessage[Save to Database]
        BroadcastMessage[Broadcast via Channel Layer]
        UpdateReadStatus[Update Read Status]
        DecryptMessage[Decrypt Message]
        UpdateUI[Update Chat UI]
    end
    
    subgraph "Data Stores"
        MessageDB[(Message Database)]
        ConversationDB[(Conversation Database)]
        RedisCache[(Redis Cache)]
    end
    
    User -->|Connection Request| Authenticate
    Authenticate -->|User Context| EstablishConnection
    EstablishConnection -->|Connected| User
    
    User -->|Message Content| EncryptMessage
    EncryptMessage -->|Encrypted Data| QueueMessage
    
    QueueMessage -->|Attachment Data| UploadAttachments
    UploadAttachments -->|Upload Files| Storage
    Storage -->|File URLs| UploadAttachments
    
    QueueMessage -->|Message Data| SaveMessage
    SaveMessage -->|Message Record| MessageDB
    MessageDB -->|Confirmation| SaveMessage
    
    SaveMessage -->|Conversation Update| ConversationDB
    ConversationDB -->|Confirmation| SaveMessage
    
    SaveMessage -->|Broadcast Signal| BroadcastMessage
    BroadcastMessage -->|Channel Events| RedisCache
    RedisCache -->|Distribution| BroadcastMessage
    
    BroadcastMessage -->|Encrypted Message| User
    User -->|Decryption Request| DecryptMessage
    DecryptMessage -->|Plaintext| UpdateUI
    UpdateUI -->|Updated Chat| User
    
    User -->|Read Receipt| UpdateReadStatus
    UpdateReadStatus -->|Status Update| MessageDB
    UpdateReadStatus -->|Cache Update| RedisCache
    
    style User fill:#e1f5ff
    style Storage fill:#fff4e1
    style MessageDB fill:#e1ffe1
    style ConversationDB fill:#e1ffe1
    style RedisCache fill:#ffe1e1
```

## 5. Level 1 DFD - User Management Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Admin[Admin]
    end
    
    subgraph "User Management Process"
        ValidateCredentials[Validate Credentials]
        CreateSession[Create Session]
        UpdateProfile[Update Profile]
        ManageFollows[Manage Follows]
        HandleBlocks[Handle Blocks]
        UpdatePreferences[Update Preferences]
        TrackSessions[Track Sessions]
        DeviceManagement[Device Management]
    end
    
    subgraph "Data Stores"
        UserDB[(User Database)]
        SessionDB[(Session Database)]
        FollowDB[(Follow Database)]
        BlockDB[(Block Database)]
        RedisCache[(Redis Cache)]
    end
    
    User -->|Login Credentials| ValidateCredentials
    ValidateCredentials -->|Valid User| UserDB
    UserDB -->|User Data| ValidateCredentials
    
    ValidateCredentials -->|Session Data| CreateSession
    CreateSession -->|Session Record| SessionDB
    SessionDB -->|Confirmation| CreateSession
    CreateSession -->|Session Cookie| User
    
    User -->|Profile Updates| UpdateProfile
    UpdateProfile -->|User Record| UserDB
    UserDB -->|Confirmation| UpdateProfile
    
    User -->|Follow Actions| ManageFollows
    ManageFollows -->|Follow Records| FollowDB
    FollowDB -->|Confirmation| ManageFollows
    ManageFollows -->|Notification Trigger| User
    
    User -->|Block Actions| HandleBlocks
    HandleBlocks -->|Block Records| BlockDB
    BlockDB -->|Confirmation| HandleBlocks
    
    User -->|Preference Changes| UpdatePreferences
    UpdatePreferences -->|User Record| UserDB
    UpdatePreferences -->|Cache Update| RedisCache
    
    User -->|Session Activity| TrackSessions
    TrackSessions -->|Session Data| SessionDB
    TrackSessions -->|Online Status| RedisCache
    
    User -->|Device Switch| DeviceManagement
    DeviceManagement -->|Device Records| UserDB
    DeviceManagement -->|Session Update| SessionDB
    
    Admin -->|User Management| UserDB
    UserDB -->|User Reports| Admin
    
    style User fill:#e1f5ff
    style Admin fill:#ffe1f5
    style UserDB fill:#e1ffe1
    style SessionDB fill:#e1ffe1
    style FollowDB fill:#e1ffe1
    style BlockDB fill:#e1ffe1
    style RedisCache fill:#ffe1e1
```

## 6. Level 1 DFD - Notification System Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        PushService[Web Push Service]
    end
    
    subgraph "Notification Process"
        ReceiveEvents[Receive Events]
        FilterNotifications[Filter by Preferences]
        CreateNotification[Create Notification Record]
        UpdateCache[Update Redis Cache]
        WebSocketPush[WebSocket Push]
        CheckPushEnabled[Check Push Enabled]
        SendPushNotification[Send Web Push]
        MarkAsRead[Mark as Read]
        CleanupOld[Cleanup Old Notifications]
    end
    
    subgraph "Data Stores"
        NotificationDB[(Notification Database)]
        UserDB[(User Database)]
        RedisCache[(Redis Cache)]
        PushDB[(Push Subscription DB)]
    end
    
    User -->|User Actions| ReceiveEvents
    
    ReceiveEvents -->|Event Data| FilterNotifications
    FilterNotifications -->|User Preferences| UserDB
    UserDB -->|Preferences| FilterNotifications
    
    FilterNotifications -->|Filtered Events| CreateNotification
    CreateNotification -->|Notification Record| NotificationDB
    NotificationDB -->|Confirmation| CreateNotification
    
    CreateNotification -->|Cache Key| UpdateCache
    UpdateCache -->|Cached Count| RedisCache
    RedisCache -->|Confirmation| UpdateCache
    
    CreateNotification -->|Push Signal| WebSocketPush
    WebSocketPush -->|Real-time Alert| User
    
    CreateNotification -->|Check Push| CheckPushEnabled
    CheckPushEnabled -->|Subscription Data| PushDB
    PushDB -->|Subscription Info| CheckPushEnabled
    
    CheckPushEnabled -->|Push Request| SendPushNotification
    SendPushNotification -->|Push Data| PushService
    PushService -->|Browser Notification| User
    
    User -->|Read Action| MarkAsRead
    MarkAsRead -->|Update Record| NotificationDB
    MarkAsRead -->|Cache Update| RedisCache
    
    CleanupOld -->|Delete Records| NotificationDB
    CleanupOld -->|Cache Cleanup| RedisCache
    
    style User fill:#e1f5ff
    style PushService fill:#fff4e1
    style NotificationDB fill:#e1ffe1
    style UserDB fill:#e1ffe1
    style RedisCache fill:#ffe1e1
    style PushDB fill:#e1ffe1
```

## 7. Level 1 DFD - Groups Management Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Admin[Admin]
    end
    
    subgraph "Groups Process"
        CreateGroup[Create Group]
        ValidateMembership[Validate Membership]
        ProcessJoinRequest[Process Join Request]
        ManageRoles[Manage Roles]
        GroupPosting[Group Posting]
        UpdateGroupFeed[Update Group Feed]
        AutoEnroll[Auto Enroll New Users]
    end
    
    subgraph "Data Stores"
        GroupDB[(Group Database)]
        MembershipDB[(Membership Database)]
        PostDB[(Post Database)]
        UserDB[(User Database)]
        CourseDB[(Course Database)]
    end
    
    User -->|Group Data| CreateGroup
    CreateGroup -->|Group Record| GroupDB
    GroupDB -->|Confirmation| CreateGroup
    
    User -->|Join Request| ValidateMembership
    ValidateMembership -->|Group Policy| GroupDB
    GroupDB -->|Policy Info| ValidateMembership
    
    ValidateMembership -->|Membership Record| MembershipDB
    MembershipDB -->|Confirmation| ValidateMembership
    
    ValidateMembership -->|Request Data| ProcessJoinRequest
    ProcessJoinRequest -->|Approval Decision| Admin
    Admin -->|Approval| ProcessJoinRequest
    
    ProcessJoinRequest -->|Update Membership| MembershipDB
    
    Admin -->|Role Changes| ManageRoles
    ManageRoles -->|Membership Update| MembershipDB
    MembershipDB -->|Confirmation| ManageRoles
    
    User -->|Post to Group| GroupPosting
    GroupPosting -->|Post Record| PostDB
    PostDB -->|Confirmation| GroupPosting
    
    GroupPosting -->|Group Feed Update| UpdateGroupFeed
    UpdateGroupFeed -->|Feed Data| GroupDB
    
    User -->|New User Signup| AutoEnroll
    AutoEnroll -->|User Course/Year| UserDB
    UserDB -->|Academic Info| AutoEnroll
    
    AutoEnroll -->|Matching Groups| GroupDB
    GroupDB -->|Group List| AutoEnroll
    
    AutoEnroll -->|Auto Membership| MembershipDB
    
    style User fill:#e1f5ff
    style Admin fill:#ffe1f5
    style GroupDB fill:#e1ffe1
    style MembershipDB fill:#e1ffe1
    style PostDB fill:#e1ffe1
    style UserDB fill:#e1ffe1
    style CourseDB fill:#e1ffe1
```

## 8. Level 1 DFD - Academic Courses Process

```mermaid
graph TD
    subgraph "External Entities"
        User[User]
        Admin[Admin]
    end
    
    subgraph "Courses Process"
        ManageSchools[Manage Schools]
        ManageCourses[Manage Courses]
        ManageYears[Manage Years]
        ManageUnits[Manage Units]
        LinkUserToCourse[Link User to Course]
        FetchCourseData[Fetch Course Data]
        UpdateUserAcademic[Update User Academic Info]
    end
    
    subgraph "Data Stores"
        SchoolDB[(School Database)]
        CourseDB[(Course Database)]
        YearDB[(Year Database)]
        UnitDB[(Unit Database)]
        UserDB[(User Database)]
    end
    
    Admin -->|School Data| ManageSchools
    ManageSchools -->|School Records| SchoolDB
    SchoolDB -->|Confirmation| ManageSchools
    
    Admin -->|Course Data| ManageCourses
    ManageCourses -->|Course Records| CourseDB
    CourseDB -->|Confirmation| ManageCourses
    
    Admin -->|Year Data| ManageYears
    ManageYears -->|Year Records| YearDB
    YearDB -->|Confirmation| ManageYears
    
    Admin -->|Unit Data| ManageUnits
    ManageUnits -->|Unit Records| UnitDB
    UnitDB -->|Confirmation| ManageUnits
    
    User -->|Course Selection| LinkUserToCourse
    LinkUserToCourse -->|Course Data| CourseDB
    CourseDB -->|Course Info| LinkUserToCourse
    
    LinkUserToCourse -->|Year Data| YearDB
    YearDB -->|Year Info| LinkUserToCourse
    
    LinkUserToCourse -->|User Update| UserDB
    UserDB -->|Confirmation| LinkUserToCourse
    
    User -->|Request Course Info| FetchCourseData
    FetchCourseData -->|Course Data| CourseDB
    FetchCourseData -->|Unit Data| UnitDB
    FetchCourseData -->|Course Info| User
    
    User -->|Profile Update| UpdateUserAcademic
    UpdateUserAcademic -->|User Record| UserDB
    UserDB -->|Confirmation| UpdateUserAcademic
    
    style User fill:#e1f5ff
    style Admin fill:#ffe1f5
    style SchoolDB fill:#e1ffe1
    style CourseDB fill:#e1ffe1
    style YearDB fill:#e1ffe1
    style UnitDB fill:#e1ffe1
    style UserDB fill:#e1ffe1
```

## 9. Data Dictionary

### Data Stores

| Data Store | Description | Key Entities |
|------------|-------------|--------------|
| **PostDB** | Stores all post-related data | Post, PostImage, Like, Comment, Repost, SharedPost |
| **MessageDB** | Stores messaging data | Conversation, Message, MessageAttachment, PendingMessage |
| **UserDB** | Stores user account data | User, Follow, Pinch, Block, DeviceAccount, UserSession |
| **GroupDB** | Stores group data | Group, Membership |
| **NotificationDB** | Stores notification data | Notifications, PushSubscription |
| **CourseDB** | Stores academic data | School, Course, Year, Unit |
| **SessionDB** | Stores session data | Django Sessions |
| **RedisCache** | In-memory cache for real-time data | Online status, notification counts, channel layers |
| **PushDB** | Stores push notification subscriptions | PushSubscription |

### Data Flows

| Data Flow | Source | Destination | Description |
|-----------|--------|-------------|-------------|
| **Post Content** | User | Posts Process | Text, media, course/unit selection |
| **Message Content** | User | Messaging Process | Encrypted messages, attachments |
| **Credentials** | User | Authentication | Username, password for login |
| **Session Data** | Authentication | User | Session cookie, user context |
| **Notification Events** | All Processes | Notification Process | Triggers for likes, follows, comments |
| **Real-time Updates** | WebSocket | User | Live messages, feed updates |
| **Push Notifications** | Push Service | User | Browser push notifications |
| **Media Files** | Storage | Posts/Messaging | Uploaded images, videos, documents |
| **Academic Data** | CourseDB | User | Course, year, unit information |
| **Group Data** | GroupDB | User | Group information, membership status |

### External Entities

| Entity | Description | Interactions |
|--------|-------------|--------------|
| **User** | End user of the platform | Posts, messages, profile management, group activities |
| **Admin** | Platform administrator | User management, content moderation, system configuration |
| **External Services** | Third-party APIs | Link metadata fetching, push notification services |
| **File Storage** | Media storage system | Upload and retrieval of images, videos, documents |
| **Web Push Service** | Browser push notification service | Delivery of push notifications to users |
