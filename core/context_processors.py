# core/context_processors.py

def notification_count(request):
    """Protocol: Provides a global count of unread intel reports."""
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}