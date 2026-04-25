from django.urls import path
from . import views

urlpatterns = [
    path('user/<str:username>/', views.profile_view, name='profile'),
    path('profile/edit/', views.update_profile_view, name='update_profile'),
    path('toggle-follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
]
