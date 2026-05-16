from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications import views

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
    path('read/<int:notif_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
    path('delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('delete-read/', views.delete_read_notifications, name='delete_read_notifications'),
]
