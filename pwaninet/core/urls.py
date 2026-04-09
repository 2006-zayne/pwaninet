from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # The Feed (Home)
    path('', views.post_list_view, name='home'),
    
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
    path('user/<str:username>', views.profile_view , name='profile'),

    #THe notifications path 
    path('notifications/' , views.notifications_list , name='notifications'),
    
    #THe link to update profile view
    path('profile/edit/' ,views.update_profile_view , name='update_profile'),

]