from django.urls import path
from notifications import views

urlpatterns = [
    path('', views.notifications_list, name='notifications'),
    path('unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('mark-as-read/', views.mark_all_as_read, name='mark_all_as_read'),
    path('read/<int:notif_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('delete/<int:notif_id>/', views.delete_notification, name='delete_notification'),
    path('delete-all/', views.delete_all_notifications, name='delete_all_notifications'),
    path('delete-read/', views.delete_read_notifications, name='delete_read_notifications'),
]
