"""
Pwanimate UI URL Configuration.
"""

from django.urls import path
from pwanimate.views import (
    PwanimateConversationDeleteView,
    PwanimateConversationHistoryView,
    PwanimateSettingsAboutView,
    PwanimateSettingsPersonalizationView,
    PwanimateSettingsUsageView,
    PwanimateSettingsView,
    PwanimateUIView,
)

app_name = "pwanimate"

urlpatterns = [
    path("", PwanimateUIView.as_view(), name="index"),
    path("history/", PwanimateConversationHistoryView.as_view(), name="conversation_history"),
    path("settings/", PwanimateSettingsView.as_view(), name="settings"),
    path("settings/personalization/", PwanimateSettingsPersonalizationView.as_view(), name="settings_personalization"),
    path("settings/usage/", PwanimateSettingsUsageView.as_view(), name="settings_usage"),
    path("settings/about/", PwanimateSettingsAboutView.as_view(), name="settings_about"),
    path("<uuid:conversation_id>/", PwanimateUIView.as_view(), name="conversation_detail"),
    path("<uuid:conversation_id>/delete/", PwanimateConversationDeleteView.as_view(), name="delete_conversation"),
]
