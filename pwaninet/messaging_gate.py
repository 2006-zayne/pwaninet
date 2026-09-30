"""Shared HTTP response for messaging routes frozen during the MVP."""

from django.http import HttpResponse, JsonResponse


def messaging_frozen(request, *args, **kwargs):
    """Reject messaging page and API requests while the feature is frozen."""
    detail = "Messaging is unavailable while the MVP feature is frozen."
    if "/api/" in request.path or "/v1/" in request.path:
        response = JsonResponse({"detail": detail}, status=410)
    else:
        response = HttpResponse(detail, status=410, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
