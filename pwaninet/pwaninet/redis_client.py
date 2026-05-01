"""
Centralized Redis connection management with connection pooling.
Prevents connection exhaustion and resource leaks.
"""

import redis
import socket
import os
from typing import Optional

# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_connection: Optional[redis.Redis] = None


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
        )
    
    return _redis_pool


def get_redis_client() -> redis.Redis:
    """
    Get Redis client from pool.
    
    Always use this instead of creating new connections directly.
    The client is backed by the shared connection pool.
    
    Returns:
        redis.Redis: Redis client connected via connection pool
    """
    global _redis_connection
    
    if _redis_connection is None:
        pool = get_redis_pool()
        _redis_connection = redis.Redis(connection_pool=pool)
    
    return _redis_connection


def close_redis() -> None:
    """Close Redis connection pool. Call during app shutdown."""
    global _redis_pool, _redis_connection
    
    if _redis_connection is not None:
        _redis_connection.close()
        _redis_connection = None
    
    if _redis_pool is not None:
        _redis_pool.disconnect()
        _redis_pool = None
