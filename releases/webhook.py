"""
GitHub Webhook Handler for Automatic Release Synchronization.

Listens for GitHub `release` events and synchronizes release metadata,
release notes, and version states directly to the database.
"""
import hmac
import hashlib
import json
import logging
import os
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Release, ReleaseItem
from .services import ReleaseService

logger = logging.getLogger(__name__)


def _verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC SHA-256 signature from GitHub."""
    if not signature_header or not signature_header.startswith('sha256='):
        return False
    expected_sig = signature_header.split('sha256=')[-1]
    mac = hmac.new(secret.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), expected_sig)


@csrf_exempt
@require_POST
def github_release_webhook(request):
    """
    Webhook endpoint for GitHub Releases: POST /api/releases/webhook/github/
    Automatically processes published GitHub releases.
    """
    secret = getattr(settings, 'GITHUB_WEBHOOK_SECRET', None) or os.environ.get('GITHUB_WEBHOOK_SECRET')
    
    # Verify HMAC signature if secret is configured
    if secret:
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not _verify_signature(request.body, signature, secret):
            logger.warning("[GitHub Webhook] Invalid signature received")
            return HttpResponseForbidden("Invalid webhook signature")

    event = request.headers.get('X-GitHub-Event', '')
    if event == 'ping':
        return JsonResponse({"status": "pong", "message": "PwaniNet GitHub webhook active"})

    if event != 'release':
        return JsonResponse({"status": "ignored", "message": f"Event '{event}' ignored"})

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        logger.error("[GitHub Webhook] Failed to decode JSON payload: %s", e)
        return HttpResponseBadRequest("Invalid JSON")

    action = payload.get('action')
    if action not in ['published', 'released', 'created', 'edited']:
        return JsonResponse({"status": "ignored", "message": f"Action '{action}' ignored"})

    gh_release = payload.get('release', {})
    tag_name = gh_release.get('tag_name', '').lstrip('v').strip()
    if not tag_name:
        return HttpResponseBadRequest("Missing tag_name in release payload")

    title = gh_release.get('name') or f"Release {tag_name}"
    body = gh_release.get('body') or ""
    is_prerelease = gh_release.get('prerelease', False)

    # Resolve build number safely
    highest_rel = Release.objects.order_by('-build_number').first()
    next_build = (highest_rel.build_number + 1) if highest_rel else 1

    # Check if release record already exists
    release = Release.objects.filter(version=tag_name).first()
    created = False
    if not release:
        release = Release.objects.create(
            version=tag_name,
            build_number=next_build,
            release_title=title,
            release_summary=body[:500] if body else f"PwaniNet Release {tag_name}",
            release_type='PATCH' if tag_name.count('.') == 2 and tag_name.split('.')[-1] != '0' else 'MINOR',
            status='PUBLISHED',
            published=True,
            release_channel='BETA' if is_prerelease else 'STABLE',
            is_current_release=not is_prerelease,
        )
        created = True
        logger.info("[GitHub Webhook] Created new release record: %s (build %s)", tag_name, release.build_number)
    else:
        release.release_title = title
        if body:
            release.release_summary = body[:500]
        release.status = 'PUBLISHED'
        release.published = True
        if not is_prerelease:
            release.is_current_release = True
        release.save()
        logger.info("[GitHub Webhook] Updated existing release record: %s", tag_name)

    if not is_prerelease:
        Release.objects.filter(is_current_release=True).exclude(id=release.id).update(is_current_release=False)

    # Parse markdown release notes lines into ReleaseItem records
    if body and created:
        order = 1
        for line in body.splitlines():
            line = line.strip()
            if not line or not (line.startswith('-') or line.startswith('*')):
                continue
            item_text = line.lstrip('-* ').strip()
            if not item_text:
                continue
            category = 'FEATURE'
            lower = item_text.lower()
            if any(k in lower for k in ['fix', 'bug', 'patch', 'resolve', 'crash']):
                category = 'BUGFIX'
            elif any(k in lower for k in ['perf', 'optimize', 'speed', 'cache']):
                category = 'PERFORMANCE'
            elif any(k in lower for k in ['sec', 'auth', 'token']):
                category = 'SECURITY'
            
            ReleaseItem.objects.create(
                release=release,
                category=category,
                title=item_text[:200],
                description=item_text,
                display_order=order
            )
            order += 1

    # Invalidate all in-memory LRU and Redis caches
    ReleaseService.invalidate_all_version_caches()

    return JsonResponse({
        "status": "success",
        "action": "created" if created else "updated",
        "version": release.version,
        "build_number": release.build_number,
        "is_current": release.is_current_release,
    })
