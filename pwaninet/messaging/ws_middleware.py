"""
WebSocket middleware for rate limiting and connection tracking.
Prevents spam and DOS attacks on WebSocket connections.
"""

from pwaninet.redis_client import get_redis_client
from datetime import datetime, timedelta
import json


class WebSocketRateLimiter:
    """
    Rate limits WebSocket messages per user/connection.
    Implements token bucket algorithm with 100 messages/minute per connection.
    """

    DEFAULT_RATE = 100  # messages per minute
    WINDOW = 60  # seconds
    KEY_PREFIX = 'ws_rate'

    @classmethod
    def get_rate_key(cls, user_id: int, connection_id: str) -> str:
        """Get rate limit key for a WebSocket connection."""
        return f"{cls.KEY_PREFIX}:{user_id}:{connection_id}"

    @classmethod
    def is_rate_limited(cls, user_id: int, connection_id: str, rate: int = None) -> bool:
        """
        Check if connection has exceeded rate limit.

        Args:
            user_id: ID of user
            connection_id: Unique connection identifier
            rate: Messages per minute (default: 100)

        Returns:
            True if rate limited, False if allowed
        """
        if rate is None:
            rate = cls.DEFAULT_RATE

        try:
            redis_client = get_redis_client()
            key = cls.get_rate_key(user_id, connection_id)

            # Increment counter and get current value
            current = redis_client.incr(key)

            # Set expiration on first request
            if current == 1:
                redis_client.expire(key, cls.WINDOW)

            # Check if exceeded limit
            return current > rate
        except Exception:
            # If Redis fails, allow message (fail open)
            return False

    @classmethod
    def get_rate_status(cls, user_id: int, connection_id: str, rate: int = None) -> dict:
        """
        Get current rate limit status for a connection.

        Args:
            user_id: ID of user
            connection_id: Unique connection identifier
            rate: Messages per minute (default: 100)

        Returns:
            Dict with current_count, limit, and remaining
        """
        if rate is None:
            rate = cls.DEFAULT_RATE

        try:
            redis_client = get_redis_client()
            key = cls.get_rate_key(user_id, connection_id)

            current = int(redis_client.get(key) or 0)
            ttl = redis_client.ttl(key)

            return {
                'current': current,
                'limit': rate,
                'remaining': max(0, rate - current),
                'reset_in': ttl if ttl > 0 else cls.WINDOW,
            }
        except Exception:
            return {
                'current': 0,
                'limit': rate,
                'remaining': rate,
                'reset_in': cls.WINDOW,
            }

    @classmethod
    def reset_limit(cls, user_id: int, connection_id: str) -> None:
        """Reset rate limit for a connection (useful for cleanup)."""
        try:
            redis_client = get_redis_client()
            key = cls.get_rate_key(user_id, connection_id)
            redis_client.delete(key)
        except Exception:
            pass


class WebSocketConnectionTracker:
    """
    Tracks active WebSocket connections per user.
    Allows limiting concurrent connections or detecting suspicious activity.
    """

    KEY_PREFIX = 'ws_conn'
    MAX_CONNECTIONS_PER_USER = 20
    CONNECTION_TIMEOUT = 3600  # 1 hour

    @classmethod
    def get_connections_key(cls, user_id: int) -> str:
        """Get Redis key for user's connections."""
        return f"{cls.KEY_PREFIX}:{user_id}"

    @classmethod
    def register_connection(cls, user_id: int, connection_id: str, metadata: dict = None) -> bool:
        """
        Register a new WebSocket connection.

        Args:
            user_id: ID of user
            connection_id: Unique connection identifier
            metadata: Connection metadata (ip, user_agent, etc)

        Returns:
            True if registered, False if exceeded max connections
        """
        try:
            redis_client = get_redis_client()
            conn_key = cls.get_connections_key(user_id)

            # Clean up stale connections (older than CONNECTION_TIMEOUT)
            connections = redis_client.smembers(conn_key)
            now = datetime.now()
            for conn_json in connections:
                try:
                    conn_data = json.loads(conn_json)
                    connected_at = datetime.fromisoformat(conn_data.get('connected_at', '2000-01-01'))
                    if (now - connected_at).total_seconds() > cls.CONNECTION_TIMEOUT:
                        redis_client.srem(conn_key, conn_json)
                except (json.JSONDecodeError, ValueError):
                    # Remove malformed entries
                    redis_client.srem(conn_key, conn_json)

            # Check current connection count after cleanup
            conn_count = redis_client.scard(conn_key)
            if conn_count >= cls.MAX_CONNECTIONS_PER_USER:
                return False

            # Register connection
            conn_data = {
                'connection_id': connection_id,
                'connected_at': datetime.now().isoformat(),
            }
            if metadata:
                conn_data.update(metadata)

            redis_client.sadd(conn_key, json.dumps(conn_data))
            redis_client.expire(conn_key, cls.CONNECTION_TIMEOUT)

            return True
        except Exception:
            # Fail open - allow connection if Redis fails
            return True

    @classmethod
    def unregister_connection(cls, user_id: int, connection_id: str) -> None:
        """Unregister a WebSocket connection."""
        try:
            redis_client = get_redis_client()
            conn_key = cls.get_connections_key(user_id)

            # Find and remove connection
            connections = redis_client.smembers(conn_key)
            for conn_json in connections:
                conn_data = json.loads(conn_json)
                if conn_data.get('connection_id') == connection_id:
                    redis_client.srem(conn_key, conn_json)
                    break
        except Exception:
            pass

    @classmethod
    def get_active_connections(cls, user_id: int) -> list:
        """Get list of active connections for a user."""
        try:
            redis_client = get_redis_client()
            conn_key = cls.get_connections_key(user_id)

            connections = redis_client.smembers(conn_key)
            return [json.loads(c) for c in connections]
        except Exception:
            return []

    @classmethod
    def get_connection_count(cls, user_id: int) -> int:
        """Get number of active connections for a user."""
        try:
            redis_client = get_redis_client()
            conn_key = cls.get_connections_key(user_id)
            return redis_client.scard(conn_key)
        except Exception:
            return 0
