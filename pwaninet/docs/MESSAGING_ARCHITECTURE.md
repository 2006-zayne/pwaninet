# Pwaninet Messaging Domain - Architecture Guide

## Overview

The messaging system is built on a **modular, event-driven architecture** that separates concerns between backend (Django + Django Channels), frontend (JavaScript SOT pattern), and real-time communication (WebSockets).

---

## Core Concepts

### 1. Domain Entities

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Conversation   │────▶│ ConversationMember│────▶│     User        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │
         │
         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│     Message     │────▶│   MessageRead    │     │ MessageReaction │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

#### Conversation
- **Purpose**: Container for messages between users
- **Types**: 
  - `direct` - One-to-one private chats
  - `group` - Multi-user group chats
- **Key Fields**: `type`, `name`, `is_encrypted`, `created_at`, `updated_at`

#### Message
- **Purpose**: The core communication unit
- **Content Types**:
  - Plain text
  - Encrypted text (E2E)
  - Media (images, videos, audio, documents)
  - Links with rich previews
- **Key Fields**: `content`, `sender`, `conversation`, `attachment`, `link_*` fields

#### ConversationMember
- **Purpose**: Junction table linking users to conversations
- **Role**: Tracks membership and enables querying user's conversations

#### MessageRead
- **Purpose**: Read receipts per message per user
- **Use Case**: Tracking who has seen which message

---

## Backend Architecture

### 1. API Layer (REST + DRF)

#### ViewSets (CRUD Operations)

```python
# URL Pattern: /messaging/v1/
router.register(r'conversations', ConversationViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'reactions', MessageReactionViewSet)
router.register(r'themes', ConversationThemeViewSet)
```

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/conversations/` | GET, POST | List/create conversations |
| `/conversations/{id}/` | GET, PATCH, DELETE | Manage specific conversation |
| `/messages/` | GET, POST | List messages, send new message |
| `/messages/{id}/` | GET, PATCH, DELETE | Manage message |
| `/reactions/` | POST | Add emoji reaction |
| `/themes/` | GET, POST, PATCH | Chat themes per conversation |

#### Custom Endpoints

```python
# URL: /messaging/api/attachments/upload/
POST - Upload media files (50MB limit)

# URL: /messaging/api/links/fetch-metadata/
POST - Fetch OpenGraph metadata for URLs

# URL: /messaging/search-followed-users/
GET - Search users for new conversations

# URL: /messaging/create/
POST - Create new conversation
```

### 2. WebSocket Layer (Django Channels)

#### Consumer: `ChatConsumer`

**Connection Flow:**
1. User connects via WebSocket (`ws://host/ws/chat/{conversation_id}/`)
2. Consumer authenticates user via JWT token in query params
3. User joins `room_group_name` (channel layer group)
4. Real-time bidirectional communication enabled

**Message Types Handled:**

| Type | Direction | Purpose |
|------|-----------|---------|
| `chat_message` | Receive/Send | Send/receive text/media/link messages |
| `typing_indicator` | Receive/Send | Show "typing..." status |
| `read_receipt` | Receive/Send | Mark messages as read |
| `message_delivered` | Receive | Delivery confirmation |
| `user_status` | Receive | Online/offline status |

**WebSocket Message Format:**
```json
{
  "type": "chat_message",
  "temp_id": "temp_123456789",
  "content": "Hello!",
  "message_type": "text",
  "encrypted_content": null,
  "is_encrypted": false,
  "link_url": "https://example.com",
  "link_title": "Example Site",
  "link_type": "link"
}
```

### 3. Models Deep Dive

#### Message Model Schema

