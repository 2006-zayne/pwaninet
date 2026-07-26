"""
Language Preference Middleware
Set language based on user's language_preference field.
"""
from django.utils.deprecation import MiddlewareMixin
from django.utils import translation


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
