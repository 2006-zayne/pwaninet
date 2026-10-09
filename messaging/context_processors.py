from django.core.cache import cache
from .models import ConversationMember, Message


def get_cached_unread_message_count(user):
    """
    Calculate and cache total unread direct message count for user.
    Uses Message.id indexing and a 30s cache TTL to prevent repeated DB hits.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return 0

    cache_key = f"msg:unread_count:user:{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    total_unread = 0
    members = ConversationMember.objects.filter(user=user).select_related('last_read_message')
    for member in members:
        qs = Message.objects.filter(conversation_id=member.conversation_id).exclude(sender_id=user.id)
        if member.last_read_message_id:
            qs = qs.filter(id__gt=member.last_read_message_id)
        total_unread += qs.count()

    cache.set(cache_key, total_unread, timeout=30)
    return total_unread


def invalidate_unread_message_count_cache(user_id):
    """Invalidate cached unread message count for a specific user."""
    cache.delete(f"msg:unread_count:user:{user_id}")


def messaging_nav_context(request):
    """
    Context processor to provide total unread direct messages count for navigation bars.
    Provides `unread_messages_count` integer globally.
    """
    if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
        return {
            'unread_messages_count': get_cached_unread_message_count(request.user)
        }
    return {
        'unread_messages_count': 0
    }
