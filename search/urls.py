from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.unified_search_view, name='unified_search'),
    path('', views.unified_search_view, name='search'),
    path('suggest/', views.search_suggest_view, name='search_suggest'),
    path('clear-recent/', views.clear_recent_searches_view, name='clear_recent_searches'),
]
