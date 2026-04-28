from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'follows', views.FollowViewSet, basename='follow')
router.register(r'device-accounts', views.DeviceAccountViewSet, basename='device-account')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Registration
    path('register/', views.register_view, name='register'),
    
    # Logout view
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html', next_page='login'), name='logout'),
    
    # Profile URLs
    path('user/<str:username>/', views.profile_view, name='profile'),
    path('user/<str:username>/mark-shared-viewed/', views.mark_shared_viewed, name='mark_shared_viewed'),
    path('profile/edit/', views.update_profile_view, name='update_profile'),
    path('toggle-follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
    path('notification-preferences/', views.notification_preferences_view, name='notification_preferences'),
    path('accounts/switch/<int:user_id>/', views.switch_account_view, name='switch_account'),
    path('accounts/device-accounts/', views.get_device_accounts_view, name='device_accounts'),
    path('accounts/remove/<int:user_id>/', views.remove_account_from_device_view, name='remove_account_from_device'),
    path('user/<str:username>/photo/<str:photo_type>/', views.view_profile_photo_fullscreen, name='view_profile_photo_fullscreen'),
]
