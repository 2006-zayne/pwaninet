"""
Device alert service (Phase 1).

Detects sign-ins from devices the user has never trusted, sends the
non-blocking challenge (DeviceVerificationEvent + notification pipeline), and
implements the user's response: approve (trust) or deny (block device, with an
optional full "nuke" escalation that revokes sessions and forces a password
reset). Enforced invariants:

- Device fingerprints are stored only as peppered hashes (device_service.hash_device_id).
- Approval/denial can NEVER be performed by the device being verified.
- TrustedDevice.is_primary is unique per user (maintained here).
- SECURITY-category notifications are mandatory in the preference engine, so
  device alerts can never be muted by user preferences.
"""
import sys
import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from users.models import (
    User,
    DeviceAccount,
    TrustedDevice,
    DeviceVerificationEvent,
    BlockedDevice,
    DeviceBlockReason,
    DeviceAlertChannel,
    DeviceVerificationStatus,
)
from notifications.models import NotificationObject
from notifications.events.registry import EventTypes
from notifications.events.publisher import EventPublisher

logger = logging.getLogger(__name__)

CHALLENGE_EXPIRY_HOURS = int(getattr(settings, 'DEVICE_VERIFICATION_EXPIRY_HOURS', 24))
DEVICE_ALERT_EMAIL_FALLBACK = getattr(settings, 'DEVICE_ALERT_EMAIL_FALLBACK', True)

_GEOIP_INSTANCE = None
_GEOIP_READY = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_device_hash(request):
    """Peppered hash of the device ID for this request, or None."""
    try:
        from users.services.device_service import get_or_create_device_id, hash_device_id
        device_id = get_or_create_device_id(request)
        if not device_id:
            return None
        return hash_device_id(device_id)
    except Exception as e:
        logger.warning(f"[DEVICE-ALERT] Could not resolve device hash: {e}")
        return None


def _geoip_lookup(ip_address):
    """
    Best-effort offline IP geolocation (GeoLite2-City via geoip2).

    Optional: enabled only when the ``geoip2`` package is installed and
    settings.GEOIP_PATH points at the database. Returns (city, country);
    either may be blank.
    """
    global _GEOIP_INSTANCE, _GEOIP_READY
    if not ip_address or not getattr(settings, 'GEOIP_PATH', None):
        return '', ''
    if not _GEOIP_READY:
        _GEOIP_READY = True
        try:
            from django.contrib.gis.geoip2 import GeoIP2
            _GEOIP_INSTANCE = GeoIP2()
        except Exception as e:
            logger.debug(f"[DEVICE-ALERT] GeoIP unavailable: {e}")
    try:
        if _GEOIP_INSTANCE:
            city_record = _GEOIP_INSTANCE.city(ip_address)
            return (city_record.get('city') or '', city_record.get('country_name') or '')
    except Exception:
        pass
    return '', ''


def _format_time(value):
    """Timestamp string for alert copy, project timezone (Africa/Nairobi)."""
    try:
        local = timezone.localtime(value)
    except Exception:
        local = value
    return local.strftime('%a %d %b %Y, %H:%M')


def _device_label(event):
    bits = [b for b in (event.device_name, event.browser) if b]
    return ' · '.join(bits) if bits else (event.device_type or 'New device')


def _verification_sheet_url(event):
    try:
        return f"/users/security/device-verifications/{event.pk}/"
    except Exception:
        return '/users/settings/privacy/devices/'


# ---------------------------------------------------------------------------
# Detection (called from session_service after a successful login creates a
# new UserSession row)
# ---------------------------------------------------------------------------

