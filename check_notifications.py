import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import PlatformEvent, NotificationObject, NotificationPreference
from releases.models import Release

# Check for release events
events = PlatformEvent.objects.filter(source='RELEASES')
print(f'Release events: {events.count()}')
for event in events:
    print(f'  Event: {event.event_type}, Source: {event.source}')

# Check for notifications
notifications = NotificationObject.objects.all()
print(f'Total notifications: {notifications.count()}')

# Check user preferences
prefs = NotificationPreference.objects.all()
print(f'Notification preferences: {prefs.count()}')

# Check release status
release = Release.objects.first()
if release:
    print(f'Release {release.version} - Published: {release.published}, Status: {release.status}')
