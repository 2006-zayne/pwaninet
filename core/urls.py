from django.urls import path
from users.views import register_view
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Registration
    path('register/', register_view, name='register'),

    # Logout view
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html', next_page='login'), name='logout'),
]