```python
class Message(models.Model):
    # Core
    conversation = ForeignKey(Conversation)
    sender = ForeignKey(User)
    content = TextField()  # Plain text
    
    # Encryption (E2E)
    encrypted_content = TextField()  # Encrypted payload
    is_encrypted = BooleanField(default=False)
    
    # Media Attachments
    attachment = FileField(upload_to='message_attachments/%Y/%m/%d/')
    attachment_type = CharField(choices=['image','video','audio','document'])
    
    # Link Previews (Rich Content)
    link_url = URLField(max_length=2048)
    link_title = CharField(max_length=500)
    link_description = TextField()
    link_image = URLField(max_length=2048)
    link_type = CharField(choices=['link','facebook','youtube','instagram','twitter','internal_post','internal_profile'])
    
    # Threading
    reply_to = ForeignKey('self', related_name='replies')
    
    # Metadata
    created_at = DateTimeField(auto_now_add=True)
    edited_at = DateTimeField(null=True)
    is_deleted = BooleanField(default=False)
```

---

## Frontend Architecture (SOT Pattern)

### 1. Source of Truth (SOT) Architecture

The frontend uses a **Single Source of Truth** pattern with unidirectional data flow:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Actions                          │
│         (Click, Type, Upload, Paste Link)                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    AppController                             │
│              (Orchestrates, No Business Logic)               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    MessageService                            │
│    (Ingestion Layer - Validates, Normalizes, Forwards)       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Store (SOT)                            │
│          (State Container, Pure Mutations Only)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     UIController                             │
│              (Read-Only Subscriber, Renders UI)            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MessageRenderer                          │
│              (Pure Rendering, No Logic)                      │
└─────────────────────────────────────────────────────────────┘
```

### 2. Key Services

#### MessageService (`static/js/chat/core/message-service.js`)

**Responsibilities:**
- URL extraction and link metadata fetching
- Message normalization (canonical schema)
- WebSocket communication via `webSocketManager`
- REST API fallback when WebSocket fails
- Optimistic updates (temporary IDs until server confirms)

**Key Methods:**
```javascript
// Send message (detects links automatically)
sendMessage(content, options) -> tempId

// Extract URLs from text
extractUrls(text) -> [urls]

// Fetch link metadata from backend
fetchLinkMetadata(url) -> metadata

// Normalize server messages to canonical format
normalizeServerMessage(raw) -> canonicalMessage
```

#### Store (`static/js/chat/core/store.js`)

**Responsibilities:**
- Holds application state (messages, typing indicators, connection status)
- Pure mutation methods (addMessage, updateMessage, replaceMessage)
- Pub-sub pattern for state changes
- Message deduplication and sorting

**State Shape:**
```javascript
{
  messages: [],           // Array of canonical messages
  conversationId: null,   // Current conversation ID
  currentUserId: null,    // Logged-in user ID
  connectionState: 'connected', // WebSocket status
  typingUsers: Map(),     // UserID -> {username, isTyping}
  peerOnlineStatus: Map(), // UserID -> {isOnline, lastSeen}
  uiState: {}
}
```

#### MessageRenderer (`static/js/chat/ui/renderer.js`)

**Responsibilities:**
- Pure DOM manipulation based on state
- Message type detection and rendering:
  - Text messages
  - Emoji messages (large, no bubble)
  - Media messages (images, videos, audio, documents)
  - Link messages (rich previews, embeds)
  - System messages
- Grouping messages by sender (first, middle, last, single)
- Read receipt avatars and status icons

### 3. Message Types & Rendering

```javascript
// Canonical Message Schema
{
  id: "123",                    // Server-assigned or temp ID
  conversationId: 7,
  senderId: 42,
  timestamp: "2024-01-15T10:30:00Z",
  status: "sent" | "delivered" | "read",
  content: "Hello!",
  type: "text" | "emoji" | "media" | "link" | "system",
  metadata: {
    // For media:
    url: "...",
    type: "image" | "video" | "audio",
    
    // For links:
    link_url: "...",
    link_title: "...",
    link_image: "...",
    link_type: "youtube" | "facebook" | "link"
  },
  isOptimistic: false,          // True until server confirms
  sortOrder: 1705312200000      // Timestamp for sorting
}
```

---

## Data Flow Examples

### 1. Sending a Text Message

```
1. User types "Hello" and hits Enter
   ↓
