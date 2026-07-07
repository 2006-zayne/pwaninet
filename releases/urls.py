from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReleaseViewSet, UserReleaseViewViewSet

router = DefaultRouter()
router.register(r'releases', ReleaseViewSet, basename='release')
router.register(r'user-release-views', UserReleaseViewViewSet, basename='user-release-view')

urlpatterns = [
    path('api/', include(router.urls)),
]
