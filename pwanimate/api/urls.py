"""
Pwanimate API URL Configuration.
"""

from django.urls import path
from pwanimate.api.views import (
    PwanimateChatView,
    PwanimateConversationDetailView,
    PwanimateConversationListView,
    PwanimateQuotaStatusView,
)

app_name = "pwanimate_api"

urlpatterns = [
    path("chat/", PwanimateChatView.as_view(), name="chat"),
    path("conversations/", PwanimateConversationListView.as_view(), name="conversation_list"),
    path("conversations/<uuid:conversation_id>/", PwanimateConversationDetailView.as_view(), name="conversation_detail"),
    path("quota-status/", PwanimateQuotaStatusView.as_view(), name="quota_status"),
]
