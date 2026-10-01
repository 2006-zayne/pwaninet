"""Opt-in request and database timing for diagnosing slow page requests."""

import logging
import time
import uuid

from django.conf import settings
from django.db import connection

logger = logging.getLogger('performance')


class PerformanceTimingMiddleware:
    """Add Server-Timing headers and one concise log per request when enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'PERFORMANCE_TIMING_ENABLED', False):
            return self.get_response(request)

        request_id = uuid.uuid4().hex[:12]
        request.performance_request_id = request_id
        total_start = time.perf_counter()
        db_elapsed = 0.0
        db_queries = 0

        def time_query(execute, sql, params, many, context):
            nonlocal db_elapsed, db_queries
            started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                db_elapsed += time.perf_counter() - started
                db_queries += 1

        try:
            with connection.execute_wrapper(time_query):
                response = self.get_response(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - total_start) * 1000
            logger.exception(
                'request_id=%s method=%s path=%s status=exception total_ms=%.1f db_ms=%.1f db_queries=%d',
                request_id, request.method, request.path, elapsed_ms, db_elapsed * 1000, db_queries,
            )
            raise

        elapsed_ms = (time.perf_counter() - total_start) * 1000
        db_ms = db_elapsed * 1000
        response['X-Request-ID'] = request_id
        response['Server-Timing'] = f'app;dur={elapsed_ms:.1f}, db;dur={db_ms:.1f}, db-queries;desc="{db_queries}"'
        logger.info(
            'request_id=%s method=%s path=%s status=%d total_ms=%.1f db_ms=%.1f db_queries=%d',
            request_id, request.method, request.path, response.status_code,
            elapsed_ms, db_ms, db_queries,
        )
        return response
