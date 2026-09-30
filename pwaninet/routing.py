"""
WebSocket routing configuration for pwaninet project.

ARCHITECTURAL RULE:
Each WebSocket consumer must have a single source of truth file.
Duplicate class names across modules are forbidden.
"""

from django.urls import re_path
from realtime.consumers import NotificationConsumer, FeedConsumer, OnlineStatusConsumer, CommentConsumer

websocket_urlpatterns = [
    # Notification consumer
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    # Feed update consumer
    re_path(r'ws/feed/$', FeedConsumer.as_asgi()),
    # Online status consumer
    re_path(r'ws/online/$', OnlineStatusConsumer.as_asgi()),
    # Comment updates consumer (supports both integer ID and UUID share_id)
    re_path(r'ws/post/(?P<post_id>[a-zA-Z0-9_-]+)/comments/$', CommentConsumer.as_asgi()),
]
