"""
WebSocket consumers for real-time features.
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
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.user_group_name = f"notifications_{self.user.id}"

        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave user's notification group
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

    async def notification(self, event):
        """Send notification to client."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))


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


class ChatConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time messaging in conversations."""

    async def connect(self):
        """Handle WebSocket connection."""
        if self.scope["user"].is_anonymous:
            await self.close()
            return

        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.conversation_group_name = f"chat_{self.conversation_id}"

        # Check if user is a participant in the conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        # Join conversation group
        await self.channel_layer.group_add(
            self.conversation_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.conversation_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    async def handle_message(self, data):
        """Handle sending a message."""
        content = data.get('content')
        reply_to_id = data.get('reply_to')

        if not content:
            return

        # Save message to database
        message = await self.save_message(content, reply_to_id)

        # Broadcast message to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username
            }
        )

    async def handle_typing(self, data):
        """Handle typing indicator."""
        is_typing = data.get('is_typing', False)

        # Broadcast typing status to conversation group
        await self.channel_layer.group_send(
            self.conversation_group_name,
            {
                'type': 'typing_indicator',
                'user': self.user.username,
                'is_typing': is_typing
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt."""
        message_id = data.get('message_id')
        if message_id:
            await self.mark_message_as_read(message_id)

    async def chat_message(self, event):
        """Send chat message to client."""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender']
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to client."""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'user': event['user'],
            'is_typing': event['is_typing']
        }))

    @database_sync_to_async
    def check_participant(self):
        """Check if user is a participant in the conversation."""
        from messaging.models import Conversation
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content, reply_to_id=None):
        """Save message to database."""
        from messaging.models import Message, Conversation
        from django.utils import timezone

        conversation = Conversation.objects.get(id=self.conversation_id)
        reply_to = None
        if reply_to_id:
            reply_to = Message.objects.filter(id=reply_to_id).first()

        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            reply_to=reply_to
        )
        
        # Update conversation's updated_at
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        # Serialize message for WebSocket
        from messaging.serializers import MessageSerializer
        return MessageSerializer(message).data

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark message as read."""
        from messaging.models import Message
        try:
            message = Message.objects.get(id=message_id, recipient=self.user)
            message.mark_as_read()
        except Message.DoesNotExist:
            pass
