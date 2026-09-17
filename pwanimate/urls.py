"""
Pwanimate UI URL Configuration.
"""

from django.urls import path
from pwanimate.views import PwanimateUIView

app_name = "pwanimate"

urlpatterns = [
    path("", PwanimateUIView.as_view(), name="index"),
    path("<uuid:conversation_id>/", PwanimateUIView.as_view(), name="conversation_detail"),
]
