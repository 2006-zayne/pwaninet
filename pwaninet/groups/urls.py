"""
Web URLs for groups app.
Contains both Django web view routes and API routes.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.groups_dashboard, name='groups_dashboard'),
    path('<int:group_id>/', views.groups_detail_view, name='groups_detail'),
    path('create/', views.create_group_view, name='create_group'),
    path('toggle/<int:group_id>/', views.toggle_group_membership, name='toggle_membership'),
    path('<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('<int:group_id>/invite/<int:user_id>/', views.invite_to_group, name='invite_to_group'),
    path('invite/respond/<int:notif_id>/<str:action>/', views.respond_to_invite, name='respond_to_invite'),
    path('<int:group_id>/approve/<int:user_id>/', views.approve_from_notification, name='approve_from_notification'),
    path('<int:group_id>/reject/<int:user_id>/', views.reject_from_notification, name='reject_from_notification'),
    path('api/unread-counts/', views.group_unread_counts_api, name='group_unread_counts_api'),
    path('search-users/', views.search_users_view, name='search_users'),
    path('<int:group_id>/photo/<str:photo_type>/', views.view_group_photo_fullscreen, name='view_group_photo_fullscreen'),
    # API endpoints
    path('api/groups/<int:pk>/assign-role/', views.GroupViewSet.as_view({'post': 'assign_role'}), name='group_assign_role'),
    path('api/groups/<int:pk>/leave/', views.GroupViewSet.as_view({'post': 'leave'}), name='group_leave'),
    path('api/groups/<int:pk>/assign-and-leave/', views.GroupViewSet.as_view({'post': 'assign_and_leave'}), name='group_assign_and_leave'),
]
