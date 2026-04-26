# Real-Time Notifications & Chat Architecture

## Overview

This document outlines the architecture and implementation plan for adding real-time notifications, browser popups, WebSockets, and preparing the infrastructure for future chat features.

## Goals

1. **Real-time notifications** - Instant delivery without page refresh
2. **Browser notifications** - Desktop push notifications
3. **WebSocket infrastructure** - Foundation for chat features
4. **Scalable architecture** - Support for high-concurrency scenarios

---

## Phase 1: Dependencies & Infrastructure

### Backend Dependencies

Add to `requirements.txt`:

```txt
# WebSocket support
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0

# Redis for message broker
redis==5.0.0
hiredis==2.2.3

# Additional utilities
django-redis==5.4.0
```

### System Requirements

- **Redis Server** (for channel layer and caching)
- **Daphne** (ASGI server for WebSockets)
- **Nginx** (for WebSocket proxying in production)

### Installation Steps

```bash
# Install Redis
sudo apt-get install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Install Python dependencies
pip install channels channels-redis daphne django-redis
```

---

## Phase 2: Django Configuration

### 1. Update `pwaninet/settings/local.py`

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'channels',
]

ASGI_APPLICATION = 'pwaninet.asgi.application'

# Channel layer configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}

# Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 2. Create `pwaninet/asgi.py`

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')

django_asgi_app = get_asgi_application()

import notifications.routing
import chat.routing  # For future chat feature

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                notifications.routing.websocket_urlpatterns,
                chat.routing.websocket_urlpatterns,  # Future chat
            ])
        )
    ),
})
```

### 3. Update `pwaninet/wsgi.py` (for production)

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
application = get_wsgi_application()
```

---

## Phase 3: WebSocket Consumers

### 1. Create `notifications/consumers.py`

```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from notifications.models import Notifications
from notifications.services.notification_service import get_cached_unread_count

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
            return
        
        self.user_id = self.scope["user"].id
        self.group_name = f"user_{self.user_id}"
        
        # Join user's personal notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current unread count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        # Handle client messages (e.g., mark as read)
        data = json.loads(text_data)
        
        if data.get('type') == 'mark_read':
            notification_id = data.get('notification_id')
            await self.mark_notification_read(notification_id)
    
    async def notification_message(self, event):
        """Handle incoming notification from channel layer"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def unread_count_update(self, event):
        """Handle unread count updates"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count']
        }))
    
    @database_sync_to_async
    def get_unread_count(self):
        return get_cached_unread_count(self.scope["user"].id)
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notif = Notifications.objects.get(
                id=notification_id,
                recipient=self.scope["user"]
            )
            notif.is_read = True
            notif.save()
            return True
        except Notifications.DoesNotExist:
            return False
```

### 2. Create `notifications/routing.py`

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
```

---

## Phase 4: Notification Service Updates

### Update `notifications/services/notification_service.py`

```python
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notifications

def create_notification(recipient, sender, notification_type, msg, group=None, post=None):
    """Create notification and trigger real-time delivery"""
    notification = Notifications.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        msg=msg,
        group=group,
        post=post
    )
    
    # Trigger real-time delivery via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{recipient.id}",
        {
            'type': 'notification_message',
            'notification': {
                'id': notification.id,
                'sender': {
                    'id': sender.id,
                    'username': sender.username,
                    'profile_pic': sender.profile_pic.url if sender.profile_pic else None
                },
                'notification_type': notification.notification_type,
                'msg': notification.msg,
                'group_id': notification.group.id if notification.group else None,
                'group_name': notification.group.name if notification.group else None,
                'post_id': notification.post.id if notification.post else None,
                'timestamp': notification.timestamp.isoformat(),
                'is_read': notification.is_read
            }
        }
    )
    
    # Update unread count
    invalidate_unread_count_cache(recipient.id)
    async_to_sync(channel_layer.group_send)(
        f"user_{recipient.id}",
        {
            'type': 'unread_count_update',
            'count': get_cached_unread_count(recipient.id)
        }
    )
    
    return notification
