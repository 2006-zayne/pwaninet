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
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    # This maps 'accounts/login/' and 'accounts/logout/' automatically
    path('accounts/', include('django.contrib.auth.urls')),
    # PWA Offline Page
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('test/offline/', TemplateView.as_view(template_name='offline.html'), name='offline_test'),
    # Service worker served from app root so it controls entire scope (important for offline/splash)
    path('service-worker.js', TemplateView.as_view(template_name='service-worker.js', content_type='application/javascript'), name='service_worker'),
    # PWA Test Pages
    path('test/splash/', TemplateView.as_view(template_name='splash_test.html'), name='splash_test'),
    path('test/splash-debug/', TemplateView.as_view(template_name='splash_debug.html'), name='splash_debug'),
    path('test/splash-offline/', TemplateView.as_view(template_name='splash_offline_test.html'), name='splash_offline_test'),
    path('test/splash-always/', TemplateView.as_view(template_name='splash_always_test.html'), name='splash_always_test'),
    path('test/native-pwa/', TemplateView.as_view(template_name='native_pwa_test.html'), name='native_pwa_test'),
    path('test/pwa-debug/', TemplateView.as_view(template_name='debug_pwa_launch.html'), name='debug_pwa_launch'),
    path('test/pwa-detection/', TemplateView.as_view(template_name='debug_pwa_detection.html'), name='debug_pwa_detection'),
    path('clear-cache/', TemplateView.as_view(template_name='clear_cache.html'), name='clear_cache'),
    path('startup/', TemplateView.as_view(template_name='startup_base.html'), name='startup_base'),
    path('api/health/', TemplateView.as_view(template_name='health_check.html'), name='health_check'),
    path('debug/startup/', TemplateView.as_view(template_name='debug_startup.html'), name='debug_startup'),
    # Messaging Test Pages
    path('test/messaging/', TemplateView.as_view(template_name='test_messaging_architecture.html'), name='test_messaging_architecture'),
    path('test/messaging-debug/', TemplateView.as_view(template_name='debug_messaging.html'), name='debug_messaging'),
    path('test/messaging-debug-fixed/', TemplateView.as_view(template_name='debug_messaging_fixed.html'), name='debug_messaging_fixed'),
    path('test/messaging-offline/', TemplateView.as_view(template_name='messaging_offline_test.html'), name='messaging_offline_test'),
    # PWA Test Pages
    path('test/pwa/', TemplateView.as_view(template_name='pwa_test.html'), name='pwa_test'),
    path('test/pwa-install/', TemplateView.as_view(template_name='pwa_install_test.html'), name='pwa_install_test'),
    path('test/static-js/', TemplateView.as_view(template_name='test_static_js.html'), name='test_static_js'),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Domain app URLs
    path('', include(('posts.urls', 'posts'), namespace='posts')),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('groups/', include(('groups.urls', 'groups'), namespace='groups')),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
    path('courses/', include('courses.urls')),
    path('messaging/', include(('messaging.urls', 'messaging'), namespace='messaging')),
    # JWT Token endpoints (temporarily disabled due to pkg_resources issue)
    # path('api/token/', include('rest_framework_simplejwt.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
