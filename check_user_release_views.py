import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from releases.models import Release, UserReleaseView
from django.contrib.auth import get_user_model

User = get_user_model()

# Check release
release = Release.objects.first()
if release:
    print(f'Release: {release.version}, ID: {release.id}')
    
    # Check user release views UserReleaseView.objects.filter(release=release)
    print(f'UserReleaseView count: {views.count()}')
    for view in views:
        print(f'  User: {view.user.username}, Viewed at: {view.viewed_at}')
    
    # Check which users haven't viewed
    all_users = User.objects.filter(is_active=True)
    viewed_users = views.values_list('user_id', flat=True)
    unviewed_users = all_users.exclude(id__in=viewed_users)
    print(f'Users who haven\'t viewed: {unviewed_users.count()}')
    for user in unviewed_users:
        print(f'  {user.username}')
else:
    print('No release found')
