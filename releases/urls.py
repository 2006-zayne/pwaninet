from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReleaseViewSet, UserReleaseViewViewSet, VersionAPIView, CreateReleaseView
from .web_views import (
    release_list,
    dashboard,
    create_release,
    edit_release,
    detail_release,
    publish_release,
    archive_release,
    set_current_release,
    add_release_item,
    delete_release_item,
)

router = DefaultRouter()
router.register(r'releases', ReleaseViewSet, basename='release')
router.register(r'user-release-views', UserReleaseViewViewSet, basename='user-release-view')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    path('api/version/', VersionAPIView.as_view(), name='version'),
    path('api/releases/create/', CreateReleaseView.as_view(), name='create_release'),
    
    # Release Center UI routes (/system/releases/)
    path('system/releases/', dashboard, name='release_dashboard'),
    path('system/releases/list/', release_list, name='release_list'),
    path('system/releases/create/', create_release, name='release_create'),
    path('system/releases/<int:release_id>/edit/', edit_release, name='release_edit'),
    path('system/releases/<int:release_id>/', detail_release, name='release_detail'),
    path('system/releases/<int:release_id>/publish/', publish_release, name='release_publish'),
    path('system/releases/<int:release_id>/archive/', archive_release, name='release_archive'),
    path('system/releases/<int:release_id>/set-current/', set_current_release, name='release_set_current'),
    path('system/releases/<int:release_id>/add-item/', add_release_item, name='release_add_item'),
    path('system/releases/items/<int:item_id>/delete/', delete_release_item, name='release_delete_item'),
]
