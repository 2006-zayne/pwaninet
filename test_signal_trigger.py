import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release
from releases.signals import track_release_status_change, log_release_audit_trail

# Get the release
release = Release.objects.first()
if not release:
    print('No release found')
    exit()

print(f'Release: {release.version}, ID: {release.id}')
print(f'Is current: {release.is_current_release}')

# Manually trigger pre_save to set the old value
track_release_status_change(Release.__class__, release)

print(f'_old_is_current set: {hasattr(release, "_old_is_current")}')
if hasattr(release, '_old_is_current'):
    print(f'_old_is_current value: {release._old_is_current}')

# Now change and save
release.is_current_release = True
print(f'About to save with is_current_release={release.is_current_release}')
release.save()
print('Saved')
