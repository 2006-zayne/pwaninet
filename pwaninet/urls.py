"""
URL configuration for pwaninet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function:  from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.views.generic import TemplateView, RedirectView
from django.http import HttpResponse, HttpResponseRedirect, FileResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from notifications import views as notification_views
from users.views import toggle_profile_photo_like, PwaniLoginView

# PWA Manifest - served as static file to bypass auth middleware
@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def serve_manifest(request):
    import os
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.webmanifest')
    try:
        with open(manifest_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/manifest+json')
    except FileNotFoundError:
        return HttpResponse('Manifest not found', status=404)

# Service Worker - served dynamically with active version to bust cache on release
@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def serve_service_worker(request):
    import os
    import re
    from releases.services import ReleaseService
    from pwaninet import version as app_version_module

    sw_path = os.path.join(settings.BASE_DIR, 'static', 'service-worker.js')
    try:
        with open(sw_path, 'r') as f:
            content = f.read()

        # Resolve active version & build number dynamically
        try:
            rel = ReleaseService.get_latest_release()
            current_ver = rel.version if rel else getattr(app_version_module, 'resolve_latest_version', app_version_module.resolve_version)()
            current_build = rel.build_number if rel else app_version_module.resolve_build_number()
        except Exception:
            current_ver = app_version_module.resolve_version()
            current_build = app_version_module.resolve_build_number()

        current_ver = str(current_ver).lstrip('v').strip()
        current_build = str(current_build).strip()

        # Dynamically inject the active version and build number into service worker
        content = re.sub(r"let CACHE_VERSION\s*=\s*['\"][^'\"]*['\"];", f"let CACHE_VERSION = '{current_ver}';", content)
        content = re.sub(r"let CACHE_BUILD\s*=\s*['\"][^'\"]*['\"];", f"let CACHE_BUILD = '{current_build}';", content)

        response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    except FileNotFoundError:
        return HttpResponse('Service worker not found', status=404)

# Messaging redirect - FROZEN FOR MVP
def redirect_messaging(request):
    """Redirect any messaging URLs to home page since messaging is frozen for MVP"""
    return HttpResponseRedirect('/')

GITHUB_RELEASE_APK_URL = 'https://github.com/2006-zayne/pwaninet/releases/latest/download/pwaninet.apk'


from django.core.signing import TimestampSigner, BadSignature
from django.http import FileResponse, HttpResponseForbidden, HttpResponseRedirect
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "HEAD"])
def download_android_apk(request):
    """
    Version-agnostic mobile download controller.
    Abstracts storage paths, records request telemetry, resolves the latest production release,
    and gates access via signed tokens if marked private or beta.
    """
    # Telemetry logging
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    logger.info(f"Mobile app download requested by IP: {ip_address}, User-Agent: {user_agent}")
    
    is_beta_or_private = getattr(settings, 'APK_IS_BETA', False)
    
    if is_beta_or_private:
        token = request.GET.get('token')
        if not token:
            return HttpResponseForbidden("This is a private/beta release. Download token required.")
        signer = TimestampSigner()
        try:
            # Token expires in 1 hour
            data = signer.unsign_object(token, max_age=3600)
        except BadSignature:
            return HttpResponseForbidden("Invalid or expired download token.")
    
    github_url = getattr(settings, 'APK_DOWNLOAD_URL', 'https://github.com/2006-zayne/pwaninet/releases/latest/download/pwaninet.apk')
    
    if getattr(settings, 'REDIRECT_APK_TO_GITHUB', True) and not getattr(settings, 'DEBUG', False):
        return HttpResponseRedirect(github_url)
    
    import os
    local_candidates = [
        os.path.join(settings.BASE_DIR, 'media', 'downloads', 'pwaninet.apk'),
        os.path.join(settings.BASE_DIR, 'android', 'app', 'build', 'outputs', 'apk', 'release', 'app-release.apk'),
    ]
    for apk_path in local_candidates:
        if os.path.exists(apk_path) and os.path.getsize(apk_path) > 0:
            return FileResponse(
                open(apk_path, 'rb'),
                as_attachment=True,
                filename='pwaninet.apk',
                content_type='application/vnd.android.package-archive'
            )
            
    return HttpResponseRedirect(github_url)


import functools

@functools.lru_cache(maxsize=1)
def _generate_apk_qr_svg_bytes():
    """
    Generate a pixel-perfect, scannable QR code SVG for https://pwaninet.app/apk/
    Results are cached in-process so subsequent requests cost nothing.
    """
    import qrcode
    import qrcode.image.svg
    import io as _io
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,  # 4-module quiet zone required by QR spec
    )
    qr.add_data('https://pwaninet.app/apk/')
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    buf = _io.BytesIO()
    img.save(buf)
    return buf.getvalue()


@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def qr_code_svg(request):
    """
    Serve a clean, scannable SVG QR code pointing to https://pwaninet.app/apk/.
    Cached in-process; sets a long Cache-Control header for edge caching.
    """
    try:
        svg_bytes = _generate_apk_qr_svg_bytes()
    except Exception:
        return HttpResponse('QR generation failed', status=500)

    response = HttpResponse(svg_bytes, content_type='image/svg+xml')
    response['Cache-Control'] = 'public, max-age=86400'  # 24h browser/CDN cache
    response['X-Content-Type-Options'] = 'nosniff'
    return response

urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom login with diagnostics and structured logging
    path('accounts/login/', PwaniLoginView.as_view(), name='login'),
    path('login/', PwaniLoginView.as_view(), name='login_direct'),
    # This maps 'accounts/logout/' and remaining auth views automatically
    path('accounts/', include('django.contrib.auth.urls')),
    # PWA Offline Page (handles both /offline/ and /offline.html)
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('offline.html', TemplateView.as_view(template_name='offline.html'), name='offline_html'),
    path('test/offline/', TemplateView.as_view(template_name='offline.html'), name='offline_test'),
    # PWA Manifest and Service Worker - served without auth middleware
    path('manifest.webmanifest', serve_manifest, name='manifest'),
    path('service-worker.js', serve_service_worker, name='service_worker'),
    # Direct Android APK download routes (permanent endpoints for social sharing & settings)
    path('download/app/latest/', download_android_apk, name='download_android_apk'),
    path('apk/', download_android_apk, name='download_apk_short'),
    path('apk/qr/', qr_code_svg, name='qr_code_svg'),
    # PWA Test Pages
    path('test/native-pwa/', TemplateView.as_view(template_name='native_pwa_test.html'), name='native_pwa_test'),
    path('clear-cache/', TemplateView.as_view(template_name='clear_cache.html'), name='clear_cache'),
    path('api/health/', TemplateView.as_view(template_name='health_check.html'), name='health_check'),
    # Messaging Test Pages - FROZEN FOR MVP
    # path('test/messaging/', TemplateView.as_view(template_name='test_messaging_architecture.html'), name='test_messaging_architecture'),
    # path('test/messaging-debug/', TemplateView.as_view(template_name='debug_messaging.html'), name='debug_messaging'),
    # path('test/messaging-debug-fixed/', TemplateView.as_view(template_name='debug_messaging_fixed.html'), name='debug_messaging_fixed'),
    # path('test/messaging-offline/', TemplateView.as_view(template_name='messaging_offline_test.html'), name='messaging_offline_test'),
    # PWA Test Pages
    path('test/pwa/', TemplateView.as_view(template_name='pwa_test.html'), name='pwa_test'),
    path('test/pwa-install/', TemplateView.as_view(template_name='pwa_install_test.html'), name='pwa_install_test'),
    path('test/static-js/', TemplateView.as_view(template_name='test_static_js.html'), name='test_static_js'),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Push Notification API routes
    path('api/push/vapid-public-key/', notification_views.VapidPublicKeyView.as_view(), name='vapid_public_key'),
    path('api/push/subscribe/', notification_views.SubscribeView.as_view(), name='push_subscribe'),
    path('api/push/unsubscribe/', notification_views.UnsubscribeView.as_view(), name='push_unsubscribe'),
    # User photo like API
    path('api/users/<str:username>/photos/<str:photo_type>/like/', toggle_profile_photo_like, name='toggle_profile_photo_like'),
    # Domain app URLs
    path('search/', include(('search.urls', 'search'), namespace='search')),
    path('', include(('posts.urls', 'posts'), namespace='posts')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('groups/', include(('groups.urls', 'groups'), namespace='groups')),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('courses/', include('courses.urls')),
    path('documents/', include(('documents.urls', 'documents'), namespace='documents')),
    path('', include('releases.urls')),
    # Messaging - Unfrozen for group chat functionality
    path('messaging/', include(('messaging.urls', 'messaging'), namespace='messaging')),
    # JWT Token endpoints (temporarily disabled due to pkg_resources issue)
    # path('api/token/', include('rest_framework_simplejwt.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
