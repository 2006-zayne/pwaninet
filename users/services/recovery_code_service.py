"""
users/services/recovery_code_service.py

Single-use recovery code service for PwaniNet.
Handles generation of high-entropy unambiguous codes, PBKDF2 hashed storage,
concurrency-safe atomic consumption, and regeneration.
"""

import logging
import secrets
from typing import List, Optional

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone

from users.models import RecoveryCode

logger = logging.getLogger('users.auth')

# Unambiguous alphabet: 32 characters (excluding 0, O, 1, I)
RECOVERY_CODE_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
RECOVERY_CODE_LENGTH = 12


def normalize_recovery_code(code: str) -> str:
    """
    Normalize user input: uppercase, strip whitespace, hyphens, and delimiters.
    """
    if not code:
        return ""
    return "".join(c.upper() for c in str(code) if c.isalnum())


def _format_code(raw: str) -> str:
    """
    Format a 12-character raw string into grouped format: XXXX-XXXX-XXXX.
    """
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def _generate_single_code() -> str:
    """
    Generate a single 12-character cryptographically secure recovery code.
    """
    raw = "".join(secrets.choice(RECOVERY_CODE_ALPHABET) for _ in range(RECOVERY_CODE_LENGTH))
    return _format_code(raw)


def generate_recovery_codes(user, count: Optional[int] = None) -> List[str]:
    """
    Generate a set of high-entropy recovery codes for user.
    Hashes each code using Django's make_password (PBKDF2) before persisting.
    Returns the list of plaintext formatted recovery codes (e.g. ['XXXX-XXXX-XXXX', ...]).

    Plaintext codes are returned ONLY at this point and are NEVER stored.
    """
    if not user or not user.is_authenticated:
        raise ValueError("Valid authenticated user required.")

    code_count = count or getattr(settings, 'RECOVERY_CODE_COUNT', 8)
    plaintext_codes: List[str] = []
    recovery_code_objects: List[RecoveryCode] = []

    # Ensure uniqueness within the batch
    seen_normalized = set()
    while len(plaintext_codes) < code_count:
        code = _generate_single_code()
        norm = normalize_recovery_code(code)
        if norm not in seen_normalized:
            seen_normalized.add(norm)
            plaintext_codes.append(code)
            hashed = make_password(norm)
            recovery_code_objects.append(
                RecoveryCode(
                    user=user,
                    code_hash=hashed,
                    is_consumed=False
                )
            )

    with transaction.atomic():
        RecoveryCode.objects.bulk_create(recovery_code_objects)

    logger.info(f"[SECURITY-RECOVERY-CODE] GENERATED: {len(plaintext_codes)} recovery codes generated for user '{user.username}'")
    return plaintext_codes


def consume_recovery_code(user, code: str) -> bool:
    """
    Verify and atomically consume a single-use recovery code.
    Uses select_for_update() inside transaction.atomic() to guarantee single consumption
    even under concurrent submissions.

    Returns:
    - True if code was valid and consumed.
    - False if invalid or already consumed.
    """
    if not user or not code:
        return False

    clean_code = normalize_recovery_code(code)
    if len(clean_code) != RECOVERY_CODE_LENGTH:
        logger.warning(f"[SECURITY-RECOVERY-CODE] FAILED: Invalid recovery code format for user '{user.username}'")
        return False

    with transaction.atomic():
        # Lock unconsumed codes for this user to serialize concurrent attempts
        active_codes = list(
            RecoveryCode.objects.select_for_update().filter(
                user=user,
                is_consumed=False
            )
        )

        matched_code: Optional[RecoveryCode] = None
        for rc in active_codes:
            if check_password(clean_code, rc.code_hash):
                matched_code = rc
                break

        if not matched_code:
            logger.warning(f"[SECURITY-RECOVERY-CODE] FAILED: Recovery code failed verification for user '{user.username}'")
            return False

        # Mark consumed
        matched_code.is_consumed = True
        matched_code.consumed_at = timezone.now()
        matched_code.save(update_fields=['is_consumed', 'consumed_at'])

        remaining = len(active_codes) - 1
        logger.info(
            f"[SECURITY-RECOVERY-CODE] CONSUMED: Recovery code id={matched_code.id} consumed for user '{user.username}' "
            f"(remaining active codes: {remaining})"
        )
        return True


def verify_recovery_code(user, code: str) -> bool:
    """
    Check if a recovery code is valid without consuming it.
    """
    if not user or not code:
        return False

    clean_code = normalize_recovery_code(code)
    if len(clean_code) != RECOVERY_CODE_LENGTH:
        return False

    active_codes = RecoveryCode.objects.filter(user=user, is_consumed=False)
    for rc in active_codes:
        if check_password(clean_code, rc.code_hash):
            return True
    return False


def regenerate_recovery_codes(user, count: Optional[int] = None) -> List[str]:
    """
    Invalidate all existing recovery codes for user and generate a fresh set.
    Returns the new list of plaintext formatted recovery codes.
    """
    if not user or not user.is_authenticated:
        raise ValueError("Valid authenticated user required.")

    with transaction.atomic():
        # Invalidate old codes
        RecoveryCode.objects.filter(user=user).delete()
        new_codes = generate_recovery_codes(user, count=count)

    logger.info(f"[SECURITY-RECOVERY-CODE] REGENERATED: Recovery codes regenerated for user '{user.username}'")
    return new_codes


def get_remaining_recovery_codes_count(user) -> int:
    """
    Get the count of active (unconsumed) recovery codes for user.
    """
    if not user or not user.is_authenticated:
        return 0
    return RecoveryCode.objects.filter(user=user, is_consumed=False).count()
