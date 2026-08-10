from django.core.cache import cache
from notifications.models import NotificationObject
from notifications.notifications.registry import NotificationStatuses
from notifications.queries.notification_queries import (
    get_notification_for_user,
    get_notifications_for_user,
    get_unread_count,
    mark_user_notifications_as_read,
    delete_notification,
    delete_all_notifications,
    delete_read_notifications,
    get_grouped_notifications,
    get_unread_counts_for_groups
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def _unread_count_cache_key(user_id):
    return f'''notif:unread_count:user:{user_id}'''


def get_cached_unread_count(user):
    cache_key = _unread_count_cache_key(user.id)
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    count = get_unread_count(user)
    cache.set(cache_key, count, timeout=30)
    return count


def invalidate_unread_count_cache(user_id):
    cache.delete(_unread_count_cache_key(user_id))


def build_notifications_context(user, mark_read=False, notification_type=None, is_read=None, grouped=False, use_canonical_payload=False):
    if mark_read:
        mark_user_notifications_as_read(user)
        cache.set(_unread_count_cache_key(user.id), 0, timeout=30)
    
    if grouped:
        notifications = get_grouped_notifications(user, notification_type=notification_type, is_read=is_read)
    else:
        notifications = get_notifications_for_user(user, notification_type=notification_type, is_read=is_read)
    
    context = {
        'notifications': notifications,
        'filter_type': notification_type,
        'filter_read': is_read,
        'grouped': grouped,
        'use_canonical_payload': use_canonical_payload
    }
    
    return context


def build_unread_notification_html(user):
    count = get_cached_unread_count(user)
    html = '<span style="position: relative; display: inline-block;"><i class="bi bi-bell-fill"></i>'
    if count > 0:
        html += f'''\n            <span class="position-absolute badge rounded-pill bg-danger border border-light"\n                style="font-size: 0.65rem; padding: 0.3em 0.45em; min-width: 18px; text-align: center; top: -4px; right: -6px; z-index: 10;">\n                {count}\n                <span class="visually-hidden">unread messages</span>\n            </span>'''
    html += '</span><span style="font-size: 0.55rem; font-weight: 600; white-space: nowrap;">Notifications</span>'
    return html


def mark_single_notification_as_read(user, notif_id):
    notification = get_notification_for_user(user, notif_id)
    if notification:
        notification.status = NotificationStatuses.READ.value
        notification.save(update_fields=['status'])
        invalidate_unread_count_cache(user.id)
        invalidate_group_unread_cache(user.id)
        
        # Broadcast unread count update via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{user.id}",
            {
                'type': 'unread_count_update',
                'count': get_unread_count(user)
            }
        )
    return notification


def delete_single_notification(user, notif_id):
    notification = delete_notification(user, notif_id)
    if notification:
        invalidate_unread_count_cache(user.id)
        invalidate_group_unread_cache(user.id)
    return notification


def delete_all_user_notifications(user):
    delete_all_notifications(user)
    invalidate_unread_count_cache(user.id)
    invalidate_group_unread_cache(user.id)
    
    # Broadcast unread count update via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user.id}",
        {
            'type': 'unread_count_update',
            'count': 0
        }
    )


def delete_user_read_notifications(user):
    delete_read_notifications(user)
    invalidate_unread_count_cache(user.id)
    invalidate_group_unread_cache(user.id)
    
    # Broadcast unread count update via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notifications_{user.id}",
        {
            'type': 'unread_count_update',
            'count': get_unread_count(user)
        }
    )


def _group_unread_cache_key(user_id):
    return f'notif:group_unread:user:{user_id}'


def get_group_unread_counts(user, group_ids):
    """
    Get unread notification counts for multiple groups with caching.
    Returns a dictionary mapping group_id -> count.
    """
    cache_key = _group_unread_cache_key(user.id)
    cached_value = cache.get(cache_key)
    
    if cached_value is not None:
        # Filter cached results to only requested groups
        return {gid: cached_value.get(gid, 0) for gid in group_ids}
    
    # Query database
    counts = get_unread_counts_for_groups(user, group_ids)
    
    # Cache for 10 seconds
    cache.set(cache_key, counts, timeout=10)
    
    return counts


def invalidate_group_unread_cache(user_id):
    cache.delete(_group_unread_cache_key(user_id))
