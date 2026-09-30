import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()
from notifications.rules.rules import get_rules_for_event
from notifications.models import PlatformEvent

# Get the release event
event = PlatformEvent.objects.filter(source='RELEASES').first()
if event:
    print(f'Event type: {event.event_type}')
    
    # Get matching rules
    rules = get_rules_for_event(event.event_type)
    print(f'Matching rules: {len(rules)}')
    for rule in rules:
        print(f'  Rule: {rule.name}, Trigger: {rule.trigger}')
else:
    print('No release event found')
