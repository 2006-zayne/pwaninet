"""
Custom pagination classes for messaging API.
Implements cursor-based and limit-offset pagination for messages.
"""

from rest_framework.pagination import LimitOffsetPagination, CursorPagination
from rest_framework.response import Response
from rest_framework.utils import formatting


class MessageLimitOffsetPagination(LimitOffsetPagination):
    """
    Pagination for message lists with configurable limit.
    Supports limit and offset query parameters.
    
    Usage:
        /api/v1/messages/?limit=50&offset=0
        /api/v1/messages/?limit=100  (max 100)
    """
    default_limit = 20
    max_limit = 100
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    template = None


class MessageCursorPagination(CursorPagination):
    """
    Cursor-based pagination for message lists.
    More efficient for large datasets, prevents issues with concurrent inserts.
    
    Usage:
        /api/v1/messages/?cursor=cD0xMjM0NTY3ODk=
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-created_at'
    template = None


class BeforeMessageIdPagination:
    """
    Custom cursor-based pagination using before_message_id for message history.
    This is optimized for chat applications where users scroll up to load older messages.
    
    Query parameters:
        - before_message_id: Load messages older than this message ID
        - limit: Number of messages to return (default 30, max 100)
    
    Response includes:
        - results: List of messages
        - has_more: Whether there are older messages available
        - next_cursor: The before_message_id for the next page (oldest message in current set)
    """
    
    def __init__(self, default_limit=30, max_limit=100):
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate queryset using before_message_id cursor strategy.
        """
        limit = self.get_limit(request)
        before_message_id = request.query_params.get('before_message_id')
        
        # Base queryset - order by created_at descending (newest first)
        queryset = queryset.order_by('-created_at')
        
        # Apply cursor filter if provided
        if before_message_id:
            try:
                before_message_id = int(before_message_id)
                # Filter messages older than the cursor message
                queryset = queryset.filter(id__lt=before_message_id)
            except (ValueError, TypeError):
                pass
        
        # Apply limit
        queryset = queryset[:limit + 1]  # Fetch one extra to check if there are more
        
        self.queryset = list(queryset)
        self.request = request
        self.has_more = len(self.queryset) > limit
        
        # Remove the extra item if we fetched it
        if self.has_more:
            self.queryset = self.queryset[:limit]
        
        return self.queryset
    
    def get_limit(self, request):
        """
        Get the limit from request, respecting max_limit.
        """
        try:
            limit = int(request.query_params.get('limit', self.default_limit))
            return min(max(limit, 1), self.max_limit)
        except (ValueError, TypeError):
            return self.default_limit
    
    def get_paginated_response(self, data):
        """
        Return paginated response with cursor information.
        """
        # Get the oldest message ID for next cursor
        next_cursor = None
        if self.queryset and self.has_more:
            next_cursor = self.queryset[-1].id
        
        return Response({
            'results': data,
            'has_more': self.has_more,
            'next_cursor': next_cursor,
            'count': len(data)
        })
