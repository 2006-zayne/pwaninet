"""
Centralized Redis connection management with connection pooling and health checks.
Prevents connection exhaustion and resource leaks.
"""

import redis
import socket
import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_connection: Optional[redis.Redis] = None
_last_health_check = 0
_health_check_interval = 30  # seconds


def get_redis_pool() -> redis.ConnectionPool:
    """
    Get or create Redis connection pool.
    
    Uses connection pooling to limit concurrent connections and prevent
    resource exhaustion when handling many concurrent WebSocket connections.
    
    Returns:
        redis.ConnectionPool: Shared connection pool
    """
    global _redis_pool
    
    if _redis_pool is None:
        redis_host = os.environ.get('REDIS_HOST', '127.0.0.1')
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_db = int(os.environ.get('REDIS_DB', 0))
        
        _redis_pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,
            max_connections=50,  # Limit concurrent connections
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,  # Built-in Redis health check
        )
        logger.info(f"Created Redis connection pool for {redis_host}:{redis_port}")
    
    return _redis_pool


def check_redis_health(client: redis.Redis) -> bool:
    """
    Check if Redis connection is healthy.
    
    Args:
        client: Redis client to check
        
    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        client.ping()
        return True
    except (redis.ConnectionError, redis.TimeoutError, socket.timeout) as e:
        logger.warning(f"Redis health check failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Redis health check: {e}")
        return False


def get_redis_client() -> redis.Redis:
    """
    Get Redis client from pool with health check.
    
    Always use this instead of creating new connections directly.
    The client is backed by the shared connection pool.
    Performs periodic health checks and reconnection if needed.
    
    Returns:
        redis.Redis: Redis client connected via connection pool
    """
    global _redis_connection, _last_health_check
    
    if _redis_connection is None:
        pool = get_redis_pool()
        _redis_connection = redis.Redis(connection_pool=pool)
        logger.info("Created Redis client from pool")
    
    # Periodic health check
    current_time = time.time()
    if current_time - _last_health_check > _health_check_interval:
        _last_health_check = current_time
        if not check_redis_health(_redis_connection):
            logger.warning("Redis health check failed, recreating connection")
            # Force reconnection
            try:
                _redis_connection.close()
            except Exception:
                pass
            pool = get_redis_pool()
            _redis_connection = redis.Redis(connection_pool=pool)
            # Verify new connection
            if not check_redis_health(_redis_connection):
                logger.error("Failed to establish healthy Redis connection")
    
    return _redis_connection


def close_redis() -> None:
    """Close Redis connection pool. Call during app shutdown."""
    global _redis_pool, _redis_connection
    
    if _redis_connection is not None:
        try:
            _redis_connection.close()
            logger.info("Closed Redis client connection")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        _redis_connection = None
    
    if _redis_pool is not None:
        try:
            _redis_pool.disconnect()
            logger.info("Disconnected Redis connection pool")
        except Exception as e:
            logger.error(f"Error disconnecting Redis pool: {e}")
        _redis_pool = None
