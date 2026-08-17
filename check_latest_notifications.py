import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import NotificationObject

# Check latest notifications
latest_notifications = NotificationObject.objects.filter(notification_type='RELEASE').order_by('-created_at')[:15]
print(f'Latest RELEASE notifications: {latest_notifications.count()}')
for notif in latest_notifications:
    print(f'  Recipient: {notif.recipient.username if notif.recipient else "None"}, Status: {notif.status}')
    print(f'    Metadata target_id: {notif.metadata.get("target_id")}')
