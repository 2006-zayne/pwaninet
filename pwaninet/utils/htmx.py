import json
from django.http import HttpResponse


def htmx_location_response(path, target='#page-content-target'):
    """
    Return an HTTP 204 response with an HX-Location header targeting
    the SPA page container (#page-content-target).
    
    This performs a smooth HTMX-driven page swap without triggering
    a full browser page unload, preserving active uploads in window.uploadManager.
    """
    response = HttpResponse(status=204)
    response['HX-Location'] = json.dumps({
        'path': path,
        'target': target,
    })
    return response
