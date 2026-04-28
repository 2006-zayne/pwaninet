# Pwaninet Messaging System - Frontend Integration Guide

This document describes the messaging features available in Pwaninet and provides the API endpoints and WebSocket connections needed for frontend implementation.

---

## Overview

Pwaninet supports a comprehensive real-time messaging system with the following capabilities:

- **Direct Messages (DMs)**: Private one-on-one conversations between users
- **Group Messages**: Real-time messaging within groups
- **Real-time Updates**: WebSocket-based instant message delivery
- **Typing Indicators**: See when someone is typing
- **Read Receipts**: Track when messages are read
- **Message Reactions**: React to messages with emojis
- **Message Replies**: Reply to specific messages
- **Message Editing**: Edit sent messages
- **Attachments**: Send files with messages
- **Online Status**: Track which users are online
- **Conversation Management**: Create, manage, and organize conversations

---

## API Endpoints

### Base URL
All messaging API endpoints are under `/api/messaging/`

### Authentication
All API endpoints require authentication. Include the authentication token in the request headers:
```
Authorization: Token <your_token>
```

---

## Conversations

### List Conversations
```
GET /api/messaging/conversations/
```

**Query Parameters:**
- `is_group` (optional): Filter by group conversations (`true`/`false`)
- `search` (optional): Search by conversation name
- `ordering` (optional): Order by `created_at` or `updated_at` (default: `-updated_at`)

**Response:**
```json
{
  "id": 1,
  "participants": [
    {
      "id": 1,
      "username": "user1",
      "first_name": "John",
      "last_name": "Doe",
      "profile_pic": "/media/profile_pic/..."
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "is_group": false,
  "name": null,
  "last_message": {
    "id": 123,
    "content": "Hello!",
    "sender": {...},
    "created_at": "2024-01-01T12:00:00Z"
  },
  "unread_count": 2
}
```

### Create Conversation
```
POST /api/messaging/conversations/
```

**Request Body:**
```json
{
  "participant_ids": [2, 3],
  "is_group": false,
  "name": "My Conversation"
}
```

**Response:** Returns the created conversation object

### Get Conversation Details
```
GET /api/messaging/conversations/{id}/
```

**Response:** Returns conversation details with all messages

### Add Participant to Conversation
```
POST /api/messaging/conversations/{id}/add_participant/
```

**Request Body:**
```json
{
  "user_id": 5
}
```

### Remove Participant from Conversation
```
POST /api/messaging/conversations/{id}/remove_participant/
```

**Request Body:**
```json
{
  "user_id": 5
}
```

### Mark Conversation as Read
```
POST /api/messaging/conversations/{id}/mark_read/
```

**Response:**
```json
{
  "status": "marked as read",
  "count": 5
}
```

---

## Messages

### List Messages
```
GET /api/messaging/messages/
```

**Query Parameters:**
- `conversation` (optional): Filter by conversation ID
- `sender` (optional): Filter by sender ID
- `recipient` (optional): Filter by recipient ID
- `group` (optional): Filter by group ID
- `search` (optional): Search message content
- `ordering` (optional): Order by `created_at` (default: `-created_at`)

**Response:**
```json
{
  "id": 123,
  "conversation": 1,
  "sender": {...},
  "recipient": {...},
  "group": {...},
  "content": "Hello, how are you?",
  "created_at": "2024-01-01T12:00:00Z",
  "read_at": "2024-01-01T12:05:00Z",
  "attachments": null,
  "is_edited": false,
  "edited_at": null,
  "reply_to": null,
  "reactions": [
    {
      "id": 1,
      "message": 123,
      "user": {...},
      "reaction": "👍",
      "created_at": "2024-01-01T12:01:00Z"
    }
  ]
}
```

### Send Message
```
POST /api/messaging/messages/
```

**Request Body:**
```json
{
  "conversation": 1,
  "recipient": 2,
  "group": null,
  "content": "Hello!",
  "attachments": null,
  "reply_to": null
}
```

