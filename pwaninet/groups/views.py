from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count

from .models import Group, Membership, MembershipRole, MembershipStatus
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
from notifications.services.notification_service import create_notification, invalidate_unread_count_cache, get_cached_unread_count


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
        
        serializer = MembershipCreateSerializer(
            data={},
            context={'request': request, 'group_id': group.id}
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )

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
        from notifications.models import Notifications
        from notifications.services.notification_service import create_notification, invalidate_unread_count_cache
        create_notification(
            recipient=membership.user,
            sender=request.user,
            notification_type=Notifications.GROUP_APPROVED,
            msg=f'Welcome to {group.name}! You can now contribute to the group.',
            group=group
        )
        invalidate_unread_count_cache(membership.user.id)
        
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
        
        # Prevent leaving if you're the last admin
        if membership.role == MembershipRole.ADMIN:
            admin_count = Membership.objects.filter(
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            ).count()
            if admin_count == 1:
                return Response(
                    {'detail': 'You cannot leave as the last admin. Assign another admin first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        membership.delete()
        return Response(
            {'detail': 'You have left the group.'},
            status=status.HTTP_200_OK
        )


# ============================================================================
# DJANGO WEB VIEWS
# ============================================================================

@login_required
def groups_dashboard(request):
    user_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.APPROVED)
    pending_groups = Group.objects.filter(memberships__user=request.user, memberships__status=MembershipStatus.PENDING)
    all_groups = Group.objects.all().annotate(member_count=Count('memberships', filter=Q(memberships__status=MembershipStatus.APPROVED))).order_by('-member_count')
    user_group_ids = set(user_groups.values_list('id', flat=True))
    pending_group_ids = set(pending_groups.values_list('id', flat=True))
    return render(request, 'groups/groups_dashboard.html', {
        'user_groups': user_groups,
        'all_groups': all_groups,
        'user_group_ids': user_group_ids,
        'pending_group_ids': pending_group_ids,
        'unread_notifications_count': get_cached_unread_count(request.user),
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
        # For official groups, membership needs approval (pending status)
        # For community groups, auto-approve
        status = MembershipStatus.PENDING if group.is_official else MembershipStatus.APPROVED
        membership = Membership.objects.create(group=group, user=request.user, status=status)
        if status == MembershipStatus.APPROVED:
            messages.success(request, f'You joined {group.name}!')
            # Send welcome notification
            create_notification(
                recipient=request.user,
                sender=request.user,
                notification_type=Notifications.GROUP_APPROVED,
                msg=f'Welcome to {group.name}! You can now contribute to the group.',
                group=group
            )
            invalidate_unread_count_cache(request.user.id)
        else:
            messages.info(request, f'Your request to join {group.name} is pending approval.')
            # Send request confirmation notification - use group creator as sender
            sender_user = group.created_by if group.created_by else request.user
            create_notification(
                recipient=request.user,
                sender=sender_user,
                notification_type=Notifications.GROUP_REQUEST,
                msg=f'Your request to join {group.name} has been sent. You will be notified when it is accepted.',
                group=group
            )
            invalidate_unread_count_cache(request.user.id)
    
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
        create_notification(
            recipient=target,
            sender=request.user,
            notification_type=Notifications.INVITE,
            msg=f'invited you to join {group.name}.',
            group=group
        )
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
