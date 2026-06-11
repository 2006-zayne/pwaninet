"""
API URLs for posts app including task status endpoints.
"""
from django.urls import path
from . import views

app_name = 'posts_api'

urlpatterns = [
    # Task status endpoint for progress tracking
    path('task-status/<str:task_id>/', views.task_status_view, name='task_status'),
]
