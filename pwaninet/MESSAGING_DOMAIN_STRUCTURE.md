# Messaging Domain Structure

## Overview

This document outlines the complete structure of the messaging domain, including all related files outside the domain such as static assets, templates, and Django components.

---

## Domain Root Structure

```
/home/zayne/projects/pwaninet/
├── messaging/                          # Django app (messaging domain)
├── static/js/                          # Static JavaScript files
├── templates/messaging/                # Django templates
└── docs/                              # Documentation
```

---

## Django App: `messaging/`

### Core Django Files
```
messaging/
├── __init__.py
├── admin.py                           # Django admin configuration
├── apps.py                            # Django app configuration
├── models.py                          # Database models
├── views.py                           # Django views
├── urls.py                            # URL routing
├── forms.py                           # Django forms
├── serializers.py                     # API serializers
├── managers.py                        # Custom model managers
├── signals.py                         # Django signals
├── permissions.py                     # Permission classes
├── filters.py                         # Query filters
├── pagination.py                      # Pagination classes
├── validators.py                      # Custom validators
├── utils.py                           # Utility functions
└── tests/                            # Test suite
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    ├── test_permissions.py
    └── fixtures/
```

### Database Migrations
```
messaging/migrations/
├── __init__.py
├── 0001_initial.py
├── 0002_add_message_read_receipts.py
├── 0003_add_conversation_encryption.py
├── 0004_add_theme_support.py
├── 0005_add_message_attachments.py
└── 0006_add_voice_messages.py
```

### API Endpoints
```
messaging/api/
├── __init__.py
├── v1/                               # API version 1
│   ├── __init__.py
│   ├── urls.py                       # API URL routing
│   ├── views.py                      # API viewsets
│   ├── serializers.py                # API serializers
│   ├── permissions.py                # API permissions
│   ├── throttling.py                 # Rate limiting
│   └── pagination.py                 # API pagination
└── v2/                               # API version 2 (future)
    └── ...
```

### Management Commands
```
messaging/management/
├── __init__.py
└── commands/
    ├── __init__.py
    ├── cleanup_old_messages.py       # Cleanup old messages
    ├── export_conversations.py       # Export conversation data
    └── generate_thumbnails.py        # Generate image thumbnails
```

### Database Queries
```
messaging/queries/
├── __init__.py
├── conversation_queries.py           # Conversation-related queries
├── message_queries.py               # Message-related queries
├── user_queries.py                  # User-related queries
└── theme_queries.py                  # Theme-related queries
```

---

## Static Assets: `static/js/`

### Legacy Files (Pre-Refactor)
```
static/js/
├── messaging.js                      # Legacy monolithic JavaScript
├── encryption.js                     # E2E encryption utilities
├── chat_theme_manager.js             # Legacy theme management
├── auto_video_play.js                # Auto-play video functionality
└── bootstrap.bundle.min.js           # Bootstrap JavaScript library
```

### Refactored Chat System
```
static/js/chat/
├── bootstrap.js                      # Single entry point
├── ARCHITECTURE_REFACTOR.md          # Architecture documentation
│
├── shared/                           # Shared utilities
│   ├── constants.js                  # Events and constants
│   └── utils.js                      # Utility functions
│
├── core/                             # Core business logic
│   ├── event-bus.js                  # Event system
│   ├── store.js                      # State management
│   ├── websocket.js                  # WebSocket management
│   ├── message-service.js            # Message operations
│   ├── sync-engine.js                # Real-time sync engine
│   └── app-controller.js             # Application orchestrator
│
├── features/                         # Feature modules
│   ├── emoji/
│   │   └── emoji.service.js          # Emoji functionality
│   ├── camera/
│   │   └── camera.service.js          # Camera functionality
│   ├── voice/
│   │   └── voice.service.js          # Voice recording
│   └── attachments/
│       └── attachment.service.js     # File attachments
│
└── ui/                               # User interface
    ├── ui-controller.js              # UI coordinator
    ├── renderer.js                   # Message rendering
    ├── input.js                      # Input handling
    ├── header.js                     # Header UI
    └── theme/
        └── theme.service.js          # Theme management (merged)
```

---

## Templates: `templates/messaging/`

