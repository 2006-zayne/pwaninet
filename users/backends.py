import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger('users.auth')
UserModel = get_user_model()


class CaseInsensitiveAuthBackend(ModelBackend):
    """
    Custom authentication backend that supports:
    1. Case-insensitive username lookup (handles mobile auto-capitalization).
    2. Stripping leading/trailing whitespace (handles mobile autocorrect spaces).
    3. Case-insensitive email lookup fallback if an email is entered.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        clean_username = str(username).strip()
        if not clean_username:
            return None

        # Normalize handle if user typed '@handle' (e.g. '@zayne')
        lookup_identifier = clean_username
        if lookup_identifier.startswith('@') and lookup_identifier.count('@') == 1 and '.' not in lookup_identifier:
            lookup_identifier = lookup_identifier.lstrip('@')

        user = None
        # If input looks like an email address, try matching by email first
        if '@' in lookup_identifier:
            user = UserModel.objects.filter(email__iexact=lookup_identifier).first()
            if user:
                logger.info(f"[AUTH-BACKEND] Found user by email: '{user.username}' (email='{lookup_identifier}')")

        # Case-insensitive username lookup
        if user is None:
            user = UserModel.objects.filter(username__iexact=lookup_identifier).first()
            if user:
                msg = f"[AUTH-BACKEND] Found user by case-insensitive username: '{user.username}' (input='{lookup_identifier}')"
                print(msg, flush=True)
                logger.info(msg)

        # Fallback email lookup (if user identifier matches email)
        if user is None and '@' not in lookup_identifier:
            user = UserModel.objects.filter(email__iexact=lookup_identifier).first()

        # Fallback to unstripped clean_username
        if user is None and lookup_identifier != clean_username:
            user = UserModel.objects.filter(username__iexact=clean_username).first()

        if user is None:
            msg = f"[AUTH-BACKEND] No user found matching identifier '{clean_username}'"
            print(msg, flush=True)
            logger.info(msg)
            # Run default password hasher to mitigate timing attacks
            UserModel().set_password(password)
            return None

        if not self.user_can_authenticate(user):
            msg = f"[AUTH-BACKEND] User '{user.username}' is not permitted to authenticate (is_active={user.is_active})"
            print(msg, flush=True)
            logger.warning(msg)
            return None

        if user.check_password(password):
            msg = f"[AUTH-BACKEND] Password verified successfully for user '{user.username}'"
            print(msg, flush=True)
            logger.info(msg)
            return user
        else:
            msg = f"[AUTH-BACKEND] Invalid password provided for user '{user.username}'"
            print(msg, flush=True)
            logger.warning(msg)
            return None
