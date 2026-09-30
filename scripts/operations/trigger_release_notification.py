import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release
from releases.signals import create_release_published_event

# Get the published release
release = Release.objects.first()
if release and release.published:
    print(f'Triggering notification for release {release.version}')
    create_release_published_event(release)
    print('Notification event created')
else:
    print('No published release found')
