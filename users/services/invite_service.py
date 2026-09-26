import os
import base64
import hashlib
import struct
import logging
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from users.models import PlatformInvite, InviteType

logger = logging.getLogger(__name__)


def _get_cipher_key():
    """
    Derive a 256-bit AES encryption key deterministically from settings.SECRET_KEY.
    """
    secret = getattr(settings, 'SECRET_KEY', 'pwaninet_default_secure_secret_key_fallback')
    return hashlib.sha256(b"pwaninet:invite:aes256:v1:" + secret.encode('utf-8')).digest()


def encrypt_invite_token(user_id, invite_type):
    """
    Encrypt user ID and invite type into an authenticated, URL-safe AES-256-GCM ciphertext.
    There is zero readable plaintext (no IDs, no usernames, no type names).
    """
    type_code = 1 if invite_type == InviteType.APP_DOWNLOAD else 2
    salt = os.urandom(4)
    payload = struct.pack('>IB4s', int(user_id), type_code, salt)
    nonce = os.urandom(12)

    aesgcm = AESGCM(_get_cipher_key())
    ciphertext = aesgcm.encrypt(nonce, payload, None)

    # 12-byte nonce + 9-byte payload + 16-byte GCM tag = 37 bytes binary -> 50 chars base64url
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii').rstrip('=')
    return token


def decrypt_invite_token(token):
    """
    Decrypt and verify an AES-256-GCM encrypted invite token.
    Returns (user_id, invite_type) tuple or None if invalid / tampered with.
    """
    if not token or not isinstance(token, str):
        return None

    try:
        padding = '=' * ((4 - len(token) % 4) % 4)
        raw = base64.urlsafe_b64decode((token + padding).encode('ascii'))
        if len(raw) < 29:
            return None

        nonce = raw[:12]
        ciphertext = raw[12:]

        aesgcm = AESGCM(_get_cipher_key())
        payload = aesgcm.decrypt(nonce, ciphertext, None)

        user_id, type_code, salt = struct.unpack('>IB4s', payload)
        resolved_type = InviteType.APP_DOWNLOAD if type_code == 1 else InviteType.PLATFORM_INVITE
        return user_id, resolved_type
    except Exception as e:
        logger.debug(f"Failed to decrypt invite token '{token}': {e}")
        return None


def get_or_create_invite(user, invite_type):
    """
    Ensure an invite record exists for a user and invite type with an encrypted AES-256-GCM token.
    """
    invite = PlatformInvite.objects.filter(inviter=user, invite_type=invite_type).first()
    if not invite:
        token = encrypt_invite_token(user.id, invite_type)
        invite = PlatformInvite.objects.create(
            inviter=user,
            invite_type=invite_type,
            token=token
        )
    elif not decrypt_invite_token(invite.token):
        # Refresh legacy/unencrypted token with AES-256-GCM encrypted token
        invite.token = encrypt_invite_token(user.id, invite_type)
        invite.save(update_fields=['token'])

    return invite


def get_invite_data(user, request=None):
    """
    Return dictionary with encrypted tokens, URLs, copywriting, and statistics for both invite types.
    """
    app_invite = get_or_create_invite(user, InviteType.APP_DOWNLOAD)
    platform_invite = get_or_create_invite(user, InviteType.PLATFORM_INVITE)

    if request:
        app_url = request.build_absolute_uri(reverse('encrypted_invite_landing', kwargs={'token': app_invite.token}))
        platform_url = request.build_absolute_uri(reverse('encrypted_invite_landing', kwargs={'token': platform_invite.token}))
    else:
        app_url = f"/i/{app_invite.token}/"
        platform_url = f"/i/{platform_invite.token}/"

    app_copy = str(_("📱 Download the official PwaniNet Android app for campus updates, course groups, and offline access:"))
    platform_copy = str(_("🎓 Join me on PwaniNet! Connect with classmates, access course groups, and collaborate:"))

    return {
        'app_download': {
            'token': app_invite.token,
            'url': app_url,
            'text': f"{app_copy} {app_url}",
            'copy_text': app_copy,
            'clicks': app_invite.clicks_count,
            'conversions': app_invite.conversions_count,
        },
        'platform_invite': {
            'token': platform_invite.token,
            'url': platform_url,
            'text': f"{platform_copy} {platform_url}",
            'copy_text': platform_copy,
            'clicks': platform_invite.clicks_count,
            'conversions': platform_invite.conversions_count,
        }
    }


def track_invite_click(token):
    """
    Record an inbound click telemetry event for an invite link.
    Supports both database token lookup and on-the-fly AES-256-GCM decryption.
    """
    if not token:
        return None

    invite = PlatformInvite.objects.select_related('inviter').filter(token=token).first()
    if not invite:
        decrypted = decrypt_invite_token(token)
        if decrypted:
            user_id, invite_type = decrypted
            from users.models import User
            try:
                inviter = User.objects.get(id=user_id)
                invite, _ = PlatformInvite.objects.get_or_create(
                    inviter=inviter,
                    invite_type=invite_type,
                    defaults={'token': token}
                )
            except User.DoesNotExist:
                return None

    if invite:
        invite.clicks_count += 1
        invite.last_clicked_at = timezone.now()
        invite.save(update_fields=['clicks_count', 'last_clicked_at'])

    return invite


def process_invite_conversion(token, new_user):
    """
    Attribute a successful signup to an invite link and connect inviter with invitee.
    """
    if not token or not new_user:
        return None

    invite = PlatformInvite.objects.select_related('inviter').filter(token=token).first()
    if not invite:
        decrypted = decrypt_invite_token(token)
        if decrypted:
            user_id, invite_type = decrypted
            from users.models import User
            try:
                inviter = User.objects.get(id=user_id)
                invite, _ = PlatformInvite.objects.get_or_create(
                    inviter=inviter,
                    invite_type=invite_type,
                    defaults={'token': token}
                )
            except User.DoesNotExist:
                return None

    if not invite:
        return None

    invite.conversions_count += 1
    invite.save(update_fields=['conversions_count'])

    inviter = invite.inviter
    if inviter and inviter != new_user:
        try:
            from users.models import Follow
            Follow.objects.get_or_create(follower=new_user, following=inviter)
        except Exception as e:
            logger.warning(f"Could not establish follow relationship on invite conversion: {e}")

        try:
            from notifications.events import publish_event, EventTypes, EventSources, EventActions
            publish_event(
                event_type=EventTypes.FOLLOW.value,
                source=EventSources.USERS.value,
                action=EventActions.FOLLOWED.value,
                actor=new_user,
                target_type='User',
                target_id=str(inviter.id),
                context_type='USER',
                context_id=str(inviter.id),
                audience=str(inviter.id),
                metadata={
                    'actor_username': new_user.username,
                    'recipient_username': inviter.username,
                    'message': f"@{new_user.username} joined PwaniNet using your invite link!",
                }
            )
        except Exception as e:
            logger.warning(f"Could not publish notification for invite conversion: {e}")

    return invite