**Note:** Either `recipient` or `group` should be provided, but not both.

### Update Message
```
PUT /api/messaging/messages/{id}/
PATCH /api/messaging/messages/{id}/
```

**Request Body:**
```json
{
  "content": "Updated message content"
}
```

**Note:** Messages can only be edited by the sender.

### Mark Message as Read
```
POST /api/messaging/messages/{id}/mark_read/
```

**Response:** Returns the updated message object

### Add Reaction to Message
```
POST /api/messaging/messages/{id}/add_reaction/
```

**Request Body:**
```json
{
  "reaction": "👍"
}
```

**Available Reactions:**
- `👍` - Thumbs Up
- `❤️` - Heart
- `😂` - Laugh
- `😮` - Surprised
- `😢` - Sad
- `😡` - Angry

**Response:** If the reaction already exists, it will be removed. Otherwise, a new reaction is created.

---

## Message Reactions

### List Reactions
```
GET /api/messaging/reactions/
```

**Query Parameters:**
- `message` (optional): Filter by message ID
- `user` (optional): Filter by user ID
- `reaction` (optional): Filter by reaction type

---

## WebSocket Connections

### WebSocket Endpoints

All WebSocket connections use the following base URL:
```
ws://<your-domain>/ws/
```

### Notification WebSocket
```
ws://<your-domain>/ws/notifications/
```

**Purpose:** Receive real-time notifications

**Authentication:** Requires authenticated user session

