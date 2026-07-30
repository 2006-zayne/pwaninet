from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notifications

def get_notifications_for_user(user, notification_type=None, is_read=None):
    queryset = user.notifications.all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    return queryset.order_by('-timestamp')


def get_notifications_by_time_periods(user, notification_type=None, is_read=None):
    """
    Group notifications by smart time periods: Just now, Today, Yesterday, Earlier
    """
    queryset = user.notifications.select_related('sender', 'post', 'group').all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    one_hour_ago = now - timedelta(hours=1)
    
    notifications = queryset.order_by('-timestamp')
    
    grouped = {
        'just_now': [],
        'today': [],
        'yesterday': [],
        'earlier': []
    }
    
    for notif in notifications:
        if notif.timestamp >= one_hour_ago:
            grouped['just_now'].append(notif)
        elif notif.timestamp >= today_start:
            grouped['today'].append(notif)
        elif notif.timestamp >= yesterday_start:
            grouped['yesterday'].append(notif)
        else:
            grouped['earlier'].append(notif)
    
    return grouped


def get_grouped_notifications(user, notification_type=None, is_read=None):
    """
    Group notifications by type and related object (post/group).
    Returns a list of grouped notification data with avatar information.
    """
    queryset = user.notifications.select_related('sender', 'post', 'group').all()
    
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
                'senders': [],
                'sender_avatars': [],
                'count': 0,
                'is_read': notif.is_read,
                'latest_timestamp': notif.timestamp
            }
        
        grouped[group_key]['notifications'].append(notif)
        grouped[group_key]['count'] += 1
        
        # Track unique senders and their avatars
        if notif.sender.id not in [s.id for s in grouped[group_key]['senders']]:
            grouped[group_key]['senders'].append(notif.sender)
            grouped[group_key]['sender_avatars'].append({
                'username': notif.sender.username,
                'profile_pic': notif.sender.profile_pic.url if notif.sender.profile_pic else None
            })
        
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


def get_notifications_grouped_by_sender(user, notification_type=None, is_read=None):
    """
    Group notifications by sender (person).
    Returns a list of sender groups with their activities.
    """
    queryset = user.notifications.select_related('sender', 'post', 'group').all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    # Group by sender
    grouped = {}
    
    for notif in queryset.order_by('-timestamp'):
        sender_id = notif.sender.id
        
        if sender_id not in grouped:
            grouped[sender_id] = {
                'sender': notif.sender,
                'sender_avatar': {
                    'username': notif.sender.username,
                    'profile_pic': notif.sender.profile_pic.url if notif.sender.profile_pic else None
                },
                'notifications': [],
                'unread_count': 0,
                'total_count': 0,
                'latest_timestamp': notif.timestamp
            }
        
        grouped[sender_id]['notifications'].append(notif)
        grouped[sender_id]['total_count'] += 1
        if not notif.is_read:
            grouped[sender_id]['unread_count'] += 1
        if notif.timestamp > grouped[sender_id]['latest_timestamp']:
            grouped[sender_id]['latest_timestamp'] = notif.timestamp
    
    # Convert to list and sort by latest timestamp
    grouped_list = list(grouped.values())
    grouped_list.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return grouped_list


def get_notifications_hybrid_grouped(user, notification_type=None, is_read=None):
    """
    Hybrid grouping: Group by activity type/object, but if a single sender has multiple
    activities in that group, display as sender-grouped. Otherwise show activity-grouped
    with overlapping avatars.
    """
    queryset = user.notifications.select_related('sender', 'post', 'group').all()
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        queryset = queryset.filter(is_read=is_read)
    
    # First group by activity (type + post + group)
    activity_groups = {}
    
    for notif in queryset.order_by('-timestamp'):
        group_key = (notif.notification_type, notif.post_id, notif.group_id)
        
        if group_key not in activity_groups:
            activity_groups[group_key] = {
                'notification_type': notif.notification_type,
                'post': notif.post,
                'group': notif.group,
                'notifications': [],
                'senders': [],
                'sender_avatars': [],
                'count': 0,
                'is_read': notif.is_read,
                'latest_timestamp': notif.timestamp
            }
        
        activity_groups[group_key]['notifications'].append(notif)
        activity_groups[group_key]['count'] += 1
        
        # Track unique senders
        if notif.sender.id not in [s.id for s in activity_groups[group_key]['senders']]:
            activity_groups[group_key]['senders'].append(notif.sender)
            activity_groups[group_key]['sender_avatars'].append({
                'username': notif.sender.username,
                'profile_pic': notif.sender.profile_pic.url if notif.sender.profile_pic else None
            })
        
        if notif.timestamp > activity_groups[group_key]['latest_timestamp']:
            activity_groups[group_key]['latest_timestamp'] = notif.timestamp
        if not notif.is_read:
            activity_groups[group_key]['is_read'] = False
    
    # Convert to list and determine display mode for each group
    result = []
    for group in activity_groups.values():
        # If only 1 sender with multiple notifications, convert to sender-grouped format
        if len(group['senders']) == 1 and group['count'] > 1:
            sender = group['senders'][0]
            sender_group = {
                'sender': sender,
                'sender_avatar': group['sender_avatars'][0],
                'notifications': group['notifications'],
                'unread_count': sum(1 for n in group['notifications'] if not n.is_read),
                'total_count': group['count'],
                'latest_timestamp': group['latest_timestamp'],
                'display_mode': 'sender_grouped'
            }
            result.append(sender_group)
        else:
            # Use activity-grouped format
            group['display_mode'] = 'activity_grouped'
            result.append(group)
    
    # Sort by latest timestamp
    result.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return result

