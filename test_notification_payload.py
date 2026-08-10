"""
Test script to verify notification payload generation.
Run with: python manage.py shell < test_notification_payload.py
Or: python test_notification_payload.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from notifications.models import NotificationObject
from notifications.rendering.adapters import get_payload_adapter
import json

def test_payload_generation():
    """Test that NotificationObjectAdapter generates proper JSON payloads."""
    
    # Get a sample notification
    notifications = NotificationObject.objects.all()[:5]
    
    if not notifications:
        print("No NotificationObjects found in database.")
        print("Create some notifications first by triggering events (like, follow, etc.)")
        return
    
    print(f"Testing payload generation for {len(notifications)} notifications...\n")
    
    for notification in notifications:
        print(f"=== Notification ID: {notification.notification_id} ===")
        print(f"Type: {notification.notification_type}")
        print(f"Status: {notification.status}")
        print(f"Recipient: {notification.recipient.username}")
        print(f"Title: {notification.title}")
        print(f"Context: {notification.context_type} - {notification.context_id}")
        print(f"Metadata: {notification.metadata}")
        
        # Generate payload
        adapter = get_payload_adapter(notification)
        payload = adapter.to_standard_payload(notification)
        
        print(f"\n--- Generated Payload ---")
        print(json.dumps(payload, indent=2, default=str))
        
        # Verify payload structure
        required_keys = ['id', 'type', 'created_at', 'read', 'priority', 'actor', 'context', 'resource', 'content', 'metadata', 'actions', 'status', 'rendering_hints']
        missing_keys = [key for key in required_keys if key not in payload]
        
        if missing_keys:
            print(f"\n❌ MISSING KEYS: {missing_keys}")
        else:
            print(f"\n✅ All required keys present")
        
        # Verify actor resolution
        if payload.get('actor'):
            print(f"✅ Actor resolved: {payload['actor']['username']}")
        else:
            print(f"⚠️  No actor resolved")
        
        print("\n" + "="*60 + "\n")
    
    print("Payload generation test complete.")

if __name__ == '__main__':
    test_payload_generation()
