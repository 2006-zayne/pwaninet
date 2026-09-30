import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import NotificationObject

# Check recent notifications
recent_notifications = NotificationObject.objects.order_by('-created_at')[:15]
print(f'Recent notifications: {recent_notifications.count()}')
for notif in recent_notifications:
    print(f'  ID: {str(notif.notification_id)[:8]}..., Type: {notif.notification_type}, Recipient: {notif.recipient.username if notif.recipient else "None"}')
    print(f'    Metadata: {notif.metadata}')
