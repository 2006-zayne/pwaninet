import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import PlatformEvent, NotificationObject
from releases.models import Release

# Check release event
event = PlatformEvent.objects.filter(source='RELEASES').first()
if event:
    print(f'Event found: {event.event_type}')
    print(f'Metadata: {event.metadata}')
else:
    print('No release event found')

# Check for release notifications
release_notifications = NotificationObject.objects.filter(
    metadata__contains={'target_id': '1'}
)
print(f'Release notifications: {release_notifications.count()}')
for notif in release_notifications:
    print(f'  Notification: {notif.id}, Recipient: {notif.recipient.username if notif.recipient else "None"}')
