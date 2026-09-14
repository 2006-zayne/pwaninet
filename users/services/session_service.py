import logging
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from user_agents import parse

from users.models import UserSession, DeviceAccount
from users.services.device_service import get_or_create_device_id, hash_device_id

logger = logging.getLogger('users.auth')


def parse_device_metadata(user_agent_string):
    """
    Extract structured device, browser, and OS metadata from User-Agent string.
    """
    if not user_agent_string:
        return {
            'device_name': 'Unknown Device',
            'device_type': 'desktop',
            'browser': 'Unknown Browser',
            'operating_system': 'Unknown OS',
        }

    try:
        user_agent = parse(user_agent_string)

        device_type = 'desktop'
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'

        browser_family = user_agent.browser.family or 'Unknown'
        browser_version = user_agent.browser.version_string or ''
        browser = f"{browser_family} {browser_version}".strip()

        os_family = user_agent.os.family or 'Unknown'
        os_version = user_agent.os.version_string or ''
        operating_system = f"{os_family} {os_version}".strip()

        device_model = user_agent.device.family or 'Unknown Device'
        if device_model == 'Other':
            device_model = f"{operating_system} {device_type.capitalize()}"

        return {
            'device_name': device_model,
            'device_type': device_type,
            'browser': browser,
            'operating_system': operating_system,
        }
    except Exception as e:
        logger.debug(f"[SECURITY-SESSION] Error parsing user agent: {e}")
        return {
            'device_name': 'Unknown Device',
            'device_type': 'desktop',
            'browser': 'Unknown Browser',
            'operating_system': 'Unknown OS',
        }


def get_client_ip(request):
    """
    Resolve client IP address from request headers.
    """
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def create_or_update_session(user, request):
    """
    Create or update UserSession and DeviceAccount upon successful authentication.
    Prevents duplicates and guarantees accurate metadata.
    """
    if not request or not user or not user.is_authenticated:
        return None

    if not hasattr(request, 'session'):
        return None

    session_key = request.session.session_key
    if not session_key:
        request.session.save()
        session_key = request.session.session_key

    if not session_key:
        logger.warning(f"[SECURITY-SESSION] Unable to obtain session_key for user '{user.username}'")
        return None

    ip_address = get_client_ip(request)
    user_agent_string = request.META.get('HTTP_USER_AGENT', '')
    meta = parse_device_metadata(user_agent_string)

    user_session, created = UserSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'ip_address': ip_address,
            'user_agent': user_agent_string,
            'device_name': meta['device_name'],
            'device_type': meta['device_type'],
            'browser': meta['browser'],
            'operating_system': meta['operating_system'],
            'last_activity': timezone.now(),
            'is_current': True,
        }
    )

    masked_key = f"{session_key[:8]}..." if len(session_key) > 8 else "***"
    action = "CREATED" if created else "UPDATED"
    logger.info(
        f"[SECURITY-SESSION] {action}: session_key={masked_key} for user '{user.username}' (id={user.id}) "
        f"from IP={ip_address}, device={meta['device_name']}"
    )

    # Maintain DeviceAccount tracking
    device_id = get_or_create_device_id(request)
    if device_id:
        hashed_device_id = hash_device_id(device_id)
        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': session_key,
                'last_used': timezone.now(),
            }
        )

    return user_session


def revoke_session(session_identifier, user=None):
    """
    Revoke a specific session by UserSession ID or session_key.
    Deletes the Django Session and UserSession, and clears DeviceAccount session_key.
    Returns True if found and revoked, False otherwise.
    """
    try:
        if isinstance(session_identifier, int) or (isinstance(session_identifier, str) and session_identifier.isdigit()):
            qs = UserSession.objects.filter(id=int(session_identifier))
        else:
            qs = UserSession.objects.filter(session_key=str(session_identifier))

        if user:
            qs = qs.filter(user=user)

        user_session = qs.first()
        if not user_session:
            return False

        target_key = user_session.session_key
        target_user = user_session.user

        # Delete Django Session
        Session.objects.filter(session_key=target_key).delete()

        # Delete UserSession record
        user_session.delete()

        # Clear session_key on DeviceAccount
        DeviceAccount.objects.filter(session_key=target_key).update(session_key=None)

        masked_key = f"{target_key[:8]}..." if len(target_key) > 8 else "***"
        logger.info(f"[SECURITY-SESSION] REVOKED: session_key={masked_key} for user '{target_user.username}'")
        return True
    except Exception as e:
        logger.error(f"[SECURITY-SESSION] Failed to revoke session {session_identifier}: {e}")
        return False


def revoke_all_user_sessions(user, keep_session_key=None):
    """
    Revoke all sessions for a user, optionally preserving keep_session_key.
    Returns count of revoked sessions.
    """
    if not user:
        return 0

    try:
        qs = UserSession.objects.filter(user=user)
        if keep_session_key:
            qs = qs.exclude(session_key=keep_session_key)

        session_keys_to_delete = list(qs.values_list('session_key', flat=True))
        count = len(session_keys_to_delete)

        if session_keys_to_delete:
            # 1. Delete from Django Session table
            Session.objects.filter(session_key__in=session_keys_to_delete).delete()

            # 2. Delete from UserSession table
            qs.delete()

            # 3. Clear session_key in DeviceAccount
            DeviceAccount.objects.filter(
                user=user,
                session_key__in=session_keys_to_delete
            ).update(session_key=None)

        logger.info(
            f"[SECURITY-SESSION] REVOKED_ALL: {count} sessions revoked for user '{user.username}' "
            f"(keep_current={'yes' if keep_session_key else 'no'})"
        )
        return count
    except Exception as e:
        logger.error(f"[SECURITY-SESSION] Failed to revoke all sessions for user {user.username}: {e}")
        return 0


def revoke_other_user_sessions(user, current_session_key):
    """
    Revoke all sessions for a user except the current one.
    """
    return revoke_all_user_sessions(user, keep_session_key=current_session_key)
