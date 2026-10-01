"""
Pwanimate API URL Configuration.
"""

from django.urls import path
from pwanimate.api.views import (
    PwanimateAttachmentDownloadView,
    PwanimateAttachmentMediaView,
    PwanimateAttachmentStatusView,
    PwanimateAttachmentUploadView,
    PwanimateChatView,
    PwanimateConversationDetailView,
    PwanimateConversationListView,
    PwanimateContextDocumentSearchView,
    PwanimateGeneratedResourceView,
    PwanimateQuotaStatusView,
    PwanimateVoiceTranscriptionView,
)

app_name = "pwanimate_api"

urlpatterns = [
    path("chat/", PwanimateChatView.as_view(), name="chat"),
    path("messages/<int:message_id>/resources/", PwanimateGeneratedResourceView.as_view(), name="generated_resource"),
    path("conversations/", PwanimateConversationListView.as_view(), name="conversation_list"),
    path("conversations/<uuid:conversation_id>/", PwanimateConversationDetailView.as_view(), name="conversation_detail"),
    path("quota-status/", PwanimateQuotaStatusView.as_view(), name="quota_status"),
    path("voice/transcribe/", PwanimateVoiceTranscriptionView.as_view(), name="voice_transcribe"),
    path("context/documents/", PwanimateContextDocumentSearchView.as_view(), name="context_document_search"),
    path("attachments/upload/", PwanimateAttachmentUploadView.as_view(), name="attachment_upload"),
    path("attachments/<uuid:attachment_id>/status/", PwanimateAttachmentStatusView.as_view(), name="attachment_status"),
    path("attachments/<uuid:attachment_id>/view/", PwanimateAttachmentMediaView.as_view(), name="attachment_view"),
    path("attachments/<uuid:attachment_id>/download/", PwanimateAttachmentDownloadView.as_view(), name="attachment_download"),
]
