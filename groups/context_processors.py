from notifications.services.notification_service import check_any_unread_group_activity


def groups_nav_context(request):
    """
    Context processor to provide group activity status for navigation bar.
    Provides `has_unread_group_activity` boolean for desktop & mobile nav red dot.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'has_unread_group_activity': False}

    return {
        'has_unread_group_activity': check_any_unread_group_activity(request.user)
    }
