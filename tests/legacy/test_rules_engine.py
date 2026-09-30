import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.models import PlatformEvent
from notifications.rules.engine import RulesEngine

# Get the release event
event = PlatformEvent.objects.filter(source='RELEASES').first()
if event:
    print(f'Processing event: {event.event_type}')
    
    # Manually process through Rules Engine
    notifications = RulesEngine.process_event(event)
    print(f'Notifications created: {len(notifications)}')
    
    for notif in notifications:
        print(f'  Notification ID: {notif.notification_id}, Recipient: {notif.recipient.username if notif.recipient else "None"}')
else:
    print('No release event found')
