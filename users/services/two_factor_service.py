"""
users/services/two_factor_service.py

Two-factor authentication (TOTP RFC 6238) service for PwaniNet.
Handles secret generation, authenticated encryption at rest, verification
with clock drift tolerance, concurrency-safe replay protection, and provisioning URIs.
"""

import base64
import datetime
import hashlib
import logging
import re
from typing import Optional, Tuple

import pyotp
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from users.models import UserTwoFactor

logger = logging.getLogger('users.auth')


class TwoFactorError(Exception):
    """Base exception for two-factor authentication operations."""
    pass


class TwoFactorConfigurationError(TwoFactorError):
    """Raised when 2FA cryptographic configuration is invalid."""
    pass


def _get_fernet() -> MultiFernet:
    """
    Get MultiFernet instance for authenticated encryption/decryption of TOTP secrets.
    Supports key rotation via comma-separated keys in MFA_ENCRYPTION_KEY.
    Falls back to a deterministic key derived from SECRET_KEY in dev/test.
    """
    raw_keys = getattr(settings, 'MFA_ENCRYPTION_KEY', None)
    try:
        if raw_keys:
            key_list = [k.strip().encode('utf-8') for k in raw_keys.split(',') if k.strip()]
        else:
            # Deterministic SHA256-derived key from SECRET_KEY
            derived = hashlib.sha256(b"pwaninet-mfa-encryption:" + settings.SECRET_KEY.encode('utf-8')).digest()
            key_list = [base64.urlsafe_b64encode(derived)]

        fernet_instances = [Fernet(k) for k in key_list]
        return MultiFernet(fernet_instances)
    except Exception as e:
        logger.error("[SECURITY-2FA] Failed to initialize MFA encryption key")
        raise TwoFactorConfigurationError("MFA encryption key configuration error.") from None


def encrypt_secret(plaintext_secret: str) -> str:
    """
    Encrypt a plaintext base32 TOTP secret using authenticated encryption.
    Returns URL-safe base64 ciphertext string.
    """
    if not plaintext_secret:
        raise ValueError("Secret cannot be empty.")
    fernet = _get_fernet()
    token_bytes = fernet.encrypt(plaintext_secret.encode('utf-8'))
    return token_bytes.decode('utf-8')


