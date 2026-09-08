import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from pwaninet.redis_client import get_redis_client
from .models import Group, Membership, GroupMessage

User = get_user_model()

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL = 30
MESSAGE_TIMEOUT = 5  # seconds to wait for message processing
WS_MESSAGE_RATE = 100  # messages per minute


# Simple connection tracking without messaging dependency
class SimpleConnectionTracker:
    _connections = {}

    @classmethod
    def register_connection(cls, user_id, connection_id, metadata=None):
        cls._connections[(user_id, connection_id)] = {
            'metadata': metadata or {},
            'connected_at': asyncio.get_event_loop().time()
        }
        return True

    @classmethod
    def unregister_connection(cls, user_id, connection_id):
        cls._connections.pop((user_id, connection_id), None)

    @classmethod
    def get_connection_count(cls, user_id):
        return sum(1 for (uid, _) in cls._connections.keys() if uid == user_id)


# Simple presence tracking without messaging dependency
class SimplePresenceService:
    _heartbeats = {}

    @classmethod
    def record_heartbeat(cls, user_id, connection_id, metadata=None):
        cls._heartbeats[(user_id, connection_id)] = {
            'timestamp': asyncio.get_event_loop().time(),
            'metadata': metadata or {}
        }

    @classmethod
    def is_user_online(cls, user_id):
        current_time = asyncio.get_event_loop().time()
        for (uid, cid), data in cls._heartbeats.items():
            if uid == user_id and (current_time - data['timestamp']) < 120:  # 2 minutes timeout
                return True
        return False


class GroupChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time group chat with heartbeat."""

    async def connect(self):
        """Handle WebSocket connection with heartbeat task and rate limiting."""
        self.user = self.scope.get('user')
        self.user_id = getattr(self.user, "id", None)

        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'group_{self.group_id}'
        self.heartbeat_task = None
        self.connection_id = self.channel_name

        print(f"[BACKEND] Group chat WebSocket connection attempt from user {self.user_id} to group {self.group_id}")

        if not self.user or not self.user.is_authenticated:
            print("[BACKEND] Unauthenticated user, closing connection")
            await self.close()
            return

        is_member = await self.is_group_member()

        if not is_member:
            print(f"[BACKEND] User {self.user_id} is not a member, closing connection")
            await self.close()
            return

        tracked = SimpleConnectionTracker.register_connection(
            self.user_id,
            self.connection_id,
            metadata={
                'group_id': self.group_id,
                'ip': self.scope.get('client', ['unknown'])[0],
            }
        )

        if not tracked:
            print("[BACKEND] Connection not tracked, closing")
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        try:
            await self.accept()
        except RuntimeError as e:
            print(f"[BACKEND] Error accepting WebSocket connection: {e}")
            await self.close()
            return

        # Record initial heartbeat for this connection
        SimplePresenceService.record_heartbeat(
            self.user_id,
            self.connection_id,
            metadata={
                'group_id': self.group_id,
                'ip': self.scope.get('client', ['unknown'])[0],
            }
        )

        connection_count = SimpleConnectionTracker.get_connection_count(self.user_id)

        # Broadcast user online status based on heartbeat freshness
        is_online = SimplePresenceService.is_user_online(self.user_id)
        if is_online:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user_id,
                    'username': self.user.username,
                    'online': True
                }
            )

        print(f"[BACKEND] Group chat WebSocket connection accepted for user {self.user_id} in group {self.group_id}")

    async def is_group_member(self):
        """Check if user is an approved member of the group."""
        try:
            membership = await database_sync_to_async(Membership.objects.get)(
                user_id=self.user_id,
                group_id=self.group_id,
                status='APPROVED'
            )
            return True
        except Membership.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        print(f"[BACKEND] Group chat WebSocket disconnect for user {self.user_id} from group {self.group_id}")

        # Remove from channel group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Unregister connection
        SimpleConnectionTracker.unregister_connection(self.user_id, self.connection_id)

        # Check if user is still online (has other connections)
        is_online = SimplePresenceService.is_user_online(self.user_id)
        if not is_online:
            # Broadcast offline status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status',
                    'user_id': self.user_id,
                    'username': self.user.username,
                    'online': False
                }
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'heartbeat':
                # Handle heartbeat
                SimplePresenceService.record_heartbeat(
                    self.user_id,
                    self.connection_id,
                    metadata={
                        'group_id': self.group_id,
                        'ip': self.scope.get('client', ['unknown'])[0],
                    }
                )
                await self.send_json({'type': 'heartbeat_ack'})

            elif message_type == 'chat_message':
                # Handle chat message
                await self.handle_chat_message(data)

            elif message_type == 'typing':
                # Handle typing indicator
                await self.handle_typing_indicator(data)

        except json.JSONDecodeError:
            print(f"[BACKEND] Invalid JSON received from user {self.user_id}")
        except Exception as e:
            print(f"[BACKEND] Error processing message: {e}")

    async def handle_chat_message(self, data):
        """Handle chat message."""
        content = data.get('content')
        message_type = data.get('message_type', 'text')

        if not content and message_type == 'text':
            return

        # Create message
        message = await database_sync_to_async(GroupMessage.objects.create)(
            group_id=self.group_id,
            sender_id=self.user_id,
            content=content,
            message_type=message_type
        )

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'group_message',
                'message': {
                    'id': message.id,
                    'group_id': message.group_id,
                    'sender_id': message.sender_id,
                    'sender_username': self.user.username,
                    'content': message.content,
                    'message_type': message.message_type,
                    'created_at': message.created_at.isoformat(),
                    'status': message.status
                }
            }
        )

    async def handle_typing_indicator(self, data):
        """Handle typing indicator."""
        is_typing = data.get('typing', False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user_id,
                'username': self.user.username,
                'typing': is_typing
            }
        )

    async def group_message(self, event):
        """Handle group message broadcast."""
        await self.send_json({
            'type': 'chat_message',
            'message': event['message']
        })

    async def user_status(self, event):
        """Handle user status broadcast."""
        await self.send_json({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'online': event['online']
        })

    async def typing_indicator(self, event):
        """Handle typing indicator broadcast."""
        await self.send_json({
            'type': 'typing_indicator',
            'user_id': event['user_id'],
            'username': event['username'],
            'typing': event['typing']
        })

    async def group_reaction(self, event):
        """Handle reaction broadcast."""
        await self.send_json({
            'type': 'reaction',
            'message_id': event['message_id'],
            'reaction': event['reaction']
        })

    async def member_evicted(self, event):
        """Handle eviction of a member from group chat."""
        if str(event.get('user_id')) == str(self.user_id):
            await self.send_json({
                'type': 'evicted',
                'reason': event.get('reason', 'You are no longer a member of this group.')
            })
            await self.close(code=4003)


def evict_group_member_socket(group_id, user_id, reason="Removed from group"):
    """
    Broadcast eviction message to group channel layer to disconnect evicted member.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'group_{group_id}',
                {
                    'type': 'member_evicted',
                    'user_id': user_id,
                    'reason': reason,
                }
            )
    except Exception as e:
        print(f"Error evicting socket for user {user_id}: {e}")

