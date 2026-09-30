"""Record coarse daily activity for authenticated dashboard analytics."""

import logging

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    """Record one heartbeat per active account every two minutes."""

    CACHE_TTL_SECONDS = 120

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user is not None
            and user.is_authenticated
        ):
            now = timezone.now()
            activity_date = timezone.localdate(now)
            cache_key = f"admin-dashboard:activity:{user.pk}:{activity_date.isoformat()}"
            try:
                if cache.add(cache_key, '1', timeout=self.CACHE_TTL_SECONDS):
                    from admin_dashboard.models import UserDailyActivity

                    UserDailyActivity.objects.update_or_create(
                        user_id=user.pk,
                        activity_date=activity_date,
                        defaults={'last_seen_at': now},
                    )
            except Exception:
                # Analytics must never make a student's page request fail.
                logger.exception('Could not record daily user activity')
        return self.get_response(request)
