from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from notifications.models import Notifications
from notifications.services.notification_service import (
    build_notifications_context,
    build_unread_notification_html,
    get_cached_unread_count,
    invalidate_unread_count_cache,
    mark_single_notification_as_read
)


@login_required
def notifications_list(request):
    context = build_notifications_context(request.user, mark_read=True)
    context['unread_notifications_count'] = 0
    return render(request, 'notifications/notifications.html', context)


@login_required
def unread_notification_count(request):
    html = build_unread_notification_html(request.user)
    return HttpResponse(html)


@login_required
def mark_notification_as_read(request, notif_id):
    mark_single_notification_as_read(request.user, notif_id)
    from notifications.services.notification_service import build_notifications_context
    context = build_notifications_context(request.user, mark_read=False)
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    response = render(request, 'notifications/partials/notification_list.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
def mark_all_as_read(request):
    if request.method == 'POST':
        Notifications.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        invalidate_unread_count_cache(request.user.id)
    return HttpResponse('')
