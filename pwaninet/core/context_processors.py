# core/context_processors.py
from notifications.services.notification_service import get_cached_unread_count

def notification_count(request):
    """Protocol: Provides a global count of unread intel reports."""
    if request.user.is_authenticated:
        count = get_cached_unread_count(request.user)
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}