"""Shared HTTP response for messaging routes (legacy compatibility)."""

from django.http import HttpResponseRedirect, JsonResponse


def messaging_frozen(request, *args, **kwargs):
    """Safe fallback redirecting to conversation list or returning 404 for APIs."""
    if "/api/" in request.path or "/v1/" in request.path:
        return JsonResponse({"detail": "Not found"}, status=404)
    return HttpResponseRedirect('/messaging/')
