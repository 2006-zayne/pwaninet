from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from notifications.models import NotificationObject
from notifications.notifications.registry import NotificationStatuses

def get_notifications_for_user(user, notification_type=None, is_read=None, search_query=None):
    queryset = NotificationObject.objects.filter(recipient=user)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        # Map is_read to status: True -> READ, False -> CREATED
        status = NotificationStatuses.READ.value if is_read else NotificationStatuses.CREATED.value
        queryset = queryset.filter(status=status)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    return queryset.order_by('-updated_at')


def get_notifications_by_time_periods(user, notification_type=None, is_read=None, search_query=None, cursor=None, limit=20):
    """
    Group notifications by smart time periods: Now, Earlier Today, Yesterday, This Week, Last Week, Earlier
    Per specification: Section 3.4
    
    Args:
        user: The user to fetch notifications for
        notification_type: Optional filter by notification type
        is_read: Optional filter by read status
        search_query: Optional search query
        cursor: Optional cursor for pagination (timestamp string)
        limit: Maximum number of notifications to return per page
    """
    queryset = NotificationObject.objects.filter(recipient=user)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        status = NotificationStatuses.READ.value if is_read else NotificationStatuses.CREATED.value
        queryset = queryset.filter(status=status)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # Apply cursor-based pagination
    if cursor:
        from datetime import datetime
        try:
            # Cursor format: "timestamp|notification_id" (ISO timestamp with colons)
            # Split on pipe to separate timestamp from UUID
            cursor_parts = cursor.split('|')
            cursor_time_str = cursor_parts[0]
            cursor_id = cursor_parts[1] if len(cursor_parts) > 1 else None
            cursor_time = datetime.fromisoformat(cursor_time_str)
            
            if cursor_id:
                # Filter: get notifications with updated_at < cursor_time OR (updated_at = cursor_time AND notification_id < cursor_id)
                # This ensures we get only notifications that come after the cursor position
                queryset = queryset.filter(
                    Q(updated_at__lt=cursor_time) | 
                    Q(updated_at=cursor_time, notification_id__lt=cursor_id)
                )
            else:
                # Fallback to timestamp only
                queryset = queryset.filter(updated_at__lt=cursor_time)
        except (ValueError, TypeError):
            # Invalid cursor, ignore
            pass
    
    # Get one extra notification to determine if there are more results
    notifications_list = list(queryset.order_by('-updated_at')[:limit + 1])
    
    # Determine if there are more results
    has_more = len(notifications_list) > limit
    notifications = notifications_list[:limit]
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=now.weekday())  # Monday
    last_week_start = week_start - timedelta(weeks=1)
    
    grouped = {
        'now': [],
        'earlier_today': [],
        'yesterday': [],
        'this_week': [],
        'last_week': [],
        'earlier': []
    }
    
    next_cursor = None
    
    for notif in notifications:
        # Now: within the last hour
        if notif.created_at >= now - timedelta(hours=1):
            grouped['now'].append(notif)
        # Earlier Today: today but more than 1 hour ago
        elif notif.created_at >= today_start:
            grouped['earlier_today'].append(notif)
        # Yesterday
        elif notif.created_at >= yesterday_start:
            grouped['yesterday'].append(notif)
        # This Week: this week but before yesterday
        elif notif.created_at >= week_start:
            grouped['this_week'].append(notif)
        # Last Week: last week
        elif notif.created_at >= last_week_start:
            grouped['last_week'].append(notif)
        # Earlier: everything else
        else:
            grouped['earlier'].append(notif)
    
    # Set next cursor based on the last notification's updated_at and notification_id
    if notifications and has_more:
        next_cursor = f"{notifications[-1].updated_at.isoformat()}|{notifications[-1].notification_id}"
    
    return grouped, next_cursor


def get_grouped_notifications(user, notification_type=None, is_read=None, search_query=None):
    """
    Group notifications by type and related object (post/group).
    Returns a list of grouped notification data with avatar information.
    """
    queryset = NotificationObject.objects.filter(recipient=user)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        status = NotificationStatuses.READ.value if is_read else NotificationStatuses.CREATED.value
        queryset = queryset.filter(status=status)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # Group by notification_type and context
    grouped = {}
    
    for notif in queryset.order_by('-updated_at'):
        # Create a grouping key
        group_key = (notif.notification_type, notif.context_type, notif.context_id)
        
        if group_key not in grouped:
            grouped[group_key] = {
                'notification_type': notif.notification_type,
                'context_type': notif.context_type,
                'context_id': notif.context_id,
                'notifications': [],
                'count': 0,
                'status': notif.status,
                'latest_timestamp': notif.created_at
            }
        
        grouped[group_key]['notifications'].append(notif)
        grouped[group_key]['count'] += 1
        
        if notif.created_at > grouped[group_key]['latest_timestamp']:
            grouped[group_key]['latest_timestamp'] = notif.created_at
        if notif.status == NotificationStatuses.CREATED.value:
            grouped[group_key]['is_read'] = False
    
    # Convert to list and sort by latest timestamp
    grouped_list = list(grouped.values())
    grouped_list.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return grouped_list


def mark_user_notifications_as_read(user):
    return NotificationObject.objects.filter(
        recipient=user,
        status=NotificationStatuses.CREATED.value
    ).update(status=NotificationStatuses.READ.value)


def get_unread_count(user):
    # Count all notifications that are not yet read
    # This includes CREATED, QUEUED, DELIVERED, and SEEN statuses
    count = NotificationObject.objects.filter(
        recipient=user
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).count()
    return count


