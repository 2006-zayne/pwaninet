from django.db.models import Count, Q
from notifications.models import Notifications

def get_notifications_for_user(user, notification_type=None, is_read=None):
    queryset = user.notifications.all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    return queryset.order_by('-timestamp')


def get_grouped_notifications(user, notification_type=None, is_read=None):
    """
    Group notifications by type and related object (post/group).
    Returns a list of grouped notification data.
    """
    queryset = user.notifications.all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    # Group by notification_type, post, and group
    grouped = {}
    
    for notif in queryset.order_by('-timestamp'):
        # Create a grouping key
        group_key = (notif.notification_type, notif.post_id, notif.group_id)
        
        if group_key not in grouped:
            grouped[group_key] = {
                'notification_type': notif.notification_type,
                'post': notif.post,
                'group': notif.group,
                'notifications': [],
                'count': 0,
                'is_read': notif.is_read,
                'latest_timestamp': notif.timestamp
            }
        
        grouped[group_key]['notifications'].append(notif)
        grouped[group_key]['count'] += 1
        if notif.timestamp > grouped[group_key]['latest_timestamp']:
            grouped[group_key]['latest_timestamp'] = notif.timestamp
        if not notif.is_read:
            grouped[group_key]['is_read'] = False
    
    # Convert to list and sort by latest timestamp
    grouped_list = list(grouped.values())
    grouped_list.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return grouped_list


def mark_user_notifications_as_read(user):
    return Notifications.objects.filter(recipient = user, is_read = False).update(is_read = True)


def get_unread_count(user):
    return user.notifications.filter(is_read = False).count()


def get_notification_for_user(user, notif_id):
    return Notifications.objects.filter(id = notif_id, recipient = user).first()


def get_unread_count_by_type(user, notification_type):
    return user.notifications.filter(is_read=False, notification_type=notification_type).count()


def delete_notification(user, notif_id):
    notification = get_notification_for_user(user, notif_id)
    if notification:
        notification.delete()
    return notification


def delete_all_notifications(user):
    return user.notifications.all().delete()


def delete_read_notifications(user):
    return user.notifications.filter(is_read=True).delete()


def get_unread_count_by_group(user, group_id):
    return user.notifications.filter(is_read=False, group_id=group_id).count()


def get_unread_counts_for_groups(user, group_ids):
    """
    Get unread notification counts for multiple groups at once.
    Returns a dictionary mapping group_id -> count.
    Counts ALL notifications related to groups (not just specific types).
    """
    if not group_ids:
        return {}
    
    counts = user.notifications.filter(
        is_read=False,
        group_id__in=group_ids
    ).values('group_id').annotate(
        count=Count('id')
    )
    
    return {item['group_id']: item['count'] for item in counts}

