"""
Release permissions for PwaniNet Release Center.

Provides dedicated permissions for release management without requiring
Django superuser access.
"""
from rest_framework import permissions


class ReleasePermission(permissions.BasePermission):
    """
    Base permission class for release management.
    """
    
    def has_permission(self, request, view):
        """Check if user has any release permission"""
        return request.user.is_authenticated


class CanViewRelease(ReleasePermission):
    """
    Permission to view releases.
    """
    
    def has_permission(self, request, view):
        """All authenticated users can view releases"""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """View permission for specific release"""
        return request.user.is_authenticated


class CanManageRelease(ReleasePermission):
    """
    Permission to manage releases (create, edit, delete drafts).
    """
    
    def has_permission(self, request, view):
        """Check if user can manage releases"""
        if not request.user.is_authenticated:
            return False
        
        # Check for dedicated permission
        if request.user.has_perm('releases.manage_release'):
            return True
        
        # Fallback to staff for now (to be removed in production)
        return request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        """Check if user can manage this specific release"""
        if not request.user.is_authenticated:
            return False
        
        # Only allow managing draft releases unless user has publish permission
        if obj.status != 'DRAFT' and not request.user.has_perm('releases.publish_release'):
            return False
        
        return request.user.has_perm('releases.manage_release') or request.user.is_staff


class CanPublishRelease(ReleasePermission):
    """
    Permission to publish releases.
    """
    
    def has_permission(self, request, view):
        """Check if user can publish releases"""
        if not request.user.is_authenticated:
            return False
        
        return request.user.has_perm('releases.publish_release') or request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        """Check if user can publish this specific release"""
        if not request.user.is_authenticated:
            return False
        
        # Can only publish releases in testing or draft status
        if obj.status not in ['DRAFT', 'TESTING']:
            return False
        
        return request.user.has_perm('releases.publish_release') or request.user.is_staff


class CanArchiveRelease(ReleasePermission):
    """
    Permission to archive releases.
    """
    
    def has_permission(self, request, view):
        """Check if user can archive releases"""
        if not request.user.is_authenticated:
            return False
        
        return request.user.has_perm('releases.archive_release') or request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        """Check if user can archive this specific release"""
        if not request.user.is_authenticated:
            return False
        
        # Cannot archive current release
        if obj.is_current_release:
            return False
        
        return request.user.has_perm('releases.archive_release') or request.user.is_staff


class IsReleaseOwnerOrStaff(permissions.BasePermission):
    """
    Permission to check if user is the release creator or staff.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user is owner or staff"""
        if request.user.is_staff:
            return True
        
        return obj.created_by == request.user