2. UIController._handleSendMessage()
   ↓
3. MessageService.sendMessage("Hello")
   - Detects no URLs
   - Creates optimistic message with temp_id
   - Sends via WebSocket
   ↓
4. WebSocketManager sends to backend
   ↓
5. ChatConsumer.handle_chat_message()
   - Creates Message in DB
   - Broadcasts to room group
   ↓
6. Other clients receive via WebSocket
   ↓
7. MessageService.processIncomingMessage()
   - Normalizes to canonical format
   - Replaces optimistic message with real ID
   ↓
8. Store.addMessage() → triggers subscribers
   ↓
9. UIController re-renders messages
```

### 2. Sending a Link (Rich Preview)

```
1. User pastes "Check this: https://youtube.com/watch?v=abc123"
   ↓
2. MessageService.sendMessage()
   - extractUrls() finds URL
   - fetchLinkMetadata() calls /api/links/fetch-metadata/
   - Backend fetches OpenGraph data
   ↓
3. Link metadata attached to message
   ↓
4. Sent via WebSocket with link_* fields
   ↓
5. Backend stores link data in Message model
   ↓
6. Renderer._createLinkMessage()
   - Detects link_type === 'youtube'
   - Creates YouTube iframe embed
   - Or shows rich preview card
```

### 3. Sending Media

```
1. User clicks attachment → selects photo
   ↓
2. File uploaded via /api/attachments/upload/
   ↓
3. Backend validates (size, type), saves file
   ↓
4. Message created with attachment fields
   ↓
5. Broadcast via WebSocket (channel_layer.group_send)
   ↓
6. Receiver's MessageRenderer._createMediaMessage()
   - Detects attachment_type === 'image'
   - Renders <img> tag
```

---

## API Reference

### REST Endpoints

#### Conversations
```http
GET    /messaging/v1/conversations/
POST   /messaging/v1/conversations/
GET    /messaging/v1/conversations/{id}/
PATCH  /messaging/v1/conversations/{id}/
DELETE /messaging/v1/conversations/{id}/
```

#### Messages
```http
GET    /messaging/v1/messages/?conversation={id}
POST   /messaging/v1/messages/
GET    /messaging/v1/messages/{id}/
PATCH  /messaging/v1/messages/{id}/
DELETE /messaging/v1/messages/{id}/
```

#### Media Upload
```http
POST /messaging/api/attachments/upload/
Content-Type: multipart/form-data

Body:
  - file: <binary>
  - conversation_id: 7

Response:
  {
    "id": 123,
    "attachment_url": "/media/message_attachments/2024/...",
    "attachment_type": "image",
    "sender": {...}
  }
```

#### Link Metadata
```http
POST /messaging/api/links/fetch-metadata/
Content-Type: application/json

Body:
  {"url": "https://example.com"}

Response:
  {
    "url": "https://example.com",
    "title": "Example Domain",
    "description": "This domain is for use...",
    "image": "https://example.com/og-image.jpg",
    "type": "link"
  }
```

### WebSocket Protocol

#### Connection
```javascript
// URL
wss://host/ws/chat/{conversation_id}/?token={jwt_token}
```

#### Sending Messages
```javascript
{
  "type": "chat_message",
  "temp_id": "temp_1705312200000_abc123",
  "content": "Hello!",
  "message_type": "text",
  "encrypted_content": null,
  "is_encrypted": false,
  "reply_to": null
}
```

#### Typing Indicators
```javascript
// Send
{
  "type": "typing_indicator",
  "is_typing": true
}

// Receive
{
  "type": "typing",
  "user_id": 42,
  "username": "john",
  "is_typing": true
}
```

#### Read Receipts
```javascript
// Send
{
  "type": "read_receipt",
  "message_id": 123
}