```

---

## Phase 5: Frontend Implementation

### 1. WebSocket Client (`static/js/notifications.js`)

```javascript
class NotificationWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.reconnect();
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => this.connect(), this.reconnectDelay);
        }
    }
    
    handleMessage(data) {
        switch(data.type) {
            case 'notification':
                this.showNotification(data.notification);
                this.updateUnreadBadge();
                break;
            case 'unread_count':
                this.updateUnreadBadge(data.count);
                break;
        }
    }
    
    showNotification(notification) {
        // Browser notification
        if (Notification.permission === 'granted') {
            new Notification(`${notification.sender.username}`, {
                body: notification.msg,
                icon: notification.sender.profile_pic || '/static/images/default_user.jpg',
                tag: `notification-${notification.id}`
            });
        }
        
        // In-app toast
        this.showToast(notification);
        
        // Play sound
        this.playNotificationSound();
    }
    
    showToast(notification) {
        const toast = document.createElement('div');
        toast.className = 'notification-toast';
        toast.innerHTML = `
            <div class="toast-content">
                <img src="${notification.sender.profile_pic || '/static/images/default_user.jpg'}" class="toast-avatar">
                <div class="toast-message">
                    <strong>${notification.sender.username}</strong>
                    <p>${notification.msg}</p>
                </div>
                <button class="toast-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => toast.remove(), 5000);
    }
    
    updateUnreadBadge(count) {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.play().catch(e => console.log('Audio play failed:', e));
    }
    
    markAsRead(notificationId) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'mark_read',
                notification_id: notificationId
            }));
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Initialize on page load
let notificationWS;
document.addEventListener('DOMContentLoaded', () => {
    notificationWS = new NotificationWebSocket();
    notificationWS.connect();
});

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}
```

### 2. Toast Notification CSS (`static/css/toast.css`)

```css
.notification-toast {
    position: fixed;
    top: 20px;
    right: 20px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    padding: 16px;
    z-index: 9999;
    animation: slideIn 0.3s ease;
    max-width: 350px;
}

@keyframes slideIn {
    from {
        transform: translateX(400px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.toast-content {
    display: flex;
    align-items: center;
    gap: 12px;
}

.toast-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
}

.toast-message {
    flex: 1;
}

.toast-message strong {
    display: block;
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
}

.toast-message p {
    margin: 4px 0 0;
    font-size: 13px;
    color: #666;
}

.toast-close {
    background: none;
    border: none;
    font-size: 20px;
    color: #999;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.toast-close:hover {
    color: #333;
}
```

### 3. Update Base Template (`templates/base.html`)

```html
<head>
    <!-- ... existing head ... -->
    <link rel="stylesheet" href="{% static 'css/toast.css' %}">
</head>

<body>
    <!-- ... existing body ... -->
    
    <!-- Notification badge in navbar -->
    <a href="{% url 'notifications:notifications' %}" class="nav-link position-relative">
        <i class="bi bi-bell"></i>
        <span id="notification-badge" class="badge bg-danger rounded-pill" 
              style="display: none; position: absolute; top: -5px; right: -5px; font-size: 10px; padding: 3px 6px;">
        </span>
    </a>
    
    <script src="{% static 'js/notifications.js' %}"></script>
</body>
```

---

## Phase 6: Chat Feature Preparation

### 1. Chat Models Structure with End-to-End Encryption

```python
# chat/models.py
from django.db import models
from django.conf import settings
import json

class ChatRoom(models.Model):
    """Group chat rooms"""
    name = models.CharField(max_length=200)
    group = models.OneToOneField('groups.Group', on_delete=models.CASCADE, null=True, blank=True)
    is_direct = models.BooleanField(default=False)  # For DMs
    is_encrypted = models.BooleanField(default=True)  # E2E encryption enabled
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class ChatParticipant(models.Model):
    """Users in a chat room with encryption keys"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    
    # E2E encryption: Store public keys for each participant
    public_key = models.TextField(blank=True, null=True)  # User's public key for this room
    
    class Meta:
        unique_together = ('room', 'user')

class Message(models.Model):
    """Chat messages with encryption support"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Encrypted content (if room is encrypted)
    encrypted_content = models.TextField(blank=True, null=True)
    # Plaintext content (if room is not encrypted)
    content = models.TextField(blank=True, null=True)
    
    # For file attachments (also encrypted)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    
    # Encryption metadata
    encryption_version = models.CharField(max_length=20, default='v1')
    is_encrypted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Message reactions
    reactions = models.JSONField(default=dict, blank=True)  # {"emoji": [user_ids]}
    
    # Message status
    is_deleted = models.BooleanField(default=False)
    deleted_for = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='deleted_messages')
    
    class Meta:
        ordering = ['created_at']

class MessageReadReceipt(models.Model):
    """Track which users have read which messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('message', 'user')

class TypingIndicator(models.Model):
    """Track typing status (ephemeral, stored in Redis ideally)"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_typing = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now_add=True)
```

### 2. End-to-End Encryption Implementation

```python
# chat/encryption.py
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import base64

class EncryptionManager:
    """Handle E2E encryption for chat messages"""
    
    @staticmethod
    def generate_key_pair():
        """Generate RSA key pair for user"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode('utf-8'), public_pem.decode('utf-8')
    
    @staticmethod
    def encrypt_message(message: str, public_key_pem: str) -> str:
        """Encrypt message with recipient's public key"""
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(),
            backend=default_backend()
        )
        
        encrypted = public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted).decode('utf-8')
    
    @staticmethod
    def decrypt_message(encrypted_message: str, private_key_pem: str) -> str:
        """Decrypt message with user's private key"""
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None,
            backend=default_backend()
        )
        
        encrypted_bytes = base64.b64decode(encrypted_message.encode('utf-8'))
        
        decrypted = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted.decode('utf-8')
    
    @staticmethod
    def generate_symmetric_key():
        """Generate symmetric key for group chat"""
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_symmetric(message: str, key: bytes) -> str:
        """Encrypt with symmetric key (for group chats)"""
        fernet = Fernet(key)
        encrypted = fernet.encrypt(message.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')
    
    @staticmethod
    def decrypt_symmetric(encrypted_message: str, key: bytes) -> str:
        """Decrypt with symmetric key"""
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_message.encode('utf-8'))
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
```

### 3. Chat Consumer with Encryption Support

```python
# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message, ChatParticipant
from .encryption import EncryptionManager

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"
        
        # Check if user is participant
        is_participant = await self.is_participant()
        if not is_participant:
            await self.close()
            return
        
        # Get user's private key from session or secure storage
        self.private_key = self.scope['session'].get('private_key')
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send recent messages (decrypted if encrypted)
        messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages,
            'is_encrypted': await self.is_room_encrypted()
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data['type'] == 'message':
            content = data.get('content')
            encrypted_content = data.get('encrypted_content')
            
            # Save message (server stores encrypted version)
            message = await self.save_message(
                content=content,
                encrypted_content=encrypted_content
            )
            
            # Broadcast to room (encrypted if room is encrypted)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message
                }
            )
        
        elif data['type'] == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user_id': self.scope["user"].id,
                    'username': self.scope["user"].username
                }
            )
        
        elif data['type'] == 'read_receipt':
            await self.mark_as_read(data['message_id'])
    
    async def chat_message(self, event):
        # Decrypt if necessary before sending
        message = event['message']
        if message.get('is_encrypted') and self.private_key:
            try:
                message['content'] = EncryptionManager.decrypt_message(
                    message['encrypted_content'],
                    self.private_key
                )
            except Exception as e:
                message['content'] = '[Encrypted message - decryption failed]'
        
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))
    
    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username']
        }))
    
    @database_sync_to_async
    def is_participant(self):
        return ChatParticipant.objects.filter(
            room_id=self.room_id,
            user=self.scope["user"]
        ).exists()
    
    @database_sync_to_async
    def is_room_encrypted(self):
        room = ChatRoom.objects.get(id=self.room_id)
        return room.is_encrypted
    
    @database_sync_to_async
    def save_message(self, content, encrypted_content):
        room = ChatRoom.objects.get(id=self.room_id)
        return Message.objects.create(
            room=room,
            sender=self.scope["user"],
            content=content if not room.is_encrypted else None,
            encrypted_content=encrypted_content if room.is_encrypted else None,
            is_encrypted=room.is_encrypted
        )
    
    @database_sync_to_async
    def get_recent_messages(self, limit=50):
        messages = Message.objects.filter(
            room_id=self.room_id,
            is_deleted=False
        ).select_related('sender')[:limit]
        
        return [{
            'id': m.id,
            'sender': {
                'id': m.sender.id,
                'username': m.sender.username,
                'profile_pic': m.sender.profile_pic.url if m.sender.profile_pic else None
            },
            'content': m.content,  # Plaintext for non-encrypted rooms
            'encrypted_content': m.encrypted_content,  # For client-side decryption
            'image': m.image.url if m.image else None,
            'created_at': m.created_at.isoformat(),
            'is_edited': m.is_edited,
            'is_encrypted': m.is_encrypted,
            'reactions': m.reactions
        } for m in messages]
    
    @database_sync_to_async
    def mark_as_read(self, message_id):
        from .models import MessageReadReceipt
        MessageReadReceipt.objects.get_or_create(
            message_id=message_id,
            user=self.scope["user"]
        )
```

### 4. Chat Routing (`chat/routing.py`)

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]
```

---

## Phase 7: Chat UI/UX Design

### 1. Chat Section Architecture

The chat feature will be a **separate section** from posts, accessible via:

**Navigation Structure:**
```
PwaniNet
├── Home (Feed)
├── Groups
│   ├── [Group Name]
│   │   ├── Posts Tab (current view)
│   │   ├── Chat Tab (new)
│   │   ├── Members Tab
│   │   └── Files Tab
├── Messages (DMs)
└── Notifications
```

### 2. Group Chat UI Template (`chat/templates/chat/group_chat.html`)

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<style>
  /* Chat container layout */
  .chat-container {
    display: grid;
    grid-template-columns: 300px 1fr;
    height: calc(100vh - 80px);
    background: #f8fafc;
  }
  
  /* Sidebar - Chat list */
  .chat-sidebar {
    background: white;
    border-right: 1px solid #e2e8f0;
    overflow-y: auto;
  }
  
  .chat-list-item {
    padding: 16px;
    border-bottom: 1px solid #f1f5f9;
    cursor: pointer;
    transition: background 0.2s;
  }
  
  .chat-list-item:hover, .chat-list-item.active {
    background: #f1f5f9;
  }
  
  .chat-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    object-fit: cover;
  }
  
  .chat-info {
    flex: 1;
    margin-left: 12px;
  }
  
  .chat-name {
    font-weight: 700;
    font-size: 14px;
    color: #1e293b;
  }
  
  .chat-preview {
    font-size: 13px;
    color: #64748b;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .chat-meta {
    text-align: right;
  }
  
  .chat-time {
    font-size: 11px;
    color: #94a3b8;
  }
  
  .unread-badge {
    background: #2563eb;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    margin-top: 4px;
  }
  
  /* Main chat area */
  .chat-main {
    display: flex;
    flex-direction: column;
    background: white;
  }
  
  /* Chat header */
  .chat-header {
    padding: 16px 24px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  
  .chat-header-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .encryption-badge {
    background: #f0fdf4;
    color: #16a34a;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  /* Messages area */
  .chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    background: #f8fafc;
  }
  
  .message {
    display: flex;
    margin-bottom: 16px;
    max-width: 70%;
  }
  
  .message.sent {
    margin-left: auto;
    flex-direction: row-reverse;
  }
  
  .message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }
  
  .message-bubble {
    background: white;
    padding: 12px 16px;
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    margin: 0 12px;
  }
  
  .message.sent .message-bubble {
    background: #2563eb;
    color: white;
  }
  
  .message-sender {
    font-weight: 700;
    font-size: 13px;
    margin-bottom: 4px;
  }
  
  .message-content {
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
  }
  
  .message-time {
    font-size: 11px;
    color: #94a3b8;
    margin-top: 4px;
  }
  
  .message.sent .message-time {
    color: rgba(255,255,255,0.7);
  }
  
  .message-reactions {
    display: flex;
    gap: 4px;
    margin-top: 8px;
  }
  
  .reaction {
    background: #f1f5f9;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    cursor: pointer;
  }
  
  .reaction:hover {
    background: #e2e8f0;
  }
  
  /* Typing indicator */
  .typing-indicator {
    display: flex;
    gap: 4px;
    padding: 12px 16px;
    margin-left: 60px;
  }
  
  .typing-dot {
    width: 8px;
    height: 8px;
    background: #94a3b8;
    border-radius: 50%;
    animation: typing 1.4s infinite;
  }
  
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  
  @keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-4px); }
  }
  
  /* Input area */
  .chat-input-area {
    padding: 16px 24px;
    border-top: 1px solid #e2e8f0;
    background: white;
  }
  
  .chat-input-wrapper {
    display: flex;
    gap: 12px;
    align-items: flex-end;
  }
  
  .chat-input {
    flex: 1;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 12px 16px;
    font-size: 14px;
    resize: none;
    max-height: 120px;
  }
  
  .chat-input:focus {
    outline: none;
    border-color: #2563eb;
  }
  
  .chat-actions {
    display: flex;
    gap: 8px;
  }
  
  .chat-btn {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: none;
    background: #f1f5f9;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }
  
  .chat-btn:hover {
    background: #e2e8f0;
  }
  
  .chat-btn.send {
    background: #2563eb;
    color: white;
  }
  
  .chat-btn.send:hover {
    background: #1d4ed8;
  }
  
  /* Encryption lock icon */
  .encryption-lock {
    color: #16a34a;
  }
</style>

<div class="chat-container">
  <!-- Sidebar -->
  <div class="chat-sidebar">
    <div class="p-4 border-b">
      <input type="text" placeholder="Search chats..." 
             class="w-full px-4 py-2 rounded-full border text-sm">
    </div>
    
    <div id="chat-list">
      <!-- Chat items loaded dynamically -->
    </div>
  </div>
  
  <!-- Main Chat -->
  <div class="chat-main">
    <!-- Header -->
    <div class="chat-header">
      <div class="chat-header-info">
        <img src="{{ group.group_pic.url }}" class="chat-avatar" alt="">
        <div>
          <h3 class="chat-name">{{ group.name }}</h3>
          <div class="encryption-badge">
            <i class="bi bi-lock-fill encryption-lock"></i>
            End-to-end encrypted
          </div>
        </div>
      </div>
      <div class="chat-actions">
        <button class="chat-btn" title="Video call">
          <i class="bi bi-camera-video"></i>
        </button>
        <button class="chat-btn" title="Voice call">
          <i class="bi bi-telephone"></i>
        </button>
        <button class="chat-btn" title="Group info">
          <i class="bi bi-info-circle"></i>
        </button>
      </div>
    </div>
    
    <!-- Messages -->
    <div class="chat-messages" id="chat-messages">
      <!-- Messages loaded dynamically -->
    </div>
    
    <!-- Typing indicator -->
    <div class="typing-indicator" id="typing-indicator" style="display: none;">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
    
    <!-- Input -->
    <div class="chat-input-area">
      <div class="chat-input-wrapper">
        <button class="chat-btn" title="Attach file">
          <i class="bi bi-paperclip"></i>
        </button>
        <textarea class="chat-input" id="message-input" 
                  placeholder="Type a message..." rows="1"></textarea>
        <button class="chat-btn" title="Emoji">
          <i class="bi bi-emoji-smile"></i>
        </button>
        <button class="chat-btn send" id="send-btn">
          <i class="bi bi-send-fill"></i>
        </button>
      </div>
    </div>
  </div>
</div>

<script src="{% static 'js/chat.js' %}"></script>
{% endblock %}
```

