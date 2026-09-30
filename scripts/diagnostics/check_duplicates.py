"""
Check for duplicate notifications in the database.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from notifications.models import NotificationObject
from collections import defaultdict

def check_duplicates():
    """Check for duplicate notifications."""
    notifications = NotificationObject.objects.all()
    
    # Group by recipient, type, and context
    groups = defaultdict(list)
    for n in notifications:
        key = (n.recipient_id, n.notification_type, n.context_type, n.context_id)
        groups[key].append(n)
    
    print(f"Total notifications: {notifications.count()}")
    print(f"Unique groups: {len(groups)}")
    
    # Show potential duplicates
    for key, notifs in groups.items():
        if len(notifs) > 1:
            print(f"\n=== Potential Duplicates ===")
            print(f"Recipient: {key[0]}, Type: {key[1]}, Context: {key[2]}-{key[3]}")
            print(f"Count: {len(notifs)}")
            for n in notifs:
                print(f"  - ID: {n.notification_id}, Created: {n.created_at}, Status: {n.status}, Aggregation Key: {n.aggregation_key}")

if __name__ == '__main__':
    check_duplicates()