// Receive (broadcast to others)
{
  "type": "read_receipt",
  "message_id": 123,
  "user_id": 42,
  "read_avatar": "/media/avatars/john.jpg"
}
```

---

## Scaling Considerations

### 1. Database Scaling

**Current Setup:**
- PostgreSQL with standard indexes
- Indexes on: `conversation + created_at`, `sender + created_at`

**For High Scale:**
```sql
-- Partition messages by conversation_id (range partitioning)
-- Separate hot conversations to faster storage
-- Archive old messages to cold storage
```

### 2. WebSocket Scaling

**Current:** Single Channels layer (Redis)

**For High Scale:**
- Use Redis Cluster for channel layer
- Multiple ASGI workers behind load balancer
- Sticky sessions by conversation_id

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Worker 1  │     │   Worker 2  │     │   Worker N  │
│  (Room A-C) │     │  (Room D-F) │     │  (Room G+)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌─────────────┐
                    │ Redis Cluster│
                    │  (Pub/Sub)   │
                    └─────────────┘
```

### 3. Media Storage

**Current:** Local filesystem (`message_attachments/%Y/%m/%d/`)

**For High Scale:**
- Migrate to S3 / GCS / Azure Blob
- CDN for media delivery (CloudFlare, CloudFront)
- Image resizing service (Thumbor, Imgix)

### 4. Link Previews

**Current:** Real-time fetch on send

**For High Scale:**
- Cache metadata in Redis (TTL: 24h)
- Async job queue (Celery + Redis/RabbitMQ)
- Rate limiting per domain

```python
# Cached fetch
async def fetch_link_metadata(url):
    cache_key = f"link_meta:{hash(url)}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    metadata = await fetch_and_parse(url)
    redis.setex(cache_key, 86400, json.dumps(metadata))
    return metadata
```

### 5. Message Search

**Current:** No search functionality

**For Scale:**
- Elasticsearch for full-text search
- Separate index per conversation or sharded by time
- Async indexing on message creation

---

## Security Considerations

1. **Authentication**: JWT tokens via query params (WebSocket) or headers (REST)
2. **Authorization**: Check `ConversationMember` on every operation
3. **Rate Limiting**: Implement on WebSocket and REST endpoints
4. **Content Validation**: Validate file types, sizes, sanitize HTML
5. **E2E Encryption**: Optional end-to-end encryption for sensitive conversations

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `messaging/models.py` | Database schema |
| `messaging/views.py` | REST API endpoints |
| `messaging/consumers.py` | WebSocket handling |
| `messaging/serializers.py` | DRF serializers |
| `messaging/urls.py` | URL routing |
| `static/js/chat/core/message-service.js` | Frontend message handling |
| `static/js/chat/core/store.js` | State management |
| `static/js/chat/ui/renderer.js` | DOM rendering |
| `static/js/chat/ui/ui-controller.js` | UI event handling |
| `messaging/templates/messaging/conversation_detail_refactored.html` | Main chat UI |

---

## Quick Start for New Features

To add a new message type:

1. **Backend:**
   - Update `Message` model (add fields)
   - Update `MessageSerializer`
   - Update `ChatConsumer.handle_chat_message()`
   - Create migration: `python3 manage.py makemigrations`

2. **Frontend:**
   - Update `message-service.js` `normalizeServerMessage()`
   - Add to `mapType()` if new type
   - Update `renderer.js` `_createMessageElement()`
   - Add `_create{Type}Message()` method
   - Add CSS styles

3. **Test:**
   - Send message with new type
   - Verify rendering in both directions
   - Check mobile/desktop views

---

## Summary

The messaging system is designed for:
- **Real-time**: WebSockets for instant delivery
- **Extensible**: Easy to add new message types
- **Scalable**: Clear separation of concerns, stateless where possible
- **Maintainable**: SOT pattern prevents state bugs
- **Feature-rich**: Media, links, encryption, reactions, read receipts

Key architectural decisions:
1. SOT pattern on frontend prevents UI state bugs
2. WebSocket primary, REST fallback for reliability
3. OpenGraph fetching on backend (avoids CORS)
4. Optimistic updates for perceived performance
5. Canonical message schema unifies all message types
