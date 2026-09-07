"""Document domain permissions for REST API endpoints."""

from rest_framework import permissions
from users.models import GlobalRole


class IsDocumentUploaderOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing:
    - Safe read access to all for public ready documents.
    - Safe read access for uploader/staff/president/delegate for non-public or non-ready documents.
    - Write/Update/Delete access ONLY to the document uploader, staff, superuser,
      or users with presidential/delegate global roles.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Safe methods (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            if obj.status == 'ready' and obj.visibility == 'public':
                return True

            if not request.user or not request.user.is_authenticated:
                return False

            if obj.uploaded_by == request.user:
                return True

            if request.user.is_staff or request.user.is_superuser:
                return True

            if getattr(request.user, 'global_role', None) in [GlobalRole.PRESIDENT, GlobalRole.DELEGATE]:
                return True

            return False

        # Mutating methods (PUT, PATCH, DELETE)
        if not request.user or not request.user.is_authenticated:
            return False

        if obj.uploaded_by == request.user:
            return True

        if request.user.is_staff or request.user.is_superuser:
            return True

        if getattr(request.user, 'global_role', None) in [GlobalRole.PRESIDENT, GlobalRole.DELEGATE]:
            return True

        return False
