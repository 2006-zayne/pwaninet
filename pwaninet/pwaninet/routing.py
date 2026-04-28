"""
WebSocket routing configuration for pwaninet project.
"""

from django.urls import re_path
from . import consumers
from messaging.routing import websocket_urlpatterns as messaging_websocket_urlpatterns

websocket_urlpatterns = [
    # Notification consumer
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    # Feed update consumer
    re_path(r'ws/feed/$', consumers.FeedConsumer.as_asgi()),
    # Online status consumer
    re_path(r'ws/online/$', consumers.OnlineStatusConsumer.as_asgi()),
    # Messaging consumer
    re_path(r'ws/chat/(?P<conversation_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
] + messaging_websocket_urlpatterns
