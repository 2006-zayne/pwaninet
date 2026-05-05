import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from pwaninet.redis_client import get_redis_client
from .models import Conversation, ConversationMember, Message
from .ws_middleware import WebSocketRateLimiter, WebSocketConnectionTracker

User = get_user_model()

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30
MESSAGE_TIMEOUT = 5  # seconds to wait for message processing
WS_MESSAGE_RATE = 100  # messages per minute


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat in conversations with heartbeat."""

    async def connect(self):
        """Handle WebSocket connection with heartbeat task and rate limiting."""
        print(f'[BACKEND] WebSocket connection attempt from user {self.scope["user"].id} to conversation {self.scope["url_route"]["kwargs"]["conversation_id"]}')
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        self.heartbeat_task = None
        self.message_timeout_handle = None
        self.connection_id = self.channel_name  # Unique per connection

        if not self.user.is_authenticated:
            print(f'[BACKEND] User {self.user.id} is not authenticated, closing connection')
            await self.close()
            return

        # Check if user is a member of the conversation
        is_member = await self.is_conversation_member()
        print(f'[BACKEND] User {self.user.id} is_member check: {is_member}')
        if not is_member:
            print(f'[BACKEND] User {self.user.id} is not a member of conversation {self.conversation_id}, closing connection')
            await self.close()
            return

        # Register connection for tracking
        tracked = WebSocketConnectionTracker.register_connection(
            self.user.id,
            self.connection_id,
            metadata={
                'conversation_id': self.conversation_id,
                'ip': self.scope.get('client', ['unknown'])[0],
            }
        )
        print(f'[BACKEND] Connection tracking result: {tracked}')

        if not tracked:
            print(f'[BACKEND] Connection not tracked, closing')
            await self.close()
            return

        # Join room group
        print(f'[BACKEND] User {self.user.id} joining room group: {self.room_group_name}')
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f'[BACKEND] User {self.user.id} accepted and joined room: {self.room_group_name}')

        # Register this connection
        WebSocketConnectionTracker.register_connection(self.user.id, self.channel_name)

        # Set user online in Redis (only if this is the first connection)
        connection_count = WebSocketConnectionTracker.get_connection_count(self.user.id)
        if connection_count == 1:
            await self.set_user_online(True)
            # Broadcast user online status to room members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': True
                }
            )

        # Start heartbeat task to detect stale connections
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection and cleanup."""
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Unregister this connection (synchronous method, handle None user)
        if self.user and hasattr(self.user, 'id'):
            WebSocketConnectionTracker.unregister_connection(self.user.id, self.channel_name)

        # Only set user offline if this was the last connection
        connection_count = WebSocketConnectionTracker.get_connection_count(self.user.id)
        if connection_count == 0:
            await self.set_user_online(False)
            # Broadcast user offline status to room members
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'is_online': False,
                    'last_seen': asyncio.get_event_loop().time()
                }
            )

    async def heartbeat_loop(self):
        """Send periodic heartbeat messages to keep connection alive and refresh online status."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    # Refresh Redis TTL to keep user online
                    await self.set_user_online(True)

                    await self.send(text_data=json.dumps({
                        'type': 'ping',
                        'timestamp': asyncio.get_event_loop().time()
                    }))
                except Exception:
                    # Connection might be closed, let disconnect handle cleanup
                    break
        except asyncio.CancelledError:
            pass

    async def receive(self, text_data):
        """Handle incoming WebSocket messages with timeout and rate limiting."""
        # Check rate limit
        if WebSocketRateLimiter.is_rate_limited(self.user.id, self.connection_id, WS_MESSAGE_RATE):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Rate limit exceeded'
            }))
            return

        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            # Skip heartbeat responses
            if message_type == 'pong':
                return

            if message_type == 'chat_message':
                await asyncio.wait_for(self.handle_chat_message(data), timeout=MESSAGE_TIMEOUT)
            elif message_type == 'typing_indicator':
                await asyncio.wait_for(self.handle_typing_indicator(data), timeout=MESSAGE_TIMEOUT)
            elif message_type == 'read_receipt':
                await asyncio.wait_for(self.handle_read_receipt(data), timeout=MESSAGE_TIMEOUT)
        except asyncio.TimeoutError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Message processing timeout'
            }))
        except json.JSONDecodeError:
            pass
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message."""
        content = data.get('content')
        encrypted_content = data.get('encrypted_content')
        is_encrypted = data.get('is_encrypted', False)
        reply_to_id = data.get('reply_to')
        
        print(f'[BACKEND] Handling chat message from user {self.user.id} in conversation {self.conversation_id}')
        temp_id = data.get('temp_id')  # Get temp_id for optimistic update matching

        # Must have either plain content or encrypted content
        if not content and not encrypted_content:
            return

        # Create message in database
        message = await self.create_message(content, encrypted_content, is_encrypted, reply_to_id)

        # Add temp_id to message for client-side optimistic update matching
        if temp_id:
            message['temp_id'] = temp_id

        # Broadcast to room group
        print(f'[BACKEND] Broadcasting message {message["id"]} to room group: {self.room_group_name}')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )
        print(f'[BACKEND] Message {message["id"]} broadcasted to room group')

    async def handle_typing_indicator(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt."""
        message_id = data.get('message_id')

        if not message_id:
            return

        print(f'[BACKEND] Processing read receipt for message {message_id} from user {self.user.id}')

        # Mark message as read
        await self.mark_message_as_read(message_id)

        # Get user avatar for the read receipt
        read_avatar = await self.get_user_avatar()
        print(f'[BACKEND] Got avatar for read receipt: {read_avatar}')

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'message_id': message_id,
                'user_id': self.user.id,
                'read_avatar': read_avatar
            }
        )
        print(f'[BACKEND] Broadcasted read receipt for message {message_id}')

    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        message = event['message']
        print(f'[BACKEND] Sending message to client: {message["id"]}')
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': message
        }))
        print(f'[BACKEND] Message sent to client')

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def user_status(self, event):
        """Send user online/offline status to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online'],
            'last_seen': event.get('last_seen')
        }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'read_avatar': event.get('read_avatar')
        }))

    @database_sync_to_async
    def is_conversation_member(self):
        """Check if user is a member of the conversation."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.members.filter(user=self.user).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, content, encrypted_content, is_encrypted, reply_to_id):
        """Create a new message in the database."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            reply_to = None
            if reply_to_id:
                reply_to = Message.objects.filter(id=reply_to_id).first()

            # If conversation is encrypted by default, mark message as encrypted
            if is_encrypted or (conversation.is_encrypted and encrypted_content):
                message = Message.objects.create(
                    conversation=conversation,
                    sender=self.user,
                    content=None,  # Don't store plaintext for encrypted messages
                    encrypted_content=encrypted_content,
                    is_encrypted=True,
                    reply_to=reply_to
                )
            else:
                message = Message.objects.create(
                    conversation=conversation,
                    sender=self.user,
                    content=content,
                    reply_to=reply_to
                )

            # Update conversation timestamp
            conversation.save()

            # Serialize message
            from .serializers import MessageSerializer
            serializer = MessageSerializer(message)
            return serializer.data
        except Conversation.DoesNotExist:
            return None

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read for the current user."""
        try:
            from .models import MessageRead
            message = Message.objects.get(id=message_id)

            # Create read receipt
            MessageRead.objects.get_or_create(
                message=message,
                user=self.user
            )

            # Update member's last read message
            member = message.conversation.members.filter(user=self.user).first()
            if member:
                member.last_read_message = message
                member.save()
        except Message.DoesNotExist:
            pass

    @database_sync_to_async
    def get_user_avatar(self):
        """Get current user's avatar URL for read receipts."""
        try:
            if self.user.profile_photo:
                return self.user.profile_photo.url
        except Exception:
            pass
        return None

    async def set_user_online(self, is_online):
        """Set user online status in Redis using connection pool."""
        try:
            redis_client = get_redis_client()
            key = f'user_online:{self.user.id}'
            
            if is_online:
                # Set with 5 minute TTL (heartbeat should refresh)
                redis_client.setex(key, 300, '1')
            else:
                redis_client.delete(key)
        except Exception:
            pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for global notifications."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f'notifications_{self.user.id}'

        # Join user's notification group
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def notify(self, event):
        """Send notification to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for online status tracking."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.accept()

        # Set user online
        await self.set_user_online(True)

        # Send current online users
        online_users = await self.get_online_users()
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'data': online_users
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Set user offline
        await self.set_user_online(False)

    async def set_user_online(self, is_online):
        """Set user online status in Redis using connection pool."""
        try:
            redis_client = get_redis_client()
            key = f'user_online:{self.user.id}'
            
            if is_online:
                redis_client.setex(key, 300, '1')
                # Broadcast to all online status consumers
                await self.channel_layer.group_send(
                    'online_status',
                    {
                        'type': 'user_status_change',
                        'user_id': self.user.id,
                        'is_online': True
                    }
                )
            else:
                redis_client.delete(key)
                await self.channel_layer.group_send(
                    'online_status',
                    {
                        'type': 'user_status_change',
                        'user_id': self.user.id,
                        'is_online': False
                    }
                )
        except Exception:
            pass

    async def get_online_users(self):
        """Get list of online users from Redis using connection pool."""
        try:
            redis_client = get_redis_client()
            keys = redis_client.keys('user_online:*')
            user_ids = [int(key.split(':')[1]) for key in keys]
            return user_ids
        except Exception:
            return []

    async def user_status_change(self, event):
        """Send user status change to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'user_status_change',
            'user_id': event['user_id'],
            'is_online': event['is_online']
        }))
