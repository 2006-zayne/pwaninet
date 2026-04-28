import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, ConversationMember, Message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat in conversations."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if user is a member of the conversation
        is_member = await self.is_conversation_member()
        if not is_member:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Set user online in Redis
        await self.set_user_online(True)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Set user offline in Redis
        await self.set_user_online(False)

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            pass

    async def handle_chat_message(self, data):
        """Handle incoming chat message."""
        content = data.get('content')
        reply_to_id = data.get('reply_to')

        if not content:
            return

        # Create message in database
        message = await self.create_message(content, reply_to_id)

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

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

        # Mark message as read
        await self.mark_message_as_read(message_id)

        # Broadcast to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'message_id': message_id,
                'user_id': self.user.id
            }
        )

    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'message',
            'data': message
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'user_id': event['user_id']
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
    def create_message(self, content, reply_to_id):
        """Create a new message in the database."""
        try:
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

    async def set_user_online(self, is_online):
        """Set user online status in Redis."""
        try:
            redis_client = redis.Redis(
                host='127.0.0.1',
                port=6379,
                db=0,
                decode_responses=True
            )
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
        """Set user online status in Redis."""
        try:
            redis_client = redis.Redis(
                host='127.0.0.1',
                port=6379,
                db=0,
                decode_responses=True
            )
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
        """Get list of online users from Redis."""
        try:
            redis_client = redis.Redis(
                host='127.0.0.1',
                port=6379,
                db=0,
                decode_responses=True
            )
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
