from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from notifications.models import PushSubscription, NotificationObject
from notifications.notifications.registry import NotificationStatuses
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
from notifications.services.preference_service import NotificationPreferenceService
from .serializers import (
    NotificationSerializer,
    NotificationUpdateSerializer,
    NotificationBulkActionSerializer,
    SubscriptionSerializer,
    UnsubscribeSerializer
)
from .filters import NotificationFilter
from .services.subscription_service import SubscriptionService
from .rendering import render_notification


@login_required
def expand_notification(request, notif_id):
    """Get expanded actor list for aggregated notification."""
    try:
        notification = NotificationObject.objects.get(
            notification_id=notif_id,
            recipient=request.user
        )
        from notifications.rendering.adapters import get_payload_adapter
        
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        # Render the expanded actors list
        return render(request, 'notifications/partials/expanded_actors.html', {
            'payload': payload
        })
    except NotificationObject.DoesNotExist:
        return HttpResponse('')


@login_required
def notifications_list(request):
    notification_type = request.GET.get('type')
    is_read_param = request.GET.get('read')
    cursor = request.GET.get('cursor')
    limit = int(request.GET.get('limit', 10))
    grouped_param = request.GET.get('grouped', 'false')
    time_filter = request.GET.get('time', 'all')
    sender_grouped_param = request.GET.get('sender_grouped', 'false')
    hybrid_grouped_param = request.GET.get('hybrid_grouped', 'false')
    search_query = request.GET.get('search', '')
    partial = request.GET.get('partial', 'false')
    
    is_read = None
    if is_read_param == 'true':
        is_read = True
    elif is_read_param == 'false':
        is_read = False
    
    grouped = grouped_param == 'true'
    sender_grouped = sender_grouped_param == 'true'
    hybrid_grouped = hybrid_grouped_param == 'true'
    
    # Use time-based grouping by default (unless explicitly overridden)
    if sender_grouped:
        from notifications.queries.notification_queries import get_notifications_grouped_by_sender
        notifications = get_notifications_grouped_by_sender(
            request.user,
            notification_type=notification_type,
            is_read=is_read,
            search_query=search_query
        )
        context = {
            'notifications': notifications,
            'filter_type': notification_type,
            'filter_read': is_read,
            'current_filter_type': notification_type,
            'current_filter_read': is_read_param,
            'current_grouped': grouped_param,
            'current_sender_grouped': sender_grouped_param,
            'current_hybrid_grouped': hybrid_grouped_param,
            'has_pagination': False,
            'unread_notifications_count': get_cached_unread_count(request.user),
            'time_filter': 'all',
            'search_query': search_query,
            'next_cursor': None
        }
    elif grouped:
        from notifications.queries.notification_queries import get_grouped_notifications
        notifications = get_grouped_notifications(
            request.user,
            notification_type=notification_type,
            is_read=is_read,
            search_query=search_query
        )
        context = {
            'notifications': notifications,
            'filter_type': notification_type,
            'filter_read': is_read,
            'current_filter_type': notification_type,
            'current_filter_read': is_read_param,
            'current_grouped': grouped_param,
            'current_sender_grouped': sender_grouped_param,
            'current_hybrid_grouped': hybrid_grouped_param,
            'has_pagination': False,
            'unread_notifications_count': get_cached_unread_count(request.user),
            'time_filter': 'all',
            'search_query': search_query,
            'next_cursor': None
        }
    elif hybrid_grouped:
        from notifications.queries.notification_queries import get_notifications_hybrid_grouped
        notifications = get_notifications_hybrid_grouped(
            request.user,
            notification_type=notification_type,
            is_read=is_read,
            search_query=search_query
        )
        context = {
            'notifications': notifications,
            'filter_type': notification_type,
            'filter_read': is_read,
            'current_filter_type': notification_type,
            'current_filter_read': is_read_param,
            'current_grouped': grouped_param,
            'current_sender_grouped': sender_grouped_param,
            'current_hybrid_grouped': hybrid_grouped_param,
            'has_pagination': False,
            'unread_notifications_count': get_cached_unread_count(request.user),
            'time_filter': 'all',
            'search_query': search_query,
            'next_cursor': None
        }
    else:
        # Default: use time-based grouping with cursor pagination
        from notifications.queries.notification_queries import get_notifications_by_time_periods
        time_grouped, next_cursor = get_notifications_by_time_periods(
            request.user,
            notification_type=notification_type,
            is_read=is_read,
            search_query=search_query,
            cursor=cursor,
            limit=limit
        )
        context = {
            'time_grouped': time_grouped,
            'time_filter': 'all',
            'filter_type': notification_type,
            'filter_read': is_read,
            'current_filter_type': notification_type,
            'current_filter_read': is_read_param,
            'current_grouped': grouped_param,
            'current_sender_grouped': sender_grouped_param,
            'current_hybrid_grouped': hybrid_grouped_param,
            'has_pagination': False,
            'unread_notifications_count': get_cached_unread_count(request.user),
            'search_query': search_query,
            'next_cursor': next_cursor
        }
    
    # If partial request, return JSON for infinite scroll
    if partial == 'true':
        from notifications.rendering.adapters import get_payload_adapter
        
        html_content = ''
        total_count = 0
        
        if 'time_grouped' in context:
            # Render time-grouped notifications with section headers
            period_names = {
                'now': 'Now',
                'earlier_today': 'Earlier Today',
                'yesterday': 'Yesterday',
                'this_week': 'This Week',
                'last_week': 'Last Week',
                'earlier': 'Earlier'
            }
            
            for period, notifications in context['time_grouped'].items():
                if notifications:
                    total_count += len(notifications)
                    # Add section header
                    html_content += f'<div class="time-section"><div class="time-section-header"><h6 class="fw-bold text-uppercase text-muted small mb-2 px-2">{period_names.get(period, period)}</h6></div>'
                    
                    # Render notification cards for this period
                    for notif in notifications:
                        html_content += render_notification(notif)
                    
                    html_content += '</div>'
        
        return JsonResponse({
            'html': html_content,
            'next_cursor': context.get('next_cursor'),
            'has_more': context.get('next_cursor') is not None,
            'count': total_count
        })
    
    return render(request, 'notifications/notifications.html', context)


