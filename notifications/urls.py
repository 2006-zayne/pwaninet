from django.urls import path, include
from django.views.decorators.http import require_http_methods
from rest_framework.routers import DefaultRouter
from notifications import views
from notifications.rendering.api_views import (
    notification_profiles_list,
    notification_profile_detail,
    render_notification_payload,
    rendering_pipeline_status,
)

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Push notification API routes
    path('api/push/vapid-public-key/', views.VapidPublicKeyView.as_view(), name='vapid_public_key'),
    path('api/push/subscribe/', views.SubscribeView.as_view(), name='push_subscribe'),
    path('api/push/unsubscribe/', views.UnsubscribeView.as_view(), name='push_unsubscribe'),
    
    # Web routes
    path('', views.notifications_list, name='notifications'),
    path('unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('mark-as-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('resource-preview/<uuid:notif_id>/', views.resource_preview, name='resource_preview'),
    path('read/<uuid:notif_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('delete/<uuid:notif_id>/', views.delete_notification, name='delete_notification'),
    path('delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('delete-read/', views.delete_read_notifications, name='delete_read_notifications'),
    path('expand/<uuid:notif_id>/', views.expand_notification, name='expand_notification'),
    
    # Notification preference routes
    path('set-dnd/', views.set_do_not_disturb, name='set_do_not_disturb'),
    path('clear-dnd/', views.clear_do_not_disturb, name='clear_do_not_disturb'),
    
    # Profile-driven rendering API routes
    path('api/rendering/profiles/', notification_profiles_list, name='notification_profiles_list'),
    path('api/rendering/profiles/<str:notification_type>/', notification_profile_detail, name='notification_profile_detail'),
    path('api/rendering/render/', render_notification_payload, name='render_notification_payload'),
    path('api/rendering/status/', rendering_pipeline_status, name='rendering_pipeline_status'),
]
