from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('load-years/', views.load_years, name='load_years'),
]
