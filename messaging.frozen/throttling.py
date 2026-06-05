"""
Custom throttling classes for messaging API.
Implements rate limiting for different message operations.
"""

from rest_framework.throttling import ScopedRateThrottle


class MessageSendThrottle(ScopedRateThrottle):
    """
    Rate limit for sending messages.
    Prevents message spam and DOS attacks.
    
    Config: 60 messages per minute per user
    """
    scope = 'message_send'


class MessageReactionThrottle(ScopedRateThrottle):
    """
    Rate limit for adding reactions.
    Prevents reaction spam.
    
    Config: 30 reactions per minute per user
    """
    scope = 'message_reaction'


class ConversationCreateThrottle(ScopedRateThrottle):
    """
    Rate limit for creating conversations.
    Prevents conversation spam.
    
    Config: 10 conversations per minute per user
    """
    scope = 'conversation_create'


class WebSocketMessageThrottle(ScopedRateThrottle):
    """
    Rate limit for WebSocket messages.
    Prevents connection spam through WebSocket.
    
    Config: 100 messages per minute per connection
    """
    scope = 'ws_message'
