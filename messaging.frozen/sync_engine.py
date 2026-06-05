"""
Message deduplication and sync engine for real-time chat.
Prevents duplicate messages and handles offline sync scenarios.
"""

from datetime import datetime, timedelta
from pwaninet.redis_client import get_redis_client
import hashlib
import json


class MessageDeduplicator:
    """
    Deduplicates messages using idempotency keys and timestamps.
    Prevents duplicate messages when:
    - User sends same message twice
    - Connection drops and message is retried
    - WebSocket broadcasts duplicate
    """

    DEDUP_WINDOW = 60  # seconds - time window for duplicate detection
    KEY_PREFIX = 'msg_dedup'

    @classmethod
    def get_dedup_key(cls, conversation_id: int, sender_id: int, content: str, timestamp: float = None) -> str:
        """
        Generate a unique deduplication key for a message.
        
        Args:
            conversation_id: ID of conversation
            sender_id: ID of sender
            content: Message content
            timestamp: Message timestamp (for additional uniqueness)
        
        Returns:
            Deduplication key
        """
        msg_hash = hashlib.md5(f"{conversation_id}:{sender_id}:{content}".encode()).hexdigest()
        return f"{cls.KEY_PREFIX}:{conversation_id}:{msg_hash}"

    @classmethod
    def is_duplicate(cls, dedup_key: str) -> bool:
        """
        Check if message is duplicate within dedup window.
        
        Args:
            dedup_key: Deduplication key
        
        Returns:
            True if duplicate, False if new
        """
        try:
            redis_client = get_redis_client()
            exists = redis_client.get(dedup_key)
            return exists is not None
        except Exception:
            return False

    @classmethod
    def mark_processed(cls, dedup_key: str) -> None:
        """
        Mark message as processed to prevent duplicates.
        
        Args:
            dedup_key: Deduplication key
        """
        try:
            redis_client = get_redis_client()
            redis_client.setex(dedup_key, cls.DEDUP_WINDOW, '1')
        except Exception:
            pass

    @classmethod
    def get_conversation_sync_state(cls, conversation_id: int, user_id: int) -> dict:
        """
        Get sync state for a conversation (last message timestamp, unread count).
        
        Args:
            conversation_id: ID of conversation
            user_id: ID of user
        
        Returns:
            Sync state dict with last_sync_time and unread_count
        """
        try:
            redis_client = get_redis_client()
            sync_key = f"sync:{conversation_id}:{user_id}"
            sync_data = redis_client.hgetall(sync_key)
            
            return {
                'last_sync_time': float(sync_data.get('last_sync_time', 0)),
                'last_message_id': int(sync_data.get('last_message_id', 0)),
            }
        except Exception:
            return {'last_sync_time': 0, 'last_message_id': 0}

    @classmethod
    def update_sync_state(cls, conversation_id: int, user_id: int, last_message_id: int) -> None:
        """
        Update sync state for a conversation.
        
        Args:
            conversation_id: ID of conversation
            user_id: ID of user
            last_message_id: ID of last seen message
        """
        try:
            redis_client = get_redis_client()
            sync_key = f"sync:{conversation_id}:{user_id}"
            redis_client.hset(sync_key, mapping={
                'last_sync_time': datetime.now().timestamp(),
                'last_message_id': last_message_id,
            })
            redis_client.expire(sync_key, 86400 * 7)  # Expire after 7 days
        except Exception:
            pass


class MessageQueue:
    """
    Queue for messages that failed to send, enabling offline sync.
    Frontend can queue messages locally and sync when reconnected.
    """

    QUEUE_PREFIX = 'msg_queue'
    MAX_QUEUE_SIZE = 100
    QUEUE_TIMEOUT = 3600  # 1 hour - messages older than this are discarded

    @classmethod
    def get_queue_key(cls, user_id: int) -> str:
        """Get Redis key for user's message queue."""
        return f"{cls.QUEUE_PREFIX}:{user_id}"

    @classmethod
    def enqueue_message(cls, user_id: int, message: dict) -> bool:
        """
        Add message to offline queue.
        
        Args:
            user_id: ID of user
            message: Message data dict
        
        Returns:
            True if queued successfully, False otherwise
        """
        try:
            redis_client = get_redis_client()
            queue_key = cls.get_queue_key(user_id)
            
            # Add timestamp
            message['queued_at'] = datetime.now().timestamp()
            
            # Use list to maintain order
            redis_client.lpush(queue_key, json.dumps(message))
            
            # Trim to max size (keep newest)
            redis_client.ltrim(queue_key, 0, cls.MAX_QUEUE_SIZE - 1)
            
            # Set expiration
            redis_client.expire(queue_key, cls.QUEUE_TIMEOUT)
            
            return True
        except Exception:
            return False

    @classmethod
    def get_queued_messages(cls, user_id: int) -> list:
        """
        Get all queued messages for a user.
        
        Args:
            user_id: ID of user
        
        Returns:
            List of message dicts
        """
        try:
            redis_client = get_redis_client()
            queue_key = cls.get_queue_key(user_id)
            
            messages_json = redis_client.lrange(queue_key, 0, -1)
            messages = [json.loads(m) for m in messages_json]
            
            # Filter out old messages
            now = datetime.now().timestamp()
            valid_messages = [
                m for m in messages
                if now - m.get('queued_at', now) < cls.QUEUE_TIMEOUT
            ]
            
            return valid_messages
        except Exception:
            return []

    @classmethod
    def clear_queue(cls, user_id: int) -> None:
        """Clear all queued messages for a user."""
        try:
            redis_client = get_redis_client()
            queue_key = cls.get_queue_key(user_id)
            redis_client.delete(queue_key)
        except Exception:
            pass
