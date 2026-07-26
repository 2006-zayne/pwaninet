"""
CSRF Exempt Middleware
Exempt API endpoints from CSRF verification in local development.
This is a development-only convenience - production should use proper CSRF handling.
"""
from django.utils.deprecation import MiddlewareMixin


class CSRFExemptMiddleware(MiddlewareMixin):
    """
    Exempt API endpoints from CSRF verification in local development.
    This is a development-only convenience - production should use proper CSRF handling.
    """
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
