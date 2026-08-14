import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release
from releases.services import ReleaseService
from notifications.models import PlatformEvent, NotificationObject

# Get the release
release = Release.objects.first()
if not release:
    print('No release found')
    exit()

print(f'Release: {release.version}, ID: {release.id}')

# Delete existing release events and notifications
PlatformEvent.objects.filter(source='RELEASES').delete()
NotificationObject.objects.filter(notification_type='RELEASE').delete()
print('Deleted existing release events and notifications')

# If already current, unset it first
if release.is_current_release:
    print('Unsetting as current...')
    release.is_current_release = False
    release.save()
    print('Unset as current')

# Now set as current to trigger the signal
print('Setting as current to trigger notification...')
ReleaseService.set_current_release(release)
print('Set as current')

# Check for events
events = PlatformEvent.objects.filter(source='RELEASES')
print(f'Release events created: {events.count()}')
for event in events:
    print(f'  Event: {event.event_type}')
    print(f'  Metadata: {event.metadata}')

# Check for notifications
release_notifications = NotificationObject.objects.filter(notification_type='RELEASE')
print(f'Release notifications created: {release_notifications.count()}')
for notif in release_notifications[:3]:
    print(f'  Recipient: {notif.recipient.username if notif.recipient else "None"}')
    print(f'    Metadata target_id: {notif.metadata.get("target_id")}')
