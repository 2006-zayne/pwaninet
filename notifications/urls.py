from django.urls import path
from notifications import views

urlpatterns = [
    path('', views.notifications_list, name='notifications'),
    path('unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('mark-as-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('read/<int:notif_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
]
