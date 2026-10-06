from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.http import JsonResponse, HttpResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import requests
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)

from .models import Conversation, ConversationMember, Message, MessageReaction, ConversationTheme, MessageAttachment
from .services.link_preview_service import LinkPreviewService
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationMemberSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReactionSerializer,
    ConversationThemeSerializer,
    ConversationThemeCreateUpdateSerializer,
    FileUploadValidator
)
from .pagination import BeforeMessageIdPagination
from .observability import metrics


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversations."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type']
    search_fields = ['name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        """Return conversations for the current user."""
        return Conversation.objects.filter(
            members__user=self.request.user
        ).distinct()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        """Create a new conversation and add the current user as member."""
        conversation = serializer.save()
        # Only add current user if not already in member_ids
        member_ids = self.request.data.get('member_ids', [])
        if self.request.user.id not in member_ids:
            ConversationMember.objects.create(
                conversation=conversation,
                user=self.request.user
            )
        return conversation

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to the conversation."""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from users.models import User
        try:
            user = User.objects.get(id=user_id)
            member, created = ConversationMember.objects.get_or_create(
                conversation=conversation,
                user=user
            )
            return Response(
                ConversationMemberSerializer(member).data,
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from the conversation."""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ConversationMember.objects.filter(
            conversation=conversation,
            user_id=user_id
        ).delete()
        return Response(
            {'status': 'member removed'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark all messages in conversation as read for current user."""
        conversation = self.get_object()
        member = conversation.members.filter(user=request.user).first()

        if not member:
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        last_message = conversation.messages.last()
        if last_message:
            member.last_read_message = last_message
            member.save()

        return Response(
            {'status': 'marked as read'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def set_public_key(self, request, pk=None):
        """Set the public key for the current user in this conversation."""
        conversation = self.get_object()
        member = conversation.members.filter(user=request.user).first()

        if not member:
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )

        public_key = request.data.get('public_key')
        if not public_key:
            return Response(
                {'error': 'public_key is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        member.public_key = public_key
        member.save()

        return Response(
            ConversationMemberSerializer(member).data,
            status=status.HTTP_200_OK
        )


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages with pagination and rate limiting."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['conversation', 'sender']
    search_fields = ['content']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    pagination_class = None  # Messages use custom pagination per view

    def get_queryset(self):
        """Return messages the user has access to with optimized queries."""
        user = self.request.user
        return Message.objects.filter(
            conversation__members__user=user
        ).select_related(
            'sender',
            'conversation',
            'reply_to'
        ).prefetch_related(
            'reactions'
        ).distinct()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MessageUpdateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """Create a new message and broadcast via WebSocket with rate limiting."""
        # Handle conversation_id from FormData for file uploads
        conversation_id = self.request.data.get('conversation_id')
        if conversation_id and not serializer.validated_data.get('conversation'):
            from .models import Conversation
            serializer.validated_data['conversation'] = Conversation.objects.get(id=conversation_id)
        
        message = serializer.save(sender=self.request.user)
        
        # Generate link preview if message contains URLs
        try:
            LinkPreviewService.generate_preview_for_message(message)
        except Exception as e:
            # Log error but don't block message creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[LINK_PREVIEW] Error generating preview: {str(e)}")
        
        # Update conversation timestamp
        message.conversation.save()
        
        # Broadcast message via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{message.conversation.id}",
            {
                'type': 'chat_message',
                'message': MessageSerializer(message).data
            }
        )
        
        return message

    def perform_update(self, serializer):
        """Update message and mark as edited."""
        from django.utils import timezone
        serializer.save(edited_at=timezone.now())

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read for the current user using ConversationMember.last_read_message."""
        message = self.get_object()
        
        # Check if user is a member of the conversation
        if not message.conversation.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update member's last read message (this replaces per-message read receipts)
        member = message.conversation.members.filter(user=request.user).first()
        if member:
            member.last_read_message = message
            member.save()
        
        return Response(
            {'status': 'marked as read', 'message_id': message.id},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def add_reaction(self, request, pk=None):
        """Add or remove a reaction to a message."""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if reaction already exists
        existing_reaction = MessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji
        ).first()
        
        if existing_reaction:
            existing_reaction.delete()
            return Response(
                {'status': 'reaction removed'},
                status=status.HTTP_200_OK
            )
        
        # Create new reaction
        reaction_obj = MessageReaction.objects.create(
            message=message,
            user=request.user,
            emoji=emoji
        )
        
        return Response(
            MessageReactionSerializer(reaction_obj).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'])
    def paginated(self, request):
        """
        Get paginated messages for a conversation using cursor-based pagination.
        Uses before_message_id cursor strategy for efficient message history loading.
        
        Query parameters:
            - conversation_id: Required ID of the conversation
            - before_message_id: Optional cursor to load messages older than this ID
            - limit: Number of messages to return (default 30, max 100)
        
        Returns:
            - results: List of messages (newest first)
            - has_more: Whether there are older messages available
            - next_cursor: The before_message_id for the next page
            - count: Number of messages in this batch
        """
        conversation_id = request.query_params.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is a member of the conversation
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            members__user=request.user
        )
        
        # Get messages for this conversation
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related(
            'sender',
            'reply_to'
        ).prefetch_related(
            'reactions'
        )
        
        # Apply cursor-based pagination
        paginator = BeforeMessageIdPagination(default_limit=30, max_limit=100)
        paginated_messages = paginator.paginate_queryset(messages, request)
        
        # Serialize paginated messages
        serializer = MessageSerializer(paginated_messages, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)


class MessageReactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing message reactions."""
    serializer_class = MessageReactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['message', 'user', 'emoji']

    def get_queryset(self):
        """Return reactions for messages the user has access to."""
        user = self.request.user
        return MessageReaction.objects.filter(
            message__conversation__members__user=user
        ).distinct()


# Template Views
@login_required
def conversation_list(request):
    """Display list of user's conversations with optimized queries."""
    # Fetch all conversations for the user with prefetched relations
    conversations = Conversation.objects.filter(
        members__user=request.user
    ).prefetch_related(
        'members__user',
        'messages__sender'
    ).annotate(
        # Optimize: get last message in one query instead of N+1
        last_msg_id=models.Max('messages__id'),
        last_msg_time=models.Max('messages__created_at')
    ).order_by('-last_msg_time').distinct()

    # Calculate read status and unread count efficiently
    conversation_data = []
    for conversation in conversations:
        # Get last message efficiently from the queryset
        last_message = conversation.messages.order_by('-created_at').first()
        
        # Get read status from conversation model (which checks if other members have read)
        read_status = None
        if last_message and last_message.sender == request.user:
            read_status = conversation.get_last_message_read_status(request.user) or 'sent'
        
        # Calculate unread count for this user
        member = conversation.members.filter(user=request.user).first()
        if member and member.last_read_message:
            unread_count = conversation.messages.filter(
                created_at__gt=member.last_read_message.created_at
            ).count()
        else:
            unread_count = conversation.messages.count()
        
        conversation_data.append({
            'conversation': conversation,
            'read_status': read_status,
            'unread_count': unread_count
        })

    from users.models import User, Follow
    from users.services.friend_suggestion_service import get_friend_suggestions_for_user
    # Only show users that the current user is following
    users = User.objects.filter(
        follower_relationships__follower=request.user
    ).exclude(id=request.user.id).distinct()
    suggested_users = get_friend_suggestions_for_user(request.user, limit=10)

    # Friends not yet messaged in direct conversations
    existing_direct_user_ids = set(ConversationMember.objects.filter(
        conversation__type='direct',
        conversation__members__user=request.user
    ).exclude(user=request.user).values_list('user_id', flat=True))

    unmessaged_friends = users.exclude(id__in=existing_direct_user_ids)

    # Detect desktop vs mobile client
    ua_string = request.META.get('HTTP_USER_AGENT', '')
    is_mobile = False
    try:
        from user_agents import parse
        user_agent = parse(ua_string)
        is_mobile = user_agent.is_mobile
    except Exception:
        is_mobile = any(k in ua_string.lower() for k in ['mobile', 'android', 'iphone', 'ipod'])

    # Desktop: hop directly into three-panel layout with empty state unless view=list requested
    if not is_mobile and request.GET.get('view') != 'list':
        from django.utils import timezone
        from datetime import timedelta
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        context = {
            'conversation': None,
            'messages': [],
            'conversation_data': conversation_data,
            'users': users,
            'unmessaged_friends': unmessaged_friends,
            'media_photos_videos': [],
            'media_docs': [],
            'media_audio': [],
            'legacy_photos_videos': [],
            'legacy_docs': [],
            'legacy_audio': [],
            'media_links': [],
            'today': today.strftime('%Y-%m-%d'),
            'yesterday': yesterday.strftime('%Y-%m-%d'),
        }
        return render(request, 'messaging/conversation_detail_refactored.html', context)

    # Get IDs of users that current user is following
    following_ids = set(Follow.objects.filter(
        follower=request.user
    ).values_list('followed_id', flat=True))

    active_conversation = request.GET.get('conversation')
    active_conversation_obj = None
    messages = []

    if active_conversation:
        active_conversation_obj = get_object_or_404(
            Conversation,
            id=active_conversation,
            members__user=request.user
        )
        messages = active_conversation_obj.messages.all().order_by('created_at')

    context = {
        'conversation_data': conversation_data,
        'users': users,
        'unmessaged_friends': unmessaged_friends,
        'suggested_users': suggested_users,
        'following_ids': following_ids,
        'active_conversation': active_conversation,
        'active_conversation_obj': active_conversation_obj,
        'messages': messages,
    }

    return render(request, 'messaging/conversation_list.html', context)



@login_required
def search_followed_users(request):
    """Search followed users for new conversation modal using HTMX."""
    from users.models import User
    search_query = request.GET.get('search', '')

    users = User.objects.filter(
        follower_relationships__follower=request.user
    ).exclude(id=request.user.id).distinct()

    if search_query:
        users = users.filter(
            username__icontains=search_query
        ) | users.filter(
            first_name__icontains=search_query
        ) | users.filter(
            last_name__icontains=search_query
        )

    return render(request, 'messaging/partials/user_search_results.html', {'users': users})


@login_required
def conversation_detail(request, conversation_id):
    """Display a specific conversation."""
    from django.utils import timezone
    from datetime import timedelta
    
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id,
        members__user=request.user
    )
    
    messages = conversation.messages.all().order_by('created_at')
    
    # Mark conversation as read
    member = conversation.members.filter(user=request.user).first()
    if member:
        last_message = messages.last()
        if last_message:
            member.last_read_message = last_message
            member.save()
    
    # Active conversation list for desktop WhatsApp left rail
    conversations = Conversation.objects.filter(
        members__user=request.user
    ).prefetch_related(
        'members__user',
        'messages__sender'
    ).annotate(
        last_msg_id=models.Max('messages__id'),
        last_msg_time=models.Max('messages__created_at')
    ).order_by('-last_msg_time').distinct()

    conversation_data = []
    for conv in conversations:
        last_msg = conv.messages.order_by('-created_at').first()
        read_status = None
        if last_msg and last_msg.sender == request.user:
            read_status = conv.get_last_message_read_status(request.user) or 'sent'
        
        mem = conv.members.filter(user=request.user).first()
        if mem and mem.last_read_message:
            unread_count = conv.messages.filter(
                created_at__gt=mem.last_read_message.created_at
            ).count()
        else:
            unread_count = conv.messages.count()
        
        conversation_data.append({
            'conversation': conv,
            'read_status': read_status,
            'unread_count': unread_count
        })

    # Pre-categorize media for the dynamic WhatsApp right media rail
    attachments = MessageAttachment.objects.filter(
        message__conversation=conversation
    ).select_related('message')
    
    media_photos_videos = attachments.filter(file_type__in=['image', 'video']).order_by('-message__created_at')
    media_docs = attachments.filter(file_type='document').order_by('-message__created_at')
    media_audio = attachments.filter(file_type='audio').order_by('-message__created_at')
    
    # Legacy attachments fallback
    legacy_attachments = messages.filter(attachment__isnull=False).exclude(attachment='')
    legacy_photos_videos = legacy_attachments.filter(attachment_type__in=['image', 'video']).order_by('-created_at')
    legacy_docs = legacy_attachments.filter(attachment_type='document').order_by('-created_at')
    legacy_audio = legacy_attachments.filter(attachment_type='audio').order_by('-created_at')
    
    media_links = messages.filter(
        models.Q(link_url__isnull=False) | models.Q(link_preview__isnull=False)
    ).exclude(link_url='').select_related('link_preview').order_by('-created_at')
    
    # Followed friends for new conversation modal in left rail
    from users.models import User
    users = User.objects.filter(
        follower_relationships__follower=request.user
    ).exclude(id=request.user.id).distinct()

    existing_direct_user_ids = set(ConversationMember.objects.filter(
        conversation__type='direct',
        conversation__members__user=request.user
    ).exclude(user=request.user).values_list('user_id', flat=True))

    unmessaged_friends = users.exclude(id__in=existing_direct_user_ids)

    # Calculate today and yesterday dates
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    context = {
        'conversation': conversation,
        'messages': messages,
        'conversation_data': conversation_data,
        'users': users,
        'unmessaged_friends': unmessaged_friends,
        'media_photos_videos': media_photos_videos,
        'media_docs': media_docs,
        'media_audio': media_audio,
        'legacy_photos_videos': legacy_photos_videos,
        'legacy_docs': legacy_docs,
        'legacy_audio': legacy_audio,
        'media_links': media_links,
        'today': today.strftime('%Y-%m-%d'),
        'yesterday': yesterday.strftime('%Y-%m-%d'),
    }

    return render(request, 'messaging/conversation_detail_refactored.html', context)


@csrf_exempt
@login_required
def create_conversation(request):
    """Create a new conversation or redirect to existing one."""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        conversation_type = request.POST.get('type', 'direct')
        
        if not user_id:
            messages.error(request, 'User ID is required.')
            return redirect('messaging:conversation_list')
        
        try:
            from users.models import User
            other_user = User.objects.get(id=user_id)
            
            # Check if conversation already exists
            existing = Conversation.get_direct_conversation_between(
                request.user, other_user
            )
            
            if existing:
                messages.info(request, 'Existing conversation found.')
                return redirect('messaging:conversation_detail', conversation_id=existing.id)
            
            # Create new conversation
            conversation = Conversation.objects.create(type=conversation_type)
            
            # Add members
            ConversationMember.objects.create(conversation=conversation, user=request.user)
            ConversationMember.objects.create(conversation=conversation, user=other_user)
            
            messages.success(request, 'Conversation created successfully.')
            return redirect('messaging:conversation_detail', conversation_id=conversation.id)
            
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            messages.error(request, f'Failed to create conversation: {str(e)}')
    
    return redirect('messaging:conversation_list')


class ConversationThemeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversation themes."""
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationThemeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['conversation']

    def get_queryset(self):
        """Return themes for the current user."""
        return ConversationTheme.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['create', 'update', 'partial_update']:
            return ConversationThemeCreateUpdateSerializer
        return ConversationThemeSerializer

    def perform_create(self, serializer):
        """Create a theme for the current user and conversation."""
        conversation_id = self.request.data.get('conversation')
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verify user is a member of this conversation
        if not conversation.members.filter(user=self.request.user).exists():
            raise PermissionError("You are not a member of this conversation")
        
        serializer.save(user=self.request.user, conversation=conversation)

    def perform_update(self, serializer):
        """Update a theme for the current user."""
        # Verify user owns this theme
        if serializer.instance.user != self.request.user:
            raise PermissionError("You can only edit your own themes")
        serializer.save()

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Apply a theme to the conversation."""
        theme = self.get_object()
        conversation = theme.conversation
        
        # Verify user is a member of this conversation
        if not conversation.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Theme is already applied since it's user-specific
        return Response({
            'message': 'Theme applied successfully',
            'theme': ConversationThemeSerializer(theme).data
        })

    @action(detail=False, methods=['get'])
    def by_conversation(self, request):
        """Get theme for a specific conversation."""
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response(
                {'error': 'conversation_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Verify user is a member of this conversation
        if not conversation.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            theme = ConversationTheme.objects.get(
                user=request.user,
                conversation=conversation
            )
            serializer = self.get_serializer(theme)
            return Response(serializer.data)
        except ConversationTheme.DoesNotExist:
            # Return default theme
            return Response({
                'theme_type': 'solid',
                'light_color': '#f8fafc',
                'dark_color': '#18191f',
                'overlay_opacity': 0.3,
                'light_overlay_color': '#ffffff',
                'dark_overlay_color': '#000000'
            })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def attachment_upload(request):
    """Handle file attachment uploads for messages."""
    try:
        file = request.FILES.get('file')
        conversation_id = request.data.get('conversation_id')
        
        if not file:
            metrics.record_upload_failure(request.user.id, 'NO_FILE', 0)
            return Response(
                {'error': 'No file provided', 'error_code': 'NO_FILE'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not conversation_id:
            metrics.record_upload_failure(request.user.id, 'NO_CONVERSATION_ID', 0)
            return Response(
                {'error': 'conversation_id is required', 'error_code': 'NO_CONVERSATION_ID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is a member of the conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.members.filter(user=request.user).exists():
            metrics.record_upload_failure(request.user.id, 'NOT_MEMBER', file.size)
            return Response(
                {'error': 'You are not a member of this conversation', 'error_code': 'NOT_MEMBER'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate file using FileUploadValidator
        is_valid, error_code, error_message, attachment_type = FileUploadValidator.validate(file)
        
        if not is_valid:
            metrics.record_upload_failure(request.user.id, error_code, file.size)
            return Response(
                {'error': error_message, 'error_code': error_code},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if this is a recorded voice note
        is_voice_note = request.data.get('is_voice_note') in ['true', 'True', True, '1', 1] or file.name.startswith('voice_')
        final_attachment_type = 'voice_note' if is_voice_note else attachment_type
        final_message_type = 'voice_note' if is_voice_note else ('audio' if attachment_type == 'audio' else 'media')

        # Create message with attachment
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            attachment=file,
            attachment_type=final_attachment_type,
            message_type=final_message_type,
            content=file.name if final_attachment_type in ['document', 'audio'] else ''
        )

        # Also create MessageAttachment for media rail indexing
        try:
            MessageAttachment.objects.create(
                message=message,
                file=message.attachment,
                file_type='audio' if is_voice_note else attachment_type,
                caption='',
                order=0,
                size=file.size
            )
        except Exception as ma_err:
            logger.warning(f"Could not create secondary MessageAttachment: {ma_err}")
        
        # Update conversation timestamp
        conversation.save()
        
        # Broadcast message via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation.id}",
            {
                'type': 'chat_message',
                'message': MessageSerializer(message).data
            }
        )
        
        return Response(
            MessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {'error': str(e), 'error_code': 'SERVER_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def process_video_attachment(uploaded_file, trim_start=0.0, trim_end=None, is_muted=False, rotation=0, is_trimmed=False):
    """
    Trims, mutes, and/or rotates a video file using ffmpeg.
    Returns (processed_file, file_size, duration).
    Falls back safely to original file if processing is not required or fails.
    """
    needs_trim = bool(is_trimmed) or (trim_start and float(trim_start) > 0.05) or (trim_end and float(trim_end) > 0.05)
    needs_mute = bool(is_muted)
    needs_rotate = bool(rotation and (int(rotation) % 360) != 0)

    if not (needs_trim or needs_mute or needs_rotate):
        return uploaded_file, uploaded_file.size, None

    in_temp_path = None
    out_temp_path = None

    try:
        import os
        import subprocess
        import tempfile
        import logging
        from django.core.files.uploadedfile import SimpleUploadedFile

        logger = logging.getLogger(__name__)

        ext = os.path.splitext(uploaded_file.name)[1].lower() or '.mp4'
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as in_temp:
            in_temp_path = in_temp.name
            for chunk in uploaded_file.chunks():
                in_temp.write(chunk)

        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as out_temp:
            out_temp_path = out_temp.name

        cmd = ['/usr/bin/ffmpeg', '-y', '-i', in_temp_path]

        start_val = max(0.0, float(trim_start)) if trim_start else 0.0
        if start_val > 0.05:
            cmd.extend(['-ss', f'{start_val:.3f}'])

        end_val = float(trim_end) if trim_end else 0.0
        if end_val > start_val:
            duration = end_val - start_val
            cmd.extend(['-t', f'{duration:.3f}'])
        elif start_val > 0.05 and not end_val:
            duration = None
        else:
            duration = None

        vf_filters = []
        if needs_rotate:
            rot = int(rotation) % 360
            if rot == 90:
                vf_filters.append('transpose=1')
            elif rot == 180:
                vf_filters.append('transpose=2,transpose=2')
            elif rot == 270:
                vf_filters.append('transpose=2')

        if vf_filters:
            cmd.extend(['-vf', ','.join(vf_filters)])

        cmd.extend(['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23'])

        if needs_mute:
            cmd.append('-an')
        else:
            cmd.extend(['-c:a', 'aac', '-b:a', '128k'])

        cmd.extend(['-movflags', '+faststart', out_temp_path])

        logger.info(f"[VIDEO_TRIM] Running: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)

        if res.returncode != 0:
            logger.error(f"[VIDEO_TRIM] FFmpeg error ({res.returncode}): {res.stderr.decode('utf-8', errors='ignore')[-400:]}")
            uploaded_file.seek(0)
            return uploaded_file, uploaded_file.size, None

        with open(out_temp_path, 'rb') as f:
            processed_data = f.read()

        out_name = os.path.splitext(uploaded_file.name)[0] + '.mp4'
        processed_file = SimpleUploadedFile(
            name=out_name,
            content=processed_data,
            content_type='video/mp4'
        )
        return processed_file, len(processed_data), duration
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"[VIDEO_TRIM] Processing exception: {e}", exc_info=True)
        uploaded_file.seek(0)
        return uploaded_file, uploaded_file.size, None
    finally:
        import os
        if in_temp_path and os.path.exists(in_temp_path):
            try:
                os.remove(in_temp_path)
            except Exception:
                pass
        if out_temp_path and os.path.exists(out_temp_path):
            try:
                os.remove(out_temp_path)
            except Exception:
                pass


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def batch_attachment_upload(request):
    """Handle batch file attachment uploads for media group messages."""
    try:
        from .serializers import MessageAttachmentCreateSerializer
        import json
        
        conversation_id = request.data.get('conversation_id')
        global_caption = request.data.get('global_caption', '')
        attachments_data = request.data.get('attachments_data')
        
        if not conversation_id:
            return Response(
                {'error': 'conversation_id is required', 'error_code': 'NO_CONVERSATION_ID'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify user is a member of the conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)
        if not conversation.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this conversation', 'error_code': 'NOT_MEMBER'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Parse attachments data if provided as JSON string
        if attachments_data and isinstance(attachments_data, str):
            try:
                attachments_data = json.loads(attachments_data)
            except json.JSONDecodeError:
                return Response(
                    {'error': 'Invalid attachments_data format', 'error_code': 'INVALID_DATA'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Get all uploaded files
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {'error': 'No files provided', 'error_code': 'NO_FILES'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate all files
        validated_attachments = []
        for idx, file in enumerate(files):
            is_valid, error_code, error_message, attachment_type = FileUploadValidator.validate(file)
            
            if not is_valid:
                return Response(
                    {'error': f'File {idx + 1}: {error_message}', 'error_code': error_code},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get metadata for this attachment if provided
            attachment_metadata = {}
            if attachments_data and idx < len(attachments_data):
                attachment_metadata = attachments_data[idx]

            final_file = file
            final_size = file.size
            final_duration = None

            if attachment_type == 'video':
                trim_start = attachment_metadata.get('trim_start', 0)
                trim_end = attachment_metadata.get('trim_end', 0)
                is_trimmed = attachment_metadata.get('is_trimmed', False)
                is_muted = attachment_metadata.get('is_muted', False)
                rotation = attachment_metadata.get('rotation', 0)

                final_file, final_size, final_duration = process_video_attachment(
                    file,
                    trim_start=trim_start,
                    trim_end=trim_end,
                    is_muted=is_muted,
                    rotation=rotation,
                    is_trimmed=is_trimmed
                )
            
            validated_attachments.append({
                'file': final_file,
                'file_type': attachment_type,
                'caption': attachment_metadata.get('caption', ''),
                'order': attachment_metadata.get('order', idx),
                'size': final_size,
                'duration': final_duration
            })
        
        # Partition validated attachments into:
        # 1. Photos & Videos (Grouped Collage or Single Media)
        # 2. Documents (Each document gets its OWN dedicated card / bubble)
        # 3. Audio (Each audio track gets its OWN dedicated bubble)
        media_group_attachments = [a for a in validated_attachments if a['file_type'] in ['image', 'video']]
        document_attachments = [a for a in validated_attachments if a['file_type'] == 'document']
        audio_attachments = [a for a in validated_attachments if a['file_type'] == 'audio']

        created_messages = []

        # 1. Handle Images & Videos
        if media_group_attachments:
            if len(media_group_attachments) == 1:
                single_att = media_group_attachments[0]
                caption_text = single_att['caption'] or global_caption or ''
                media_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    attachment=single_att['file'],
                    attachment_type=single_att['file_type'],
                    message_type='media',
                    content=caption_text,
                    global_caption=caption_text
                )
                try:
                    MessageAttachment.objects.create(
                        message=media_msg,
                        file=media_msg.attachment,
                        file_type=single_att['file_type'],
                        caption=caption_text,
                        order=0,
                        size=single_att['size'],
                        duration=single_att.get('duration')
                    )
                except Exception as ma_err:
                    logger.warning(f"Secondary MessageAttachment failed: {ma_err}")
                created_messages.append(media_msg)
            else:
                group_msg = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    global_caption=global_caption,
                    message_type='media_group',
                    content=global_caption or ''
                )
                for order_idx, att in enumerate(media_group_attachments):
                    created_att = MessageAttachment.objects.create(
                        message=group_msg,
                        file=att['file'],
                        file_type=att['file_type'],
                        caption=att['caption'],
                        order=order_idx,
                        size=att['size'],
                        duration=att.get('duration')
                    )
                    if order_idx == 0:
                        group_msg.attachment = created_att.file
                        group_msg.attachment_type = created_att.file_type
                group_msg.save(update_fields=['attachment', 'attachment_type'])
                created_messages.append(group_msg)

        # 2. Handle Documents (Each document gets its OWN card / bubble)
        for doc_att in document_attachments:
            doc_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                attachment=doc_att['file'],
                attachment_type='document',
                message_type='media',
                content=doc_att['caption'] or doc_att['file'].name
            )
            try:
                MessageAttachment.objects.create(
                    message=doc_msg,
                    file=doc_msg.attachment,
                    file_type='document',
                    caption=doc_att['caption'],
                    order=0,
                    size=doc_att['size']
                )
            except Exception as ma_err:
                logger.warning(f"Secondary MessageAttachment failed for document: {ma_err}")
            created_messages.append(doc_msg)

        # 3. Handle Audio (Each audio gets its OWN bubble)
        for audio_att in audio_attachments:
            is_vn = audio_att['file'].name.startswith('voice_')
            audio_msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                attachment=audio_att['file'],
                attachment_type='voice_note' if is_vn else 'audio',
                message_type='voice_note' if is_vn else 'audio',
                content=audio_att['caption'] or audio_att['file'].name
            )
            try:
                MessageAttachment.objects.create(
                    message=audio_msg,
                    file=audio_msg.attachment,
                    file_type='audio',
                    caption=audio_att['caption'],
                    order=0,
                    size=audio_att['size'],
                    duration=audio_att.get('duration')
                )
            except Exception as ma_err:
                logger.warning(f"Secondary MessageAttachment failed for audio: {ma_err}")
            created_messages.append(audio_msg)

        # Update conversation timestamp
        conversation.save()

        # Broadcast all created messages via WebSocket
        channel_layer = get_channel_layer()
        for msg in created_messages:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    'type': 'chat_message',
                    'message': MessageSerializer(msg).data
                }
            )

        if not created_messages:
            return Response(
                {'error': 'No messages created', 'error_code': 'NO_MESSAGES'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Return single object if 1 message created, or array if multiple
        if len(created_messages) == 1:
            return Response(
                MessageSerializer(created_messages[0]).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(
                MessageSerializer(created_messages, many=True).data,
                status=status.HTTP_201_CREATED
            )
        
    except Exception as e:
        return Response(
            {'error': str(e), 'error_code': 'SERVER_ERROR'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fetch_link_metadata(request):
    """Fetch OpenGraph metadata for a URL."""
    try:
        url = request.data.get('url')
        if not url:
            return Response(
                {'error': 'URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate URL format
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return Response(
                {'error': 'Invalid URL format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Detect link type
        link_type = detect_link_type(url)
        
        # For internal links, we can skip external fetching
        if link_type in ['internal_post', 'internal_profile']:
            # TODO: Fetch internal metadata from database
            return Response({
                'url': url,
                'title': 'Internal Link',
                'description': 'View this content',
                'image': None,
                'type': link_type
            })
        
        # Fetch page content
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text
        except requests.RequestException as e:
            return Response(
                {'error': f'Failed to fetch URL: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract OpenGraph metadata
        metadata = extract_opengraph_metadata(html, url)
        metadata['type'] = link_type
        
        return Response(metadata, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def detect_link_type(url):
    """Detect the type of link based on URL patterns."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Internal links
    if domain in ['localhost', '127.0.0.1'] or domain.endswith('.local'):
        if '/post/' in url or '/p/' in url:
            return 'internal_post'
        elif '/profile/' in url or '/u/' in url:
            return 'internal_profile'
    
    # Social media platforms
    if 'facebook.com' in domain or 'fb.com' in domain:
        return 'facebook'
    elif 'youtube.com' in domain or 'youtu.be' in domain:
        return 'youtube'
    elif 'instagram.com' in domain:
        return 'instagram'
    elif 'twitter.com' in domain or 'x.com' in domain:
        return 'twitter'
    
    return 'link'


def extract_opengraph_metadata(html, url):
    """Extract OpenGraph metadata from HTML."""
    metadata = {
        'url': url,
        'title': None,
        'description': None,
        'image': None
    }
    
    # Extract title
    title_match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not title_match:
        title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()
    
    # Extract description
    desc_match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if desc_match:
        metadata['description'] = desc_match.group(1).strip()
    
    # Extract image
    image_match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if image_match:
        image_url = image_match.group(1).strip()
        # Make image URL absolute if it's relative
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            parsed = urlparse(url)
            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
        metadata['image'] = image_url
    
    # Fallback to URL as title if no title found
    if not metadata['title']:
        metadata['title'] = url
    
    return metadata


def unread_message_count(request):
    """Return HTML for unread message count badge (similar to notifications)."""
    if not request.user or not request.user.is_authenticated:
        return HttpResponse('<i class="bi bi-chat-dots-fill"></i>')
    # Calculate total unread messages across all conversations
    total_unread = 0
    conversations = Conversation.objects.filter(members__user=request.user).prefetch_related('members', 'messages')
    
    for conversation in conversations:
        member = conversation.members.filter(user=request.user).first()
        if member and member.last_read_message:
            unread = conversation.messages.filter(
                created_at__gt=member.last_read_message.created_at
            ).count()
        else:
            # If no last_read_message, count all messages as unread
            unread = conversation.messages.count()
        total_unread += unread
    
    # Build HTML similar to notification badge
    html = '<i class="bi bi-chat-dots-fill"></i>'
    if total_unread > 0:
        html += f'''
            <span class="position-absolute top-0 end-0 translate-middle badge rounded-pill bg-danger border border-light"
                style="font-size: 0.6rem; padding: 0.35em 0.5em; min-width: 18px; text-align: center; margin-top: -2px; margin-right: -2px;">
                {total_unread}
                <span class="visually-hidden">unread messages</span>
            </span>'''
    
    return HttpResponse(html)