### Main Templates
```
templates/messaging/
├── base.html                         # Base template for messaging
├── conversation_list.html             # List of conversations
├── conversation_detail.html          # Legacy conversation detail
├── conversation_detail_refactored.html # Refactored conversation detail
├── create_conversation.html          # Create new conversation
├── conversation_settings.html        # Conversation settings
├── message_search.html               # Message search interface
└── components/                       # Reusable template components
    ├── message_bubble.html           # Individual message component
    ├── typing_indicator.html         # Typing indicator
    ├── attachment_preview.html        # Attachment preview
    ├── emoji_picker.html             # Emoji picker modal
    ├── camera_modal.html             # Camera capture modal
    ├── voice_recorder.html          # Voice recording interface
    ├── theme_selector.html           # Theme selector modal
    └── file_uploader.html            # File upload component
```

### Email Templates
```
templates/messaging/email/
├── new_message_notification.html     # New message email
├── conversation_invite.html          # Conversation invitation
└── message_digest.html              # Daily/weekly message digest
```

---

## Database Models

### Core Models
```
# messaging/models.py

class Conversation:
    - id
    - title
    - type (group, direct)
    - created_at
    - updated_at
    - is_encrypted
    - theme (ForeignKey to Theme)

class Message:
    - id
    - conversation (ForeignKey)
    - sender (ForeignKey)
    - content
    - encrypted_content
    - message_type (text, image, video, voice, file)
    - reply_to (ForeignKey to self)
    - created_at
    - updated_at
    - read_status
    - read_avatar

class ConversationMember:
    - id
    - conversation (ForeignKey)
    - user (ForeignKey)
    - role (admin, member)
    - joined_at
    - last_read_at
    - public_key

class MessageAttachment:
    - id
    - message (ForeignKey)
    - file
    - file_type
    - file_size
    - thumbnail
    - created_at

class Theme:
    - id
    - conversation (ForeignKey)
    - theme_type
    - light_color
    - dark_color
    - light_gradient_start
    - light_gradient_end
    - dark_gradient_start
    - dark_gradient_end
    - gradient_angle
    - overlay_opacity
    - light_overlay_color
    - dark_overlay_color
    - image_fit
    - created_at
    - updated_at

class VoiceMessage:
    - id
    - message (ForeignKey)
    - audio_file
    - duration
    - waveform_data
    - transcript
    - created_at
```

---

## URL Structure

### Web URLs
```
# messaging/urls.py

/messaging/                          # Conversation list
/messaging/create/                   # Create conversation
/messaging/<int:id>/                 # Conversation detail
/messaging/<int:id>/settings/        # Conversation settings
/messaging/<int:id>/search/          # Search messages
/messaging/<int:id>/members/         # Manage members
/messaging/<int:id>/theme/           # Theme management
```

### API URLs
```
# messaging/api/v1/urls.py

/api/v1/conversations/               # List/create conversations
/api/v1/conversations/<int:id>/       # Retrieve/update/delete
/api/v1/conversations/<int:id>/messages/  # List/create messages
/api/v1/conversations/<int:id>/members/    # Manage members
/api/v1/conversations/<int:id>/search/     # Search messages
/api/v1/messages/<int:id>/read-receipt/    # Mark as read
/api/v1/attachments/                 # Upload/retrieve attachments
/api/v1/themes/                      # Create/manage themes
/api/v1/themes/by_conversation/      # Get theme by conversation
/api/v1/voice-messages/              # Voice message operations
```

### WebSocket URLs
```
# WebSocket endpoints

/ws/chat/<int:conversation_id>/      # Real-time chat WebSocket
/ws/notifications/<int:user_id>/    # User notifications WebSocket
```

---

## Related Files Outside Domain

### Django Settings
```
# settings.py (relevant sections)

INSTALLED_APPS = [
    ...
    'messaging',
    ...
]

# WebSocket configuration
ASGI_APPLICATION = 'pwaninet.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}

# File upload settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
```

### ASGI Configuration
```
# asgi.py

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/<int:conversation_id>/', ChatConsumer.as_asgi()),
            path('ws/notifications/<int:user_id>/', NotificationConsumer.as_asgi()),
        ])
    ),
})
```

