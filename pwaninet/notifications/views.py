from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from notifications.models import Notifications
from notifications.services.notification_service import (
    build_notifications_context,
    build_unread_notification_html,
    get_cached_unread_count,
    invalidate_unread_count_cache,
    mark_single_notification_as_read,
    delete_single_notification,
    delete_all_user_notifications,
    delete_user_read_notifications
)


@login_required
def notifications_list(request):
    notification_type = request.GET.get('type')
    is_read_param = request.GET.get('read')
    page = request.GET.get('page', 1)
    grouped_param = request.GET.get('grouped', 'false')
    
    is_read = None
    if is_read_param == 'true':
        is_read = True
    elif is_read_param == 'false':
        is_read = False
    
    grouped = grouped_param == 'true'
    
    context = build_notifications_context(
        request.user, 
        mark_read=True,
        notification_type=notification_type,
        is_read=is_read,
        grouped=grouped
    )
    
    # Paginate notifications (only if not grouped)
    if not grouped:
        paginator = Paginator(context['notifications'], 20)
        notifications_page = paginator.get_page(page)
        context['notifications'] = notifications_page
        context['has_pagination'] = True
    else:
        context['has_pagination'] = False
    
    context['unread_notifications_count'] = 0
    context['current_filter_type'] = notification_type
    context['current_filter_read'] = is_read_param
    context['current_grouped'] = grouped_param
    
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


@login_required
def delete_notification(request, notif_id):
    if request.method == 'POST':
        delete_single_notification(request.user, notif_id)
        notification_type = request.GET.get('type')
        is_read_param = request.GET.get('read')
        page = request.GET.get('page', 1)
        
        context = build_notifications_context(
            request.user,
            mark_read=False,
            notification_type=notification_type,
            is_read=True if is_read_param == 'true' else (False if is_read_param == 'false' else None)
        )
        
        paginator = Paginator(context['notifications'], 20)
        notifications_page = paginator.get_page(page)
        
        context['notifications'] = notifications_page
        context['unread_notifications_count'] = get_cached_unread_count(request.user)
        context['current_filter_type'] = notification_type
        context['current_filter_read'] = is_read_param
        
        response = render(request, 'notifications/partials/notification_list.html', context)
        response['HX-Trigger'] = 'updateUnreadCount'
        return response
    return HttpResponse('')


@login_required
def delete_all_notifications(request):
    if request.method == 'POST':
        delete_all_user_notifications(request.user)
    return HttpResponse('')


@login_required
def delete_read_notifications(request):
    if request.method == 'POST':
        delete_user_read_notifications(request.user)
    return HttpResponse('')
