"""
WebSocket consumers for real-time features.

ARCHITECTURAL RULE:
Each WebSocket consumer must have a single source of truth file.
Duplicate class names across modules are forbidden.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time notifications."""

    async def connect(self):
        """Handle WebSocket connection."""
        print(f'[NOTIFICATIONS] WebSocket connection attempt from user: {self.scope["user"]}')
        print(f'[NOTIFICATIONS] User is_anonymous: {self.scope["user"].is_anonymous}')
        
        if self.scope["user"].is_anonymous:
            print('[NOTIFICATIONS] Closing connection - user is anonymous')
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_group_name = f"notifications_{self.user.id}"
        
        print(f'[NOTIFICATIONS] User {self.user.id} connecting to group {self.user_group_name}')

        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Register connection and set user online
        from messaging.ws_middleware import WebSocketConnectionTracker
        WebSocketConnectionTracker.register_connection(
            self.user.id, 
            self.channel_name
        )

        # Set user online when they connect to any page
        connection_count = WebSocketConnectionTracker.get_connection_count(self.user.id)
        if connection_count == 1:
            await self.set_user_online(True)
            print(f'[NOTIFICATIONS] User {self.user.id} marked as online')

        print(f'[NOTIFICATIONS] User {self.user.id} accepted connection')
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave user's notification group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
        
        # Unregister connection and check if user should go offline
        from messaging.ws_middleware import WebSocketConnectionTracker
        WebSocketConnectionTracker.unregister_connection(self.user.id, self.channel_name)
        
        # Only set user offline if this was the last connection
        connection_count = WebSocketConnectionTracker.get_connection_count(self.user.id)
        if connection_count == 0:
            await self.set_user_online(False)
            print(f'[NOTIFICATIONS] User {self.user.id} marked as offline')

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            # Echo back for now - can be extended for specific commands
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'data': data
            }))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    async def notification(self, event):
        """Send notification to client."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    async def conversation_update(self, event):
        """Send conversation update to client for real-time list updates."""
        print(f'[NOTIFICATIONS] Sending conversation update to user {self.user.id}: {event}')
        await self.send(text_data=json.dumps({
            'type': 'conversation_update',
            'conversation_id': event['conversation_id'],
            'message_preview': event['message_preview'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'unread_count': event['unread_count']
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to client for real-time list updates."""
        print(f'[NOTIFICATIONS] Sending typing indicator to user {self.user.id}: {event}')
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'conversation_id': event['conversation_id'],
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def user_status(self, event):
        """Send user online status to client for real-time online indicators."""
        print(f'[NOTIFICATIONS] Sending user status to user {self.user.id}: {event}')
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online'],
            'last_seen': event.get('last_seen')
        }))

    async def set_user_online(self, is_online):
        """Set user online status in Redis."""
        try:
            from pwaninet.redis_client import get_redis_client
            redis_client = get_redis_client()
            key = f'user_online:{self.user.id}'
            
            if is_online:
                # Set with 5 minute TTL
                redis_client.setex(key, 300, '1')
                print(f'[NOTIFICATIONS] Set user {self.user.id} online in Redis')
            else:
                redis_client.delete(key)
                print(f'[NOTIFICATIONS] Set user {self.user.id} offline in Redis')
        except Exception as e:
            print(f'[NOTIFICATIONS] Error setting user online status: {e}')


class FeedConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time feed updates."""

    async def connect(self):
        """Handle WebSocket connection."""
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_group_name = f"feed_{self.user.id}"

        # Join user's feed group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave user's feed group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            # Echo back for now - can be extended for specific commands
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'data': data
            }))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    async def feed_update(self, event):
        """Send feed update to client."""
        await self.send(text_data=json.dumps({
            'type': 'feed_update',
            'post': event['post']
        }))


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """Consumer for tracking online status."""

    async def connect(self):
        """Handle WebSocket connection."""
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]

        # Update user's online status
        await self.update_online_status(True)

        # Join online users group
        await self.channel_layer.group_add(
            "online_users",
            self.channel_name
        )

        await self.accept()

        # Broadcast that user is now online
        await self.channel_layer.group_send(
            "online_users",
            {
                'type': 'user_joined',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Update user's offline status
        await self.update_online_status(False)

        # Leave online users group
        await self.channel_layer.group_discard(
            "online_users",
            self.channel_name
        )

        # Broadcast that user is now offline
        await self.channel_layer.group_send(
            "online_users",
            {
                'type': 'user_left',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            # Echo back for now - can be extended for specific commands
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'data': data
            }))
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    async def user_joined(self, event):
        """Broadcast that a user joined."""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    async def user_left(self, event):
        """Broadcast that a user left."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'username': event['username']
        }))

    @database_sync_to_async
    def update_online_status(self, is_online):
        """Update user's online status in database."""
        from users.models import User
        try:
            user = User.objects.get(id=self.user.id)
            user.is_online = is_online
            user.save(update_fields=['is_online'])
        except User.DoesNotExist:
            pass
