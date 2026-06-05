"""
Observability module for messaging system.
Tracks metrics for WebSocket connections, message latency, upload failures, and active connections.
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from pwaninet.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class MessagingMetrics:
    """Centralized metrics collection for messaging system."""
    
    # Redis keys for metrics
    WS_RECONNECT_KEY = "metrics:ws:reconnect"
    MESSAGE_LATENCY_KEY = "metrics:message:latency"
    UPLOAD_FAILURE_KEY = "metrics:upload:failure"
    ACTIVE_CONNECTIONS_KEY = "metrics:ws:active"
    
    def __init__(self):
        self.redis_client = None
    
    def _get_redis(self):
        """Get Redis client for metrics storage."""
        if self.redis_client is None:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    def record_websocket_reconnect(self, user_id: int, conversation_id: int):
        """Record a WebSocket reconnection event."""
        try:
            redis = self._get_redis()
            timestamp = datetime.utcnow().isoformat()
            key = f"{self.WS_RECONNECT_KEY}:{datetime.utcnow().date()}"
            
            # Increment daily reconnect count
            redis.incr(key)
            redis.expire(key, 86400)  # 24 hours TTL
            
            # Log the event
            logger.info(
                f"WebSocket reconnect: user_id={user_id}, "
                f"conversation_id={conversation_id}, timestamp={timestamp}"
            )
            
            # Store recent reconnects for monitoring (last 100)
            recent_key = f"{self.WS_RECONNECT_KEY}:recent"
            redis.lpush(recent_key, f"{user_id}:{conversation_id}:{timestamp}")
            redis.ltrim(recent_key, 0, 99)
            redis.expire(recent_key, 3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to record WebSocket reconnect: {e}")
    
    def record_message_latency(self, user_id: int, conversation_id: int, latency_ms: float):
        """Record message delivery latency."""
        try:
            redis = self._get_redis()
            
            # Store latency with timestamp
            key = f"{self.MESSAGE_LATENCY_KEY}:{datetime.utcnow().date()}"
            redis.lpush(key, f"{latency_ms:.2f}:{datetime.utcnow().isoformat()}")
            redis.ltrim(key, 0, 999)  # Keep last 1000 latencies
            redis.expire(key, 86400)  # 24 hours TTL
            
            # Log high latency (> 1 second)
            if latency_ms > 1000:
                logger.warning(
                    f"High message latency: {latency_ms:.2f}ms, "
                    f"user_id={user_id}, conversation_id={conversation_id}"
                )
            
        except Exception as e:
            logger.error(f"Failed to record message latency: {e}")
    
    def record_upload_failure(self, user_id: int, error_code: str, file_size: int):
        """Record an upload failure event."""
        try:
            redis = self._get_redis()
            
            # Increment failure count by error type
            key = f"{self.UPLOAD_FAILURE_KEY}:{error_code}:{datetime.utcnow().date()}"
            redis.incr(key)
            redis.expire(key, 86400)  # 24 hours TTL
            
            # Log the failure
            logger.warning(
                f"Upload failure: user_id={user_id}, error_code={error_code}, "
                f"file_size={file_size}, timestamp={datetime.utcnow().isoformat()}"
            )
            
            # Store recent failures for monitoring
            recent_key = f"{self.UPLOAD_FAILURE_KEY}:recent"
            redis.lpush(recent_key, f"{user_id}:{error_code}:{file_size}:{datetime.utcnow().isoformat()}")
            redis.ltrim(recent_key, 0, 99)
            redis.expire(recent_key, 3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to record upload failure: {e}")
    
    def record_active_connection(self, user_id: int, conversation_id: int, action: str = 'connect'):
        """Record active WebSocket connection changes."""
        try:
            redis = self._get_redis()
            
            # Track active connections per conversation
            key = f"{self.ACTIVE_CONNECTIONS_KEY}:{conversation_id}"
            
            if action == 'connect':
                redis.sadd(key, user_id)
                redis.expire(key, 300)  # 5 minute TTL
            elif action == 'disconnect':
                redis.srem(key, user_id)
            
            # Log significant changes
            active_count = redis.scard(key)
            logger.debug(
                f"WebSocket {action}: user_id={user_id}, "
                f"conversation_id={conversation_id}, active_count={active_count}"
            )
            
        except Exception as e:
            logger.error(f"Failed to record active connection: {e}")
    
    def get_daily_reconnect_count(self) -> int:
        """Get total WebSocket reconnect count for today."""
        try:
            redis = self._get_redis()
            key = f"{self.WS_RECONNECT_KEY}:{datetime.utcnow().date()}"
            count = redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get daily reconnect count: {e}")
            return 0
    
    def get_average_message_latency(self) -> Optional[float]:
        """Get average message latency for today."""
        try:
            redis = self._get_redis()
            key = f"{self.MESSAGE_LATENCY_KEY}:{datetime.utcnow().date()}"
            latencies = redis.lrange(key, 0, -1)
            
            if not latencies:
                return None
            
            total = 0.0
            for item in latencies:
                try:
                    latency = float(item.split(':')[0])
                    total += latency
                except (ValueError, IndexError):
                    continue
            
            return total / len(latencies) if latencies else None
            
        except Exception as e:
            logger.error(f"Failed to get average message latency: {e}")
            return None
    
    def get_upload_failure_counts(self) -> Dict[str, int]:
        """Get upload failure counts by error type for today."""
        try:
            redis = self._get_redis()
            pattern = f"{self.UPLOAD_FAILURE_KEY}:*:{datetime.utcnow().date()}"
            keys = redis.keys(pattern)
            
            counts = {}
            for key in keys:
                error_code = key.split(':')[2]
                count = redis.get(key)
                if count:
                    counts[error_code] = int(count)
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get upload failure counts: {e}")
            return {}
    
    def get_active_connection_counts(self) -> Dict[int, int]:
        """Get active connection counts per conversation."""
        try:
            redis = self._get_redis()
            pattern = f"{self.ACTIVE_CONNECTIONS_KEY}:*"
            keys = redis.keys(pattern)
            
            counts = {}
            for key in keys:
                try:
                    conversation_id = int(key.split(':')[2])
                    count = redis.scard(key)
                    counts[conversation_id] = count
                except (ValueError, IndexError):
                    continue
            
            return counts
            
        except Exception as e:
            logger.error(f"Failed to get active connection counts: {e}")
            return {}


# Global metrics instance
metrics = MessagingMetrics()
