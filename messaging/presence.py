"""
Presence service for heartbeat-based user online tracking.

This module implements server-authoritative presence tracking using:
- Client-initiated heartbeats (every ~25 seconds)
- Redis-based presence state with TTL
- Heartbeat freshness verification (60 second timeout)
- Multi-connection support
- Accurate last seen tracking

CORE PRINCIPLE:
Presence is determined by heartbeat freshness, not websocket disconnect events.
This prevents ghost-online states from browser crashes, sleep mode, or network issues.
"""

import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pwaninet.redis_client import get_redis_client
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

# Presence configuration
HEARTBEAT_TIMEOUT = 60  # seconds - user is online if heartbeat received within this time
HEARTBEAT_TTL = 120  # seconds - Redis key TTL (2x heartbeat timeout for safety)
CONNECTION_TRACKING_TTL = 600  # seconds - connection tracking TTL (10 minutes)

# Redis key patterns
PRESENCE_KEY_PREFIX = 'presence'
HEARTBEAT_KEY = f'{PRESENCE_KEY_PREFIX}:heartbeat'  # presence:heartbeat:{user_id}
CONNECTIONS_KEY = f'{PRESENCE_KEY_PREFIX}:connections'  # presence:connections:{user_id}
LAST_SEEN_KEY = f'{PRESENCE_KEY_PREFIX}:last_seen'  # presence:last_seen:{user_id}


