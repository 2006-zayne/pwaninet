from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'follows', views.FollowViewSet, basename='follow')
router.register(r'pinches', views.PinchViewSet, basename='pinch')
router.register(r'device-accounts', views.DeviceAccountViewSet, basename='device-account')

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    
    # Registration
    path('register/', views.register_view, name='register'),
    
    # Onboarding Flow
    path('onboarding/', views.onboarding_wizard_view, name='onboarding'),
    path('onboarding/batch-follow/', views.batch_follow_view, name='onboarding_batch_follow'),
    path('onboarding/complete/', views.complete_onboarding_view, name='onboarding_complete'),
    path('onboarding/dismiss-welcome/', views.dismiss_welcome_banner_view, name='onboarding_dismiss_welcome'),
    
    # HTMX endpoints for registration form
    path('academic/load-levels/', views.load_academic_levels, name='load_academic_levels'),
    path('academic/load-years/', views.load_academic_years, name='load_academic_years'),
    path('academic/load-semesters/', views.load_semesters, name='load_semesters'),
    
    # Email verification
    path('verify-email/<uidb64>/<token>/', views.verify_email_view, name='verify_email'),
    
    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        success_url='/users/password_reset/done/',
        html_email_template_name='registration/password_reset_email.html',
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/users/reset/done/',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
    
    # Logout view
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html', next_page='login'), name='logout'),
    
    # Profile URLs (connections before profile — more specific path)
    path(
        'user/<str:username>/connections/<str:list_type>/',
        views.profile_connections,
        name='profile_connections',
    ),
    path('user/<str:username>/', views.profile_view, name='profile'),
    path('user/<str:username>/mark-shared-viewed/', views.mark_shared_viewed, name='mark_shared_viewed'),
    path('profile/edit/', views.update_profile_view, name='update_profile'),
    path('toggle-follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
    path('pinch/<str:username>/', views.toggle_pinch, name='toggle_pinch'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/profile/', views.settings_profile_view, name='settings_profile'),
    path('settings/appearance/', views.settings_appearance_view, name='settings_appearance'),
    path('settings/notifications/', views.settings_notifications_view, name='settings_notifications'),
    path('settings/privacy/', views.settings_privacy_view, name='settings_privacy'),
    path('settings/privacy/password/', views.settings_password_manager_view, name='settings_password_manager'),
    path('settings/privacy/devices/', views.settings_active_devices_view, name='settings_active_devices'),
    path('settings/privacy/blocked/', views.settings_blocked_users_view, name='settings_blocked_users'),
    path('settings/privacy/profile/', views.settings_profile_privacy_view, name='settings_profile_privacy'),
    path('settings/privacy/posts/', views.settings_post_privacy_view, name='settings_post_privacy'),
    path('settings/privacy/hidden/', views.settings_hidden_authors_view, name='settings_hidden_authors'),
    path('settings/storage/', views.settings_storage_view, name='settings_storage'),
    path('settings/storage/downloads/', views.settings_downloads_view, name='settings_downloads'),
    path('settings/about/', views.settings_about_view, name='settings_about'),
    path('mark-onboarding-complete/', views.mark_onboarding_complete, name='mark_onboarding_complete'),
    path('accounts/switch/<int:user_id>/', views.switch_account_view, name='switch_account'),
    path('accounts/device-accounts/', views.get_device_accounts_view, name='device_accounts'),
    path('accounts/remove/<int:user_id>/', views.remove_account_from_device_view, name='remove_account_from_device'),
    path('user/<str:username>/photo/<str:photo_type>/', views.view_profile_photo_fullscreen, name='view_profile_photo_fullscreen'),
    path('people/search/', views.people_search, name='people_search'),
    
    # Privacy API endpoints
    path('api/privacy/sign-out-session/<int:session_id>/', views.api_sign_out_session, name='api_sign_out_session'),
    path('api/privacy/sign-out-all-sessions/', views.api_sign_out_all_sessions, name='api_sign_out_all_sessions'),
    path('api/privacy/unblock/<int:user_id>/', views.api_unblock_user, name='api_unblock_user'),
    path('api/privacy/show-hidden/<int:user_id>/', views.api_show_hidden_author, name='api_show_hidden_author'),
    
    # Online status API
    path('api/users/<int:user_id>/online-status/', views.user_online_status_api, name='user_online_status_api'),
]
