"""
Test script to verify canonical payload structure
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import NotificationObject
from notifications.rendering.adapters import get_payload_adapter

User = get_user_model()

# Create test users
try:
    user1 = User.objects.get(username='testuser1')
except User.DoesNotExist:
    user1 = User.objects.create_user(username='testuser1', email='test1@example.com', password='testpass123')

try:
    user2 = User.objects.get(username='testuser2')
except User.DoesNotExist:
    user2 = User.objects.create_user(username='testuser2', email='test2@example.com', password='testpass123')

# Create a test notification
notification = NotificationObject.objects.create(
    recipient=user1,
    notification_type='COMMENTED',
    category='SOCIAL',
    priority='NORMAL',
    title='Test notification',
    summary='This is a test notification',
    metadata={
        'actor_id': user2.id,
        'actor_username': user2.username
    }
)

print(f"Created notification: {notification.notification_id}")

# Get adapter and convert to canonical payload
adapter = get_payload_adapter(notification)
payload = adapter.to_standard_payload(notification)

print(f"\n=== Canonical Payload Structure ===")
print(f"Version: {payload.version}")
print(f"Type: {payload.type}")
print(f"Intent: {payload.intent}")
print(f"Lifecycle State: {payload.lifecycle.state}")
print(f"Profile ID: {payload.profile.id}")
print(f"Actors: {len(payload.actors)}")
if payload.actors:
    print(f"  First actor: {payload.actors[0].name} ({payload.actors[0].username})")
print(f"Context: {payload.context.name if payload.context else None}")
print(f"Resource: {payload.resource.title if payload.resource else None}")
print(f"Message Template: {payload.message.template if payload.message else None}")
print(f"Actions: {len(payload.actions)}")
for action in payload.actions:
    print(f"  - {action.label} ({action.style})")

# Convert to dict
payload_dict = payload.to_dict()
print(f"\n=== Payload Dict Keys ===")
print(f"Keys: {list(payload_dict.keys())}")

# Verify required fields
required_fields = [
    'version', 'identity', 'type', 'intent', 'lifecycle', 'profile',
    'actors', 'context', 'resource', 'message', 'components',
    'preview', 'metadata', 'actions', 'navigation', 'permissions',
    'capabilities', 'timestamps'
]

print(f"\n=== Required Fields Check ===")
for field in required_fields:
    present = field in payload_dict
    print(f"{field}: {'✓' if present else '✗'}")

# Clean up
notification.delete()
print(f"\nTest complete! Notification cleaned up.")
