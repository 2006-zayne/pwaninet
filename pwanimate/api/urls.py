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
    PwanimateCollectionListCreateView,
    PwanimateConversationDetailView,
    PwanimateConversationListView,
    PwanimateContextDocumentSearchView,
    PwanimateGeneratedResourceView,
    PwanimateQuotaStatusView,
    PwanimateStudyCheckpointView,
    PwanimateStudySessionDetailView,
    PwanimateStudySessionListView,
    PwanimateStudySessionStatusView,
    PwanimateStudySummarySaveCollectionView,
    PwanimateStudySummaryView,
    PwanimateVoiceTranscriptionView,
)

app_name = "pwanimate_api"

urlpatterns = [
    path("chat/", PwanimateChatView.as_view(), name="chat"),
    path("messages/<int:message_id>/resources/", PwanimateGeneratedResourceView.as_view(), name="generated_resource"),
    path("conversations/", PwanimateConversationListView.as_view(), name="conversation_list"),
    path("conversations/<uuid:conversation_id>/", PwanimateConversationDetailView.as_view(), name="conversation_detail"),
    path("study-sessions/", PwanimateStudySessionListView.as_view(), name="study_session_list"),
    path("study-sessions/<uuid:session_id>/", PwanimateStudySessionDetailView.as_view(), name="study_session_detail"),
    path("study-sessions/<uuid:session_id>/status/", PwanimateStudySessionStatusView.as_view(), name="study_session_status"),
    path("study-sessions/<uuid:session_id>/checkpoint/", PwanimateStudyCheckpointView.as_view(), name="study_session_checkpoint"),
    path("study-sessions/<uuid:session_id>/summary/", PwanimateStudySummaryView.as_view(), name="study_session_summary"),
    path(
        "study-sessions/<uuid:session_id>/summary/save-to-collection/",
        PwanimateStudySummarySaveCollectionView.as_view(),
        name="study_session_save_collection",
    ),
    path("collections/", PwanimateCollectionListCreateView.as_view(), name="collection_list_create"),
    path("quota-status/", PwanimateQuotaStatusView.as_view(), name="quota_status"),
    path("voice/transcribe/", PwanimateVoiceTranscriptionView.as_view(), name="voice_transcribe"),
    path("context/documents/", PwanimateContextDocumentSearchView.as_view(), name="context_document_search"),
    path("attachments/upload/", PwanimateAttachmentUploadView.as_view(), name="attachment_upload"),
    path("attachments/<uuid:attachment_id>/status/", PwanimateAttachmentStatusView.as_view(), name="attachment_status"),
    path("attachments/<uuid:attachment_id>/view/", PwanimateAttachmentMediaView.as_view(), name="attachment_view"),
    path("attachments/<uuid:attachment_id>/download/", PwanimateAttachmentDownloadView.as_view(), name="attachment_download"),
]
