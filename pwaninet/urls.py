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
from users.views import toggle_profile_photo_like

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

# Service Worker - served as static file to bypass auth middleware
@require_http_methods(["GET", "HEAD"])
@csrf_exempt
def serve_service_worker(request):
    import os
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'service-worker.js')
    try:
        with open(sw_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    except FileNotFoundError:
        return HttpResponse('Service worker not found', status=404)

# Messaging redirect - FROZEN FOR MVP
def redirect_messaging(request):
    """Redirect any messaging URLs to home page since messaging is frozen for MVP"""
    return HttpResponseRedirect('/')

GITHUB_RELEASE_APK_URL = 'https://github.com/2006-zayne/pwaninet/releases/latest/download/pwaninet.apk'


@require_http_methods(["GET", "HEAD"])
def download_android_apk(request):
    """
    Direct Android APK download endpoint.
    Issues an immediate HTTP 302 redirect directly to the GitHub Release asset URL
    for all standard and production requests, avoiding streaming large binaries
    through Django/WSGI workers.
    Keeps a local file streaming fallback only when DEBUG=True and a local APK file exists.
    """
    github_url = getattr(settings, 'APK_DOWNLOAD_URL', GITHUB_RELEASE_APK_URL)

    # Local file streaming fallback only when DEBUG=True and explicitly requested (?local=1) or configured
    if getattr(settings, 'DEBUG', False) and (
        request.GET.get('local') == '1' or
        request.GET.get('fallback') == '1' or
        not getattr(settings, 'REDIRECT_APK_TO_GITHUB', True)
    ):
        import os
        local_candidates = [
            os.path.join(settings.BASE_DIR, 'media', 'downloads', 'pwaninet.apk'),
            os.path.join(settings.BASE_DIR, 'android', 'app', 'build', 'outputs', 'apk', 'release', 'app-release.apk'),
            os.path.join(settings.BASE_DIR, 'android', 'app', 'build', 'outputs', 'apk', 'debug', 'app-debug.apk'),
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
    # This maps 'accounts/login/' and 'accounts/logout/' automatically
    path('accounts/', include('django.contrib.auth.urls')),
    # PWA Offline Page (handles both /offline/ and /offline.html)
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('offline.html', TemplateView.as_view(template_name='offline.html'), name='offline_html'),
    path('test/offline/', TemplateView.as_view(template_name='offline.html'), name='offline_test'),
    # PWA Manifest and Service Worker - served without auth middleware
    path('manifest.webmanifest', serve_manifest, name='manifest'),
    path('service-worker.js', serve_service_worker, name='service_worker'),
    # Direct Android APK download routes (permanent endpoints for social sharing & settings)
    path('download/android/', download_android_apk, name='download_android_apk'),
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