@login_required
def unread_notification_count(request):
    html = build_unread_notification_html(request.user)
    return HttpResponse(html)


@login_required
def resource_preview(request, notif_id):
    """Get resource preview for a notification."""
    try:
        notification = NotificationObject.objects.get(
            notification_id=notif_id,
            recipient=request.user
        )
        from notifications.rendering.adapters import get_payload_adapter
        
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        # Generate preview HTML based on resource type
        if payload.get('resource'):
            resource = payload['resource']
            context = {
                'resource': resource,
                'notification': notification
            }
            return render(request, 'notifications/partials/resource_preview.html', context)
        else:
            return HttpResponse('')
    except NotificationObject.DoesNotExist:
        return HttpResponse('')


@login_required
def mark_notification_as_read(request, notif_id):
    try:
        notification = NotificationObject.objects.get(
            notification_id=notif_id,
            recipient=request.user
        )
        notification.status = NotificationStatuses.READ.value
        notification.save(update_fields=['status'])
        invalidate_unread_count_cache(request.user.id)
    except NotificationObject.DoesNotExist:
        pass
    
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
        NotificationObject.objects.filter(
            recipient=request.user,
            status=NotificationStatuses.CREATED.value
        ).update(status=NotificationStatuses.READ.value)
        invalidate_unread_count_cache(request.user.id)
    return HttpResponse('')


@login_required
def delete_notification(request, notif_id):
    if request.method == 'POST':
        try:
            notification = NotificationObject.objects.get(
                notification_id=notif_id,
                recipient=request.user
            )
            notification.delete()
            invalidate_unread_count_cache(request.user.id)
        except NotificationObject.DoesNotExist:
            pass
        
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
        NotificationObject.objects.filter(recipient=request.user).delete()
        invalidate_unread_count_cache(request.user.id)
    return HttpResponse('')


@login_required
def delete_read_notifications(request):
    if request.method == 'POST':
        NotificationObject.objects.filter(
            recipient=request.user,
            status=NotificationStatuses.READ.value
        ).delete()
        invalidate_unread_count_cache(request.user.id)
    return HttpResponse('')


