# Source Generated with Decompyle++
# File: notification_service.cpython-312.pyc (Python 3.12)

from django.core.cache import cache
from core.queries.notification_queries import get_notification_for_user, get_notifications_for_user, get_unread_count, mark_user_notifications_as_read

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


def build_notifications_context(user, mark_read = (False,)):
    if mark_read:
        mark_user_notifications_as_read(user)
        cache.set(_unread_count_cache_key(user.id), 0, timeout = 30)
    return {
        'notifications': get_notifications_for_user(user) }


def build_unread_notification_html(user):
    count = get_cached_unread_count(user)
    html = '<i class="bi bi-bell-fill"></i>'
    if count > 0:
        html += f'''\n            <span class="position-absolute top-0 start-100 translate-middle\n            badge rounded-pill bg-danger border border-light"\n                style="font-size: 0.6rem; padding: 0.35em 0.5em;">\n                {count}\n            </span>'''
    return html


def mark_single_notification_as_read(user, notif_id):
    notification = get_notification_for_user(user, notif_id)
    if notification:
        notification.is_read = True
        notification.save(update_fields = [
            'is_read'])
        invalidate_unread_count_cache(user.id)
    return notification

