from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from notifications.models import NotificationObject
from notifications.notifications.registry import NotificationStatuses

def get_notifications_for_user(user, notification_type=None, is_read=None, search_query=None):
    queryset = NotificationObject.objects.filter(recipient=user).exclude(
        status__in=[NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        if is_read:
            queryset = queryset.filter(status=NotificationStatuses.READ.value)
        else:
            queryset = queryset.exclude(status=NotificationStatuses.READ.value)
    
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
    queryset = NotificationObject.objects.filter(recipient=user).exclude(
        status__in=[NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        if is_read:
            queryset = queryset.filter(status=NotificationStatuses.READ.value)
        else:
            queryset = queryset.exclude(status=NotificationStatuses.READ.value)
    
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
        notif_time = notif.updated_at or notif.created_at
        # Now: within the last hour
        if notif_time >= now - timedelta(hours=1):
            grouped['now'].append(notif)
        # Earlier Today: today but more than 1 hour ago
        elif notif_time >= today_start:
            grouped['earlier_today'].append(notif)
        # Yesterday
        elif notif_time >= yesterday_start:
            grouped['yesterday'].append(notif)
        # This Week: this week but before yesterday
        elif notif_time >= week_start:
            grouped['this_week'].append(notif)
        # Last Week: last week
        elif notif_time >= last_week_start:
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
    queryset = NotificationObject.objects.filter(recipient=user).exclude(
        status__in=[NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        if is_read:
            queryset = queryset.filter(status=NotificationStatuses.READ.value)
        else:
            queryset = queryset.exclude(status=NotificationStatuses.READ.value)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # Group by notification_type and context
    grouped = {}
    
    for notif in queryset.order_by('-updated_at'):
        notif_time = notif.updated_at or notif.created_at
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
                'latest_timestamp': notif_time
            }
        
        grouped[group_key]['notifications'].append(notif)
        grouped[group_key]['count'] += 1
        
        if notif_time > grouped[group_key]['latest_timestamp']:
            grouped[group_key]['latest_timestamp'] = notif_time
        if notif.status != NotificationStatuses.READ.value:
            grouped[group_key]['is_read'] = False
    
    # Convert to list and sort by latest timestamp
    grouped_list = list(grouped.values())
    grouped_list.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return grouped_list


def mark_user_notifications_as_read(user):
    return NotificationObject.objects.filter(
        recipient=user
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
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
    
    str_ids = list(set(str(gid) for gid in group_ids))
    
    counts = NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=str_ids
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).values('context_id').annotate(
        count=Count('notification_id')
    )
    
    res = {}
    for item in counts:
        cid = item['context_id']
        cnt = item['count']
        res[cid] = cnt
        if cid and str(cid).isdigit():
            res[int(cid)] = cnt
    return res


def get_unread_group_activity_by_type(user, group_ids):
    """
    Get unread notification counts per group broken down by type:
    announcement, post, and total.
    Returns: {group_id: {'announcement': int, 'post': int, 'total': int}}
    Keys are provided as both integer and string group IDs.
    """
    if not user or not user.is_authenticated or not group_ids:
        return {}
    
    canonical_data = {}
    for gid in group_ids:
        canonical_data[str(gid)] = {'announcement': 0, 'post': 0, 'total': 0}
        
    str_ids = list(canonical_data.keys())
    
    counts = NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=str_ids,
        notification_type__in=['GROUP_ANNOUNCEMENT', 'POST_CREATED', 'DOCUMENT_SHARED']
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).values('context_id', 'notification_type').annotate(
        count=Count('notification_id')
    )
    
    for item in counts:
        cid = str(item['context_id'])
        ntype = item['notification_type']
        cnt = item['count']
        
        if cid not in canonical_data:
            canonical_data[cid] = {'announcement': 0, 'post': 0, 'total': 0}
            
        canonical_data[cid]['total'] += cnt
        if ntype == 'GROUP_ANNOUNCEMENT':
            canonical_data[cid]['announcement'] += cnt
        elif ntype in ('POST_CREATED', 'DOCUMENT_SHARED') or 'POST' in ntype:
            canonical_data[cid]['post'] += cnt
            
    result = {}
    for cid, data in canonical_data.items():
        result[cid] = dict(data)
        if cid.isdigit():
            result[int(cid)] = dict(data)
            
    return result


def has_any_unread_group_activity(user):
    """
    Check if the user has any unread notifications for any of their approved groups.
    Only returns True if there are unread group updates (announcements or posts)
    for groups the user is currently an approved member of.
    """
    if not user or not user.is_authenticated:
        return False
    from groups.models import Membership, MembershipStatus
    user_group_ids = list(Membership.objects.filter(
        user=user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True))
    
    if not user_group_ids:
        return False
        
    str_group_ids = [str(gid) for gid in user_group_ids]
    
    return NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=str_group_ids,
        notification_type__in=['GROUP_ANNOUNCEMENT', 'POST_CREATED', 'DOCUMENT_SHARED']
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).exists()


def mark_group_notifications_as_read(user, group_id, exclude_types=None):
    """
    Mark all unread notifications for a specific group as READ for this user,
    optionally excluding specific notification types (e.g. GROUP_ANNOUNCEMENT).
    """
    if not user or not user.is_authenticated or not group_id:
        return 0
    str_gid = str(group_id)
    qs = NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=[group_id, str_gid]
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    if exclude_types:
        qs = qs.exclude(notification_type__in=exclude_types)
    return qs.update(status=NotificationStatuses.READ.value)


def get_unread_announcement_ids_for_user(user, group_id):
    """
    Returns a set of announcement IDs that are unread for this user in this group.
    """
    if not user or not user.is_authenticated or not group_id:
        return set()
    
    str_gid = str(group_id)
    notifs = NotificationObject.objects.filter(
        recipient=user,
        context_type='GROUP',
        context_id__in=[group_id, str_gid],
        notification_type='GROUP_ANNOUNCEMENT'
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    ).values_list('metadata', flat=True)
    
    unread_ids = set()
    for meta in notifs:
        if isinstance(meta, dict):
            aid = meta.get('announcement_id') or meta.get('target_id')
            if aid is not None:
                try:
                    unread_ids.add(int(aid))
                except (ValueError, TypeError):
                    unread_ids.add(str(aid))
    return unread_ids


def mark_announcement_as_read(user, announcement_id, group_id=None):
    """
    Mark unread GROUP_ANNOUNCEMENT notifications for this announcement as READ.
    """
    if not user or not user.is_authenticated or not announcement_id:
        return 0
        
    query = NotificationObject.objects.filter(
        recipient=user,
        notification_type='GROUP_ANNOUNCEMENT'
    ).exclude(
        status__in=[NotificationStatuses.READ.value, NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    if group_id:
        query = query.filter(context_type='GROUP', context_id__in=[group_id, str(group_id)])
        
    str_aid = str(announcement_id)
    int_aid = int(announcement_id) if str_aid.isdigit() else None
    
    matching_ids = []
    for notif in query:
        meta = notif.metadata or {}
        aid = meta.get('announcement_id') or meta.get('target_id')
        if aid == announcement_id or str(aid) == str_aid or (int_aid is not None and aid == int_aid):
            matching_ids.append(notif.notification_id)
            
    # Fallback: if single unread announcement notification in group, match it
    if not matching_ids and group_id:
        if query.count() == 1:
            matching_ids = list(query.values_list('notification_id', flat=True))
            
    if matching_ids:
        return NotificationObject.objects.filter(notification_id__in=matching_ids).update(
            status=NotificationStatuses.READ.value
        )
        
    return 0



def get_notifications_grouped_by_sender(user, notification_type=None, is_read=None, search_query=None):
    """
    Group notifications by sender (person).
    Returns a list of sender groups with their activities.
    """
    queryset = NotificationObject.objects.filter(recipient=user).exclude(
        status__in=[NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        if is_read:
            queryset = queryset.filter(status=NotificationStatuses.READ.value)
        else:
            queryset = queryset.exclude(status=NotificationStatuses.READ.value)
    
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
        notif_time = notif.updated_at or notif.created_at
        
        if sender_id not in grouped:
            # Extract sender info from metadata
            actor_username = notif.metadata.get('actor_username') if notif.metadata else 'Unknown'
            
            grouped[sender_id] = {
                'sender_id': sender_id,
                'sender_username': actor_username,
                'notifications': [],
                'unread_count': 0,
                'total_count': 0,
                'latest_timestamp': notif_time
            }
        
        grouped[sender_id]['notifications'].append(notif)
        grouped[sender_id]['total_count'] += 1
        if notif.status != NotificationStatuses.READ.value:
            grouped[sender_id]['unread_count'] += 1
        if notif_time > grouped[sender_id]['latest_timestamp']:
            grouped[sender_id]['latest_timestamp'] = notif_time
    
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
    queryset = NotificationObject.objects.filter(recipient=user).exclude(
        status__in=[NotificationStatuses.ARCHIVED.value, NotificationStatuses.EXPIRED.value]
    )
    
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    if is_read is not None:
        if is_read:
            queryset = queryset.filter(status=NotificationStatuses.READ.value)
        else:
            queryset = queryset.exclude(status=NotificationStatuses.READ.value)
    
    if search_query:
        queryset = queryset.filter(title__icontains=search_query) | queryset.filter(summary__icontains=search_query)
    
    # First group by activity (type + context)
    activity_groups = {}
    
    for notif in queryset.order_by('-updated_at'):
        group_key = (notif.notification_type, notif.context_type, notif.context_id)
        notif_time = notif.updated_at or notif.created_at
        
        if group_key not in activity_groups:
            activity_groups[group_key] = {
                'notification_type': notif.notification_type,
                'context_type': notif.context_type,
                'context_id': notif.context_id,
                'notifications': [],
                'actors': [],  # Changed from senders to actors
                'count': 0,
                'is_read': notif.status == NotificationStatuses.READ.value,
                'latest_timestamp': notif_time
            }
        
        activity_groups[group_key]['notifications'].append(notif)
        activity_groups[group_key]['count'] += 1
        
        # Track unique actors (from metadata)
        actor_id = notif.metadata.get('actor_id') if notif.metadata else None
        if actor_id and actor_id not in activity_groups[group_key]['actors']:
            activity_groups[group_key]['actors'].append(actor_id)
        
        if notif_time > activity_groups[group_key]['latest_timestamp']:
            activity_groups[group_key]['latest_timestamp'] = notif_time
        if notif.status == NotificationStatuses.CREATED.value:
            activity_groups[group_key]['is_read'] = False
    
    # Convert to list and determine display mode for each group
    result = []
    for group in activity_groups.values():
        sender_avatars = []
        seen_actors = set()
        for n in group['notifications']:
            meta = n.metadata or {}
            aid = meta.get('actor_id')
            if aid and aid not in seen_actors:
                seen_actors.add(aid)
                sender_avatars.append({
                    'id': aid,
                    'username': meta.get('actor_username', 'Someone'),
                    'profile_pic': meta.get('actor_avatar')
                })
        group['sender_avatars'] = sender_avatars
        
        # If only 1 actor with multiple notifications, convert to sender-grouped format
        if len(group['actors']) == 1 and group['count'] > 1:
            first_meta = group['notifications'][0].metadata or {}
            actor_id = group['actors'][0]
            actor_user = first_meta.get('actor_username', 'Someone')
            actor_pic = first_meta.get('actor_avatar')
            
            sender_group = {
                'sender': {'id': actor_id, 'username': actor_user},
                'sender_avatar': {'profile_pic': actor_pic, 'username': actor_user},
                'notifications': group['notifications'],
                'unread_count': sum(1 for n in group['notifications'] if n.status == NotificationStatuses.CREATED.value),
                'total_count': group['count'],
                'latest_timestamp': group['latest_timestamp'],
                'display_mode': 'sender_grouped'
            }
            result.append(sender_group)
        else:
            # Use activity-grouped format
            group['display_mode'] = 'activity_grouped'
            
            # Resolve post safely
            post = None
            try:
                from notifications.rendering.adapters import _get_post_safely
                if group['context_type'] in ['POST', 'POSTS'] and group['context_id']:
                    post = _get_post_safely(group['context_id'])
                if not post:
                    for n in group['notifications']:
                        meta = n.metadata or {}
                        tid = meta.get('target_id') or meta.get('post_id')
                        if tid:
                            post = _get_post_safely(tid)
                            if post:
                                break
            except Exception:
                pass
            group['post'] = post
            
            # Resolve group if applicable
            grp = None
            try:
                if group['context_type'] in ['GROUP', 'GROUPS'] and group['context_id']:
                    from groups.models import Group
                    grp = Group.objects.filter(id=int(group['context_id'])).first()
            except Exception:
                pass
            group['group'] = grp
            
            result.append(group)
    
    # Sort by latest timestamp
    result.sort(key=lambda x: x['latest_timestamp'], reverse=True)
    
    return result

