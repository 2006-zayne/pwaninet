from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.db import transaction

from .models import Group, Membership, MembershipRole, MembershipStatus, JoinPolicy
from .serializers import (
    GroupSerializer, GroupCreateSerializer, MembershipSerializer,
    MembershipCreateSerializer, MembershipActionSerializer, RoleAssignmentSerializer
)
from .permissions import (
    CanManageGroup, CanManageMembership, CanJoinOfficialGroup,
    IsApprovedMember, IsGroupAdmin
)
from posts.models import Post, Like
from users.models import User
from notifications.models import Notifications
from groups.forms import GroupForm
from groups.services.group_notification_service import (
    send_group_join_request_notification,
    send_group_approved_notification,
    send_group_rejected_notification,
    send_group_welcome_notification,
    send_group_invite_notification
)
from notifications.services.notification_service import get_cached_unread_count, get_group_unread_counts
from django.http import JsonResponse


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


# ============================================================================
# DJANGO WEB VIEWS
# ============================================================================

@login_required
def groups_dashboard(request):
    from groups.queries.group_queries import get_following_ids
    
    user_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.APPROVED)
    pending_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.PENDING)
    
    # Get suggested groups based on who user follows
    following_ids = get_following_ids(request.user)
    suggested_groups = Group.objects.filter(
        memberships__user_id__in=following_ids,
        memberships__status=MembershipStatus.APPROVED
    ).exclude(memberships__user=request.user).annotate(
        member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))
    ).order_by('-member_count')[:20]
    
    user_group_ids = set(user_groups.values_list('id', flat=True))
    pending_group_ids = set(pending_groups.values_list('id', flat=True))
    
    # Get unread notification counts for suggested groups
    suggested_group_ids = list(suggested_groups.values_list('id', flat=True))
    group_unread_counts = get_group_unread_counts(request.user, suggested_group_ids)
    
    return render(request, 'groups/groups_dashboard.html', {
        'user_groups': user_groups,
        'all_groups': suggested_groups,
        'user_group_ids': user_group_ids,
        'pending_group_ids': pending_group_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
        'group_unread_counts': group_unread_counts,
    })


@login_required
def groups_detail_view(request, group_id):
    from groups.services.group_service import build_group_detail_context
    group = get_object_or_404(Group.objects.annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))), id=group_id)
    query = request.GET.get('search_user', '')
    context = build_group_detail_context(request.user, group, query)
    liked_post_ids = set(Like.objects.filter(user=request.user, post__in=context['posts']).values_list('post_id', flat=True))
    context['liked_post_ids'] = liked_post_ids
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
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


@login_required
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
            Membership.objects.create(group=notif.group, user=request.user, status=MembershipStatus.APPROVED)
            messages.success(request, f'You joined {notif.group.name}!')
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
        notification = Notifications.objects.get(
            recipient=request.user,
            sender_id=user_id,
            group=group,
            notification_type=Notifications.GROUP_REQUEST
        )
        notification.delete()
    except Notifications.DoesNotExist:
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
        notification = Notifications.objects.get(
            recipient=request.user,
            sender_id=user_id,
            group=group,
            notification_type=Notifications.GROUP_REQUEST
        )
        notification.delete()
    except Notifications.DoesNotExist:
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
    
    return render(request, 'groups/group_photo_fullscreen.html', {
        'group': group,
        'photo_url': photo_url,
        'photo_type': photo_type,
        'photo_title': photo_title,
    })