def decrypt_secret(ciphertext: str) -> str:
    """
    Decrypt an encrypted TOTP secret.
    Raises TwoFactorError on corrupted or unauthentic ciphertext.
    """
    if not ciphertext:
        raise ValueError("Ciphertext cannot be empty.")
    fernet = _get_fernet()
    try:
        decrypted_bytes = fernet.decrypt(ciphertext.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except (InvalidToken, Exception):
        logger.error("[SECURITY-2FA] Failed to decrypt TOTP secret: invalid or corrupted ciphertext")
        raise TwoFactorError("Unable to decrypt TOTP credential.")


def generate_secret() -> str:
    """
    Generate a cryptographically secure RFC 3548 Base32 TOTP secret (160 bits).
    """
    return pyotp.random_base32()


def get_two_factor(user) -> Optional[UserTwoFactor]:
    """
    Retrieve UserTwoFactor record for user if one exists.
    """
    if not user or not user.is_authenticated:
        return None
    return UserTwoFactor.objects.filter(user=user).first()


def is_two_factor_enabled(user) -> bool:
    """
    Check whether 2FA is active and enabled for user.
    """
    two_factor = get_two_factor(user)
    return bool(two_factor and two_factor.is_enabled)


def get_two_factor_status(user) -> str:
    """
    Return current 2FA status:
    - 'not_configured': No UserTwoFactor record exists.
    - 'pending': UserTwoFactor record exists, but setup not completed (is_enabled=False).
    - 'enabled': 2FA is fully verified and active (is_enabled=True).
    """
    two_factor = get_two_factor(user)
    if not two_factor:
        return 'not_configured'
    return 'enabled' if two_factor.is_enabled else 'pending'


def initialize_two_factor(user) -> Tuple[UserTwoFactor, str]:
    """
    Initialize or reset unverified 2FA setup for user.
    Generates a new secret, encrypts it, and saves UserTwoFactor with is_enabled=False.
    Returns (UserTwoFactor instance, plaintext_secret).
    Plaintext secret must be passed to the user for enrollment and NEVER stored.
    """
    secret = generate_secret()
    encrypted = encrypt_secret(secret)

    two_factor, created = UserTwoFactor.objects.update_or_create(
        user=user,
        defaults={
            'encrypted_secret': encrypted,
            'is_enabled': False,
            'enrolled_at': None,
            'last_used_timestep': None,
        }
    )

    logger.info(f"[SECURITY-2FA] INITIALIZED: 2FA setup initialized for user '{user.username}'")
    return two_factor, secret


def get_totp_object(two_factor: UserTwoFactor) -> pyotp.TOTP:
    """
    Build a pyotp.TOTP instance from an existing UserTwoFactor record.
    """
    plaintext_secret = decrypt_secret(two_factor.encrypted_secret)
    digits = getattr(settings, 'TOTP_DIGITS', 6)
    interval = getattr(settings, 'TOTP_INTERVAL', 30)
    return pyotp.TOTP(plaintext_secret, digits=digits, interval=interval)


def get_provisioning_uri(user, issuer: Optional[str] = None) -> str:
    """
    Generate the standard otpauth://totp/ URI for authenticator app QR codes.
    """
    two_factor = get_two_factor(user)
    if not two_factor:
        raise TwoFactorError("2FA is not initialized for this user.")

    totp = get_totp_object(two_factor)
    issuer_name = issuer or getattr(settings, 'TOTP_ISSUER', 'PwaniNet')
    return totp.provisioning_uri(name=user.username, issuer_name=issuer_name)


def generate_qr_svg(provisioning_uri: str) -> str:
    """
    Generate an SVG representation of the QR code for the given provisioning URI.
    Uses qrcode library with SvgPathImage. Returns sanitized SVG string for inline HTML embedding.
    """
    import io
    import qrcode
    import qrcode.image.svg

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    buf = io.BytesIO()
    img.save(buf)
    svg_raw = buf.getvalue().decode('utf-8')
    if svg_raw.startswith('<?xml'):
        svg_raw = svg_raw.split('?>', 1)[-1].strip()
    return svg_raw


def verify_totp(user, code: str, valid_window: Optional[int] = None, allow_unverified: bool = False) -> bool:
    """
    Verify a submitted TOTP code for user.

    Enforces:
    - Input sanitation (must match digits e.g. 6 digits)
    - Controlled clock drift (default: settings.TOTP_ALLOWED_DRIFT, usually 1)
    - Replay protection with atomic concurrency safety (select_for_update)

    Parameters:
    - user: The User instance.
    - code: The string OTP code provided by the user.
    - valid_window: Clock drift tolerance in steps (default settings.TOTP_ALLOWED_DRIFT).
    - allow_unverified: If True, allows verification when is_enabled=False (e.g. during enrollment confirmation).

    Returns:
    - True if valid and consumed; False otherwise.
    """
    if not user or not code:
        return False

    # 1. Sanitize code
    clean_code = str(code).strip().replace(' ', '')
    digits = getattr(settings, 'TOTP_DIGITS', 6)
    if not re.match(r'^\d{' + str(digits) + r'}$', clean_code):
        logger.warning(f"[SECURITY-2FA] VERIFY_FAILED: Malformed code format for user '{user.username}'")
        return False

    two_factor = get_two_factor(user)
    if not two_factor:
        logger.warning(f"[SECURITY-2FA] VERIFY_FAILED: 2FA not configured for user '{user.username}'")
        return False

    if not two_factor.is_enabled and not allow_unverified:
        logger.warning(f"[SECURITY-2FA] VERIFY_FAILED: 2FA not enabled for user '{user.username}'")
        return False

    drift = valid_window if valid_window is not None else getattr(settings, 'TOTP_ALLOWED_DRIFT', 1)

    try:
        totp = get_totp_object(two_factor)
    except TwoFactorError:
        return False

    now = datetime.datetime.now(datetime.timezone.utc)
    base_timestep = totp.timecode(now)

    # Check which timestep matched (within [-drift, +drift])
    matched_timestep = None
    for offset in range(-drift, drift + 1):
        expected_code = totp.at(now, offset)
        if pyotp.utils.strings_equal(clean_code, str(expected_code)):
            matched_timestep = base_timestep + offset
            break

    if matched_timestep is None:
        logger.warning(f"[SECURITY-2FA] VERIFY_FAILED: Invalid code for user '{user.username}'")
        return False

    # Concurrency-safe atomic replay protection
    with transaction.atomic():
        locked_tf = UserTwoFactor.objects.select_for_update().get(id=two_factor.id)
        if locked_tf.last_used_timestep is not None and matched_timestep <= locked_tf.last_used_timestep:
            logger.warning(
                f"[SECURITY-2FA] REPLAY: Rejected replayed/old TOTP timestep {matched_timestep} "
                f"(last_used={locked_tf.last_used_timestep}) for user '{user.username}'"
            )
            return False

        locked_tf.last_used_timestep = matched_timestep
        locked_tf.save(update_fields=['last_used_timestep', 'updated_at'])

    logger.info(f"[SECURITY-2FA] SUCCESS: Valid TOTP verified for user '{user.username}' (timestep={matched_timestep})")
    return True


def confirm_and_enable_two_factor(user, code: str) -> bool:
    """
    Verify setup code and activate 2FA for user.
    """
    two_factor = get_two_factor(user)
    if not two_factor:
        return False

    # Verify code allowing unverified status
    if not verify_totp(user, code, allow_unverified=True):
        return False

    with transaction.atomic():
        locked_tf = UserTwoFactor.objects.select_for_update().get(id=two_factor.id)
        locked_tf.is_enabled = True
        locked_tf.enrolled_at = timezone.now()
        locked_tf.save(update_fields=['is_enabled', 'enrolled_at', 'updated_at'])

    logger.info(f"[SECURITY-2FA] ENABLED: 2FA successfully enabled for user '{user.username}'")
    return True


def disable_two_factor(user) -> bool:
    """
    Disable 2FA for user and purge recovery codes.
    """
    two_factor = get_two_factor(user)
    if not two_factor:
        return False

    with transaction.atomic():
        two_factor.delete()
        # Invalidate recovery codes as well
        from users.models import RecoveryCode
        RecoveryCode.objects.filter(user=user).delete()

    logger.info(f"[SECURITY-2FA] DISABLED: 2FA disabled and recovery codes purged for user '{user.username}'")
    return True