def evaluate_device_login(user, request, user_session):
    """
    Decide what to do about a newly created session:
      'blocked'      -> device is blocked; session revoked
      'silently_ok'  -> device already trusted (or challenge already exists)
      'bootstrapped' -> user had no trusted devices; auto-trust
      'challenge'    -> alert dispatched to trusted devices
      'skipped'      -> could not resolve device identity
    Never raises out of the login path.
    """
    try:
        device_hash = resolve_device_hash(request)
        if not device_hash:
            return 'skipped'

        if BlockedDevice.objects.filter(user=user, device_hash=device_hash).exists():
            try:
                from users.services.session_service import revoke_session
                revoke_session(user_session.session_key, user=user)
            except Exception:
                pass
            logger.warning(
                f"[DEVICE-ALERT] Blocked device login refused for user '{user.username}' "
                f"(hash={device_hash[:10]})"
            )
            return 'blocked'

        if TrustedDevice.objects.filter(user=user, device_hash=device_hash).exists():
            return 'silently_ok'

        if not TrustedDevice.objects.filter(user=user).exists():
            # Bootstrap: the user's first ever device is auto-trusted so
            # rollout does not storm every user with alerts about their own
            # daily devices (there is no trusted device to receive the alert
            # anyway). Email-only notification keeps it visible.
            TrustedDevice.objects.create(
                user=user,
                device_hash=device_hash,
                device_name=user_session.device_name if user_session else '',
                is_primary=True,
            )
            _send_bootstrap_email(user, user_session)
            logger.info(f"[DEVICE-ALERT] Bootstrapped trust for user '{user.username}'")
            return 'bootstrapped'

        # Idempotency: one pending challenge per user+session
        if DeviceVerificationEvent.objects.filter(
            user=user,
            session_key=user_session.session_key,
            status=DeviceVerificationStatus.PENDING,
        ).exists():
            return 'silently_ok'

        _send_challenge(user, request, user_session, device_hash)
        return 'challenge'
    except Exception as e:
        import traceback
        logger.error(f"[DEVICE-ALERT] evaluate_device_login failed: {e}\n{traceback.format_exc()}")
        return 'skipped'


def _send_challenge(user, request, user_session, device_hash):
    from users.services.session_service import get_client_ip

    ip_address = get_client_ip(request)
    location_city, location_country = _geoip_lookup(ip_address)

    if user_session:
        device_name = user_session.device_name or ''
        device_type = user_session.device_type or 'desktop'
        browser = user_session.browser or ''
        operating_system = user_session.operating_system or ''
        session_key = user_session.session_key or ''
    else:
        device_name, device_type, browser, operating_system, session_key = '', 'desktop', '', '', ''

    event = DeviceVerificationEvent.objects.create(
        user=user,
        device_hash=device_hash,
        device_name=device_name,
        device_type=device_type,
        browser=browser,
        operating_system=operating_system,
        ip_address=ip_address,
        location_city=location_city,
        location_country=location_country,
        session_key=session_key,
        status=DeviceVerificationStatus.PENDING,
        expires_at=timezone.now() + timedelta(hours=CHALLENGE_EXPIRY_HOURS),
    )

    metadata = {
        'target_user_id': user.pk,
        'challenge_id': str(event.pk),
        'device_label': _device_label(event),
        'location_label': event.location_label or 'Unknown location',
        'event_time': _format_time(event.created_at),
        'target_url': _verification_sheet_url(event),
    }

    try:
        published_event = EventPublisher.publish(
            event_type=EventTypes.SECURITY_DEVICE_LOGIN_NEW.value,
            source='USERS',
            action='detected',
            target_type='DeviceVerificationEvent',
            target_id=str(event.pk),
            actor=user,
            context_type='UserSession',
            context_id=user_session.session_key,
            audience=str(user.pk),
            metadata=metadata,
        )
        logger.info(
            f"[DEVICE-ALERT] Challenge {event.pk} published for user '{user.username}' "
            f"(platform_event={getattr(published_event, 'event_id', None)})"
        )
        # Link the created NotificationObject back onto the event once the
        # pipeline has run (eager in tests/dev, celery in production).
        _schedule_notification_link(event.pk)
    except Exception as e:
        logger.error(f"[DEVICE-ALERT] Failed to publish challenge {event.pk}: {e}", exc_info=True)

    # Channel bookkeeping on the audit row: push when the user has any live
    # push subscription, else in-app only (plus an email fallback).
    try:
        channel = _alert_channel(user)
        event.channel = channel
        event.save(update_fields=['channel'])
        if channel != 'push' and DEVICE_ALERT_EMAIL_FALLBACK:
            _send_challenge_email(user, event)
    except Exception as e:
        logger.warning(f"[DEVICE-ALERT] channel fallback handling failed: {e}")

    return event


