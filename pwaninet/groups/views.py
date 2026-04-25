from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Group, Membership, MembershipRole, MembershipStatus
from .serializers import (
    GroupSerializer, GroupCreateSerializer, MembershipSerializer,
    MembershipCreateSerializer, MembershipActionSerializer, RoleAssignmentSerializer
)
from .permissions import (
    CanManageGroup, CanManageMembership, CanJoinOfficialGroup,
    IsApprovedMember, IsGroupAdmin
)


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
