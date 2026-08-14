import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import PlatformEvent, NotificationObject
from releases.models import Release

# Delete existing release event
PlatformEvent.objects.filter(source='RELEASES').delete()
print('Deleted existing release events')

# Get the published release
release = Release.objects.first()
if release and release.published:
    print(f'Creating new notification event for release {release.version}')
    from releases.signals import create_release_published_event
    create_release_published_event(release)
    print('Notification event created')
    
    # Check if notifications were created
    release_notifications = NotificationObject.objects.filter(
        metadata__contains={'target_id': str(release.id)}
    )
    print(f'Release notifications created: {release_notifications.count()}')
else:
    print('No published release found')
