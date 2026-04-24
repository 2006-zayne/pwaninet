from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # The Feed (Home)
    path('', views.home_view, name='home'),
    
    # Registration
    path('register/', views.register_view, name='register'),

    #The logout view
    path('logout/' , auth_views.LogoutView.as_view(template_name = 'logout.html'), name = 'logout'),
    
    # Unit Specific Posts 
    path('unit/<int:unit_id>/', views.unit_posts_view, name='unit_detail'),
    
    # Create Post view
    path('post/new/', views.create_post_view, name='create_post'),


    # the load year url for the year filter.
    path('load-years/', views.load_years, name='load_years'),

    #The url to the profile view.
    path('user/<str:username>/', views.profile_view , name='profile'),

    #THe notifications path 
    path('notifications/' , views.notifications_list , name='notifications'),
    
    #THe link to update profile view
    path('profile/edit/' ,views.update_profile_view , name='update_profile'),

    #The url to the group membership 
    path('groups/toggle/<int:group_id>/', views.toggle_group_membership, name='toggle_membership'),

    #THe link to the groups dashboard
    path('groups/dashboard/', views.groups_dashboard, name='groups_dashboard'),

    #The url for the group dtails view
    path('groups/<int:group_id>/' , views.groups_detail_view , name= 'groups_detail'),

    # THis will help us see thosee who liked our posts
    path('post/<int:post_id>/likers/', views.post_likers_list, name='post_likers_list'),

    # Add this to resolve the 'toggle_like' Reverse error
    path('like/<int:post_id>/', views.toggle_like, name='toggle_like'),

    #THe link to group creation view.
    path('groups/create/', views.create_group_view, name='create_group'),

    #Path to the follow view .
    path('toggle-follow/<str:username>/', views.toggle_follow, name='toggle_follow'),

    path('group/<int:group_id>/edit/', views.edit_group, name='edit_group'),

    path('group/<int:group_id>/invite/<int:user_id>/', views.invite_to_group, name='invite_to_group'),

    path('invite/respond/<int:notif_id>/<str:action>/', views.respond_to_invite, name='respond_to_invite'),

    path('notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),

    path('notifications/mark-as-read/', views.mark_all_as_read, name='mark_all_as_read'), 

    path('post/<int:post_id>/', views.post_detail_view, name='post_details'),

    # core/urls.py
    path('notifications/read/<int:notif_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.toggle_comment_like, name='toggle_comment_like'),
    path('search/', views.search_view, name='search'),
]
