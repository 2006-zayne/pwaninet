import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release, ReleaseItem, ReleaseItemImage

# Check release
release = Release.objects.first()
if release:
    print(f'Release: {release.version}, ID: {release.id}')
    
    # Check items
    items = release.items.all()
    print(f'Items: {items.count()}')
    for item in items:
        print(f'  Item: {item.title}, ID: {item.id}')
        images = item.images.all()
        print(f'    Images: {images.count()}')
        for img in images:
            print(f'      - {img.image.name}, Caption: {img.caption}')
else:
    print('No release found')
