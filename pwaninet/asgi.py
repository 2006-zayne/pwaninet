"""
ASGI configuration for pwaninet project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/

ARCHITECTURAL RULE:
Each WebSocket consumer must have a single source of truth file.
Duplicate class names across modules are forbidden.
"""

import os
import logging
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from pwaninet.routing import websocket_urlpatterns

logger = logging.getLogger("uvicorn.error")


class ASGIResponseDiagnostics:
    """Add request context to response-send failures raised below Django."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        declared_length = None
        response_status = None
        bytes_attempted = 0

        async def tracked_send(message):
            nonlocal declared_length, response_status, bytes_attempted
            if message["type"] == "http.response.start":
                response_status = message.get("status")
                for name, value in message.get("headers", []):
                    if name.lower() == b"content-length":
                        try:
                            declared_length = int(value)
                        except (TypeError, ValueError):
                            declared_length = None
                        break
            elif message["type"] == "http.response.body":
                bytes_attempted += len(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception:
            # ASGI scope.path excludes the query string, so signed download tokens
            # are not written to logs. Count bytes only; never log response bodies.
            logger.error(
                "ASGI response failed method=%s path=%s status=%s content_length=%s bytes_attempted=%s",
                scope.get("method", "?"),
                scope.get("path", "?"),
                response_status,
                declared_length,
                bytes_attempted,
            )
            raise


application = ASGIResponseDiagnostics(ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
}))


# Debug: Log ASGI startup
print('[ASGI] Application initialized with WebSocket support')
