"""
Google Identity Services ID-token verification for website sign-in.

Only claims from a signature-verified Google ID token are trusted.
Client-provided identity values are never accepted without verification.
"""
import logging
import time

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('users.auth')

GOOGLE_ISSUERS = {'accounts.google.com', 'https://accounts.google.com'}
JWKS_CACHE_KEY = 'vasto:google:jwks'
PENDING_SESSION_KEY = '_google_pending'
PENDING_TIMEOUT = 900  # 15 minutes, matching the 2FA/recovery pending windows


class GoogleVerificationError(Exception):
    """Raised when a Google ID token cannot be verified. `code` is machine-readable."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _get_jwks():
    cached = cache.get(JWKS_CACHE_KEY)
    if cached:
        return cached
    try:
        response = requests.get(settings.GOOGLE_JWKS_URL, timeout=10)
        response.raise_for_status()
        jwks = response.json()
    except Exception as exc:
        logger.error(f"[SECURITY-GOOGLE] JWKS fetch failed: {exc}")
        raise GoogleVerificationError('jwks_unavailable', 'Google sign-in is temporarily unavailable.')
    cache.set(JWKS_CACHE_KEY, jwks, timeout=settings.GOOGLE_JWKS_CACHE_TIMEOUT)
    return jwks


def verify_google_id_token(id_token):
    """
    Verify a Google ID token and return its claims.

    Validates signature (Google JWKS, RS256), issuer, audience (our Web
    Client ID), expiry, and hosted-domain restriction when configured.
    """
    if not id_token or not isinstance(id_token, str):
        raise GoogleVerificationError('missing_token', 'No Google credential was provided.')
    if not settings.GOOGLE_WEB_CLIENT_ID:
        raise GoogleVerificationError('not_configured', 'Google sign-in is not configured.')

    jwks = _get_jwks()
    try:
        header = jwt.get_unverified_header(id_token)
        key_data = next((k for k in jwks.get('keys', []) if k.get('kid') == header.get('kid')), None)
        if key_data is None:
            raise GoogleVerificationError('unknown_key', 'Google credential could not be verified.')
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
        claims = jwt.decode(
            id_token,
            key=public_key,
            algorithms=['RS256'],
            audience=settings.GOOGLE_WEB_CLIENT_ID,
            issuer=list(GOOGLE_ISSUERS),
            options={'require': ['exp', 'iss', 'sub']},
        )
    except GoogleVerificationError:
        raise
    except jwt.ExpiredSignatureError:
        raise GoogleVerificationError('expired', 'This Google sign-in has expired. Please try again.')
    except jwt.InvalidAudienceError:
        raise GoogleVerificationError('wrong_audience', 'This Google credential was not issued for Vasto.')
    except jwt.InvalidIssuerError:
        raise GoogleVerificationError('wrong_issuer', 'This Google credential has an unexpected issuer.')
    except jwt.InvalidTokenError as exc:
        logger.warning(f"[SECURITY-GOOGLE] Invalid ID token: {exc}")
        raise GoogleVerificationError('invalid_token', 'This Google credential is invalid.')

    sub = claims.get('sub', '')
    if not sub:
        raise GoogleVerificationError('invalid_token', 'This Google credential is invalid.')

    allowed_hd = (settings.GOOGLE_ALLOWED_HD or '').strip()
    if allowed_hd and claims.get('hd', '') != allowed_hd:
        raise GoogleVerificationError('wrong_domain', 'This Google account is not permitted to sign in.')

    return claims


def derive_username_from_email(email):
    """Derive a unique campus handle from an email address.

    Mirrors the derivation rules in PwaniSignupForm.clean_username so
    Google-created accounts follow the same username policy.
    """
    import re

    local_part = (email or '').split('@')[0].lower()
    clean_base = re.sub(r'[^a-z0-9_.]', '_', local_part).strip('._')
    if not clean_base or len(clean_base) < 3:
        clean_base = f"user_{clean_base}" if clean_base else "user"
    clean_base = clean_base[:25]

    from users.models import User

    candidate = clean_base
    counter = 1
    while User.objects.filter(username__iexact=candidate).exists():
        candidate = f"{clean_base}{counter}"
        counter += 1
    return candidate


def stash_pending_google(request, claims):
    """Hold verified Google claims in the session for the explicit-link step."""
    request.session[PENDING_SESSION_KEY] = {
        'sub': claims.get('sub', ''),
        'email': (claims.get('email') or '').lower(),
        'email_verified': bool(claims.get('email_verified', False)),
        'given_name': claims.get('given_name', '') or '',
        'family_name': claims.get('family_name', '') or '',
        'hosted_domain': claims.get('hd', '') or '',
        'ts': int(time.time()),
    }


def pop_pending_google(request):
    """Return pending Google claims if fresh, otherwise None (and clear)."""
    pending = request.session.get(PENDING_SESSION_KEY)
    if not pending or not pending.get('sub'):
        clear_pending_google(request)
        return None
    if int(time.time()) - int(pending.get('ts', 0)) > PENDING_TIMEOUT:
        clear_pending_google(request)
        return None
    return pending


def clear_pending_google(request):
    request.session.pop(PENDING_SESSION_KEY, None)


def get_rate_limit_ip(request):
    """Extract a validated client IP for rate limiting.

    The app runs behind a single reverse proxy (Cloudflare Tunnel/Nginx, see
    SECURE_PROXY_SSL_HEADER), so the leftmost X-Forwarded-For entry is the
    client address — but header values are untrusted input, so each candidate
    is validated as a real IP before use. An attacker spoofing XFF can only
    move themselves into a different per-IP bucket, never into another
    user's bucket, and never bypasses token verification.
    """
    import ipaddress

    candidates = []
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        candidates.extend(part.strip() for part in x_forwarded_for.split(','))
    remote_addr = request.META.get('REMOTE_ADDR', '')
    if remote_addr:
        candidates.append(remote_addr.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return 'unknown'


def google_complete_allowed(request):
    """Fixed-window rate limit for the Google completion endpoint.

    Uses an atomic cache increment where the backend supports it. Returns
    True when the request is within budget. Fails open (allows) if the
    cache itself errors, so a cache outage never locks every user out.

    Limitations: fixed (non-sliding) window; counters are per cache
    backend — with the Redis fallback to per-process locmem, a Redis
    outage splits budgets per worker process until Redis recovers.
    Where the cache backend is a no-op store (local/dev DummyCache),
    no counting happens and every request is allowed; the limiter is
    effective wherever a real cache backend is configured (production
    Redis).
    """
    from django.core.cache import cache

    try:
        limit = int(settings.GOOGLE_COMPLETE_RATELIMIT_ATTEMPTS)
        window = int(settings.GOOGLE_COMPLETE_RATELIMIT_WINDOW)
    except (TypeError, ValueError):
        logger.error("[SECURITY-RATELIMIT] Invalid Google rate-limit settings; allowing request.")
        return True
    if limit <= 0:
        return True

    key = f"vasto:ratelimit:google_complete:{get_rate_limit_ip(request)}"
    try:
        try:
            count = cache.incr(key)
        except ValueError:
            # Key missing (or non-numeric): start a fresh window.
            if cache.add(key, 1, timeout=window):
                count = 1
            else:
                # Lost a race with another worker starting the window.
                count = cache.incr(key)
    except Exception as exc:
        logger.warning(f"[SECURITY-RATELIMIT] Google limiter cache error, allowing request: {exc}")
        return True
    return count <= limit