@login_required
@require_http_methods(["POST"])
def set_do_not_disturb(request):
    """Set do not disturb for a duration"""
    import json
    try:
        data = json.loads(request.body)
        hours = data.get('hours', 1)
        
        NotificationPreferenceService.set_do_not_disturb(request.user, hours)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def clear_do_not_disturb(request):
    """Clear do not disturb"""
    try:
        NotificationPreferenceService.clear_do_not_disturb(request.user)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# API ViewSets
class NotificationViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for NotificationObject model (new notification engine).
    """
    queryset = NotificationObject.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = NotificationFilter
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer

    def get_queryset(self):
        # Users can only see their own notifications
        return NotificationObject.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count for current user"""
        count = self.get_queryset().filter(status=NotificationStatuses.CREATED.value).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        count = self.get_queryset().filter(status=NotificationStatuses.CREATED.value).update(
            status=NotificationStatuses.READ.value
        )
        invalidate_unread_count_cache(request.user.id)
        return Response({'marked_read': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a specific notification as read"""
        notification = self.get_object()
        notification.status = NotificationStatuses.READ.value
        notification.save()
        invalidate_unread_count_cache(request.user.id)
        return Response({'status': 'marked as read'})

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """Mark a specific notification as unread"""
        notification = self.get_object()
        notification.status = NotificationStatuses.CREATED.value
        notification.save()
        invalidate_unread_count_cache(request.user.id)
        return Response({'status': 'marked as unread'})

    @action(detail=True, methods=['get'])
    def rendered_payload(self, request, pk=None):
        """Get the rendered payload for a specific notification (for testing)"""
        notification = self.get_object()
        from notifications.rendering.adapters import get_payload_adapter
        
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        return Response({
            'notification_id': str(notification.notification_id),
            'payload': payload
        })

    @action(detail=False, methods=['get'])
    def list_rendered(self, request):
        """Get list of notifications with rendered payloads (for testing)"""
        notifications = self.get_queryset()
        from notifications.rendering.adapters import get_payload_adapter
        
        rendered = []
        for notification in notifications[:10]:  # Limit to 10 for testing
            adapter = get_payload_adapter(notification)
            payload = adapter.to_standard_payload(notification)
            rendered.append({
                'notification_id': str(notification.notification_id),
                'payload': payload
            })
        
        return Response({
            'count': len(rendered),
            'notifications': rendered
        })

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
        queryset = self.get_queryset().filter(status=NotificationStatuses.READ.value)
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
            
            queryset = self.get_queryset().filter(notification_id__in=notification_ids)
            count = queryset.count()
            
            if action_type == 'mark_read':
                queryset.update(status=NotificationStatuses.READ.value)
                invalidate_unread_count_cache(request.user.id)
                return Response({'marked_read': count})
            elif action_type == 'mark_unread':
                queryset.update(status=NotificationStatuses.CREATED.value)
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


# Push Notification Views
from django.conf import settings
from rest_framework.views import APIView


class VapidPublicKeyView(APIView):
    """
    Public endpoint to expose VAPID public key for web push subscriptions.
    No authentication required as the public key is safe to expose.
    """
    permission_classes = []

    def get(self, request):
        """Return the VAPID public key from Django settings."""
        public_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')
        if not public_key:
            return Response(
                {'error': 'VAPID public key not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({'public_key': public_key})


class SubscribeView(APIView):
    """
    Endpoint for users to subscribe to push notifications.
    Requires authentication. Handles deduplication by endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create or update a push subscription for the authenticated user."""
        serializer = SubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                subscription = SubscriptionService.subscribe(
                    user=request.user,
                    validated_data=serializer.validated_data
                )
                return Response(
                    {
                        'status': 'subscribed',
                        'subscription_id': subscription.id,
                        'is_active': subscription.is_active
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnsubscribeView(APIView):
    """
    Endpoint for users to unsubscribe from push notifications.
    Requires authentication. Performs soft delete by setting is_active=False.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Deactivate a push subscription for the authenticated user."""
        serializer = UnsubscribeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                subscription = SubscriptionService.unsubscribe(
                    user=request.user,
                    endpoint=serializer.validated_data['endpoint']
                )
                return Response(
                    {
                        'status': 'unsubscribed',
                        'subscription_id': subscription.id,
                        'is_active': subscription.is_active
                    },
                    status=status.HTTP_200_OK
                )
            except PushSubscription.DoesNotExist:
                return Response(
                    {'error': 'Subscription not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