def _alert_channel(user):
    from notifications.models import PushSubscription
    return (
        DeviceAlertChannel.PUSH
        if PushSubscription.objects.filter(user=user, is_active=True)
        .exclude(fcm_token__exact='').exists()
        else DeviceAlertChannel.IN_APP
    )


def _schedule_notification_link(event_pk):
    """Deferred link between the challenge and its NotificationObject."""
    if getattr(settings, 'TESTING', False) or 'test' in sys.argv:
        _link_notification(event_pk)
        return
    try:
        if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
            from users.tasks import link_device_verification_notification
            link_device_verification_notification.apply(args=[event_pk])
        else:
            try:
                from users.tasks import link_device_verification_notification
                link_device_verification_notification.delay(event_pk)
            except Exception:
                _link_notification(event_pk)
    except Exception:
        try:
            _link_notification(event_pk)
        except Exception:
            pass


def _link_notification(event_pk):
    """Find the NotificationObject produced for this challenge and FK it."""
    try:
        event = DeviceVerificationEvent.objects.get(pk=event_pk)
    except DeviceVerificationEvent.DoesNotExist:
        return None
    if event.notification_id:
        return event.notification

    notification = NotificationObject.objects.filter(
        recipient_id=event.user_id,
        notification_type='SECURITY',
        context_id=event.session_key,
    ).order_by('-created_at').first()
    if not notification:
        notification = NotificationObject.objects.filter(
            recipient_id=event.user_id,
            notification_type='SECURITY',
            context_id=str(event.pk),
        ).order_by('-created_at').first()
    if notification:
        event.notification = notification
        event.save(update_fields=['notification'])
    return notification


# ---------------------------------------------------------------------------
# Response (approve / deny) — never usable by the challenged device itself
# ---------------------------------------------------------------------------

def _ratelimit_allow(user):
    key = f"devalert:respond:{user.pk}"
    try:
        count = cache.get(key)
        if count is None:
            cache.set(key, 1, 600)
            return True
        if count >= 20:
            return False
        cache.set(key, count + 1, 600)
        return True
    except Exception:
        return True


def respond(event, decision, escalation=None, acting_device_hash=None):
    """
    Act on a pending challenge.

    decision: 'approve' | 'deny'
    escalation (deny only): 'block' (default) | 'nuke'
    Returns (ok, error_code).
    """
    if decision not in ('approve', 'deny'):
        return False, 'invalid_decision'
    if event.status != DeviceVerificationStatus.PENDING:
        return False, 'already_handled'
    if event_is_expired(event):
        event.status = DeviceVerificationStatus.EXPIRED
        event.save(update_fields=['status'])
        return False, 'expired'
    acting_hash = acting_device_hash or ''
    if not acting_hash:
        return False, 'unknown_device'
    if acting_hash == event.device_hash:
        # Self-approval is forbidden: the new device itself must never be
        # able to click "it was me".
        return False, 'self_approval_forbidden'

    event.responded_at = timezone.now()
    event.responded_from_hash = acting_hash

    if decision == 'approve':
        promote_trusted_device(
            event.user, event.device_hash,
            device_name=event.device_name, source_event=event,
        )
        event.status = DeviceVerificationStatus.APPROVED
        event.save(update_fields=['responded_at', 'responded_from_hash', 'status'])
        _publish_resolution(event, EventTypes.SECURITY_DEVICE_TRUSTED, 'trusted')
        logger.info(f"[DEVICE-ALERT] Challenge {event.pk} APPROVED by another device")
        return True, None

    # Deny path
    nuke = (escalation == 'nuke')
    event.status = DeviceVerificationStatus.REJECTED
    event.save(update_fields=['responded_at', 'responded_from_hash', 'status'])
    block_device(event, secure_account=nuke)
    _publish_resolution(event, EventTypes.SECURITY_DEVICE_BLOCKED, 'blocked')
    return True, None


def event_is_expired(event):
    return (
        event.status == DeviceVerificationStatus.PENDING
        and event.expires_at <= timezone.now()
    )


def expire_if_pending(event):
    if event.status == DeviceVerificationStatus.PENDING and event.expires_at <= timezone.now():
        event.status = DeviceVerificationStatus.EXPIRED
        event.save(update_fields=['status'])
        return True
    return False


