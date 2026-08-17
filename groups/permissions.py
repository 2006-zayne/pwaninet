from rest_framework import permissions
from .models import Membership, MembershipRole, MembershipStatus


class IsApprovedMember(permissions.BasePermission):
    """
    Only approved members can interact in groups.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # If obj is a group, check membership
        if hasattr(obj, 'pk'):
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=obj,
                    status=MembershipStatus.APPROVED
                )
                return True
            except Membership.DoesNotExist:
                return False
        return False


class IsGroupAdmin(permissions.BasePermission):
    """
    Check if user is an admin of the group.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        group = obj
        if hasattr(obj, 'group'):
            group = obj.group
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False


class IsGroupModerator(permissions.BasePermission):
    """
    Check if user is a moderator or admin of the group.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        group = obj
        if hasattr(obj, 'group'):
            group = obj.group
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=group,
                status=MembershipStatus.APPROVED
            )
            return membership.role in [MembershipRole.ADMIN, MembershipRole.MODERATOR]
        except Membership.DoesNotExist:
            return False


class IsGroupDelegate(permissions.BasePermission):
    """
    Check if user is a delegate, moderator, or admin of the group.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        group = obj
        if hasattr(obj, 'group'):
            group = obj.group
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=group,
                status=MembershipStatus.APPROVED
            )
            return membership.role in [
                MembershipRole.ADMIN,
                MembershipRole.MODERATOR,
                MembershipRole.DELEGATE
            ]
        except Membership.DoesNotExist:
            return False


class CanManageGroup(permissions.BasePermission):
    """
    Only admins can edit group details or delete group.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Group creator is always an admin
        if obj.created_by == request.user:
            return True
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=obj,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False


class CanManageMembership(permissions.BasePermission):
    """
    Only admins can approve/reject join requests and assign roles.
    Enforces max 5 admins per group constraint.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        group_id = view.kwargs.get('group_id')
        if not group_id:
            return False
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group_id=group_id,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            
            # Check if assigning admin role and enforce max 5 admins
            if request.method in ['POST', 'PUT', 'PATCH']:
                new_role = request.data.get('role')
                if new_role == MembershipRole.ADMIN:
                    current_admin_count = Membership.objects.filter(
                        group_id=group_id,
                        role=MembershipRole.ADMIN,
                        status=MembershipStatus.APPROVED
                    ).count()
                    if current_admin_count >= 5:
                        return False
            
            return True
        except Membership.DoesNotExist:
            return False


class CanDeletePost(permissions.BasePermission):
    """
    Author OR admin can delete post.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Author can delete their own post
        if obj.author == request.user:
            return True
        
        # Group admin can delete any post in their group
        if obj.group:
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=obj.group,
                    role=MembershipRole.ADMIN,
                    status=MembershipStatus.APPROVED
                )
                return True
            except Membership.DoesNotExist:
                return False
        
        return False


class CanEditPost(permissions.BasePermission):
    """
    Only author can edit their post.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        return obj.author == request.user


class CanJoinOfficialGroup(permissions.BasePermission):
    """
    Only users with matching course AND year can join official groups.
    Others can view but cannot join or post.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        group_id = view.kwargs.get('group_id') or view.kwargs.get('pk')
        if not group_id:
            return True
        
        try:
            from groups.models import Group
            group = Group.objects.get(pk=group_id)
            
            # If not an official group, anyone can join
            if not group.is_official:
                return True
            
            # For official groups, check course and year match
            if group.course and group.year:
                return (
                    request.user.course == group.course and
                    request.user.year == group.year
                )
            
            # If group is official but missing course/year, allow join
            return True
            
        except Group.DoesNotExist:
            return False


class IsPostAuthorOrReadOnly(permissions.BasePermission):
    """
    Allow read-only access for approved members, write access only for author.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Read permissions
        if request.method in permissions.SAFE_METHODS:
            # Check if user is approved member of the group
            if obj.group:
                try:
                    membership = Membership.objects.get(
                        user=request.user,
                        group=obj.group,
                        status=MembershipStatus.APPROVED
                    )
                    return True
                except Membership.DoesNotExist:
                    return False
            return True
        
        # Write permissions - only author
        return obj.author == request.user


class CanViewAnnouncement(permissions.BasePermission):
    """
    Only approved group members can view announcements.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=obj.group,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False


class CanCreateAnnouncement(permissions.BasePermission):
    """
    Only group admins can create announcements.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        group_id = view.kwargs.get('group_id')
        if not group_id:
            return False
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group_id=group_id,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False


class CanEditAnnouncement(permissions.BasePermission):
    """
    Only group admins can edit announcements.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=obj.group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False


class CanDeleteAnnouncement(permissions.BasePermission):
    """
    Only group admins can delete announcements.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        try:
            membership = Membership.objects.get(
                user=request.user,
                group=obj.group,
                role=MembershipRole.ADMIN,
                status=MembershipStatus.APPROVED
            )
            return True
        except Membership.DoesNotExist:
            return False
