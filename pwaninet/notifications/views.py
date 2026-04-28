from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.paginator import Paginator
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
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
from .serializers import NotificationSerializer, NotificationUpdateSerializer, NotificationBulkActionSerializer
from .filters import NotificationFilter


@login_required
def notifications_list(request):
    notification_type = request.GET.get('type')
    is_read_param = request.GET.get('read')
    page = request.GET.get('page', 1)
    grouped_param = request.GET.get('grouped', 'false')
    time_filter = request.GET.get('time', 'all')
    
    is_read = None
    if is_read_param == 'true':
        is_read = True
    elif is_read_param == 'false':
        is_read = False
    
    grouped = grouped_param == 'true'
    
    # Use time-based grouping if requested
    if time_filter != 'all':
        from notifications.queries.notification_queries import get_notifications_by_time_periods
        time_grouped = get_notifications_by_time_periods(
            request.user,
            notification_type=notification_type,
            is_read=is_read
        )
        context = {
            'time_grouped': time_grouped,
            'time_filter': time_filter,
            'filter_type': notification_type,
            'filter_read': is_read,
            'current_filter_type': notification_type,
            'current_filter_read': is_read_param,
            'current_grouped': grouped_param,
            'has_pagination': False,
            'unread_notifications_count': get_cached_unread_count(request.user)
        }
    else:
        context = build_notifications_context(
            request.user,
            mark_read=False,
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
        
        context['unread_notifications_count'] = get_cached_unread_count(request.user)
        context['current_filter_type'] = notification_type
        context['current_filter_read'] = is_read_param
        context['current_grouped'] = grouped_param
        context['time_filter'] = 'all'
    
    return render(request, 'notifications/notifications.html', context)


@login_required
def unread_notification_count(request):
    html = build_unread_notification_html(request.user)
    return HttpResponse(html)


@login_required
def mark_notification_as_read(request, notif_id):
    mark_single_notification_as_read(request.user, notif_id)
    
    # Get the specific notification that was marked
    notification = get_notification_for_user(request.user, notif_id)
    if notification:
        notification.is_read = True
        notification.save()
    
    # Return updated notification item
    context = {
        'notifications': [notification] if notification else []
    }
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    response = render(request, 'notifications/partials/notification_list_items.html', context)
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
        
        response = render(request, 'notifications/partials/notification_list_items.html', context)
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


# API ViewSets
class NotificationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for Notifications model.
    """
    queryset = Notifications.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = NotificationFilter
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer

    def get_queryset(self):
        # Users can only see their own notifications
        return Notifications.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count for current user"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        invalidate_unread_count_cache(request.user.id)
        return Response({'marked_read': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        invalidate_unread_count_cache(request.user.id)
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark a specific notification as unread"""
        notification = self.get_object()
        notification.is_read = False
        notification.save()
        invalidate_unread_count_cache(request.user.id)
        return Response({'status': 'marked as unread'})

    @action(detail=False, methods=['post'])
    def delete_all(self, request):
        """Delete all notifications for current user"""
        count = self.get_queryset().count()
        self.get_queryset().delete()
        invalidate_unread_count_cache(request.user.id)
        return Response({'deleted': count})

    @action(detail=False, methods=['post'])
    def delete_read(self, request):
        """Delete all read notifications for current user"""
        queryset = self.get_queryset().filter(is_read=True)
        count = queryset.count()
        queryset.delete()
        invalidate_unread_count_cache(request.user.id)
        return Response({'deleted': count})

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on multiple notifications"""
        serializer = NotificationBulkActionSerializer(data=request.data)
        if serializer.is_valid():
            notification_ids = serializer.validated_data['notification_ids']
            action_type = serializer.validated_data['action']
            
            queryset = self.get_queryset().filter(id__in=notification_ids)
            count = queryset.count()
            
            if action_type == 'mark_read':
                queryset.update(is_read=True)
                invalidate_unread_count_cache(request.user.id)
                return Response({'marked_read': count})
            elif action_type == 'mark_unread':
                queryset.update(is_read=False)
                invalidate_unread_count_cache(request.user.id)
                return Response({'marked_unread': count})
            elif action_type == 'delete':
                queryset.delete()
                invalidate_unread_count_cache(request.user.id)
                return Response({'deleted': count})
            else:
                return Response(
                    {'error': 'Invalid action'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