def promote_trusted_device(user, device_hash, device_name='', source_event=None):
    trusted, _created = TrustedDevice.objects.get_or_create(
        user=user,
        device_hash=device_hash,
        defaults={
            'device_name': device_name or '',
            'source_event': source_event,
            'last_confirmed_at': timezone.now(),
        },
    )
    if not trusted.is_primary and not TrustedDevice.objects.filter(
        user=user, is_primary=True
    ).exists():
        trusted.is_primary = True
    trusted.save()
    return trusted


# ---------------------------------------------------------------------------
# The kill chain
# ---------------------------------------------------------------------------

def block_device(event, secure_account=False):
    """
    "It wasn't me". Kill the challenged session, block the device hash, and
    with the nuke escalation: revoke every session except those bound to
    trusted devices, invalidate the password, and email the summary + reset
    link.
    """
    from users.services.session_service import revoke_session

    blocked, _ = BlockedDevice.objects.get_or_create(
        user=event.user,
        device_hash=event.device_hash,
        defaults={'reason': DeviceBlockReason.USER_REPORTED, 'source_event': event},
    )

    # 1. Kill the offending session immediately — belt and braces: also hit
    #    the Django Session row directly so revocation never depends on the
    #    UserSession mirror row existing.
    if event.session_key:
        revoke_session(event.session_key, user=event.user)
        _terminate_session_hard(event.user, event.session_key)

    invalidate_blocked_hash_cache(event.user_id)

    if not secure_account:
        _notify_blocked_summary(event, nuke=False)
        return blocked

    # 2. Nuke: revoke all remaining sessions NOT bound to trusted devices
    trusted_hashes = list(
        TrustedDevice.objects.filter(user=event.user).values_list('device_hash', flat=True)
    )
    trusted_keys = set(_session_keys_for_hashes(event.user, trusted_hashes))
    revoked = 0
    for session in event.user.user_sessions.all():
        if session.session_key in trusted_keys:
            continue
        revoke_session(session.session_key, user=event.user)
        _terminate_session_hard(event.user, session.session_key)
        revoked += 1

    _invalidate_password_and_email(event.user, event, revoked)
    _notify_blocked_summary(event, nuke=True)
    logger.warning(
        f"[DEVICE-ALERT] NUKE executed for user '{event.user.username}': "
        f"blocked device hash={event.device_hash[:10]}, sessions revoked={revoked}"
    )
    return blocked


def _terminate_session_hard(user, session_key):
    """Directly delete the Django Session row and push a realtime logout to
    every open tab of this user (instant, no waiting for the next request or
    the session-guard heartbeat)."""
    if not session_key:
        return
    try:
        from django.contrib.sessions.models import Session
        Session.objects.filter(session_key=session_key).delete()
    except Exception:
        pass
    dispatch_force_logout(user.pk, [session_key])


