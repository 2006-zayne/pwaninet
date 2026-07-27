# PwaniNet Flow Chart Diagrams

## 1. System Flow Chart

```mermaid
graph TD
    Start([User Action]) --> AuthCheck{Authenticated?}
    AuthCheck -->|No| Login[Login/Register]
    AuthCheck -->|Yes| ActionSelect{Action Type}
    
    Login --> AuthCheck
    
    ActionSelect -->|Post| PostFlow[Post Creation Flow]
    ActionSelect -->|Message| MessageFlow[Messaging Flow]
    ActionSelect -->|Group| GroupFlow[Group Management Flow]
    ActionSelect -->|Profile| ProfileFlow[Profile Management Flow]
    ActionSelect -->|Notification| NotificationFlow[Notification Flow]
    
    PostFlow --> PostCreate[Create Post]
    PostCreate --> PostMedia[Upload Media]
    PostMedia --> PostSave[Save to Database]
    PostSave --> PostNotify[Trigger Notifications]
    PostNotify --> PostFeed[Update Feed]
    PostFeed --> End([Complete])
    
    MessageFlow --> ConvSelect[Select Conversation]
    ConvSelect --> WSConnect[WebSocket Connect]
    WSConnect --> MsgEncrypt[Encrypt Message]
    MsgEncrypt --> MsgSend[Send via WebSocket]
    MsgSend --> MsgStore[Store in Database]
    MsgStore --> MsgBroadcast[Broadcast to Participants]
    MsgBroadcast --> MsgUpdate[Update UI]
    MsgUpdate --> End
    
    GroupFlow --> GroupAction{Group Action}
    GroupAction -->|Create| GroupCreate[Create Group]
    GroupAction -->|Join| GroupJoin[Request to Join]
    GroupAction -->|Post| GroupPost[Post to Group]
    
    GroupCreate --> GroupSave[Save Group]
    GroupSave --> End
    
    GroupJoin --> GroupApprove{Approval Required?}
    GroupApprove -->|Yes| GroupPending[Set Pending]
    GroupApprove -->|No| GroupMember[Add Member]
    GroupPending --> End
    GroupMember --> End
    GroupPost --> PostFlow
    
    ProfileFlow --> ProfileAction{Profile Action}
    ProfileAction -->|View| ProfileView[View Profile]
    ProfileAction -->|Edit| ProfileEdit[Edit Profile]
    ProfileAction -->|Follow| ProfileFollow[Follow User]
    
    ProfileView --> ProfileData[Fetch Profile Data]
    ProfileData --> ProfilePosts[Fetch User Posts]
    ProfilePosts --> End
    
    ProfileEdit --> ProfileUpdate[Update Profile]
    ProfileUpdate --> ProfileSave[Save Changes]
    ProfileSave --> End
    
    ProfileFollow --> FollowCreate[Create Follow Relationship]
    FollowCreate --> FollowNotify[Send Notification]
    FollowNotify --> End
    
    NotificationFlow --> NotifFetch[Fetch Notifications]
    NotifFetch --> NotifDisplay[Display Notifications]
    NotifDisplay --> NotifAction{User Action}
    NotifAction -->|Mark Read| NotifRead[Mark as Read]
    NotifAction -->|Click| NotifNavigate[Navigate to Content]
    NotifRead --> End
    NotifNavigate --> End
    
    style Start fill:#e1f5ff
    style End fill:#e1ffe1
    style AuthCheck fill:#fff4e1
    style ActionSelect fill:#fff4e1
    style GroupApprove fill:#fff4e1
    style ProfileAction fill:#fff4e1
    style NotifAction fill:#fff4e1
```

## 2. User Authentication Flow

```mermaid
graph TD
    U([User]) --> L[Login Request]
    L --> V{Validate Credentials}
    V -->|Invalid| E[Show Error]
    V -->|Valid| S[Create Session]
    S --> R[Set Session Cookie]
    R --> D[Redirect to Home]
    D --> F[Fetch User Data]
    F --> O[Set Online Status]
    O --> N[Check Notifications]
    N --> H[Render Home Page]
    H --> UC([User Connected])
    
    E --> L
    
    style U fill:#e1f5ff
    style UC fill:#e1ffe1
    style V fill:#fff4e1
```

## 3. Post Creation Flow

```mermaid
graph TD
    U([User]) --> CP[Click Create Post]
    CP --> F[Open Post Form]
    F --> TI[Enter Text Content]
    TI --> MA{Add Media?}
    MA -->|Yes| MU[Upload Media]
    MA -->|No| CO{Course/Unit?}
    MU --> MP[Process Media]
    MP --> CO
    CO -->|Yes| CS[Select Course/Unit]
    CO -->|No| GR{Group?}
    CS --> GR
    GR -->|Yes| GS[Select Group]
    GR -->|No| GP{Privacy?}
    GS --> GP
    GP --> SP[Set Privacy Level]
    SP --> SV[Save to Database]
    SV --> NC[Create Notifications]
    NC --> UF[Update User Feed]
    UF --> GF{Group Post?}
    GF -->|Yes| GG[Update Group Feed]
    GF -->|No| RF[Update Redis Cache]
    GG --> RF
    RF --> WS[Broadcast via WebSocket]
    WS --> UP[Update Post UI]
    UP --> PC([Post Created])
    
    style U fill:#e1f5ff
    style PC fill:#e1ffe1
    style MA fill:#fff4e1
    style CO fill:#fff4e1
    style GR fill:#fff4e1
    style GP fill:#fff4e1
    style GF fill:#fff4e1
```

