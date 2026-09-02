from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Group, Membership, MembershipRole, MembershipStatus, JoinPolicy,
    EditPermission, InvitePermission, Announcement,
    GroupMessage, GroupMessageAttachment, GroupMessageReaction
)
from .serializers import (
    GroupSerializer, GroupCreateSerializer, MembershipSerializer,
    MembershipCreateSerializer, MembershipActionSerializer, RoleAssignmentSerializer,
    AnnouncementSerializer, AnnouncementCreateSerializer, AnnouncementUpdateSerializer,
    GroupMessageSerializer, GroupMessageCreateSerializer,
    GroupMessageAttachmentSerializer, GroupMessageReactionSerializer
)
from .permissions import (
    CanManageGroup, CanManageMembership, CanJoinOfficialGroup,
    IsApprovedMember, IsGroupAdmin, CanViewAnnouncement, CanCreateAnnouncement,
    CanEditAnnouncement, CanDeleteAnnouncement
)
from posts.models import Post, Like
from users.models import User
from groups.forms import GroupForm, GroupDetailsForm, RoleAssignmentForm, GroupPrivacyForm
from groups.services.group_notification_service import (
    send_group_join_request_notification,
    send_group_approved_notification,
    send_group_rejected_notification,
    send_group_welcome_notification,
    send_group_invite_notification
)
from notifications.services.notification_service import get_cached_unread_count, get_group_unread_counts
from notifications.models import NotificationObject
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from users.models import Follow


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing groups.
    """
    permission_classes = [IsAuthenticated]
    queryset = Group.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupCreateSerializer
        return GroupSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageGroup()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], url_path='join')
    def join(self, request, pk=None):
        """
        POST /groups/{id}/join/
        Request to join a group.
        """
        group = self.get_object()
        
        # Check official group restrictions
        if group.is_official and group.course and group.year:
            if request.user.course != group.course or request.user.year != group.year:
                return Response(
                    {'detail': 'You can only join official groups that match your course and year.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Check if already has membership
        if Membership.objects.filter(user=request.user, group=group).exists():
            return Response(
                {'detail': 'You already have a membership request for this group.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine status based on join policy
        if group.join_policy == JoinPolicy.OPEN:
            membership_status = MembershipStatus.APPROVED
        elif group.join_policy == JoinPolicy.APPROVAL:
            membership_status = MembershipStatus.PENDING
        elif group.join_policy == JoinPolicy.INVITE_ONLY:
            return Response(
                {'detail': 'This group is invite-only.'},
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            membership_status = MembershipStatus.PENDING
        
        membership = Membership.objects.create(
            user=request.user,
            group=group,
            role=MembershipRole.MEMBER,
            status=membership_status
        )
        
        # Send admin notifications for pending requests
        if membership_status == MembershipStatus.PENDING:
            send_group_join_request_notification(request.user, group)
        
        return Response({
            'status': membership_status,
            'message': 'Join request sent' if membership_status == MembershipStatus.PENDING else 'Joined successfully'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='approve/(?P<user_id>[^/.]+)')
    def approve(self, request, pk=None, user_id=None):
        """
        POST /groups/{id}/approve/{user_id}/
        Approve a join request (admin only).
        """
        group = self.get_object()
        
        # Check if user is admin
        try:
            admin_membership = Membership.objects.get(
                user=request.user,
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'Only admins can approve join requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the membership to approve
        try:
            membership = Membership.objects.get(
                user_id=user_id,
                group=group,
                status=MembershipStatus.PENDING
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'No pending membership request found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership.status = MembershipStatus.APPROVED
        membership.save()
        
        # Send welcome notification to the approved user
        send_group_approved_notification(membership.user, group, request.user)
        
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='reject/(?P<user_id>[^/.]+)')
    def reject(self, request, pk=None, user_id=None):
        """
        POST /groups/{id}/reject/{user_id}/
        Reject a join request (admin only).
        """
        group = self.get_object()
        
        # Check if user is admin
        try:
            admin_membership = Membership.objects.get(
                user=request.user,
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'Only admins can reject join requests.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the membership to reject
        try:
            membership = Membership.objects.get(
                user_id=user_id,
                group=group,
                status=MembershipStatus.PENDING
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'No pending membership request found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        membership.status = MembershipStatus.REJECTED
        membership.save()
        
        # Send rejection notification to the user
        send_group_rejected_notification(membership.user, group, request.user)
        
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='assign-role')
    def assign_role(self, request, pk=None):
        """
        POST /groups/{id}/assign-role/
        Assign a role to a member (admin only).
        Enforces max 5 admins per group constraint.
        """
        group = self.get_object()
        
        # Check if user is admin
        try:
            admin_membership = Membership.objects.get(
                user=request.user,
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'Only admins can assign roles.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RoleAssignmentSerializer(
            data=request.data,
            context={'request': request, 'group_id': group.id}
        )
        serializer.is_valid(raise_exception=True)
        
        membership = serializer.validated_data['membership']
        new_role = serializer.validated_data['role']
        
        # Cannot demote yourself from admin
        if membership.user == request.user and membership.role == MembershipRole.ADMIN:
            return Response(
                {'detail': 'You cannot change your own admin role.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.role = new_role
        membership.save()
        
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'], url_path='members')
    def members(self, request, pk=None):
        """
        GET /groups/{id}/members/
        List all members of a group.
        """
        group = self.get_object()
        memberships = group.memberships.filter(status=MembershipStatus.APPROVED)
        serializer = MembershipSerializer(memberships, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='leave')
    def leave(self, request, pk=None):
        """
        POST /groups/{id}/leave/
        Leave a group.
        """
        group = self.get_object()

        try:
            membership = Membership.objects.get(
                user=request.user,
                group=group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'You are not an approved member of this group.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is the last admin
        if membership.role == MembershipRole.ADMIN:
            admin_count = Membership.objects.filter(
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            ).count()

            if admin_count == 1:
                # Find potential successors
                moderators = Membership.objects.filter(
                    group=group,
                    role=MembershipRole.MODERATOR,
                    status=MembershipStatus.APPROVED
                ).select_related('user')[:3]

                members = Membership.objects.filter(
                    group=group,
                    role=MembershipRole.MEMBER,
                    status=MembershipStatus.APPROVED
                ).select_related('user').order_by('-id')[:5]

                successors = []
                for mod in moderators:
                    successors.append({
                        'id': mod.user.id,
                        'username': mod.user.username,
                        'name': f"{mod.user.first_name or ''} {mod.user.last_name or ''}".strip(),
                        'role': 'MODERATOR',
                        'priority': 1
                    })

                for mem in members:
                    successors.append({
                        'id': mem.user.id,
                        'username': mem.user.username,
                        'name': f"{mem.user.first_name or ''} {mem.user.last_name or ''}".strip(),
                        'role': 'MEMBER',
                        'priority': 2
                    })

                return Response({
                    'is_last_admin': True,
                    'detail': 'You are the last admin. Please assign a successor before leaving.',
                    'successors': successors
                }, status=status.HTTP_403_FORBIDDEN)

        membership.delete()
        return Response(
            {'detail': 'You have left the group.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='photos/(?P<photo_type>[^/.]+)/like')
    def photo_like(self, request, pk=None, photo_type=None):
        """
        POST /groups/{id}/photos/{photo_type}/like/
        Like or unlike a group's profile or cover photo.
        """
        group = self.get_object()
        
        # Check if user is an approved member
        try:
            Membership.objects.get(
                user=request.user,
                group=group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'You must be an approved member to like group photos.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate photo type
        if photo_type not in ['group', 'cover']:
            return Response(
                {'detail': 'Invalid photo type. Must be group or cover.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if photo exists
        if photo_type == 'cover' and not group.cover_photo:
            return Response(
                {'detail': 'This group does not have a cover photo.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from .models import GroupPhotoLike
        like, created = GroupPhotoLike.objects.get_or_create(
            user=request.user,
            group=group,
            photo_type=photo_type
        )
        
        likes_count = GroupPhotoLike.objects.filter(
            group=group,
            photo_type=photo_type
        ).count()
        
        if created:
            return Response(
                {'detail': 'Photo liked.', 'likes_count': likes_count},
                status=status.HTTP_201_CREATED
            )
        else:
            like.delete()
            return Response(
                {'detail': 'Photo unliked.', 'likes_count': likes_count},
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['post'], url_path='assign-and-leave')
    def assign_and_leave(self, request, pk=None):
        """
        POST /groups/{id}/assign-and-leave/
        Assign a new admin and then leave the group.
        Used when the last admin wants to leave.
        """
        group = self.get_object()

        # Check if user is admin
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'Only admins can use this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the successor user_id
        successor_id = request.data.get('successor_id')
        if not successor_id:
            return Response(
                {'detail': 'successor_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the successor membership
        try:
            successor_membership = Membership.objects.get(
                user_id=successor_id,
                group=group,
                status=MembershipStatus.APPROVED
            )
        except Membership.DoesNotExist:
            return Response(
                {'detail': 'Successor is not a member of this group.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Promote successor to admin
        successor_membership.role = MembershipRole.ADMIN
        successor_membership.save()

        # Leave the group
        membership.delete()

        return Response(
            {'detail': f'Admin role transferred to {successor_membership.user.username}. You have left the group.'},
            status=status.HTTP_200_OK
        )


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing group announcements.
    """
    permission_classes = [IsAuthenticated]
    queryset = Announcement.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return AnnouncementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AnnouncementUpdateSerializer
        return AnnouncementSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), CanCreateAnnouncement()]
        elif self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), CanEditAnnouncement()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), CanDeleteAnnouncement()]
        elif self.action in ['retrieve', 'list']:
            return [IsAuthenticated(), CanViewAnnouncement()]
        return super().get_permissions()

    def get_queryset(self):
        """
        Filter announcements by group_id from URL.
        Use select_related to avoid N+1 queries.
        """
        queryset = super().get_queryset()
        group_id = self.kwargs.get('group_id')
        
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Optimize queries
        queryset = queryset.select_related('author', 'group')
        
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create an announcement for a group.
        """
        group_id = self.kwargs.get('group_id')
        if not group_id:
            return Response(
                {'detail': 'group_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'group_id': group_id}
        )
        
        # Handle validation errors
        if not serializer.is_valid():
            error_messages = []
            for field, errors in serializer.errors.items():
                for error in errors:
                    if isinstance(error, str):
                        error_messages.append(f"{field.replace('_', ' ').title()}: {error}")
                    else:
                        error_messages.append(f"{field.replace('_', ' ').title()}: {str(error)}")
            
            error_detail = '; '.join(error_messages) if error_messages else 'Validation failed'
            return Response(
                {'detail': error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        
        # Return HTML for HTMX requests
        if request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            group = serializer.instance.group
            announcements = Announcement.objects.filter(
                group=group
            ).select_related('author').prefetch_related('attachments').order_by('-is_pinned', '-created_at')
            
            pinned_announcements = [a for a in announcements if a.is_pinned]
            all_announcements = [a for a in announcements if not a.is_pinned]
            
            # Get user membership for role display
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                is_admin = membership.role == MembershipRole.ADMIN
            except Membership.DoesNotExist:
                is_admin = False
            
            html = render_to_string('groups/partials/announcement_list.html', {
                'pinned_announcements': pinned_announcements,
                'all_announcements': all_announcements,
                'is_admin': is_admin,
            })
            return HttpResponse(html, content_type='text/html')
        
        return Response(
            AnnouncementSerializer(serializer.instance).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """
        Update an announcement.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        # Handle validation errors
        if not serializer.is_valid():
            error_messages = []
            for field, errors in serializer.errors.items():
                for error in errors:
                    if isinstance(error, str):
                        error_messages.append(f"{field.replace('_', ' ').title()}: {error}")
                    else:
                        error_messages.append(f"{field.replace('_', ' ').title()}: {str(error)}")
            
            error_detail = '; '.join(error_messages) if error_messages else 'Validation failed'
            return Response(
                {'detail': error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_update(serializer)
        
        # Return HTML for HTMX requests
        if request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            group = instance.group
            announcements = Announcement.objects.filter(
                group=group
            ).select_related('author').prefetch_related('attachments').order_by('-is_pinned', '-created_at')
            
            pinned_announcements = [a for a in announcements if a.is_pinned]
            all_announcements = [a for a in announcements if not a.is_pinned]
            
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                is_admin = membership.role == MembershipRole.ADMIN
            except Membership.DoesNotExist:
                is_admin = False
            
            html = render_to_string('groups/partials/announcement_list.html', {
                'pinned_announcements': pinned_announcements,
                'all_announcements': all_announcements,
                'is_admin': is_admin,
            })
            return HttpResponse(html, content_type='text/html')
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete an announcement.
        """
        instance = self.get_object()
        group = instance.group
        self.perform_destroy(instance)
        
        # Return HTML for HTMX requests
        if request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            announcements = Announcement.objects.filter(
                group=group
            ).select_related('author').prefetch_related('attachments').order_by('-is_pinned', '-created_at')
            
            pinned_announcements = [a for a in announcements if a.is_pinned]
            all_announcements = [a for a in announcements if not a.is_pinned]
            
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                is_admin = membership.role == MembershipRole.ADMIN
            except Membership.DoesNotExist:
                is_admin = False
            
            html = render_to_string('groups/partials/announcement_list.html', {
                'pinned_announcements': pinned_announcements,
                'all_announcements': all_announcements,
                'is_admin': is_admin,
            })
            return HttpResponse(html, content_type='text/html')
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='pin')
    def pin(self, request, pk=None, group_id=None):
        """
        Pin an announcement (admin only).
        """
        announcement = self.get_object()
        
        # Check permission
        permission = CanEditAnnouncement()
        if not permission.has_object_permission(request, self, announcement):
            return Response(
                {'detail': 'Only admins can pin announcements.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        announcement.is_pinned = True
        announcement.save()
        
        # Return HTML for HTMX requests
        if request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            group = announcement.group
            announcements = Announcement.objects.filter(
                group=group
            ).select_related('author').prefetch_related('attachments').order_by('-is_pinned', '-created_at')
            
            pinned_announcements = [a for a in announcements if a.is_pinned]
            all_announcements = [a for a in announcements if not a.is_pinned]
            
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                is_admin = membership.role == MembershipRole.ADMIN
            except Membership.DoesNotExist:
                is_admin = False
            
            html = render_to_string('groups/partials/announcement_list.html', {
                'pinned_announcements': pinned_announcements,
                'all_announcements': all_announcements,
                'is_admin': is_admin,
            })
            return HttpResponse(html, content_type='text/html')
        
        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='unpin')
    def unpin(self, request, pk=None, group_id=None):
        """
        Unpin an announcement (admin only).
        """
        announcement = self.get_object()
        
        # Check permission
        permission = CanEditAnnouncement()
        if not permission.has_object_permission(request, self, announcement):
            return Response(
                {'detail': 'Only admins can unpin announcements.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        announcement.is_pinned = False
        announcement.save()
        
        # Return HTML for HTMX requests
        if request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            group = announcement.group
            announcements = Announcement.objects.filter(
                group=group
            ).select_related('author').prefetch_related('attachments').order_by('-is_pinned', '-created_at')
            
            pinned_announcements = [a for a in announcements if a.is_pinned]
            all_announcements = [a for a in announcements if not a.is_pinned]
            
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                is_admin = membership.role == MembershipRole.ADMIN
            except Membership.DoesNotExist:
                is_admin = False
            
            html = render_to_string('groups/partials/announcement_list.html', {
                'pinned_announcements': pinned_announcements,
                'all_announcements': all_announcements,
                'is_admin': is_admin,
            })
            return HttpResponse(html, content_type='text/html')
        
        return Response(
            AnnouncementSerializer(announcement).data,
            status=status.HTTP_200_OK
        )


# ============================================================================
# DJANGO WEB VIEWS
# ============================================================================

@login_required
def groups_dashboard(request):
    from groups.queries.group_queries import get_following_ids
    
    # Get search query
    query = request.GET.get('q', '').strip()
    
    # Save search to session if query exists
    if query:
        recent_searches = request.session.get('recent_group_searches', [])
        # Add query if not already in recent searches
        if query not in recent_searches:
            recent_searches.insert(0, query)
            # Keep only last 5 searches
            recent_searches = recent_searches[:5]
            request.session['recent_group_searches'] = recent_searches
    
    user_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.APPROVED)
    pending_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.PENDING)
    
    # Get suggested groups based on who user follows
    following_ids = get_following_ids(request.user)
    suggested_groups = Group.objects.filter(
        memberships__user_id__in=following_ids,
        memberships__status=MembershipStatus.APPROVED
    ).exclude(memberships__user=request.user).annotate(
        member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))
    )
    
    # Apply search filter if query exists (before slicing)
    if query:
        suggested_groups = suggested_groups.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    # Apply ordering and slicing after filtering
    suggested_groups = suggested_groups.order_by('-member_count')[:20]
    
    user_group_ids = set(user_groups.values_list('id', flat=True))
    pending_group_ids = set(pending_groups.values_list('id', flat=True))
    
    # Get unread notification counts for suggested groups
    suggested_group_ids = list(suggested_groups.values_list('id', flat=True))
    group_unread_counts = get_group_unread_counts(request.user, suggested_group_ids)
    
    # Get recent searches from session
    recent_searches = request.session.get('recent_group_searches', [])
    
    context = {
        'user_groups': user_groups,
        'all_groups': suggested_groups,
        'user_group_ids': user_group_ids,
        'pending_group_ids': pending_group_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
        'group_unread_counts': group_unread_counts,
        'query': query,
        'recent_searches': recent_searches,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'groups/partials/groups_dashboard_navigation_partial.html', context)

    return render(request, 'groups/groups_dashboard.html', context)



@login_required
def groups_detail_view(request, group_id):
    from groups.services.group_service import build_group_detail_context
    group = get_object_or_404(Group.objects.annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))), id=group_id)
    query = request.GET.get('search_user', '')
    page = int(request.GET.get('page', 1))
    context = build_group_detail_context(request.user, group, query, page)
    liked_post_ids = set(Like.objects.filter(user=request.user, post__in=context['posts']).values_list('post_id', flat=True))
    context['liked_post_ids'] = liked_post_ids
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    
    # Check if HTMX request for more posts
    if request.headers.get('HX-Request'):
        return render(request, 'posts/partials/post_cards_list.html', {
            'posts': context['posts'],
            'has_more_posts': context['has_next'],
            'liked_post_ids': liked_post_ids,
        })
    
    return render(request, 'groups/groups_detail.html', context)


@login_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            Membership.objects.create(group=group, user=request.user, role=MembershipRole.ADMIN, status=MembershipStatus.APPROVED)
            messages.success(request, f'Squad "{group.name}" created successfully.')
            return redirect('groups:groups_detail', group_id=group.id)
    else:
        form = GroupForm()
    return render(request, 'groups/create_group.html', {'form': form})


# ============================================================================
# GROUP CHAT API VIEWS
# ============================================================================

class GroupMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing group messages"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['group', 'message_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return messages for groups the user is a member of"""
        user_groups = Group.objects.filter(
            memberships__user=self.request.user,
            memberships__status=MembershipStatus.APPROVED
        )
        return GroupMessage.objects.filter(group__in=user_groups).select_related(
            'sender', 'reply_to'
        ).prefetch_related('attachments', 'reactions')

    def get_serializer_class(self):
        if self.action == 'create':
            return GroupMessageCreateSerializer
        return GroupMessageSerializer

    def perform_create(self, serializer):
        """Create a new message and broadcast via WebSocket"""
        group_id = self.kwargs.get('group_id')
        message = serializer.save(
            group_id=group_id,
            sender=self.request.user
        )

        # Broadcast message to group via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'group_{group_id}',
            {
                'type': 'group_message',
                'message': GroupMessageSerializer(message).data
            }
        )
        return message

    @action(detail=True, methods=['post'], url_path='react')
    def react(self, request, pk=None):
        """Add or remove a reaction to a message"""
        message = self.get_object()
        emoji = request.data.get('emoji')

        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is a member of the group
        if not Membership.objects.filter(
            user=request.user,
            group=message.group,
            status=MembershipStatus.APPROVED
        ).exists():
            return Response(
                {'error': 'You must be a member of this group to react'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Toggle reaction
        reaction, created = GroupMessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji
        )

        if not created:
            reaction.delete()
            return Response({'status': 'removed'}, status=status.HTTP_200_OK)

        # Broadcast reaction update
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'group_{message.group.id}',
            {
                'type': 'group_reaction',
                'message_id': message.id,
                'reaction': GroupMessageReactionSerializer(reaction).data
            }
        )

        return Response(
            GroupMessageReactionSerializer(reaction).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()

        # Check if user is a member of the group
        if not Membership.objects.filter(
            user=request.user,
            group=message.group,
            status=MembershipStatus.APPROVED
        ).exists():
            return Response(
                {'error': 'You must be a member of this group'},
                status=status.HTTP_403_FORBIDDEN
            )

        message.status = 'read'
        message.save()

        return Response({'status': 'marked as read'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def group_attachment_upload(request):
    """Upload a single attachment for a group message"""
    group_id = request.data.get('group_id')
    message_id = request.data.get('message_id')
    file = request.data.get('file')

    if not group_id or not file:
        return Response(
            {'error': 'group_id and file are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user is a member of the group
    if not Membership.objects.filter(
        user=request.user,
        group_id=group_id,
        status=MembershipStatus.APPROVED
    ).exists():
        return Response(
            {'error': 'You must be a member of this group to upload attachments'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Create or get message
    if message_id:
        try:
            message = GroupMessage.objects.get(id=message_id, group_id=group_id)
        except GroupMessage.DoesNotExist:
            return Response(
                {'error': 'Message not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    else:
        message = GroupMessage.objects.create(
            group_id=group_id,
            sender=request.user,
            message_type='media_group'
        )

    # Determine attachment type
    content_type = file.content_type
    if content_type.startswith('image/'):
        attachment_type = 'image'
    elif content_type.startswith('video/'):
        attachment_type = 'video'
    elif content_type.startswith('audio/'):
        attachment_type = 'audio'
    else:
        attachment_type = 'document'

    # Create attachment
    attachment = GroupMessageAttachment.objects.create(
        message=message,
        attachment_type=attachment_type,
        file=file
    )

    # Broadcast message update
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'group_{group_id}',
        {
            'type': 'group_message',
            'message': GroupMessageSerializer(message).data
        }
    )

    return Response(
        GroupMessageAttachmentSerializer(attachment).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def group_batch_attachment_upload(request):
    """Batch upload attachments for a group message (media groups)"""
    group_id = request.data.get('group_id')
    files = request.FILES.getlist('files')
    global_caption = request.data.get('global_caption', '')

    if not group_id or not files:
        return Response(
            {'error': 'group_id and files are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user is a member of the group
    if not Membership.objects.filter(
        user=request.user,
        group_id=group_id,
        status=MembershipStatus.APPROVED
    ).exists():
        return Response(
            {'error': 'You must be a member of this group to upload attachments'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Create message
    message = GroupMessage.objects.create(
        group_id=group_id,
        sender=request.user,
        content=global_caption,
        message_type='media_group'
    )

    # Create attachments
    attachments_data = []
    for index, file in enumerate(files):
        content_type = file.content_type
        if content_type.startswith('image/'):
            attachment_type = 'image'
        elif content_type.startswith('video/'):
            attachment_type = 'video'
        elif content_type.startswith('audio/'):
            attachment_type = 'audio'
        else:
            attachment_type = 'document'

        attachment = GroupMessageAttachment.objects.create(
            message=message,
            attachment_type=attachment_type,
            file=file,
            order=index
        )
        attachments_data.append(GroupMessageAttachmentSerializer(attachment).data)

    # Broadcast message
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'group_{group_id}',
        {
            'type': 'group_message',
            'message': GroupMessageSerializer(message).data
        }
    )

    return Response(
        {
            'message': GroupMessageSerializer(message).data,
            'attachments': attachments_data
        },
        status=status.HTTP_201_CREATED
    )


@login_required
def group_chat_view(request, group_id):
    """Web view for group chat"""
    group = get_object_or_404(
        Group.objects.annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))),
        id=group_id
    )

    # Check if user is a member
    if not Membership.objects.filter(
        user=request.user,
        group=group,
        status=MembershipStatus.APPROVED
    ).exists():
        messages.error(request, 'You must be a member of this group to access the chat.')
        return redirect('groups:groups_detail', group_id=group_id)

    context = {
        'group': group,
        'unread_notifications_count': get_cached_unread_count(request.user),
    }
    return render(request, 'groups/group_chat.html', context)


@login_required
@require_http_methods(["POST"])
def toggle_group_membership(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check official group restrictions
    if group.is_official and group.course and group.year:
        if request.user.course != group.course or request.user.year != group.year:
            messages.error(request, 'You can only join official groups that match your course and year.')
            return redirect('groups:groups_detail', group_id=group_id)
    
    # Check if already has membership
    existing_membership = Membership.objects.filter(group=group, user=request.user).first()
    
    if existing_membership:
        existing_membership.delete()
        messages.success(request, f'You left {group.name}.')
    else:
        # Determine status based on join policy
        if group.join_policy == JoinPolicy.OPEN:
            membership_status = MembershipStatus.APPROVED
        elif group.join_policy == JoinPolicy.APPROVAL:
            membership_status = MembershipStatus.PENDING
        elif group.join_policy == JoinPolicy.INVITE_ONLY:
            messages.error(request, 'This group is invite-only.')
            return redirect('groups:groups_detail', group_id=group_id)
        else:
            membership_status = MembershipStatus.PENDING
        
        membership = Membership.objects.create(group=group, user=request.user, status=membership_status)
        
        if membership_status == MembershipStatus.APPROVED:
            messages.success(request, f'You joined {group.name}!')
            # Send welcome notification
            send_group_welcome_notification(request.user, group)
        else:
            messages.info(request, f'Your request to join {group.name} is pending approval.')
            # Send admin notifications for pending requests
            send_group_join_request_notification(request.user, group)
    
    return redirect('groups:groups_detail', group_id=group_id)


@login_required
def edit_group(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin (creator or has admin membership)
    is_admin = (group.created_by == request.user) or Membership.objects.filter(
        group=group, 
        user=request.user, 
        role=MembershipRole.ADMIN, 
        status=MembershipStatus.APPROVED
    ).exists()
    
    if not is_admin:
        messages.error(request, 'Only admins can edit this group.')
        return redirect('groups:groups_detail', group_id=group_id)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Squad updated.')
            return redirect('groups:groups_detail', group_id=group_id)
    else:
        form = GroupForm(instance=group)
    return render(request, 'groups/create_group.html', {'form': form, 'group': group})


@login_required
def invite_to_group(request, group_id, user_id):
    group = get_object_or_404(Group, id=group_id)
    target = get_object_or_404(User, id=user_id)
    if not Membership.objects.filter(group=group, user=target).exists():
        send_group_invite_notification(target, request.user, group)
        messages.success(request, f'Invite sent to {target.username}.')
    return redirect('groups:groups_detail', group_id=group_id)


@login_required
def respond_to_invite(request, notif_id, action):
    notif = get_object_or_404(Notifications, id=notif_id, recipient=request.user)
    if notif.group:
        if action == 'accept':
            # Update existing PENDING membership to APPROVED
            membership = Membership.objects.filter(
                group=notif.group,
                user=request.user,
                status=MembershipStatus.PENDING
            ).first()
            
            if membership:
                membership.status = MembershipStatus.APPROVED
                membership.save()
                messages.success(request, f'You joined {notif.group.name}!')
            else:
                # Fallback: create new membership if PENDING doesn't exist
                Membership.objects.create(
                    group=notif.group,
                    user=request.user,
                    status=MembershipStatus.APPROVED
                )
                messages.success(request, f'You joined {notif.group.name}!')
        else:
            # Delete PENDING membership when declined
            membership = Membership.objects.filter(
                group=notif.group,
                user=request.user,
                status=MembershipStatus.PENDING
            ).first()
            
            if membership:
                membership.delete()
                messages.info(request, 'Invite declined.')
            else:
                messages.info(request, 'Invite declined.')
    notif.delete()
    return redirect('notifications:notifications')


@login_required
def approve_from_notification(request, group_id, user_id):
    """Approve a group join request from notification"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin
    try:
        admin_membership = Membership.objects.get(
            user=request.user,
            group=group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'Only admins can approve join requests.')
        return redirect('notifications:notifications')
    
    # Get the membership to approve
    try:
        membership = Membership.objects.get(
            user_id=user_id,
            group=group,
            status=MembershipStatus.PENDING
        )
    except Membership.DoesNotExist:
        messages.error(request, f'No pending membership request found for user_id={user_id} in group={group.name}.')
        return redirect('notifications:notifications')
    
    membership.status = MembershipStatus.APPROVED
    membership.role = MembershipRole.MEMBER
    membership.save()
    
    # Send welcome notification to the approved user
    send_group_approved_notification(membership.user, group, request.user)
    
    # Delete the request notification
    try:
        notification = NotificationObject.objects.filter(
            recipient=request.user,
            context_type='GROUP',
            context_id=str(group.id),
            notification_type='GROUP_REQUEST'
        ).first()
        if notification:
            notification.delete()
    except Exception:
        pass  # Notification may have already been deleted
    
    messages.success(request, f'{membership.user.username} has been approved to join {group.name}.')
    return redirect('notifications:notifications')


@login_required
@transaction.atomic
def reject_from_notification(request, group_id, user_id):
    """Reject a group join request from notification"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is admin
    try:
        admin_membership = Membership.objects.get(
            user=request.user,
            group=group,
            role=MembershipRole.ADMIN,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'Only admins can reject join requests.')
        return redirect('notifications:notifications')
    
    # Get the membership to reject
    try:
        membership = Membership.objects.get(
            user_id=user_id,
            group=group,
            status=MembershipStatus.PENDING
        )
    except Membership.DoesNotExist:
        messages.error(request, 'No pending membership request found for this user.')
        return redirect('notifications:notifications')
    
    membership.status = MembershipStatus.REJECTED
    membership.save()
    
    # Send rejection notification to the user
    send_group_rejected_notification(membership.user, group, request.user)
    
    # Delete the request notification
    try:
        notification = NotificationObject.objects.filter(
            recipient=request.user,
            context_type='GROUP',
            context_id=str(group.id),
            notification_type='GROUP_REQUEST'
        ).first()
        if notification:
            notification.delete()
    except Exception:
        pass  # Notification may have already been deleted
    
    messages.info(request, f'{membership.user.username}\'s request to join {group.name} was rejected.')
    return redirect('notifications:notifications')


@login_required
def group_unread_counts_api(request):
    """
    API endpoint to get unread notification counts for user's groups.
    Returns JSON with group_id -> count mapping.
    """
    user_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.APPROVED)
    all_group_ids = list(user_groups.values_list('id', flat=True))
    group_unread_counts = get_group_unread_counts(request.user, all_group_ids)
    return JsonResponse(group_unread_counts)


@login_required
def search_users_view(request):
    """
    Search users by username or global role for role assignment.
    Returns JSON results.
    Supports role keywords: president, delegate, verified
    """
    from django.conf import settings
    from users.models import GlobalRole

    query = request.GET.get('q', '').strip().lower()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    # Check for role keywords
    role_keywords = {
        'president': GlobalRole.PRESIDENT,
        'delegate': GlobalRole.DELEGATE,
        'verified': GlobalRole.VERIFIED,
    }

    # If query matches a role keyword, search by role
    if query in role_keywords:
        users = User.objects.filter(
            global_role=role_keywords[query]
        ).values('id', 'username', 'first_name', 'last_name', 'profile_pic')[:20]
    else:
        # Otherwise search by username
        users = User.objects.filter(
            username__icontains=query
        ).values('id', 'username', 'first_name', 'last_name', 'profile_pic')[:20]

    # Convert profile_pic paths to full URLs
    user_list = list(users)
    for user in user_list:
        if user['profile_pic']:
            user['profile_pic'] = request.build_absolute_uri(settings.MEDIA_URL + str(user['profile_pic']))
        else:
            user['profile_pic'] = '/static/images/default_user.jpg'

    return JsonResponse(user_list, safe=False)


@login_required
def clear_recent_group_searches(request):
    """
    Clear recent group searches from session.
    """
    request.session['recent_group_searches'] = []
    from django.http import HttpResponseRedirect
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/groups/dashboard/'))


@login_required
def view_group_photo_fullscreen(request, group_id, photo_type):
    """
    View group or cover photo in full screen mode.
    Only accessible if the viewer is a member of the group or is an admin.
    """
    group = get_object_or_404(Group, id=group_id)

    # Check if user is allowed to view the photo (must be an approved member)
    is_member = Membership.objects.filter(
        user=request.user,
        group=group,
        status=MembershipStatus.APPROVED
    ).exists()

    if not is_member:
        messages.error(request, 'You need to be a member of this group to view photos in full screen.')
        return redirect('groups:groups_detail', group_id=group_id)

    # Determine which photo to show
    if photo_type == 'group':
        photo_url = group.get_photo_url
        photo_title = f"{group.name}'s Group Photo"
    elif photo_type == 'cover':
        if not group.cover_photo:
            messages.error(request, 'This group does not have a cover photo.')
            return redirect('groups:groups_detail', group_id=group_id)
        photo_url = group.cover_photo.url
        photo_title = f"{group.name}'s Cover Photo"
    else:
        messages.error(request, 'Invalid photo type.')
        return redirect('groups:groups_detail', group_id=group_id)
    
    # Get like count and check if current user liked the photo
    from .models import GroupPhotoLike
    like_count = GroupPhotoLike.objects.filter(
        group=group,
        photo_type=photo_type
    ).count()
    
    is_liked = GroupPhotoLike.objects.filter(
        user=request.user,
        group=group,
        photo_type=photo_type
    ).exists()
    
    return render(request, 'groups/group_photo_fullscreen.html', {
        'group': group,
        'photo_url': photo_url,
        'photo_type': photo_type,
        'photo_title': photo_title,
        'like_count': like_count,
        'is_liked': is_liked,
    })


@login_required
def group_members_search(request, group_id):
    """Search for group members via HTMX for the members modal"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    import logging
    
    logger = logging.getLogger(__name__)
    
    search_query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20
    
    logger.info(f"group_members_search called - group_id={group_id}, q={search_query}, page={page}")
    
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        return JsonResponse({'error': 'You must be a member to view group members'}, status=403)
    
    # Get approved memberships with search filter
    memberships_queryset = group.memberships.filter(status=MembershipStatus.APPROVED).select_related('user', 'user__course', 'user__year').order_by('-id')
    
    if search_query:
        memberships_queryset = memberships_queryset.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    paginator = Paginator(memberships_queryset, page_size)
    memberships_page = paginator.get_page(page)
    
    # Get following IDs for display
    def get_following_ids(user):
        from users.models import Follow
        return Follow.objects.filter(follower=user).values_list('followed_id', flat=True)
    
    following_ids = list(get_following_ids(request.user))
    
    # Build next page URL
    next_url = None
    if memberships_page.has_next():
        url_params = []
        if search_query:
            url_params.append(f"q={search_query}")
        url_params.append(f"page={memberships_page.next_page_number()}")
        next_url = f"?{'&'.join(url_params)}"
    
    logger.info(f"Rendering group_members_list.html with {len(memberships_page)} memberships")
    
    return render(request, 'groups/partials/group_members_list.html', {
        'memberships': memberships_page,
        'group': group,
        'following_ids': following_ids,
        'has_more': memberships_page.has_next(),
        'next_url': next_url,
        'search_query': search_query,
    })


@login_required
def group_announcements_view(request, group_id):
    """View group announcements page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group announcements.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    # Check if user is admin
    is_admin = membership.role == MembershipRole.ADMIN
    
    # Fetch announcements with optimized queries
    announcements = Announcement.objects.filter(
        group=group
    ).select_related('author').order_by('-is_pinned', '-created_at')
    
    # Separate pinned and unpinned announcements
    pinned_announcements = [a for a in announcements if a.is_pinned]
    all_announcements = [a for a in announcements if not a.is_pinned]
    
    context = {
        'group': group,
        'pinned_announcements': pinned_announcements,
        'all_announcements': all_announcements,
        'announcements': announcements,
        'is_admin': is_admin,
    }
    
    return render(request, 'groups/group_announcements.html', context)


@login_required
def group_settings_view(request, group_id):
    """View group settings page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    # Check if user is admin
    is_admin = membership.role == MembershipRole.ADMIN
    
    context = {
        'group': group,
        'is_admin': is_admin,
    }
    
    return render(request, 'groups/group_settings.html', context)


@login_required
def group_chat_view(request, group_id):
    """View group chat page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to access group chat.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    context = {
        'group': group,
    }
    
    return render(request, 'groups/group_chat.html', context)


@login_required
def group_settings_details_view(request, group_id):
    """View group settings details page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    # Check if user is admin
    is_admin = membership.role == MembershipRole.ADMIN
    
    # Check if user is moderator
    is_moderator = membership.role == MembershipRole.MODERATOR
    
    # Determine if user can edit based on group's edit_permission setting
    can_edit = False
    if group.edit_permission == EditPermission.ADMINS_ONLY:
        can_edit = is_admin
    elif group.edit_permission == EditPermission.ADMINS_MODERATORS:
        can_edit = is_admin or is_moderator
    
    if request.method == 'POST' and can_edit:
        form = GroupDetailsForm(request.POST, request.FILES, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group details updated successfully.')
            return redirect('groups:group_settings_details', group_id=group.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GroupDetailsForm(instance=group)
    
    context = {
        'group': group,
        'form': form,
        'can_edit': can_edit,
    }
    
    return render(request, 'groups/settings/group_settings_details.html', context)


@login_required
def group_settings_members_view(request, group_id):
    """View group settings members page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    # Check if user is admin (only admins can manage members)
    is_admin = membership.role == MembershipRole.ADMIN
    
    # Check if user can invite based on group's invite_permission setting
    can_invite = False
    if group.invite_permission == InvitePermission.ADMINS_ONLY:
        can_invite = is_admin
    elif group.invite_permission == InvitePermission.ALL_MEMBERS:
        can_invite = True
    
    # Handle role assignment
    if request.method == 'POST' and is_admin:
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'assign_role' and user_id:
            try:
                target_membership = Membership.objects.get(
                    user_id=user_id,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                new_role = request.POST.get('role')
                
                # Cannot demote yourself from admin
                if target_membership.user == request.user and target_membership.role == MembershipRole.ADMIN:
                    messages.error(request, 'You cannot change your own admin role.')
                else:
                    # Check max admin constraint
                    if new_role == MembershipRole.ADMIN:
                        admin_count = Membership.objects.filter(
                            group=group,
                            role=MembershipRole.ADMIN,
                            status=MembershipStatus.APPROVED
                        ).count()
                        if admin_count >= 5:
                            messages.error(request, 'Maximum of 5 admins allowed per group.')
                        else:
                            target_membership.role = new_role
                            target_membership.save()
                            messages.success(request, f'Role updated for {target_membership.user.username}.')
                    else:
                        target_membership.role = new_role
                        target_membership.save()
                        messages.success(request, f'Role updated for {target_membership.user.username}.')
            except Membership.DoesNotExist:
                messages.error(request, 'Member not found.')
        
        elif action == 'remove_member' and user_id:
            try:
                target_membership = Membership.objects.get(
                    user_id=user_id,
                    group=group,
                    status=MembershipStatus.APPROVED
                )
                
                # Cannot remove yourself if you're the last admin
                if target_membership.user == request.user:
                    admin_count = Membership.objects.filter(
                        group=group,
                        role=MembershipRole.ADMIN,
                        status=MembershipStatus.APPROVED
                    ).count()
                    if admin_count == 1:
                        messages.error(request, 'You cannot leave as the last admin. Assign a successor first.')
                    else:
                        target_membership.delete()
                        messages.success(request, f'{target_membership.user.username} removed from group.')
                        return redirect('groups:group_settings_members', group_id=group.id)
                else:
                    target_membership.delete()
                    messages.success(request, f'{target_membership.user.username} removed from group.')
            except Membership.DoesNotExist:
                messages.error(request, 'Member not found.')
    
    # Get all approved members with their roles
    members = Membership.objects.filter(
        group=group,
        status=MembershipStatus.APPROVED
    ).select_related('user').order_by(
        # Custom ordering: ADMIN -> MODERATOR -> DELEGATE -> MEMBER
        # Django doesn't have a direct way to order by enum values, so we use case statements
        # For now, we'll use a simple approach and let Python handle the sorting
    )
    
    # Sort members by role priority: ADMIN > MODERATOR > DELEGATE > MEMBER
    role_priority = {
        MembershipRole.ADMIN: 0,
        MembershipRole.MODERATOR: 1,
        MembershipRole.DELEGATE: 2,
        MembershipRole.MEMBER: 3,
    }
    members = sorted(members, key=lambda m: (role_priority.get(m.role, 99), m.joined_at))
    
    # Paginate members (20 per page)
    paginator = Paginator(members, 20)
    page_number = request.GET.get('page', 1)
    members_page = paginator.get_page(page_number)
    
    context = {
        'group': group,
        'members': members_page,
        'is_admin': is_admin,
        'can_invite': can_invite,
        'membership_roles': MembershipRole,
    }
    
    return render(request, 'groups/settings/group_settings_members.html', context)


@login_required
def get_mutual_friends_api(request, group_id):
    """API endpoint to get mutual friends for group invites"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        return JsonResponse({'error': 'You must be a member to invite users'}, status=403)
    
    # Check invite permission
    if group.invite_permission == InvitePermission.ADMINS_ONLY:
        if membership.role != MembershipRole.ADMIN:
            return JsonResponse({'error': 'Only admins can invite users'}, status=403)
    
    # Get mutual friends (users who follow request.user and are followed by request.user)
    following_ids = Follow.objects.filter(follower=request.user).values_list('followed_id', flat=True)
    follower_ids = Follow.objects.filter(followed=request.user).values_list('follower_id', flat=True)
    
    # Mutual friends are in both lists
    mutual_friend_ids = set(following_ids) & set(follower_ids)
    
    # Exclude existing group members (both APPROVED and PENDING)
    existing_member_ids = Membership.objects.filter(
        group=group
    ).values_list('user_id', flat=True)
    
    available_friend_ids = mutual_friend_ids - set(existing_member_ids)
    
    # Get user details with profile_pic URL
    friends = []
    for user in User.objects.filter(id__in=available_friend_ids):
        friend_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile_pic': user.profile_pic.url if user.profile_pic else None
        }
        friends.append(friend_data)
    
    return JsonResponse({'friends': friends})


@login_required
@require_POST
def send_group_invites_api(request, group_id):
    """API endpoint to send group invites"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        return JsonResponse({'error': 'You must be a member to invite users'}, status=403)
    
    # Check invite permission
    if group.invite_permission == InvitePermission.ADMINS_ONLY:
        if membership.role != MembershipRole.ADMIN:
            return JsonResponse({'error': 'Only admins can invite users'}, status=403)
    
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        # Debug: Log received user IDs
        print(f"DEBUG: Received user_ids: {user_ids}")
        
        # Validate max 10 invites
        if len(user_ids) > 10:
            return JsonResponse({'error': 'Maximum 10 invites at once'}, status=400)
        
        sent_count = 0
        skipped_count = 0
        not_found_count = 0
        errors = []
        
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                
                # Check if user is already a member (APPROVED) or already invited (PENDING)
                existing_membership = Membership.objects.filter(user=user, group=group).first()
                if existing_membership:
                    if existing_membership.status == MembershipStatus.APPROVED:
                        print(f"DEBUG: User {user.username} (ID: {user_id}) already a member, skipping")
                        skipped_count += 1
                        errors.append(f"{user.username} is already a member")
                        continue
                    elif existing_membership.status == MembershipStatus.PENDING:
                        print(f"DEBUG: User {user.username} (ID: {user_id}) already invited, skipping")
                        skipped_count += 1
                        errors.append(f"{user.username} is already invited")
                        continue
                
                # Create pending membership
                Membership.objects.create(
                    user=user,
                    group=group,
                    status=MembershipStatus.PENDING,
                    role=MembershipRole.MEMBER
                )
                
                # Send notification
                send_group_invite_notification(user, request.user, group)
                sent_count += 1
                print(f"DEBUG: Successfully invited {user.username} (ID: {user_id})")
                
            except User.DoesNotExist:
                print(f"DEBUG: User with id {user_id} does not exist")
                not_found_count += 1
                errors.append(f"User ID {user_id} not found")
                continue
            except Exception as e:
                print(f"DEBUG: Error inviting user {user_id}: {str(e)}")
                errors.append(f"Error inviting user {user_id}: {str(e)}")
                continue
        
        print(f"DEBUG: Final counts - sent: {sent_count}, skipped: {skipped_count}, not_found: {not_found_count}")
        
        return JsonResponse({
            'success': True,
            'sent_count': sent_count,
            'skipped_count': skipped_count,
            'not_found_count': not_found_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@login_required
def group_settings_privacy_view(request, group_id):
    """View group settings privacy page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    # Check if user is admin (only admins can access privacy settings)
    is_admin = membership.role == MembershipRole.ADMIN
    if not is_admin:
        messages.error(request, 'Only admins can access privacy settings.')
        return redirect('groups:group_settings', group_id=group.id)
    
    if request.method == 'POST':
        form = GroupPrivacyForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Privacy settings updated successfully.')
            return redirect('groups:group_settings_privacy', group_id=group.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GroupPrivacyForm(instance=group)
    
    context = {
        'group': group,
        'form': form,
        'is_admin': is_admin,
    }
    
    return render(request, 'groups/settings/group_settings_privacy.html', context)


@login_required
def group_settings_announcements_view(request, group_id):
    """View group settings announcements page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    context = {
        'group': group,
    }
    
    return render(request, 'groups/settings/group_settings_announcements.html', context)


@login_required
def group_settings_documents_view(request, group_id):
    """View group settings documents page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    context = {
        'group': group,
    }
    
    return render(request, 'groups/settings/group_settings_documents.html', context)


@login_required
def group_settings_about_view(request, group_id):
    """View group settings about page"""
    group = get_object_or_404(Group, id=group_id)
    
    # Check if user is a member
    try:
        membership = Membership.objects.get(
            user=request.user,
            group=group,
            status=MembershipStatus.APPROVED
        )
    except Membership.DoesNotExist:
        messages.error(request, 'You must be a member to view group settings.')
        return redirect('groups:groups_detail', group_id=group.id)
    
    context = {
        'group': group,
    }
    
    return render(request, 'groups/settings/group_settings_about.html', context)
