"""
Clean up duplicate notifications by aggregating them.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from notifications.models import NotificationObject
from notifications.aggregation.engine import AggregationEngine
from collections import defaultdict

def cleanup_duplicates():
    """Clean up duplicate notifications by aggregating them."""
    notifications = NotificationObject.objects.all()
    
    # Group by recipient, type, context, and aggregation key
    groups = defaultdict(list)
    for n in notifications:
        key = (n.recipient_id, n.notification_type, n.context_type, n.context_id, n.aggregation_key)
        groups[key].append(n)
    
    print(f"Total notifications: {notifications.count()}")
    print(f"Unique groups: {len(groups)}")
    
    cleaned = 0
    
    for key, notifs in groups.items():
        if len(notifs) > 1:
            print(f"\n=== Cleaning duplicates ===")
            print(f"Recipient: {key[0]}, Type: {key[1]}, Context: {key[2]}-{key[3]}, Aggregation Key: {key[4]}")
            print(f"Count: {len(notifs)}")
            
            # Sort by created_at (oldest first)
            notifs.sort(key=lambda n: n.created_at)
            
            # Use the oldest as base
            base = notifs[0]
            others = notifs[1:]
            
            # Merge notifications
            all_source_events = set(base.source_events or [])
            for other in others:
                all_source_events.update(other.source_events or [])
            
            base.source_events = list(all_source_events)
            base.event_count = len(all_source_events)
            
            # Update times
            all_times = [base.first_event_time] if base.first_event_time else []
            for other in others:
                if other.first_event_time:
                    all_times.append(other.first_event_time)
                if other.latest_event_time:
                    all_times.append(other.latest_event_time)
            
            if all_times:
                base.first_event_time = min(all_times)
                base.latest_event_time = max(all_times)
            
            # Update summary
            base.summary = AggregationEngine._generate_aggregated_summary(base)
            
            # Save base
            base.save(update_fields=[
                'source_events', 'event_count', 'first_event_time', 
                'latest_event_time', 'summary'
            ])
            
            # Delete duplicates
            for other in others:
                other.delete()
                cleaned += 1
            
            print(f"  Kept: {base.notification_id}")
            print(f"  Deleted: {len(others)} notifications")
    
    print(f"\n=== Summary ===")
    print(f"Total notifications cleaned: {cleaned}")
    print(f"Remaining notifications: {NotificationObject.objects.count()}")

if __name__ == '__main__':
    response = input("This will delete duplicate notifications. Continue? (y/n): ")
    if response.lower() == 'y':
        cleanup_duplicates()
    else:
        print("Cancelled.")