## 4. Real-Time Messaging Flow

```mermaid
graph TD
    U([User]) --> SC[Select Conversation]
    SC --> WS[WebSocket Connection]
    WS --> AM[Authenticate User]
    AM --> JM[Join Room]
    JM --> LM[Load Messages]
    LM --> DM[Display Messages]
    DM --> WT[Wait for Input]
    
    WT --> ST{Send Message?}
    ST -->|Yes| ET[Encrypt Message]
    ST -->|No| WT
    
    ET --> QS[Queue Message]
    QS --> US[Upload Attachments]
    US --> SM[Send via WebSocket]
    SM --> SR[Save to Database]
    SR --> CB[Channel Layer Broadcast]
    CB --> RP[Redis Pub/Sub]
    RP --> AR[All Receivers]
    AR --> DD[Decrypt Message]
    DD --> UM[Update Message UI]
    UM --> WT
    
    WT --> RM{Receive Message?}
    RM -->|Yes| GM[Get Message]
    RM -->|No| WT
    GM --> DD
    
    style U fill:#e1f5ff
    style ST fill:#fff4e1
    style RM fill:#fff4e1
```

## 5. Notification Flow

```mermaid
graph TD
    E([Event Trigger]) --> NT{Notification Type}
    
    NT -->|Like| LN[Like Notification]
    NT -->|Follow| FN[Follow Notification]
    NT -->|Comment| CN[Comment Notification]
    NT -->|Group| GN[Group Notification]
    NT -->|Share| SN[Share Notification]
    
    LN --> NR[Create Notification Record]
    FN --> NR
    CN --> NR
    GN --> NR
    SN --> NR
    
    NR --> RC[Redis Cache Update]
    RC --> WS[WebSocket Push]
    WS --> UI[In-App Notification]
    
    NR --> PS{Push Enabled?}
    PS -->|Yes| WP[Web Push API]
    PS -->|No| EC([End])
    WP --> PB[Push to Browser]
    PB --> BN[Browser Notification]
    BN --> EC
    
    UI --> UA{User Action}
    UA -->|Click| NV[Navigate to Content]
    UA -->|Dismiss| MR[Mark as Read]
    NV --> MR
    MR --> EC
    
    style E fill:#e1f5ff
    style EC fill:#e1ffe1
    style NT fill:#fff4e1
    style PS fill:#fff4e1
    style UA fill:#fff4e1
```

## 6. Group Membership Flow

```mermaid
graph TD
    U([User]) --> GA{Group Action}
    
    GA -->|Create| CG[Create Group]
    GA -->|Join| JG[Request to Join]
    GA -->|Leave| LG[Leave Group]
    GA -->|Manage| MG[Manage Members]
    
    CG --> GS[Set Group Settings]
    GS --> GP[Set Privacy Policy]
    GP --> SG[Save Group]
    SG --> AC([Admin Created])
    
    JG --> JP{Join Policy}
    JP -->|Open| AM[Auto-Member]
    JP -->|Approval| PR[Pending Request]
    JP -->|Invite| IN[Invite Required]
    
    AM --> SGU[Send Group Update]
    PR --> AN[Admin Notification]
    IN --> ER([End])
    
    SGU --> UC([User Joined])
    AN --> AA{Admin Action}
    AA -->|Approve| AM
    AA -->|Reject| RJ[Reject Request]
    RJ --> ER
    
    LG --> RM[Remove Membership]
    RM --> UG[Update Group]
    UG --> ER
    
    MG --> MS{Member Action}
    MS -->|Promote| PM[Promote Role]
    MS -->|Demote| DM[Demote Role]
    MS -->|Remove| RM
    
    PM --> UG
    DM --> UG
    
    style U fill:#e1f5ff
    style AC fill:#e1ffe1
    style UC fill:#e1ffe1
    style GA fill:#fff4e1
    style JP fill:#fff4e1
    style AA fill:#fff4e1
    style MS fill:#fff4e1
```

## 7. PWA Offline Flow

```mermaid
graph TD
    U([User]) --> NC{Network Check}
    NC -->|Online| OL[Online Mode]
    NC -->|Offline| OF[Offline Mode]
    
    OL --> CA[Cache Assets]
    CA --> SR[Service Worker Active]
    SR --> RF[Real-Time Features]
    RF --> WS[WebSocket Connected]
    WS --> LU[Live Updates]
    
    OF --> CC[Use Cached Content]
    CC --> PQ[Queue Actions]
    PQ --> LS[Local Storage]
    LS --> DO[Display Offline UI]
    
    NC --> NR{Network Restored?}
    NR -->|Yes| SQ[Sync Queued Actions]
    NR -->|No| OF
    
    SQ --> PS[Process Pending]
    PS --> US[Upload to Server]
    US --> UC[Update Cache]
    UC --> OL
    
    style U fill:#e1f5ff
    style NC fill:#fff4e1
    style NR fill:#fff4e1
```