def get_unread_count_by_user_id(user_id):
    # Count all notifications that are not yet read for a user ID
    # This includes CREATED, QUEUED, DELIVERED, and SEEN statuses
    count = NotificationObject.objects.filter(
        recipient_id=user_id
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).count()
    return count


def get_notification_for_user(user, notif_id):
    return NotificationObject.objects.filter(
        notification_id=notif_id,
        recipient=user
    ).first()


def get_unread_count_by_type(user, notification_type):
    # Count all notifications that are not yet read for a specific type
    return NotificationObject.objects.filter(
        recipient=user,
        notification_type=notification_type
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).count()


def delete_notification(user, notif_id):
    notification = get_notification_for_user(user, notif_id)
    if notification:
        notification.delete()
    return notification


def delete_all_notifications(user):
    return NotificationObject.objects.filter(recipient=user).delete()


def delete_read_notifications(user):
    return NotificationObject.objects.filter(
        recipient=user,
        status=NotificationStatuses.READ.value
    ).delete()


def get_unread_count_by_group(user, group_id):
    # Count all notifications that are not yet read for a specific group
    return NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id=group_id
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).count()


def get_unread_counts_for_groups(user, group_ids):
    """
    Get unread notification counts for multiple groups at once.
    Returns a dictionary mapping group_id -> count.
    Counts ALL notifications related to groups (not just specific types).
    """
    if not group_ids:
        return {}
    
    counts = NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=group_ids
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).values('context_id').annotate(
        count=Count('notification_id')
    )
    
    return {item['context_id']: item['count'] for item in counts}


def get_notifications_grouped_by_sender(user, notification_type=None, is_read=None, search_query=None):
    """
    Group notifications by sender (person).
    Returns a list of sender groups with their activities.
    """
    queryset = NotificationObject.objects.filter(recipient=user)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        status = NotificationStatuses.READ.value if is_read else NotificationStatuses.CREATED.value
        queryset = queryset.filter(status=status)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # Group by sender (extracted from metadata)
    grouped = {}
    
    for notif in queryset.order_by('-updated_at'):
        # Extract actor from metadata
        actor_id = notif.metadata.get('actor_id') if notif.metadata else None
        if not actor_id:
            continue
        
        sender_id = actor_id
        
        if sender_id not in grouped:
            # Extract sender info from metadata
            actor_username = notif.metadata.get('actor_username') if notif.metadata else 'Unknown'
            
            grouped[sender_id] = {
                'sender_id': sender_id,
                'sender_username': actor_username,
                'notifications': [],
                'unread_count': 0,
                'total_count': 0,
                'latest_timestamp': notif.created_at
            }
        
        grouped[sender_id]['notifications'].append(notif)
        grouped[sender_id]['total_count'] += 1
        if notif.status == NotificationStatuses.CREATED.value:
            grouped[sender_id]['unread_count'] += 1
        if notif.created_at > grouped[sender_id]['latest_timestamp']:
            grouped[sender_id]['latest_timestamp'] = notif.created_at
    
    # Convert to list and sort by latest timestamp
    grouped_list = list(grouped.values())
    grouped_list.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return grouped_list


def get_notifications_hybrid_grouped(user, notification_type=None, is_read=None, search_query=None):
    """
    Hybrid grouping: Group by activity type/object, but if a single sender has multiple
    activities in that group, display as sender-grouped. Otherwise show activity-grouped
    with overlapping avatars.
    """
    queryset = NotificationObject.objects.filter(recipient=user)
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        status = NotificationStatuses.READ.value if is_read else NotificationStatuses.CREATED.value
        queryset = queryset.filter(status=status)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # First group by activity (type + context)
    activity_groups = {}
    
    for notif in queryset.order_by('-updated_at'):
        group_key = (notif.notification_type, notif.context_type, notif.context_id)
        
        if group_key not in activity_groups:
            activity_groups[group_key] = {
                'notification_type': notif.notification_type,
                'context_type': notif.context_type,
                'context_id': notif.context_id,
                'notifications': [],
                'actors': [],  # Changed from senders to actors
                'count': 0,
                'is_read': notif.status == NotificationStatuses.READ.value,
                'latest_timestamp': notif.created_at
            }
        
        activity_groups[group_key]['notifications'].append(notif)
        activity_groups[group_key]['count'] += 1
        
        # Track unique actors (from metadata)
        actor_id = notif.metadata.get('actor_id') if notif.metadata else None
        if actor_id and actor_id not in activity_groups[group_key]['actors']:
            activity_groups[group_key]['actors'].append(actor_id)
        
        if notif.created_at > activity_groups[group_key]['latest_timestamp']:
            activity_groups[group_key]['latest_timestamp'] = notif.created_at
        if notif.status == NotificationStatuses.CREATED.value:
            activity_groups[group_key]['is_read'] = False
    
    # Convert to list and determine display mode for each group
    result = []
    for group in activity_groups.values():
        # If only 1 actor with multiple notifications, convert to actor-grouped format
        if len(group['actors']) == 1 and group['count'] > 1:
            actor_group = {
                'actor_id': group['actors'][0],
                'notifications': group['notifications'],
                'unread_count': sum(1 for n in group['notifications'] if n.status == NotificationStatuses.CREATED.value),
                'total_count': group['count'],
                'latest_timestamp': group['latest_timestamp'],
                'display_mode': 'actor_grouped'
            }
            result.append(actor_group)
        else:
            # Use activity-grouped format
            group['display_mode'] = 'activity_grouped'
            result.append(group)
    
    # Sort by latest timestamp
    result.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return result