class PresenceService:
    """
    Server-authoritative presence service using heartbeat-based tracking.
    
    This service manages user online status based on heartbeat freshness,
    not websocket connection/disconnection events.
    """
    
    @staticmethod
    def _get_heartbeat_key(user_id: int) -> str:
        """Get Redis key for user heartbeat timestamp."""
        return f'{HEARTBEAT_KEY}:{user_id}'
    
    @staticmethod
    def _get_connections_key(user_id: int) -> str:
        """Get Redis key for user active connections."""
        return f'{CONNECTIONS_KEY}:{user_id}'
    
    @staticmethod
    def _get_last_seen_key(user_id: int) -> str:
        """Get Redis key for user last seen timestamp."""
        return f'{LAST_SEEN_KEY}:{user_id}'
    
    @staticmethod
    def record_heartbeat(user_id: int, connection_id: str, metadata: Optional[Dict] = None) -> bool:
        """
        Record a heartbeat from a client connection.
        
        This is called when a client sends a heartbeat message.
        It updates the heartbeat timestamp and tracks the active connection.
        
        Args:
            user_id: User ID
            connection_id: Unique connection identifier (channel_name)
            metadata: Optional connection metadata (ip, user_agent, etc)
        
        Returns:
            True if heartbeat recorded successfully
        """
        try:
            redis_client = get_redis_client()
            now = time.time()
            
            # Update heartbeat timestamp with TTL
            heartbeat_key = PresenceService._get_heartbeat_key(user_id)
            redis_client.setex(heartbeat_key, HEARTBEAT_TTL, str(now))
            
            # Track active connection
            connections_key = PresenceService._get_connections_key(user_id)
            conn_data = {
                'connection_id': connection_id,
                'last_heartbeat': now,
                'connected_at': now,
            }
            if metadata:
                conn_data.update(metadata)
            
            # Use a hash to track per-connection heartbeat freshness
            conn_field = f'conn:{connection_id}'
            redis_client.hset(connections_key, conn_field, json.dumps(conn_data))
            redis_client.expire(connections_key, CONNECTION_TRACKING_TTL)
            
            # Update last seen timestamp
            last_seen_key = PresenceService._get_last_seen_key(user_id)
            redis_client.setex(last_seen_key, CONNECTION_TRACKING_TTL, str(now))
            
            print(f'[PRESENCE] Recorded heartbeat for user {user_id} (connection: {connection_id})')
            return True
        except Exception as e:
            print(f'[PRESENCE] Error recording heartbeat for user {user_id}: {e}')
            return False
    
    @staticmethod
    def is_user_online(user_id: int) -> bool:
        """
        Check if user is online based on heartbeat freshness.
        
        User is ONLINE if current_time - last_heartbeat <= HEARTBEAT_TIMEOUT (60s)
        
        Args:
            user_id: User ID
        
        Returns:
            True if user is online, False otherwise
        """
        try:
            redis_client = get_redis_client()
            heartbeat_key = PresenceService._get_heartbeat_key(user_id)
            
            heartbeat_str = redis_client.get(heartbeat_key)
            if not heartbeat_str:
                return False
            
            last_heartbeat = float(heartbeat_str)
            now = time.time()
            time_since_heartbeat = now - last_heartbeat
            
            is_online = time_since_heartbeat <= HEARTBEAT_TIMEOUT
            
            if is_online:
                print(f'[PRESENCE] User {user_id} is online (heartbeat age: {time_since_heartbeat:.1f}s)')
            else:
                print(f'[PRESENCE] User {user_id} is offline (heartbeat age: {time_since_heartbeat:.1f}s)')
            
            return is_online
        except Exception as e:
            print(f'[PRESENCE] Error checking online status for user {user_id}: {e}')
            return False
    
    @staticmethod
    def get_active_connection_count(user_id: int) -> int:
        """
        Get the number of active connections for a user.
        
        Active connections are those with recent heartbeats.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of active connections
        """
        try:
            redis_client = get_redis_client()
            connections_key = PresenceService._get_connections_key(user_id)
            
            # Get all connections
            connections = redis_client.hgetall(connections_key)
            
            # Filter connections with recent heartbeats
            now = time.time()
            active_count = 0
            stale_connections = []
            
            for conn_field, conn_json in connections.items():
                try:
                    conn_data = json.loads(conn_json)
                    last_heartbeat = conn_data.get('last_heartbeat', 0)
                    time_since_heartbeat = now - last_heartbeat
                    
                    if time_since_heartbeat <= HEARTBEAT_TIMEOUT:
                        active_count += 1
                    else:
                        # Track stale connections for cleanup
                        stale_connections.append(conn_field)
                except (json.JSONDecodeError, ValueError, TypeError):
                    stale_connections.append(conn_field)
            
            # Clean up stale connections
            if stale_connections:
                redis_client.hdel(connections_key, *stale_connections)
                print(f'[PRESENCE] Cleaned {len(stale_connections)} stale connections for user {user_id}')
            
            return active_count
        except Exception as e:
            print(f'[PRESENCE] Error getting connection count for user {user_id}: {e}')
            return 0
    
    @staticmethod
    def remove_connection(user_id: int, connection_id: str) -> None:
        """
        Remove a specific connection from tracking.
        
        This is called on websocket disconnect, but does NOT mark user offline.
        User offline status is determined by heartbeat freshness.
        
        Args:
            user_id: User ID
            connection_id: Connection identifier
        """
        try:
            redis_client = get_redis_client()
            connections_key = PresenceService._get_connections_key(user_id)
            
            conn_field = f'conn:{connection_id}'
            redis_client.hdel(connections_key, conn_field)
            
            print(f'[PRESENCE] Removed connection {connection_id} for user {user_id}')
        except Exception as e:
            print(f'[PRESENCE] Error removing connection {connection_id} for user {user_id}: {e}')
    
    @staticmethod
    def get_last_seen(user_id: int) -> Optional[datetime]:
        """
        Get the last seen timestamp for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Last seen datetime or None
        """
        try:
            redis_client = get_redis_client()
            last_seen_key = PresenceService._get_last_seen_key(user_id)
            
            last_seen_str = redis_client.get(last_seen_key)
            if not last_seen_str:
                # Fallback to database if not in Redis
                return PresenceService._get_last_seen_from_db(user_id)
            
            last_seen_timestamp = float(last_seen_str)
            return datetime.fromtimestamp(last_seen_timestamp)
        except Exception as e:
            print(f'[PRESENCE] Error getting last seen for user {user_id}: {e}')
            return None
    
    @staticmethod
    @database_sync_to_async
    def _get_last_seen_from_db(user_id: int) -> Optional[datetime]:
        """Get last seen from database as fallback."""
        try:
            user = User.objects.get(id=user_id)
            return user.last_seen
        except User.DoesNotExist:
            return None
    
    @staticmethod
    @database_sync_to_async
    def persist_last_seen_to_db(user_id: int) -> None:
        """
        Persist last seen timestamp to database.
        
        This should be called when user truly goes offline
        (heartbeat timeout expires with no active connections).
        
        Args:
            user_id: User ID
        """
        try:
            redis_client = get_redis_client()
            last_seen_key = PresenceService._get_last_seen_key(user_id)
            
            last_seen_str = redis_client.get(last_seen_key)
            if not last_seen_str:
                return
            
            last_seen_timestamp = float(last_seen_str)
            last_seen_datetime = datetime.fromtimestamp(last_seen_timestamp)
            
            user = User.objects.get(id=user_id)
            user.last_seen = last_seen_datetime
            user.is_online = False
            user.save(update_fields=['last_seen', 'is_online'])
            
            print(f'[PRESENCE] Persisted last_seen to DB for user {user_id}: {last_seen_datetime}')
        except User.DoesNotExist:
            pass
        except Exception as e:
            print(f'[PRESENCE] Error persisting last_seen for user {user_id}: {e}')
    
    @staticmethod
    def cleanup_stale_presence(user_id: int) -> None:
        """
        Clean up stale presence data for a user.
        
        This removes heartbeat and connection data when user has been offline
        for an extended period.
        
        Args:
            user_id: User ID
        """
        try:
            redis_client = get_redis_client()
            
            # Check if user is offline
            if PresenceService.is_user_online(user_id):
                return
            
            # Check if there are any active connections
            if PresenceService.get_active_connection_count(user_id) > 0:
                return
            
            # User is offline with no active connections - clean up
            heartbeat_key = PresenceService._get_heartbeat_key(user_id)
            connections_key = PresenceService._get_connections_key(user_id)
            
            redis_client.delete(heartbeat_key)
            redis_client.delete(connections_key)
            
            print(f'[PRESENCE] Cleaned up stale presence data for user {user_id}')
        except Exception as e:
            print(f'[PRESENCE] Error cleaning up presence for user {user_id}: {e}')
    
    @staticmethod
    def get_presence_info(user_id: int) -> Dict:
        """
        Get comprehensive presence information for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with is_online, last_seen, active_connections, etc.
        """
        try:
            redis_client = get_redis_client()
            heartbeat_key = PresenceService._get_heartbeat_key(user_id)
            
            heartbeat_str = redis_client.get(heartbeat_key)
            is_online = False
            last_heartbeat = None
            
            if heartbeat_str:
                last_heartbeat = float(heartbeat_str)
                now = time.time()
                is_online = (now - last_heartbeat) <= HEARTBEAT_TIMEOUT
            
            last_seen = PresenceService.get_last_seen(user_id)
            active_connections = PresenceService.get_active_connection_count(user_id)
            
            return {
                'user_id': user_id,
                'is_online': is_online,
                'last_seen': last_seen.isoformat() if last_seen else None,
                'last_heartbeat': last_heartbeat,
                'active_connections': active_connections,
            }
        except Exception as e:
            print(f'[PRESENCE] Error getting presence info for user {user_id}: {e}')
            return {
                'user_id': user_id,
                'is_online': False,
                'last_seen': None,
                'last_heartbeat': None,
                'active_connections': 0,
            }
