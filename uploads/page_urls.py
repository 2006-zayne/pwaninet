from django.urls import path

from . import page_views

urlpatterns = [
    path("", page_views.manager_view, name="upload-manager"),
]
