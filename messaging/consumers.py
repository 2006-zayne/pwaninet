import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth import get_user_model

from .models import Conversation, ConversationMember, Message, MessageReaction, MessageAttachment
from .serializers import MessageSerializer
from .presence import PresenceService
from .ws_middleware import WebSocketConnectionTracker, WebSocketRateLimiter
from .observability import metrics
from .services.link_preview_service import LinkPreviewService

logger = logging.getLogger(__name__)
User = get_user_model()

HEARTBEAT_INTERVAL = 25
WS_MESSAGE_RATE = 120  # messages per minute


class ChatConsumer(AsyncWebsocketConsumer):
    """
    High-performance real-time 1:1 and group WebSocket consumer.
    Provides instant message transmission, real WhatsApp-style checkmark receipts
    (Sent -> Delivered -> Read), Telegram-speed optimistic ACKs, typing indicators,
    audio recording states, and floating emoji reactions.
    """

    async def connect(self):
        self.user = self.scope.get('user')
        self.user_id = getattr(self.user, 'id', None)
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.connection_id = self.channel_name

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        is_member = await self._is_member()
        if not is_member:
            logger.warning(f"User {self.user_id} denied access to conversation {self.conversation_id}")
            await self.close(code=4003)
            return

        # Register connection tracking & presence
        WebSocketConnectionTracker.register_connection(
            self.user_id,
            self.connection_id,
            metadata={
                'conversation_id': self.conversation_id,
                'ip': self.scope.get('client', ['unknown'])[0],
            }
        )

        PresenceService.record_heartbeat(
            self.user_id,
            self.connection_id,
            metadata={'conversation_id': self.conversation_id}
        )

        # Join conversation room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Mark all pending messages sent to this user as 'delivered'
        delivered_ids = await self._mark_received_messages_delivered()
        for msg_id in delivered_ids:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_status_event',
                    'message_id': msg_id,
                    'status': 'delivered'
                }
            )

        # Broadcast online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_event',
                'user_id': self.user_id,
                'username': self.user.username,
                'is_online': True,
                'last_seen': None
            }
        )

        # Send peer's current presence status to the newly connected user
        peer_status = await self._get_peer_presence()
        if peer_status:
            await self.send(text_data=json.dumps({
                'type': 'peer_status',
                **peer_status
            }))

    async def disconnect(self, close_code):
        if not self.user_id:
            return

        # Discard from room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Unregister presence & connection
        PresenceService.remove_connection(self.user_id, self.channel_name)
        WebSocketConnectionTracker.unregister_connection(self.user_id, self.channel_name)

        is_still_online = PresenceService.is_user_online(self.user_id)
        last_seen = PresenceService.get_last_seen(self.user_id) or timezone.now()

        if not is_still_online:
            await PresenceService.persist_last_seen_to_db(self.user_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_status_event',
                    'user_id': self.user_id,
                    'username': self.user.username,
                    'is_online': False,
                    'last_seen': last_seen.isoformat() if hasattr(last_seen, 'isoformat') else str(last_seen)
                }
            )

    async def receive(self, text_data):
        """Receive message from WebSocket and dispatch action."""
        if WebSocketRateLimiter.is_rate_limited(self.user_id, self.connection_id, WS_MESSAGE_RATE):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Rate limit exceeded. Please wait a moment.'
            }))
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type')

        if msg_type == 'heartbeat':
            PresenceService.record_heartbeat(self.user_id, self.connection_id)
            await self.send(text_data=json.dumps({'type': 'pong'}))

        elif msg_type == 'chat_message':
            await self._handle_chat_message(data)

        elif msg_type == 'message_delivered':
            await self._handle_message_delivered(data)

        elif msg_type == 'read_receipt':
            await self._handle_read_receipt(data)

        elif msg_type == 'typing':
            await self._handle_typing(data)

        elif msg_type == 'recording_audio':
            await self._handle_recording_audio(data)

        elif msg_type == 'reaction':
            await self._handle_reaction(data)

        elif msg_type == 'edit_message':
            await self._handle_edit_message(data)

        elif msg_type == 'delete_message':
            await self._handle_delete_message(data)

    # -------------------------------------------------------------
    # Action Handlers
    # -------------------------------------------------------------

    async def _handle_chat_message(self, data):
        temp_id = data.get('temp_id')
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to_id')
        message_type = data.get('message_type', 'text')
        link_url = data.get('link_url')

        if not content and not data.get('attachment_url') and not data.get('attachments'):
            return

        # Save to database
        saved_msg, serialized = await self._save_message(data)
        if not saved_msg:
            return

        # 1. Send immediate ACK back to sender (Telegram instant feel)
        await self.send(text_data=json.dumps({
            'type': 'message_ack',
            'temp_id': temp_id,
            'message_id': saved_msg.id,
            'status': saved_msg.status,
            'created_at': saved_msg.created_at.isoformat()
        }))

        # 2. Broadcast message to all conversation members in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message_event',
                'message': serialized,
                'temp_id': temp_id
            }
        )

        # 3. Check if recipient is active to mark delivered automatically
        other_members = await self._get_other_members()
        any_peer_online = any(PresenceService.is_user_online(uid) for uid in other_members)
        if any_peer_online:
            await self._set_message_status(saved_msg.id, 'delivered')
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_status_event',
                    'message_id': saved_msg.id,
                    'status': 'delivered'
                }
            )

        # 4. Notify members' personal channel for conversation list updates
        preview_text = content or (f"[{message_type.capitalize()}]" if message_type != 'text' else 'New message')
        for member_id in other_members:
            unread_count = await self._get_unread_count(member_id)
            await self.channel_layer.group_send(
                f'notifications_{member_id}',
                {
                    'type': 'conversation_update',
                    'conversation_id': self.conversation_id,
                    'message_preview': preview_text,
                    'sender_name': self.user.username,
                    'timestamp': saved_msg.created_at.isoformat(),
                    'unread_count': unread_count
                }
            )

    async def _handle_message_delivered(self, data):
        message_id = data.get('message_id')
        if not message_id:
            return

        updated = await self._set_message_status(message_id, 'delivered')
        if updated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_status_event',
                    'message_id': message_id,
                    'status': 'delivered'
                }
            )

    async def _handle_read_receipt(self, data):
        message_id = data.get('message_id')
        last_id = await self._update_last_read(message_id)
        if last_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt_event',
                    'user_id': self.user_id,
                    'last_read_message_id': last_id
                }
            )

    async def _handle_typing(self, data):
        is_typing = bool(data.get('is_typing', False))
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_event',
                'user_id': self.user_id,
                'username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def _handle_recording_audio(self, data):
        is_recording = bool(data.get('is_recording', False))
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'recording_audio_event',
                'user_id': self.user_id,
                'username': self.user.username,
                'is_recording': is_recording
            }
        )

    async def _handle_reaction(self, data):
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        if not message_id or not emoji:
            return

        grouped_reactions = await self._toggle_reaction(message_id, emoji)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'reaction_event',
                'message_id': message_id,
                'reactions': grouped_reactions
            }
        )

    async def _handle_edit_message(self, data):
        message_id = data.get('message_id')
        content = data.get('content', '').strip()
        if not message_id or not content:
            return

        edited = await self._edit_message(message_id, content)
        if edited:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited_event',
                    'message_id': message_id,
                    'content': content,
                    'edited_at': edited.edited_at.isoformat()
                }
            )

    async def _handle_delete_message(self, data):
        message_id = data.get('message_id')
        if not message_id:
            return

        deleted = await self._delete_message(message_id)
        if deleted:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted_event',
                    'message_id': message_id
                }
            )

    # -------------------------------------------------------------
    # Group Broadcast Dispatches (Downlink to WebSocket)
    # -------------------------------------------------------------

    async def chat_message_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'temp_id': event.get('temp_id')
        }))

    async def message_status_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_status',
            'message_id': event['message_id'],
            'status': event['status']
        }))

    async def read_receipt_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user_id': event['user_id'],
            'last_read_message_id': event['last_read_message_id']
        }))

    async def typing_event(self, event):
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing']
            }))

    async def recording_audio_event(self, event):
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'recording_audio',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_recording': event['is_recording']
            }))

    async def user_status_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'is_online': event['is_online'],
            'last_seen': event.get('last_seen')
        }))

    async def reaction_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction_update',
            'message_id': event['message_id'],
            'reactions': event['reactions']
        }))

    async def message_edited_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'content': event['content'],
            'edited_at': event['edited_at']
        }))

    async def message_deleted_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))

    # -------------------------------------------------------------
    # Database Operations (Async-Safe)
    # -------------------------------------------------------------

    @database_sync_to_async
    def _is_member(self):
        return ConversationMember.objects.filter(
            conversation_id=self.conversation_id,
            user_id=self.user_id
        ).exists()

    @database_sync_to_async
    def _get_other_members(self):
        return list(
            ConversationMember.objects.filter(conversation_id=self.conversation_id)
            .exclude(user_id=self.user_id)
            .values_list('user_id', flat=True)
        )

    @database_sync_to_async
    def _get_peer_presence(self):
        other_member = ConversationMember.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(user_id=self.user_id).select_related('user').first()

        if not other_member:
            return None

        peer_user = other_member.user
        is_online = PresenceService.is_user_online(peer_user.id)
        last_seen = PresenceService.get_last_seen(peer_user.id)

        return {
            'user_id': peer_user.id,
            'username': peer_user.username,
            'is_online': is_online,
            'last_seen': last_seen.isoformat() if hasattr(last_seen, 'isoformat') else str(last_seen) if last_seen else None
        }

    @database_sync_to_async
    def _save_message(self, data):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            reply_to = None
            if data.get('reply_to_id'):
                reply_to = Message.objects.filter(id=data['reply_to_id'], conversation=conv).first()

            msg = Message.objects.create(
                conversation=conv,
                sender=self.user,
                content=data.get('content', ''),
                reply_to=reply_to,
                message_type=data.get('message_type', 'text'),
                global_caption=data.get('global_caption', ''),
                link_url=data.get('link_url'),
                link_title=data.get('link_title'),
                link_description=data.get('link_description'),
                link_image=data.get('link_image'),
                link_type=data.get('link_type', 'link'),
                status='sent'
            )

            # Link preview fetch if applicable
            if msg.link_url:
                try:
                    LinkPreviewService.generate_preview_for_message(msg)
                except Exception as e:
                    logger.debug(f"Link preview generation skipped: {e}")

            conv.save(update_fields=['updated_at'])
            serialized = MessageSerializer(msg).data
            return msg, serialized
        except Exception as e:
            logger.error(f"Error saving message: {e}", exc_info=True)
            return None, None

    @database_sync_to_async
    def _set_message_status(self, message_id, new_status):
        try:
            rows = Message.objects.filter(id=message_id, conversation_id=self.conversation_id).update(status=new_status)
            return rows > 0
        except Exception:
            return False

    @database_sync_to_async
    def _mark_received_messages_delivered(self):
        delivered_ids = list(
            Message.objects.filter(
                conversation_id=self.conversation_id,
                status='sent'
            ).exclude(sender_id=self.user_id).values_list('id', flat=True)
        )
        if delivered_ids:
            Message.objects.filter(id__in=delivered_ids).update(status='delivered')
        return delivered_ids

    @database_sync_to_async
    def _update_last_read(self, message_id=None):
        try:
            member = ConversationMember.objects.filter(
                conversation_id=self.conversation_id,
                user_id=self.user_id
            ).first()
            if not member:
                return None

            if message_id:
                target_msg = Message.objects.filter(id=message_id, conversation_id=self.conversation_id).first()
            else:
                target_msg = Message.objects.filter(conversation_id=self.conversation_id).order_by('-id').first()

            if target_msg:
                member.last_read_message = target_msg
                member.save(update_fields=['last_read_message'])

                # Update messages up to this id as read
                Message.objects.filter(
                    conversation_id=self.conversation_id,
                    id__lte=target_msg.id
                ).exclude(sender_id=self.user_id).update(status='read')

                return target_msg.id
            return None
        except Exception as e:
            logger.error(f"Error updating read receipt: {e}")
            return None

    @database_sync_to_async
    def _toggle_reaction(self, message_id, emoji):
        try:
            msg = Message.objects.get(id=message_id, conversation_id=self.conversation_id)
            existing = MessageReaction.objects.filter(message=msg, user=self.user, emoji=emoji).first()
            if existing:
                existing.delete()
            else:
                MessageReaction.objects.create(message=msg, user=self.user, emoji=emoji)

            # Build aggregated summary: [{'emoji': '❤️', 'count': 2, 'user_ids': [1, 2]}]
            reactions = msg.reactions.all().select_related('user')
            agg = {}
            for r in reactions:
                if r.emoji not in agg:
                    agg[r.emoji] = {'emoji': r.emoji, 'count': 0, 'user_ids': [], 'usernames': []}
                agg[r.emoji]['count'] += 1
                agg[r.emoji]['user_ids'].append(r.user.id)
                agg[r.emoji]['usernames'].append(r.user.username)
            return list(agg.values())
        except Exception as e:
            logger.error(f"Error toggling reaction: {e}")
            return []

    @database_sync_to_async
    def _edit_message(self, message_id, content):
        try:
            msg = Message.objects.get(id=message_id, conversation_id=self.conversation_id, sender=self.user)
            msg.content = content
            msg.edited_at = timezone.now()
            msg.save(update_fields=['content', 'edited_at'])
            return msg
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return None

    @database_sync_to_async
    def _delete_message(self, message_id):
        try:
            rows = Message.objects.filter(id=message_id, conversation_id=self.conversation_id, sender=self.user).update(
                is_deleted=True,
                content='This message was deleted'
            )
            return rows > 0
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

    @database_sync_to_async
    def _get_unread_count(self, user_id):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            member = conv.members.filter(user_id=user_id).first()
            if member and member.last_read_message:
                return conv.messages.filter(id__gt=member.last_read_message.id).count()
            return conv.messages.count()
        except Exception:
            return 0
