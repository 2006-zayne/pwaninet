import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release, ReleaseItem, ReleaseItemImage

release = Release.objects.first()
if release:
    print('Release:', release.version)
    print('Status:', release.status)
    print('Published:', release.published)
    print('Type:', release.release_type)
    items = release.items.all()
    print('Items:', items.count())
    for item in items:
        print(f'  Item: {item.title}, Images: {item.images.count()}')
else:
    print('No releases found')
