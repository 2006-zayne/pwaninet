from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Conversation, ConversationMember, Message, MessageRead, MessageReaction, ConversationTheme
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationMemberSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReadSerializer,
    MessageReactionSerializer,
    ConversationThemeSerializer,
    ConversationThemeCreateUpdateSerializer
)


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
            'reactions',
            'read_receipts'
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
        """Mark a message as read for the current user."""
        message = self.get_object()
        
        # Check if user is a member of the conversation
        if not message.conversation.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You are not a member of this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create or update read receipt
        read_receipt, created = MessageRead.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        # Update member's last read message
        member = message.conversation.members.filter(user=request.user).first()
        if member:
            member.last_read_message = message
            member.save()
        
        return Response(
            MessageReadSerializer(read_receipt).data,
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
        'messages__sender',
        'messages__read_receipts'
    ).annotate(
        # Optimize: get last message in one query instead of N+1
        last_msg_id=models.Max('messages__id')
    ).distinct()

    # Calculate read status efficiently
    conversation_data = []
    for conversation in conversations:
        # Get last message efficiently from the queryset
        last_message = conversation.messages.order_by('-created_at').first()
        
        # Check if last message is read by current user
        read_status = 'sent'  # Default
        if last_message and last_message.sender != request.user:
            # Check if current user has read this message
            if last_message.read_receipts.filter(user=request.user).exists():
                read_status = 'read'
            else:
                read_status = 'delivered'
        
        conversation_data.append({
            'conversation': conversation,
            'read_status': read_status
        })

    from users.models import User, Follow
    from users.services.friend_suggestion_service import get_friend_suggestions_for_user
    # Only show users that the current user is following
    users = User.objects.filter(
        follower_relationships__follower=request.user
    ).exclude(id=request.user.id).distinct()
    suggested_users = get_friend_suggestions_for_user(request.user, limit=10)

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
    
    # Calculate today and yesterday dates
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    context = {
        'conversation': conversation,
        'messages': messages,
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

