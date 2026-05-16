from rest_framework import permissions


class CanDeletePost(permissions.BasePermission):
    """
    Author OR admin OR moderator OR global admin can delete post.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        # Author can delete their own post
        if obj.author == request.user:
            return True
        
        # Global admins can delete any post
        from users.models import GlobalRole
        if request.user.global_role in [GlobalRole.PRESIDENT, GlobalRole.DELEGATE]:
            return True
        
        # Group admin/moderator can delete posts in their group
        if obj.group:
            from groups.models import Membership, MembershipRole, MembershipStatus
            try:
                membership = Membership.objects.get(
                    user=request.user,
                    group=obj.group,
                    role__in=[MembershipRole.ADMIN, MembershipRole.MODERATOR],
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
                from groups.models import Membership, MembershipStatus
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
