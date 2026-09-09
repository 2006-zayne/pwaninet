import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods, require_POST
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
    mark_all_user_notifications_as_read,
    delete_single_notification,
    delete_all_user_notifications,
    delete_user_read_notifications,
    broadcast_unread_count,
    resolve_notification_target_url
)
logger = logging.getLogger(__name__)
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

    if request.headers.get('HX-Request') and partial != 'true':
        return render(request, 'notifications/partials/notifications_navigation_partial.html', context)

    return render(request, 'notifications/notifications.html', context)


@login_required
def unread_notification_count(request):
    count = get_cached_unread_count(request.user)
    if request.GET.get('format') == 'json' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({'unread_count': count, 'count': count})
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
    notification = mark_single_notification_as_read(request.user, notif_id)

    # Return updated notification item
    context = {
        'notifications': [notification] if notification else []
    }
    context['unread_notifications_count'] = get_cached_unread_count(request.user)
    response = render(request, 'notifications/partials/notification_list_items.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


def open_notification(request, notif_id):
    """
    Handle clicking on a notification popup or link (/notifications/<notif_id>/).
    Marks the notification as read and redirects the user to the destination page.
    """
    notification = None
    try:
        if request.user.is_authenticated:
            notification = mark_single_notification_as_read(request.user, notif_id)
            if not notification:
                # In case notification belongs to user but under different query or edge case
                notification = NotificationObject.objects.filter(notification_id=notif_id).first()
                if notification and notification.recipient_id == request.user.id:
                    notification.status = 'READ'
                    notification.save(update_fields=['status'])
                    invalidate_unread_count_cache(request.user.id)
                    broadcast_unread_count(request.user.id)
        else:
            notification = NotificationObject.objects.filter(notification_id=notif_id).first()
            if notification and notification.status != 'READ':
                notification.status = 'READ'
                notification.save(update_fields=['status'])
                invalidate_unread_count_cache(notification.recipient_id)
                broadcast_unread_count(notification.recipient_id)
    except Exception as e:
        logger.warning(f"Error opening notification {notif_id}: {e}")

    destination = resolve_notification_target_url(notification)
    return redirect(destination)


@login_required
@require_http_methods(["POST"])
def follow_back_from_notification(request, notif_id):
    try:
        notification = NotificationObject.objects.get(
            notification_id=notif_id,
            recipient=request.user
        )
    except NotificationObject.DoesNotExist:
        return HttpResponse('')

    metadata = notification.metadata or {}
    actor_id = metadata.get('actor_id')
    target_user = None
    if actor_id:
        from users.models import User
        target_user = User.objects.filter(id=actor_id).first()
    if not target_user:
        actor_username = metadata.get('actor_username')
        if actor_username:
            from users.models import User
            target_user = User.objects.filter(username=actor_username).first()

    if target_user and target_user != request.user:
        from users.models import Follow
        Follow.objects.get_or_create(follower=request.user, followed=target_user)
        invalidate_unread_count_cache(target_user.id)
        from users.services.friend_suggestion_service import invalidate_friend_suggestions_cache
        invalidate_friend_suggestions_cache(request.user.id)

    # Mark notification as read and broadcast
    if notification.status != NotificationStatuses.READ.value:
        notification = mark_single_notification_as_read(request.user, notif_id)

    rendered_html = render_notification(notification)
    response = HttpResponse(rendered_html)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
@require_http_methods(["POST"])
def pinch_from_notification(request, notif_id):
    try:
        notification = NotificationObject.objects.get(
            notification_id=notif_id,
            recipient=request.user
        )
    except NotificationObject.DoesNotExist:
        return HttpResponse('')

    metadata = notification.metadata or {}
    actor_id = metadata.get('actor_id')
    target_user = None
    if actor_id:
        from users.models import User
        target_user = User.objects.filter(id=actor_id).first()
    if not target_user:
        actor_username = metadata.get('actor_username')
        if actor_username:
            from users.models import User
            target_user = User.objects.filter(username=actor_username).first()

    if target_user and target_user != request.user:
        from users.models import Pinch
        can_pinch, error_msg = Pinch.can_pinch(request.user, target_user)
        if can_pinch:
            Pinch.objects.create(pinch_user=request.user, pinched_user=target_user)
            invalidate_unread_count_cache(target_user.id)

    # Mark notification as read and broadcast
    if notification.status != NotificationStatuses.READ.value:
        notification = mark_single_notification_as_read(request.user, notif_id)

    rendered_html = render_notification(notification)
    response = HttpResponse(rendered_html)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
def mark_all_as_read(request):
    if request.method == 'POST':
        mark_all_user_notifications_as_read(request.user)
    from notifications.queries.notification_queries import get_notifications_by_time_periods
    time_grouped, next_cursor = get_notifications_by_time_periods(request.user)
    context = {
        'time_grouped': time_grouped,
        'time_filter': 'all',
        'unread_notifications_count': 0,
        'next_cursor': next_cursor
    }
    response = render(request, 'notifications/partials/notification_list_time_grouped.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


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


@login_required
def delete_all_notifications(request):
    if request.method == 'POST':
        delete_all_user_notifications(request.user)
    context = {
        'time_grouped': {},
        'notifications': [],
        'unread_notifications_count': 0,
        'next_cursor': None,
    }
    response = render(request, 'notifications/partials/notification_list_time_grouped.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
def delete_read_notifications(request):
    if request.method == 'POST':
        delete_user_read_notifications(request.user)
    from notifications.queries.notification_queries import get_notifications_by_time_periods
    time_grouped, next_cursor = get_notifications_by_time_periods(request.user)
    context = {
        'time_grouped': time_grouped,
        'time_filter': 'all',
        'unread_notifications_count': get_cached_unread_count(request.user),
        'next_cursor': next_cursor
    }
    response = render(request, 'notifications/partials/notification_list_time_grouped.html', context)
    response['HX-Trigger'] = 'updateUnreadCount'
    return response


@login_required
@require_http_methods(["POST"])
def bulk_action(request):
    """Handle bulk actions from selection mode: mark_read, delete"""
    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    action = data.get('action')
    notification_ids = data.get('notification_ids', [])

    if not notification_ids:
        return JsonResponse({'success': False, 'error': 'No notifications selected'}, status=400)

    queryset = NotificationObject.objects.filter(
        recipient=request.user,
        notification_id__in=notification_ids
    )
    count = queryset.count()

    if action == 'mark_read':
        queryset.exclude(
            status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
        ).update(status=NotificationStatuses.READ.value)
        invalidate_unread_count_cache(request.user.id)
        broadcast_unread_count(request.user.id)
        return JsonResponse({'success': True, 'action': 'mark_read', 'marked_read': count, 'count': count})
    elif action == 'delete':
        queryset.delete()
        invalidate_unread_count_cache(request.user.id)
        broadcast_unread_count(request.user.id)
        return JsonResponse({'success': True, 'action': 'delete', 'deleted': count, 'count': count})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)


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
                broadcast_unread_count(request.user.id)
                return Response({'success': True, 'marked_read': count, 'count': count})
            elif action_type == 'mark_unread':
                queryset.update(status=NotificationStatuses.CREATED.value)
                invalidate_unread_count_cache(request.user.id)
                broadcast_unread_count(request.user.id)
                return Response({'success': True, 'marked_unread': count, 'count': count})
            elif action_type == 'delete':
                queryset.delete()
                invalidate_unread_count_cache(request.user.id)
                broadcast_unread_count(request.user.id)
                return Response({'success': True, 'deleted': count, 'count': count})
            else:
                return Response(
                    {'success': False, 'error': 'Invalid action'},
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
        return Response({
            'public_key': public_key,
            'publicKey': public_key,
            'configured': bool(public_key)
        })


class SubscribeView(APIView):
    """
    Endpoint for users to subscribe to push notifications.
    Supports both W3C WebPush (VAPID) subscriptions and Native FCM tokens.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Create or update a push subscription for the authenticated user."""
        try:
            payload = request.data if isinstance(request.data, dict) and request.data else {}
            if not payload and request.body:
                import json
                payload = json.loads(request.body)
        except Exception:
            return Response({'error': 'Invalid JSON body'}, status=status.HTTP_400_BAD_REQUEST)

        token_type = payload.get('token_type', PushSubscription.TokenType.VAPID)
        platform = payload.get('platform', PushSubscription.Platform.WEB)
        device_id = payload.get('device_id')
        user_agent = payload.get('user_agent', request.META.get('HTTP_USER_AGENT', ''))

        if token_type == PushSubscription.TokenType.VAPID:
            endpoint = payload.get('endpoint')
            keys = payload.get('keys', {})
            p256dh = keys.get('p256dh') or payload.get('p256dh')
            auth = keys.get('auth') or payload.get('auth')

            if not endpoint or not p256dh or not auth:
                return Response(
                    {'error': 'Missing required WebPush keys (endpoint, p256dh, auth)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sub, _ = PushSubscription.objects.update_or_create(
                user=request.user,
                endpoint=endpoint,
                defaults={
                    'platform': platform,
                    'token_type': PushSubscription.TokenType.VAPID,
                    'p256dh': p256dh,
                    'auth': auth,
                    'device_id': device_id,
                    'user_agent': user_agent,
                    'is_active': True,
                }
            )
        elif token_type == PushSubscription.TokenType.FCM:
            fcm_token = payload.get('fcm_token')
            if not fcm_token:
                return Response(
                    {'error': 'Missing required fcm_token'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            sub, _ = PushSubscription.objects.update_or_create(
                user=request.user,
                fcm_token=fcm_token,
                defaults={
                    'platform': platform or PushSubscription.Platform.ANDROID_NATIVE,
                    'token_type': PushSubscription.TokenType.FCM,
                    'device_id': device_id,
                    'user_agent': user_agent,
                    'is_active': True,
                }
            )
        else:
            return Response(
                {'error': f'Unsupported token_type: {token_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure user's push_enabled preference is True
        try:
            from notifications.models import NotificationPreference
            NotificationPreference.objects.filter(user=request.user).update(push_enabled=True)
        except Exception:
            pass

        return Response(
            {
                'status': 'success',
                'message': 'Push device registered successfully.',
                'subscription_id': sub.id,
                'is_active': sub.is_active
            },
            status=status.HTTP_200_OK
        )


@login_required
@require_POST
def subscribe_push(request):
    """
    Function view alternative for push subscription.
    """
    import json
    from django.http import HttpResponseBadRequest, JsonResponse

    try:
        payload = json.loads(request.body)
    except (ValueError, json.JSONDecodeError):
        return HttpResponseBadRequest("Invalid JSON body")

    token_type = payload.get('token_type', PushSubscription.TokenType.VAPID)
    platform = payload.get('platform', PushSubscription.Platform.WEB)
    device_id = payload.get('device_id')
    user_agent = payload.get('user_agent', request.META.get('HTTP_USER_AGENT', ''))

    if token_type == PushSubscription.TokenType.VAPID:
        endpoint = payload.get('endpoint')
        keys = payload.get('keys', {})
        p256dh = keys.get('p256dh') or payload.get('p256dh')
        auth = keys.get('auth') or payload.get('auth')

        if not endpoint or not p256dh or not auth:
            return HttpResponseBadRequest("Missing required WebPush keys (endpoint, p256dh, auth)")

        sub, _ = PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'platform': platform,
                'token_type': PushSubscription.TokenType.VAPID,
                'p256dh': p256dh,
                'auth': auth,
                'device_id': device_id,
                'user_agent': user_agent,
                'is_active': True,
            }
        )
    elif token_type == PushSubscription.TokenType.FCM:
        fcm_token = payload.get('fcm_token')
        if not fcm_token:
            return HttpResponseBadRequest("Missing required fcm_token")

        sub, _ = PushSubscription.objects.update_or_create(
            user=request.user,
            fcm_token=fcm_token,
            defaults={
                'platform': platform or PushSubscription.Platform.ANDROID_NATIVE,
                'token_type': PushSubscription.TokenType.FCM,
                'device_id': device_id,
                'user_agent': user_agent,
                'is_active': True,
            }
        )
    else:
        return HttpResponseBadRequest(f"Unsupported token_type: {token_type}")

    # Ensure user's push_enabled preference is True
    try:
        from notifications.models import NotificationPreference
        NotificationPreference.objects.filter(user=request.user).update(push_enabled=True)
    except Exception:
        pass

    return JsonResponse({'status': 'success', 'message': 'Push device registered successfully.', 'subscription_id': sub.id})


class UnsubscribeView(APIView):
    """
    Endpoint for users to unsubscribe from push notifications.
    Requires authentication. Performs soft delete by setting is_active=False.
    Supports unsubscribing by endpoint (WebPush) or fcm_token (Native).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Deactivate a push subscription for the authenticated user."""
        payload = request.data if isinstance(request.data, dict) and request.data else {}
        if not payload and request.body:
            import json
            try:
                payload = json.loads(request.body)
            except Exception:
                pass

        endpoint = payload.get('endpoint')
        fcm_token = payload.get('fcm_token')

        if not endpoint and not fcm_token:
            return Response(
                {'error': 'Must provide either endpoint or fcm_token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = 0
        if endpoint:
            updated += PushSubscription.objects.filter(
                user=request.user,
                endpoint=endpoint
            ).update(is_active=False)
        if fcm_token:
            updated += PushSubscription.objects.filter(
                user=request.user,
                fcm_token=fcm_token
            ).update(is_active=False)

        return Response(
            {
                'status': 'unsubscribed',
                'is_active': False,
                'updated_count': updated
            },
            status=status.HTTP_200_OK
        )
