# Source Generated with Decompyle++
# File: notification_queries.cpython-312.pyc (Python 3.12)

from core.models import Notifications

def get_notifications_for_user(user):
    return user.notifications.all().order_by('-timestamp')


def mark_user_notifications_as_read(user):
    return Notifications.objects.filter(recipient = user, is_read = False).update(is_read = True)


def get_unread_count(user):
    return user.notifications.filter(is_read = False).count()


def get_notification_for_user(user, notif_id):
    return Notifications.objects.filter(id = notif_id, recipient = user).first()

