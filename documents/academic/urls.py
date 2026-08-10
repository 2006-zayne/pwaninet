"""
URL patterns for academic HTMX endpoints.
"""
from django.urls import path
from . import views

app_name = 'academic'

urlpatterns = [
    path('load-levels/', views.load_academic_levels, name='load_levels'),
    path('load-years/', views.load_academic_years, name='load_years'),
    path('load-semesters/', views.load_semesters, name='load_semesters'),
]