**Message Format:**
```json
{
  "type": "notification",
  "notification": {
    "id": 1,
    "recipient": {...},
    "sender": {...},
    "notification_type": "MESSAGE",
    "msg": "New message from user1",
    "is_read": false,
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

### Feed Update WebSocket
```
ws://<your-domain>/ws/feed/
```

**Purpose:** Receive real-time feed updates (new posts, messages, etc.)

**Authentication:** Requires authenticated user session

**Message Format:**
```json
{
  "type": "feed_update",
  "post": {...}
}
```

### Online Status WebSocket
```
ws://<your-domain>/ws/online/
```

**Purpose:** Track online status of users

**Authentication:** Requires authenticated user session

**Message Formats:**
```json
{
  "type": "user_joined",
  "user_id": 1,
  "username": "user1"
}
```

```json
{
  "type": "user_left",
  "user_id": 1,
  "username": "user1"
}
```

### Chat WebSocket
```
ws://<your-domain>/ws/chat/{conversation_id}/
```

**Purpose:** Real-time messaging within a specific conversation

**Authentication:** Requires authenticated user session and user must be a participant

**Send Message Format:**
```json
{
  "type": "message",
  "content": "Hello!",
  "reply_to": null
}
```

**Typing Indicator Format:**
```json
{
  "type": "typing",
  "is_typing": true
}
```

**Read Receipt Format:**
```json
{
  "type": "read_receipt",
  "message_id": 123
}
```

**Receive Message Formats:**
```json
{
  "type": "chat_message",
  "message": {
    "id": 123,
    "content": "Hello!",
    "sender": "user1",
    "created_at": "2024-01-01T12:00:00Z"
  }
}
```

```json
{
  "type": "typing_indicator",
  "user": "user1",
  "is_typing": true
}
```

---

## Frontend Templates

### Template Locations

Templates should be created in the following directory structure:

```
pwaninet/
├── templates/
│   ├── messaging/
│   │   ├── conversation_list.html       # List of all conversations
│   │   ├── conversation_detail.html     # Single conversation with messages
│   │   ├── message_form.html           # Form to send a message
│   │   └── message_item.html           # Single message component
│   └── partials/
│       ├── _message_card.html          # Reusable message card
│       ├── _conversation_card.html     # Reusable conversation card
│       └── _typing_indicator.html      # Typing indicator component
```

### Required Templates

#### 1. `conversation_list.html`
Display list of conversations with:
- Conversation name or participant names
- Last message preview
- Unread message count
- Online status indicators
- Last updated timestamp

#### 2. `conversation_detail.html`
Display conversation with:
- Conversation header (name, participants)
- Message list (scrollable)
- Message input form
- Typing indicator
- Online status of participants

#### 3. `message_item.html`
Single message component with:
- Sender avatar and name
- Message content
- Timestamp
- Edit button (for own messages)
- Reply button
- Reaction button
- Reactions display
- Read receipt indicator

#### 4. `message_form.html`
Form to send messages with:
- Text input field
- File attachment button
- Emoji picker
- Send button

### JavaScript Requirements

The frontend will need JavaScript for:
- WebSocket connection management
- Real-time message handling
- Typing indicator logic
- Auto-scroll to new messages
- Message state management
- Online status updates

---

## Data Models Reference

### Conversation Model
- `id`: Unique identifier
- `participants`: Many-to-many relationship with User
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp
- `is_group`: Boolean indicating if it's a group conversation
- `name`: Name for group conversations

### Message Model
- `id`: Unique identifier
- `conversation`: Foreign key to Conversation
- `sender`: Foreign key to User (message sender)
- `recipient`: Foreign key to User (message recipient, nullable)
- `group`: Foreign key to Group (for group messages, nullable)
- `content`: Message text content
- `created_at`: Creation timestamp
- `read_at`: Read timestamp (nullable)
- `attachments`: File attachment (nullable)
- `is_edited`: Boolean indicating if message was edited
- `edited_at`: Edit timestamp (nullable)
- `reply_to`: Foreign key to Message (for replies, nullable)

### MessageReaction Model
- `id`: Unique identifier
- `message`: Foreign key to Message
- `user`: Foreign key to User
- `reaction`: Emoji reaction (👍, ❤️, 😂, 😮, 😢, 😡)
- `created_at`: Creation timestamp

### User Model (Messaging Fields)
- `is_online`: Boolean indicating online status
- `last_seen`: Last activity timestamp

---

## Implementation Checklist

### Backend (✅ Completed)
- [x] Django Channels setup
- [x] WebSocket consumers
- [x] Message/Conversation models
- [x] API ViewSets
- [x] Serializers
- [x] URL routing
- [x] Migrations

### Frontend (To Be Implemented)
- [ ] Create conversation list template
- [ ] Create conversation detail template
- [ ] Create message components
- [ ] Implement WebSocket connection
- [ ] Implement typing indicators
- [ ] Implement read receipts
- [ ] Implement message reactions
- [ ] Implement file upload for attachments
- [ ] Implement online status indicators
- [ ] Add message editing UI
- [ ] Add reply functionality
- [ ] Add emoji picker
- [ ] Implement auto-scroll
- [ ] Add loading states
- [ ] Add error handling

---

## Testing the API

### Using cURL

**List Conversations:**
```bash
curl -X GET http://localhost:8000/api/messaging/conversations/ \
  -H "Authorization: Token <your_token>"
```

**Send Message:**
```bash
curl -X POST http://localhost:8000/api/messaging/messages/ \
  -H "Authorization: Token <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": 1,
    "content": "Hello!"
  }'
```

### Using Swagger UI

Visit `http://localhost:8000/api/docs/` to access the interactive API documentation with Swagger UI.

---

## Notes

- All timestamps are in UTC
- File uploads have a size limit (configured in Django settings)
- WebSocket connections require Redis to be running
- Messages are automatically ordered by creation time (oldest first)
- Online status is updated when users connect/disconnect via WebSocket
- Typing indicators are sent in real-time via WebSocket
- Read receipts are optional and depend on user privacy settings

---

## Next Steps

1. Create the HTML templates as specified above
2. Implement WebSocket connection logic in JavaScript
3. Style the messaging interface to match the overall design
4. Test the real-time features with multiple users
5. Add any additional features as needed

For questions or issues, refer to the API documentation at `/api/docs/` or contact the development team.
