from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('feedback/', views.feedback_inbox, name='feedback_inbox'),
    path('feedback/<uuid:ticket_id>/', views.feedback_detail, name='feedback_detail'),
    path('feedback/user/<uuid:ticket_id>/', views.user_feedback_view, name='user_feedback_view'),
    path('feedback/submit/', views.submit_feedback, name='submit_feedback'),
]