### 3. Chat JavaScript Client (`static/js/chat.js`)

```javascript
class ChatClient {
    constructor(roomId, isEncrypted = true) {
        this.roomId = roomId;
        this.isEncrypted = isEncrypted;
        this.socket = null;
        this.privateKey = null;
        this.publicKey = null;
        this.typingTimeout = null;
    }
    
    async init() {
        // Generate or load encryption keys
        if (this.isEncrypted) {
            await this.loadOrGenerateKeys();
        }
        
        // Connect to WebSocket
        this.connect();
        
        // Setup event listeners
        this.setupEventListeners();
    }
    
    async loadOrGenerateKeys() {
        // Try to load from localStorage
        const storedPrivateKey = localStorage.getItem(`private_key_${this.roomId}`);
        const storedPublicKey = localStorage.getItem(`public_key_${this.roomId}`);
        
        if (storedPrivateKey && storedPublicKey) {
            this.privateKey = storedPrivateKey;
            this.publicKey = storedPublicKey;
        } else {
            // Generate new keys (in production, use Web Crypto API)
            const { privateKey, publicKey } = await this.generateKeyPair();
            this.privateKey = privateKey;
            this.publicKey = publicKey;
            
            localStorage.setItem(`private_key_${this.roomId}`, privateKey);
            localStorage.setItem(`public_key_${this.roomId}`, publicKey);
        }
        
        // Send public key to server
        this.sendPublicKey();
    }
    
    async generateKeyPair() {
        // Use Web Crypto API for key generation
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: "RSA-OAEP",
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: "SHA-256"
            },
            true,
            ["encrypt", "decrypt"]
        );
        
        const publicKey = await window.crypto.subtle.exportKey("spki", keyPair.publicKey);
        const privateKey = await window.crypto.subtle.exportKey("pkcs8", keyPair.privateKey);
        
        return {
            publicKey: this.arrayBufferToBase64(publicKey),
            privateKey: this.arrayBufferToBase64(privateKey)
        };
    }
    
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }
    
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.roomId}/`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('Chat WebSocket connected');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.socket.onclose = () => {
            console.log('Chat WebSocket disconnected');
            // Auto-reconnect
            setTimeout(() => this.connect(), 3000);
        };
        
        this.socket.onerror = (error) => {
            console.error('Chat WebSocket error:', error);
        };
    }
    
    async handleMessage(data) {
        switch(data.type) {
            case 'history':
                this.renderMessages(data.messages);
                break;
            case 'message':
                await this.renderMessage(data.message);
                break;
            case 'typing':
                this.showTypingIndicator(data.username);
                break;
        }
    }
    
    async renderMessage(message) {
        const messagesContainer = document.getElementById('chat-messages');
        const isOwn = message.sender.id === currentUserId;
        
        let content = message.content;
        
        // Decrypt if encrypted
        if (message.is_encrypted && this.privateKey) {
            try {
                content = await this.decryptMessage(message.encrypted_content);
            } catch (e) {
                content = '[Encrypted message]';
            }
        }
        
        const messageEl = document.createElement('div');
        messageEl.className = `message ${isOwn ? 'sent' : 'received'}`;
        messageEl.innerHTML = `
            <img src="${message.sender.profile_pic}" class="message-avatar">
            <div class="message-bubble">
                ${!isOwn ? `<div class="message-sender">${message.sender.username}</div>` : ''}
                <div class="message-content">${content}</div>
                <div class="message-time">${this.formatTime(message.created_at)}</div>
                ${message.reactions ? this.renderReactions(message.reactions) : ''}
            </div>
        `;
        
        messagesContainer.appendChild(messageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    renderMessages(messages) {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = '';
        messages.forEach(msg => this.renderMessage(msg));
    }
    
    async sendMessage(content) {
        let encryptedContent = null;
        
        // Encrypt if room is encrypted
        if (this.isEncrypted) {
            encryptedContent = await this.encryptMessage(content);
        }
        
        this.socket.send(JSON.stringify({
            type: 'message',
            content: this.isEncrypted ? null : content,
            encrypted_content: encryptedContent
        }));
    }
    
    async encryptMessage(content) {
        // Use Web Crypto API for encryption
        const publicKey = await this.importKey(this.publicKey);
        const encrypted = await window.crypto.subtle.encrypt(
            {
                name: "RSA-OAEP"
            },
            publicKey,
            new TextEncoder().encode(content)
        );
        return this.arrayBufferToBase64(encrypted);
    }
    
    async decryptMessage(encryptedContent) {
        const privateKey = await this.importKey(this.privateKey, true);
        const encrypted = this.base64ToArrayBuffer(encryptedContent);
        const decrypted = await window.crypto.subtle.decrypt(
            {
                name: "RSA-OAEP"
            },
            privateKey,
            encrypted
        );
        return new TextDecoder().decode(decrypted);
    }
    
    async importKey(keyData, isPrivate = false) {
        const format = isPrivate ? 'pkcs8' : 'spki';
        const algorithm = isPrivate ? 
            { name: "RSA-OAEP", hash: "SHA-256" } : 
            { name: "RSA-OAEP" };
        const usages = isPrivate ? ['decrypt'] : ['encrypt'];
        
        return await window.crypto.subtle.importKey(
            format,
            this.base64ToArrayBuffer(keyData),
            algorithm,
            true,
            usages
        );
    }
    
    base64ToArrayBuffer(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }
    
    sendTypingIndicator() {
        this.socket.send(JSON.stringify({ type: 'typing' }));
        
        // Clear previous timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }
        
        // Stop typing indicator after 3 seconds
        this.typingTimeout = setTimeout(() => {
            this.socket.send(JSON.stringify({ type: 'stop_typing' }));
        }, 3000);
    }
    
    showTypingIndicator(username) {
        const indicator = document.getElementById('typing-indicator');
        indicator.innerHTML = `<span>${username} is typing...</span>`;
        indicator.style.display = 'flex';
        
        setTimeout(() => {
            indicator.style.display = 'none';
        }, 3000);
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    setupEventListeners() {
        const input = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        
        sendBtn.addEventListener('click', () => {
            const content = input.value.trim();
            if (content) {
                this.sendMessage(content);
                input.value = '';
            }
        });
        
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const content = input.value.trim();
                if (content) {
                    this.sendMessage(content);
                    input.value = '';
                }
            }
        });
        
        input.addEventListener('input', () => {
            this.sendTypingIndicator();
        });
    }
    
    sendPublicKey() {
        // Send public key to server for storage
        fetch(`/api/chat/${this.roomId}/set-public-key/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ public_key: this.publicKey })
        });
    }
}

// Initialize chat
const chatClient = new ChatClient(roomId, isEncrypted);
chatClient.init();
```

---

## Phase 7: Production Deployment

### 1. Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. Supervisor Configuration (for Daphne)

```ini
[program:daphne]
command=/path/to/venv/bin/daphne -b 0.0.0.0 -p 8000 pwaninet.asgi:application
directory=/path/to/pwaninet
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/daphne.log
```

### 3. Redis Configuration

```bash
# Production Redis with persistence
sudo nano /etc/redis/redis.conf

# Enable persistence
save 900 1
save 300 10
save 60 10000

# Restart Redis
sudo systemctl restart redis-server
```

---

## Phase 8: Monitoring & Scaling

### 1. Redis Monitoring

```bash
# Monitor Redis
redis-cli monitor

# Check memory usage
redis-cli info memory

# Check connected clients
redis-cli info clients
```

### 2. Channel Layer Scaling

For high-concurrency scenarios:

```python
# Use Redis Cluster for horizontal scaling
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisClusterChannelLayer',
        'CONFIG': {
            "hosts": [
                ("redis-node-1", 6379),
                ("redis-node-2", 6379),
                ("redis-node-3", 6379),
            ],
        },
    },
}
```

### 3. Load Balancing

- Use multiple Daphne workers behind Nginx
- Each Daphne instance handles WebSocket connections
- Redis handles message broadcasting across instances

---

## Implementation Checklist

### Phase 1: Infrastructure
- [ ] Install Redis server
- [ ] Install Python dependencies (channels, daphne, redis)
- [ ] Configure Redis for persistence
- [ ] Test Redis connection

### Phase 2: Django Setup
- [ ] Update settings.py with channels config
- [ ] Create asgi.py
- [ ] Update wsgi.py for production
- [ ] Test ASGI server with daphne

### Phase 3: WebSocket Consumers
- [ ] Create NotificationConsumer
- [ ] Create notification routing
- [ ] Test WebSocket connection
- [ ] Test message delivery

### Phase 4: Service Updates
- [ ] Update notification service with channel layer
- [ ] Test real-time notification delivery
- [ ] Test unread count updates

### Phase 5: Frontend
- [ ] Create WebSocket client JavaScript
- [ ] Add toast notification CSS
- [ ] Update base template with badge
- [ ] Request browser notification permission
- [ ] Test browser notifications
- [ ] Test toast notifications

### Phase 6: Chat Preparation
- [ ] Create chat models
- [ ] Create ChatConsumer
- [ ] Create chat routing
- [ ] Design chat UI components
- [ ] Test chat functionality

### Phase 7: Production
- [ ] Configure Nginx for WebSockets
- [ ] Set up Supervisor for Daphne
- [ ] Configure Redis for production
- [ ] Set up monitoring
- [ ] Load testing

---

## Performance Considerations

### 1. Connection Limits
- Default: ~1000 concurrent connections per Daphne instance
- Scale horizontally with multiple instances
- Use connection pooling for Redis

### 2. Message Queue
- Redis is fast but single-threaded
- Consider RabbitMQ for complex routing
- Monitor Redis memory usage

### 3. Database Optimization
- Add indexes on notification queries
- Use select_related/prefetch_related
- Consider read replicas for high traffic

### 4. Caching Strategy
- Cache unread counts
- Cache user permissions
- Use Redis for session storage

---

## Security Considerations

### 1. WebSocket Authentication
- Use AuthMiddlewareStack
- Validate user on every connection
- Implement rate limiting

### 2. Message Validation
- Sanitize all message content
- Validate file uploads
- Implement message size limits

### 3. CORS Configuration
- Configure allowed origins
- Validate WebSocket origins
- Use secure WebSocket (wss://) in production

---

## Cost Estimates

### Infrastructure (Monthly)
- Redis server: $10-50 (depending on size)
- Additional Daphne instances: $20-100 per instance
- Load balancer: $20-50
- Monitoring: $10-30

### Development Time
- Phase 1-2: 1-2 days
- Phase 3-4: 2-3 days
- Phase 5: 2-3 days
- Phase 6: 3-5 days
- Phase 7: 1-2 days
- **Total: 9-15 days**

---

## Alternatives

### 1. Pusher (Third-party)
- Pros: No infrastructure setup, easy integration
- Cons: Costly at scale, vendor lock-in
- Cost: Free tier (100 connections/day), $49/month for 200 connections

### 2. Firebase Cloud Messaging
- Pros: Free, reliable, cross-platform
- Cons: Not real-time WebSocket, notification-focused
- Cost: Free tier generous

### 3. Socket.io (Node.js)
- Pros: Mature ecosystem, easy to use
- Cons: Separate Node.js server needed
- Cost: Free (self-hosted)

---

## Recommended Approach

**For PwaniNet:**
1. Start with Django Channels + Redis (self-hosted)
2. Implement notifications first
3. Add chat feature later
4. Scale horizontally as needed
5. Monitor and optimize based on usage

This provides:
- Full control over infrastructure
- Cost-effective at scale
- Seamless integration with existing Django stack
- Foundation for future real-time features