def dispatch_force_logout(user_id, session_keys):
    """
    Broadcast an instant-logout event over the user's existing notifications
    websocket channel. Any open tab holding one of these session keys
    immediately drops itself to the login screen (session_guard.js).
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user_id}",
                {
                    'type': 'force_logout',
                    'session_keys': list(session_keys or []),
                },
            )
    except Exception as e:
        logger.debug(f"[DEVICE-ALERT] force_logout broadcast unavailable: {e}")


def invalidate_blocked_hash_cache(user_id):
    try:
        from pwaninet.middleware.device_block_middleware import invalidate_blocked_device_cache
        invalidate_blocked_device_cache(user_id)
    except Exception:
        pass


def revoke_session_keys(user, keep_session_key=None):
    """Session keys about to be revoked (used to broadcast force_logout to
    currently-open tabs). Pure query — the caller performs revocation."""
    try:
        qs = user.user_sessions.exclude(session_key='').filter(session_key__isnull=False)
        if keep_session_key:
            qs = qs.exclude(session_key=keep_session_key)
        return list(qs.values_list('session_key', flat=True))
    except Exception:
        return []


def _session_keys_for_hashes(user, device_hashes):
    try:
        return list(DeviceAccount.objects.filter(
            user=user, device_id__in=device_hashes
        ).exclude(session_key__isnull=True).exclude(session_key='').values_list(
            'session_key', flat=True
        ))
    except Exception:
        return []


def _publish_resolution(event, event_type, action):
    try:
        EventPublisher.publish(
            event_type=event_type.value,
            source='USERS',
            action=action,
            target_type='DeviceVerificationEvent',
            target_id=str(event.pk),
            actor=event.user,
            context_type='UserSession',
            context_id=event.session_key,
            audience=str(event.user.pk),
            metadata={
                'target_user_id': event.user.pk,
                'challenge_id': str(event.pk),
                'device_label': _device_label(event),
            },
        )
    except Exception as e:
        logger.warning(f"[DEVICE-ALERT] resolution publish failed: {e}")


def _notify_blocked_summary(event, nuke=False):
    """In-app confirmation so the user sees what was done, in the inbox."""
    try:
        NotificationObject.objects.create(
            recipient=event.user,
            source_events=[],
            notification_type='SECURITY',
            category='SECURITY',
            priority='CRITICAL',
            title='Device blocked' if not nuke else 'Account secured',
            summary=(
                'We signed out the unrecognized device and blocked it.'
                if not nuke else
                'We blocked the device, signed you out everywhere except '
                'trusted devices, and emailed password reset instructions.'
            ),
            context_type='DeviceVerificationEvent',
            context_id=str(event.pk),
            status='DELIVERED',
            metadata={'target_url': '/users/settings/privacy/devices/'},
        )
        invalidate_and_broadcast(event.user_id)
    except Exception as e:
        logger.warning(f"[DEVICE-ALERT] blocked summary notification failed: {e}")


def invalidate_and_broadcast(user_id):
    try:
        from notifications.services.notification_service import (
            invalidate_unread_count_cache, broadcast_unread_count,
        )
        invalidate_unread_count_cache(user_id)
        broadcast_unread_count(user_id)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Emails (best-effort; never raise)
# ---------------------------------------------------------------------------

def _mail(subject, body, user):
    try:
        from django.core.mail import send_mail
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        return True
    except Exception as e:
        logger.warning(f"[DEVICE-ALERT] email '{subject}' failed: {e}")
        return False


def _send_challenge_email(user, event):
    if not user.email:
        return False
    return _mail(
        'New sign-in to your vasto account',
        (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"A device just signed in to your vasto account:\n"
            f"  Device: {_device_label(event)}\n"
            f"  Location: {event.location_label or 'Unknown location'} (approx. from IP)\n"
            f"  When: {_format_time(event.created_at)}\n\n"
            f"Open the security alert in the app to confirm or block it, or "
            f"manage devices under Settings → Privacy → Devices.\n"
        ),
        user,
    )


def _send_bootstrap_email(user, user_session=None):
    if not DEVICE_ALERT_EMAIL_FALLBACK or not user.email:
        return False
    label = user_session.device_name if user_session else ''
    return _mail(
        'A device was trusted on your vasto account',
        (
            f"Hi {user.get_full_name() or user.username},\n\n"
            f"To reduce alerts, the first device you signed in with is automatically "
            f"trusted: {label or 'This device'}.\n"
            f"You'll now get an alert whenever a NEW device signs in. Manage trusted "
            f"devices under Settings → Privacy → Devices.\n"
        ),
        user,
    )


def _invalidate_password_and_email(user, event, revoked_count):
    password_invalidated = False
    if user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=['password'])
        password_invalidated = user.email
    if user.email:
        _mail(
            'We secured your vasto account — action required',
            (
                f"We blocked an unrecognized device that signed in with your credentials:\n"
                f"  Device: {_device_label(event)}\n"
                f"  Location: {event.location_label or 'Unknown location'} (approx.)\n"
                f"  When: {_format_time(event.responded_at or event.created_at)}\n"
                f"  Signed out: {revoked_count} other session(s).\n\n"
                + (
                    "Your password has been disabled until you set a new one:\n"
                    f"  {_password_reset_url(user)}\n"
                    if password_invalidated else
                    "You sign in without a password, so no password was changed.\n"
                )
                + "\nIf this WAS you, contact support to restore access.\n"
                "Two-factor authentication stays on and continues protecting your account.\n"
            ),
            user,
        )


def _password_reset_url(user):
    """Standard reset link built from django.contrib.auth token machinery."""
    try:
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return f"/accounts/password_reset_confirm/{uidb64}/{token}/"
    except Exception:
        return "/users/password_reset/"