### URL Configuration
```
# urls.py (project root)

urlpatterns = [
    ...
    path('messaging/', include('messaging.urls')),
    path('api/v1/', include('messaging.api.v1.urls')),
    ...
]
```

### Static Files Configuration
```
# settings.py

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
```

---

## Consumer Classes (WebSocket)

### Chat Consumer
```
# messaging/consumers.py

class ChatConsumer(AsyncWebsocketConsumer):
    - Handle WebSocket connections
    - Message broadcasting
    - Typing indicators
    - Read receipts
    - Presence management
```

### Notification Consumer
```
# messaging/consumers.py

class NotificationConsumer(AsyncWebsocketConsumer):
    - User notifications
    - New message alerts
    - Typing indicators
    - Online status updates
```

---

## Celery Tasks

### Background Tasks
```
# messaging/tasks.py

@shared_task
def send_message_notification(message_id, recipient_ids):
    - Send email notifications
    - Push notifications

@shared_task
def process_attachment(attachment_id):
    - Generate thumbnails
    - Virus scanning
    - File validation

@shared_task
def cleanup_old_messages():
    - Delete messages older than retention period
    - Archive old conversations

@shared_task
def generate_message_digest(user_id, period):
    - Generate daily/weekly message summaries
```

---

## Testing Structure

### Unit Tests
```
messaging/tests/
├── test_models.py                     # Model tests
├── test_views.py                      # View tests
├── test_serializers.py                # Serializer tests
├── test_permissions.py                # Permission tests
├── test_queries.py                    # Query tests
├── test_consumers.py                  # WebSocket consumer tests
├── test_tasks.py                      # Celery task tests
├── test_utils.py                      # Utility function tests
└── fixtures/
    ├── conversations.json             # Test conversation data
    ├── messages.json                  # Test message data
    └── users.json                     # Test user data
```

### Integration Tests
```
messaging/tests/integration/
├── test_messaging_flow.py            # End-to-end messaging flow
├── test_real_time_sync.py            # WebSocket sync tests
├── test_file_uploads.py              # File upload tests
├── test_encryption.py                # E2E encryption tests
└── test_theme_system.py              # Theme system tests
```

---

## Documentation

### API Documentation
```
docs/api/
├── messaging_v1.md                   # API v1 documentation
├── websocket_api.md                  # WebSocket API documentation
├── authentication.md                  # Authentication guide
└── rate_limiting.md                  # Rate limiting documentation
```

### User Documentation
```
docs/user/
├── getting_started.md               # Getting started guide
├── features.md                       # Feature documentation
├── troubleshooting.md                # Troubleshooting guide
└── privacy.md                        # Privacy and security
```

### Developer Documentation
```
docs/developer/
├── architecture.md                   # System architecture
├── deployment.md                     # Deployment guide
├── contributing.md                   # Contribution guidelines
└── changelog.md                      # Version changelog
```

---

## Configuration Files

### Environment Variables
```
# .env.example

# Messaging settings
MESSAGING_MAX_MESSAGE_LENGTH=10000
MESSAGING_MAX_FILE_SIZE=52428800
MESSAGING_RETENTION_DAYS=365
MESSAGING_ENABLE_ENCRYPTION=true

# WebSocket settings
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS=1000

# Storage settings
AWS_S3_BUCKET_NAME=messaging-files
AWS_S3_REGION=us-east-1
```

### Docker Configuration
```
# docker-compose.yml (messaging services)

services:
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

  celery:
    build: .
    command: celery -A pwaninet worker -l info
    depends_on:
      - redis

  celery-beat:
    build: .
    command: celery -A pwaninet beat -l info
    depends_on:
      - redis
```

---

## Summary

The messaging domain consists of:

1. **Django App (`messaging/`)** - Core business logic, models, views, APIs
2. **Static Assets (`static/js/chat/`)** - Refactored JavaScript chat system
3. **Templates (`templates/messaging/`)** - Django templates for UI
4. **Related Files** - Django settings, ASGI config, URL routing, consumers, tasks

The refactored chat system follows strict layered architecture with event-driven communication, ensuring maintainability, testability, and real-time sync stability.
