"""
DEPRECATED: WebSocket consumers have been moved.

ARCHITECTURAL RULE:
Each WebSocket consumer must have a single source of truth file.
Duplicate class names across modules are forbidden.

Consumer locations:
- ChatConsumer: messaging/consumers.py
- NotificationConsumer: realtime/consumers.py
- FeedConsumer: realtime/consumers.py
- OnlineStatusConsumer: realtime/consumers.py

This file is kept for backwards compatibility only.
Import consumers from their respective modules instead.
"""
