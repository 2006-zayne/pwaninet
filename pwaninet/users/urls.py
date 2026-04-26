from django.urls import path
from . import views

urlpatterns = [
    path('user/<str:username>/', views.profile_view, name='profile'),
    path('profile/edit/', views.update_profile_view, name='update_profile'),
    path('toggle-follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
    path('notification-preferences/', views.notification_preferences_view, name='notification_preferences'),
    path('accounts/switch/<int:user_id>/', views.switch_account_view, name='switch_account'),
    path('accounts/device-accounts/', views.get_device_accounts_view, name='device_accounts'),
    path('accounts/remove/<int:user_id>/', views.remove_account_from_device_view, name='remove_account_from_device'),
]
