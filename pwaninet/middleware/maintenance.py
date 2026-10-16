"""Per-page maintenance locks, managed from the Django admin.

When a :class:`admin_dashboard.models.PageMaintenance` row is active, any
request whose path starts with its ``path_prefix`` is short-circuited with
``maintenance.html`` (HTTP 503). Everything else passes through untouched.
"""

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

CACHE_KEY = "maintenance:active_locks"
CACHE_TIMEOUT = 60

# Never lock these: admin itself, static/media assets, the health probe used
# by the maintenance page auto-retry, and the offline fallbacks.
EXEMPT_PREFIXES = (
    "/admin/",
    "/static/",
    "/staticfiles/",
    "/media/",
    "/private_media/",
    "/api/health/",
    "/offline/",
    "/offline.html",
    "/manifest.webmanifest",
    "/service-worker.js",
    "/favicon",
)


def get_active_locks():
    locks = cache.get(CACHE_KEY)
    if locks is None:
        from admin_dashboard.models import PageMaintenance
        locks = list(
            PageMaintenance.objects.filter(is_active=True).values(
                "name", "path_prefix", "headline", "message", "eta", "show_eta",
            )
        )
        cache.set(CACHE_KEY, locks, CACHE_TIMEOUT)
    return locks


def _wants_json(request):
    if request.headers.get("HX-Request"):
        return True
    return "application/json" in request.headers.get("Accept", "")


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lock = self._matching_lock(request)
        if lock is None:
            return self.get_response(request)
        return self._locked_response(request, lock)

    def _matching_lock(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
            return None
        user = getattr(request, "user", None)
        if user is not None and (user.is_staff or user.is_superuser):
            return None
        for lock in get_active_locks():
            if path.startswith(lock["path_prefix"]):
                return lock
        return None

    def _locked_response(self, request, lock):
        eta_display = None
        retry_after = 3600
        if lock["eta"]:
            local_eta = timezone.localtime(lock["eta"])
            eta_display = local_eta.strftime("%d %b · %H:%M %Z").strip()
            retry_after = max(int((lock["eta"] - timezone.now()).total_seconds()), 60)
        if _wants_json(request):
            response = JsonResponse(
                {
                    "locked": True,
                    "area": lock["name"],
                    "headline": lock["headline"],
                    "message": lock["message"],
                    "eta": lock["eta"].isoformat() if lock["eta"] else None,
                },
                status=503,
            )
        else:
            response = render(
                request,
                "maintenance.html",
                {
                    "area": lock["name"],
                    "headline": lock["headline"],
                    "message": lock["message"],
                    "eta_display": eta_display,
                    "show_eta": lock["show_eta"],
                },
                status=503,
            )
        response["Retry-After"] = str(retry_after)
        return response
