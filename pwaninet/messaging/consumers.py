import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from pwaninet.redis_client import get_redis_client
from .models import Conversation, ConversationMember, Message
from .ws_middleware import WebSocketRateLimiter, WebSocketConnectionTracker

# ARCHITECTURAL RULE:
# Each WebSocket consumer must have a single source of truth file.
# Duplicate class names across modules are forbidden.
# This file contains ONLY ChatConsumer for messaging functionality.

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

        # FIX 3: Send peer's current online status to newly connected user
        # This ensures the online indicator is shown immediately on page load/reconnect
        await self.send_peer_online_status()

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
        attachment = data.get('attachment')
        attachment_type = data.get('attachment_type')
        link_url = data.get('link_url')
        link_title = data.get('link_title')
        link_description = data.get('link_description')
        link_image = data.get('link_image')
        link_type = data.get('link_type')
        
        print(f'[BACKEND] Handling chat message from user {self.user.id} in conversation {self.conversation_id}')
        temp_id = data.get('temp_id')  # Get temp_id for optimistic update matching

        # Must have either plain content, encrypted content, attachment, or link
        if not content and not encrypted_content and not attachment and not link_url:
            return

        # Create message in database
        message = await self.create_message(content, encrypted_content, is_encrypted, reply_to_id, attachment, attachment_type, link_url, link_title, link_description, link_image, link_type)

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
        
        # Update message status to 'delivered' since it was broadcast to the room
        await self.update_message_status(message['id'], 'delivered')
        
        # Broadcast conversation update to other members (not sender) for real-time list updates
        await self.broadcast_conversation_update_to_others(message)
        
        # FIX 1: Broadcast "delivered" status to other members (not the sender)
        # This ensures sent → delivered transition when receiver is online
        other_members = await self.get_other_conversation_members()
        for other_member_id in other_members:
            if other_member_id != self.user.id:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_delivered',
                        'message_id': message['id'],
                        'user_id': other_member_id,
                        'status': 'delivered'
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
        
        # Broadcast to notification groups for conversation list updates
        await self.broadcast_typing_indicator(is_typing)

    async def handle_read_receipt(self, data):
        """Handle read receipt."""
        message_id = data.get('message_id')

        if not message_id:
            return

        print(f'[BACKEND] Processing read receipt for message {message_id} from user {self.user.id}')

        # Mark message as read
        await self.mark_message_as_read(message_id)

        # Update message status to 'read'
        await self.update_message_status(message_id, 'read')

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

    async def message_delivered(self, event):
        """Send message delivered status to WebSocket."""
        # Only send to the recipient (user_id in event), not back to all room members
        if event.get('user_id') == self.user.id or not event.get('user_id'):
            # Broadcast to all in room
            await self.send(text_data=json.dumps({
                'type': 'message_delivered',
                'message_id': event['message_id'],
                'status': 'delivered'
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
    def create_message(self, content, encrypted_content, is_encrypted, reply_to_id, attachment=None, attachment_type=None, link_url=None, link_title=None, link_description=None, link_image=None, link_type=None):
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
                    reply_to=reply_to,
                    attachment=attachment,
                    attachment_type=attachment_type,
                    link_url=link_url,
                    link_title=link_title,
                    link_description=link_description,
                    link_image=link_image,
                    link_type=link_type
                )
            else:
                message = Message.objects.create(
                    conversation=conversation,
                    sender=self.user,
                    content=content,
                    reply_to=reply_to,
                    attachment=attachment,
                    attachment_type=attachment_type,
                    link_url=link_url,
                    link_title=link_title,
                    link_description=link_description,
                    link_image=link_image,
                    link_type=link_type
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

    @database_sync_to_async
    def get_other_conversation_members(self):
        """Get list of other user IDs in this conversation."""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return list(
                conversation.members.exclude(user=self.user).values_list('user_id', flat=True)
            )
        except Conversation.DoesNotExist:
            return []

    def is_peer_online(self, peer_id):
        """Check if a peer user is currently online in Redis."""
        try:
            redis_client = get_redis_client()
            key = f'user_online:{peer_id}'
            return redis_client.exists(key) == 1
        except Exception:
            return False

    async def send_peer_online_status(self):
        """Send the current peer's online status to the connected user."""
        try:
            # Get all other members in conversation
            other_members = await self.get_other_conversation_members()
            
            # For direct conversations, there should be only one other member
            if other_members:
                peer_id = other_members[0]
                is_online = self.is_peer_online(peer_id)
                
                # Send peer's current online status
                await self.send(text_data=json.dumps({
                    'type': 'user_status',
                    'user_id': peer_id,
                    'is_online': is_online,
                    'last_seen': None
                }))
                print(f'[BACKEND] Sent peer {peer_id} status (online={is_online}) to user {self.user.id}')
        except Exception as e:
            print(f'[BACKEND] Error sending peer online status: {e}')

    async def update_message_status(self, message_id, status):
        """Update message status in database."""
        try:
            from messaging.models import Message
            message = await database_sync_to_async(Message.objects.get)(id=message_id)
            message.status = status
            await database_sync_to_async(message.save)()
            print(f'[BACKEND] Updated message {message_id} status to {status}')
        except Exception as e:
            print(f'[BACKEND] Error updating message status: {e}')

    async def broadcast_conversation_update_to_others(self, message):
        """Broadcast conversation update to other members (not sender) for real-time list updates."""
        try:
            print(f'[BACKEND] Starting conversation update broadcast for conversation {self.conversation_id}')
            
            # Get conversation details for update
            conversation = await database_sync_to_async(Conversation.objects.get)(id=self.conversation_id)
            other_members = await self.get_other_conversation_members()
            
            # Only send to others, not the sender
            all_member_ids = other_members
            print(f'[BACKEND] Broadcasting to other members: {all_member_ids}')
            
            # Get message preview text
            content = message.get('content', '')
            encrypted_content = message.get('encrypted_content', '')
            preview_text = content if content else (encrypted_content[:50] + '...' if encrypted_content else 'Encrypted message')
            
            # Get sender name
            sender_name = self.user.username if self.user.username else 'Unknown'
            
            # Send update to other conversation members
            for member_id in all_member_ids:
                # Calculate unread count for this member
                member = await database_sync_to_async(conversation.members.filter(user_id=member_id).first)()
                unread_count = 0
                if member and member.last_read_message:
                    unread_count = await database_sync_to_async(
                        lambda: conversation.messages.filter(
                            created_at__gt=member.last_read_message.created_at
                        ).count()
                    )()
                elif member:
                    # If no last_read_message, count all messages as unread
                    unread_count = await database_sync_to_async(conversation.messages.count)()
                
                update_data = {
                    'type': 'conversation_update',
                    'conversation_id': self.conversation_id,
                    'message_preview': preview_text,
                    'sender_name': sender_name,
                    'timestamp': message.get('created_at'),
                    'unread_count': unread_count
                }
                
                print(f'[BACKEND] Sending conversation update to user {member_id}: {update_data}')
                await self.channel_layer.group_send(
                    f'notifications_{member_id}',
                    update_data
                )
                print(f'[BACKEND] Successfully sent conversation update to user {member_id} for conversation {self.conversation_id}')
                
        except Exception as e:
            print(f'[BACKEND] Error broadcasting conversation update: {e}')
            import traceback
            traceback.print_exc()

    async def broadcast_conversation_update(self, message):
        """Broadcast conversation update to all members for real-time list updates."""
        try:
            print(f'[BACKEND] Starting conversation update broadcast for conversation {self.conversation_id}')
            
            # Get conversation details for update
            conversation = await database_sync_to_async(Conversation.objects.get)(id=self.conversation_id)
            other_members = await self.get_other_conversation_members()
            
            # Include sender in the update list
            all_member_ids = other_members + [self.user.id]
            print(f'[BACKEND] Broadcasting to members: {all_member_ids}')
            
            # Get message preview text
            content = message.get('content', '')
            encrypted_content = message.get('encrypted_content', '')
            preview_text = content if content else (encrypted_content[:50] + '...' if encrypted_content else 'Encrypted message')
            
            # Get sender name
            sender_name = self.user.username if self.user.username else 'Unknown'
            
            # Send update to all conversation members
            for member_id in all_member_ids:
                # Calculate unread count for this member
                member = await database_sync_to_async(conversation.members.filter(user_id=member_id).first)()
                unread_count = 0
                if member and member.last_read_message:
                    unread_count = await database_sync_to_async(
                        lambda: conversation.messages.filter(
                            created_at__gt=member.last_read_message.created_at
                        ).count()
                    )()
                elif member:
                    # If no last_read_message, count all messages as unread
                    unread_count = await database_sync_to_async(conversation.messages.count)()
                
                update_data = {
                    'type': 'conversation_update',
                    'conversation_id': self.conversation_id,
                    'message_preview': preview_text,
                    'sender_name': sender_name,
                    'timestamp': message.get('created_at'),
                    'unread_count': unread_count
                }
                
                print(f'[BACKEND] Sending conversation update to user {member_id}: {update_data}')
                await self.channel_layer.group_send(
                    f'notifications_{member_id}',
                    update_data
                )
                print(f'[BACKEND] Successfully sent conversation update to user {member_id} for conversation {self.conversation_id}')
                
        except Exception as e:
            print(f'[BACKEND] Error broadcasting conversation update: {e}')
            import traceback
            traceback.print_exc()

    async def broadcast_typing_indicator(self, is_typing):
        """Broadcast typing indicator to all conversation members for list updates."""
        try:
            print(f'[BACKEND] Starting typing indicator broadcast for conversation {self.conversation_id}, typing: {is_typing}')
            
            # Get conversation details
            conversation = await database_sync_to_async(Conversation.objects.get)(id=self.conversation_id)
            other_members = await self.get_other_conversation_members()
            
            # Include sender in the update list (except sender doesn't need to see their own typing)
            all_member_ids = other_members  # Only send to others, not self
            print(f'[BACKEND] Broadcasting typing indicator to members: {all_member_ids}')
            
            # Get sender name
            sender_name = self.user.username if self.user.username else 'Unknown'
            
            # Send typing indicator to all other conversation members
            for member_id in all_member_ids:
                typing_data = {
                    'type': 'typing_indicator',
                    'conversation_id': self.conversation_id,
                    'user_id': self.user.id,
                    'username': sender_name,
                    'is_typing': is_typing
                }
                
                print(f'[BACKEND] Sending typing indicator to user {member_id}: {typing_data}')
                await self.channel_layer.group_send(
                    f'notifications_{member_id}',
                    typing_data
                )
                
                if is_typing:
                    print(f'[BACKEND] Successfully sent typing indicator to user {member_id} for conversation {self.conversation_id}')
                else:
                    print(f'[BACKEND] Successfully sent typing stopped indicator to user {member_id} for conversation {self.conversation_id}')
                    
        except Exception as e:
            print(f'[BACKEND] Error broadcasting typing indicator: {e}')
            import traceback
            traceback.print_exc()

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
