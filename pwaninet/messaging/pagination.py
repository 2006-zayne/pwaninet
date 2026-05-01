"""
Custom pagination classes for messaging API.
Implements cursor-based and limit-offset pagination for messages.
"""

from rest_framework.pagination import LimitOffsetPagination, CursorPagination


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
