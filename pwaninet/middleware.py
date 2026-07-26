"""
Custom middleware for Pwaninet.
"""
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation
from django.conf import settings


class CSRFExemptMiddleware(MiddlewareMixin):
    """
    Exempt API endpoints from CSRF verification in local development.
    This is a development-only convenience - production should use proper CSRF handling.
    """
    def process_request(self, request):
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)


class LanguagePreferenceMiddleware(MiddlewareMixin):
    """
    Set language based on user's language_preference field.
    """
    def process_request(self, request):
        if request.user.is_authenticated:
            user_lang = request.user.language_preference
            if user_lang in ['en', 'sw']:
                translation.activate(user_lang)
                request.LANGUAGE_CODE = user_lang
