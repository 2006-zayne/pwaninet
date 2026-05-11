"""
WebSocket routing configuration for pwaninet project.

ARCHITECTURAL RULE:
Each WebSocket consumer must have a single source of truth file.
Duplicate class names across modules are forbidden.
"""

from django.urls import re_path
from realtime.consumers import NotificationConsumer, FeedConsumer, OnlineStatusConsumer
from messaging.routing import websocket_urlpatterns as messaging_websocket_urlpatterns

websocket_urlpatterns = [
    # Notification consumer
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    # Feed update consumer
    re_path(r'ws/feed/$', FeedConsumer.as_asgi()),
    # Online status consumer
    re_path(r'ws/online/$', OnlineStatusConsumer.as_asgi()),
] + messaging_websocket_urlpatterns
