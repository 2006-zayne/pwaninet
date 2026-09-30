"""
Pwanimate API Views.

Exposes authenticated HTTP endpoints for persistent conversations,
RAG interactions, conversation listings, and detail/deletion.
"""

import logging
import uuid
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.signing import TimestampSigner
from urllib.parse import urlencode
from django.template.loader import render_to_string
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from pwanimate.ai.exceptions import (
    AIGatewayError,
    AIProviderConfigurationError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from pwanimate.api.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    PwanimateAttachmentSerializer,
)
from pwanimate.models import PwanimateConversation, PwanimateAttachment, PwanimateMessage
from pwanimate.orchestrator import (
    OrchestrationRequest,
    OrchestratorValidationError,
    PwanimateOrchestrator,
)
from django.core.exceptions import ValidationError
from pwanimate.services.conversation import ConversationService
from pwanimate.services.attachment import AttachmentService
from pwanimate.ai.gateway.quota_tracker import get_quota_tracker
from documents.models import Document

logger = logging.getLogger(__name__)


class PwanimateChatView(APIView):
    """
    Primary conversational endpoint for Pwanimate.

    Accepts an authenticated student question, persists user and assistant turns,
    invokes the Pwanimate Orchestrator, and returns a structured JSON answer
    with conversation and message IDs, citations, source provenance, and timing.
    """

    permission_classes = [permissions.IsAuthenticated]
    orchestrator = None

    def get_orchestrator(self) -> PwanimateOrchestrator:
        return self.orchestrator or PwanimateOrchestrator()

    def post(self, request):
        """
        Process a chat or RAG query.

        Expected JSON payload:
            message (str): Student's query (required).
            conversation_id (str): Optional UUID of existing conversation.
            history (list): Optional fallback client history if conversation_id is omitted.
            sources (list): Optional list of source strings ['document', 'post'].
            task (str): Optional task override ('rag', 'general').
            provider (str): Optional provider override ('gemini', 'groq', 'openrouter', 'mock').
            model (str): Optional model override.
            attachments (list): Optional list of attachment UUIDs or objects.
            context_resources (list): Optional list of Context Rail resource descriptors.
        """
        data = request.data or {}
        message = data.get("message") or data.get("query")
        if not message or not isinstance(message, str) or not message.strip():
            return Response(
                {"error": "Field 'message' is required and must be a non-empty string."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation_id = data.get("conversation_id")
        conversation = None

        if conversation_id:
            conversation = ConversationService.get_owned_conversation(
                user=request.user,
                conversation_id=conversation_id,
            )
            if conversation is None:
                if data.get("create_conversation") is True:
                    try:
                        requested_id = uuid.UUID(str(conversation_id))
                    except (ValueError, TypeError, AttributeError):
                        return Response(
                            {"error": "Invalid conversation ID."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    if PwanimateConversation.objects.filter(id=requested_id).exists():
                        return Response(
                            {"error": "Conversation not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )
                    conversation = ConversationService.create_conversation(
                        user=request.user,
                        conversation_id=requested_id,
                    )
                else:
                    return Response(
                        {"error": "Conversation not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
        else:
            conversation = ConversationService.create_conversation(user=request.user)

        # Validate attachments if provided
        raw_attachment_ids = data.get("attachments") or data.get("attachment_ids") or []
        attachment_objs = []
        if isinstance(raw_attachment_ids, list) and raw_attachment_ids:
            for item in raw_attachment_ids:
                aid = item.get("id") if isinstance(item, dict) else item
                if not aid:
                    continue
                att = AttachmentService.get_authorized_attachment(
                    user=request.user,
                    attachment_id=aid,
                )
                if not att:
                    return Response(
                        {"error": f"Attachment '{aid}' not found or unauthorized."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                attachment_objs.append(att)

        conversation_attachments = list(conversation.attachments.all()) if conversation else []
        all_known_attachments = {str(att.id): att for att in conversation_attachments}
        all_known_attachments.update({str(att.id): att for att in attachment_objs})
        pending_documents = [
            att for att in all_known_attachments.values()
            if att.attachment_type == "document"
            and att.processing_status in {"pending", "processing"}
        ]
        if pending_documents:
            return Response(
                {"error": "Pwanimate is still reading the attached document. Try again when it shows Ready."},
                status=status.HTTP_409_CONFLICT,
            )
        failed_documents = [
            att for att in attachment_objs
            if att.attachment_type == "document" and att.processing_status == "failed"
        ]
        if failed_documents:
            return Response(
                {"error": "Pwanimate could not read one of these documents. Remove it and try a clearer or text-based copy."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        context_resources = data.get("context_resources") or []
        if not isinstance(context_resources, list):
            context_resources = []

        clean_query = message.strip()
        retry_requested = data.get("retry") is True
        retry_message_id = data.get("retry_user_message_id")
        if retry_message_id is not None:
            try:
                retry_message_id = int(retry_message_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "Invalid retry message ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        user_msg = None
        if retry_requested:
            user_msg = ConversationService.get_retryable_user_message(
                conversation,
                clean_query,
                message_id=retry_message_id,
            )
            if retry_message_id is not None and user_msg is None:
                return Response(
                    {"error": "Message to retry was not found in this conversation."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if user_msg is not None and user_msg.content != clean_query:
                return Response(
                    {"error": "Retry content must match the original message."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if user_msg is None:
            user_msg = ConversationService.persist_user_message(conversation, clean_query)

        # Load history without the original turn being retried, so it is sent only once.
        server_history = ConversationService.load_history(
            conversation,
            exclude_message_id=user_msg.id if retry_requested else None,
        )

        # Fallback to client history only if no server history exists yet (backward compatibility)
        history = server_history
        if not server_history and not conversation_id and data.get("history"):
            history = data.get("history", [])

        # Atomically link attachments to conversation and user message
        if attachment_objs:
            with transaction.atomic():
                for att in attachment_objs:
                    att.conversation = conversation
                    att.message = user_msg
                    att.save(update_fields=["conversation", "message"])

        # Multi-turn attachment context preservation:
        # Include current turn attachments plus active working materials attached earlier in this conversation
        active_attachments = list(attachment_objs)
        if conversation:
            seen_ids = {a.id for a in active_attachments}
            for conv_att in conversation.attachments.all().order_by("created_at"):
                if conv_att.id not in seen_ids and conv_att.processing_status != "failed":
                    active_attachments.append(conv_att)
                    seen_ids.add(conv_att.id)

        sources = data.get("sources")
        task = data.get("task", "rag")
        provider = data.get("provider")
        model = data.get("model")

        try:
            orchestration_req = OrchestrationRequest(
                query=clean_query,
                user=request.user,
                history=history,
                task=task,
                sources=sources,
                provider=provider,
                model=model,
                attachments=active_attachments,
                context_resources=context_resources,
                local_time=data.get("local_time"),
                timezone_name=data.get("timezone"),
            )
            orchestrator = self.get_orchestrator()
            # External LLM generation occurs outside database transactions
            response = orchestrator.run(orchestration_req)

            # Persist assistant response turn with defensive fallback
            answer_text = (response.answer or "").strip()
            if not answer_text:
                answer_text = "I'm sorry, I was unable to generate a response. Please try asking again or rephrasing your question."

            asst_msg = ConversationService.persist_assistant_message(
                conversation=conversation,
                content=answer_text,
                citations=response.citations,
                sources=response.sources,
            )

            res_data = response.to_dict()
            if response.people:
                res_data["people_html"] = render_to_string(
                    "pwanimate/partials/people_section.html",
                    {"people": response.people},
                    request=request,
                )
            res_data["conversation_id"] = str(conversation.id)
            res_data["message_id"] = asst_msg.id
            res_data["user_message_id"] = user_msg.id
            if attachment_objs:
                res_data["attachments"] = PwanimateAttachmentSerializer(attachment_objs, many=True).data

            # Include fallback info and quota status
            fallback_info = {
                "fallback_used": response.metadata.get("fallback_used", False),
                "original_provider": response.metadata.get("original_provider", response.provider),
                "provider_used": response.provider,
                "vision_fallback": response.metadata.get("vision_route") == "fallback",
                "vision_text_fallback": response.metadata.get("vision_text_fallback", False),
            }
            res_data["fallback_info"] = fallback_info
            res_data["quota_info"] = response.quota_info
            res_data["quota_status"] = get_quota_tracker().get_status()

            thoughts_tokens = response.metadata.get("thoughts_tokens")
            total_output_tokens = response.metadata.get("total_output_tokens")
            max_output_tokens = response.metadata.get("max_output_tokens")

            logger.info(
                "PwanimateChatView response: user=%s conv=%s msg_id=%s provider=%s model=%s finish_reason=%s prompt_tokens=%s completion_tokens=%s thoughts_tokens=%s total_output_tokens=%s total_tokens=%s max_output_tokens=%s ans_len=%d",
                getattr(request.user, "username", "anon"),
                conversation.id,
                asst_msg.id,
                response.provider,
                response.model,
                response.finish_reason,
                response.prompt_tokens,
                response.completion_tokens,
                thoughts_tokens,
                total_output_tokens,
                response.total_tokens,
                max_output_tokens,
                len(response.answer),
            )

            return Response(res_data, status=status.HTTP_200_OK)

        except OrchestratorValidationError as exc:
            return Response(
                {"error": str(exc), "conversation_id": str(conversation.id), "user_message_id": user_msg.id},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AIProviderConfigurationError as exc:
            logger.warning("Pwanimate provider capability error: %s", exc)
            return Response(
                {"error": exc.message, "conversation_id": str(conversation.id), "user_message_id": user_msg.id},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            logger.warning("Pwanimate validation error: %s", exc)
            return Response(
                {
                    "error": str(exc.messages if hasattr(exc, "messages") else exc),
                    "conversation_id": str(conversation.id),
                    "user_message_id": user_msg.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AIProviderRateLimitError as exc:
            logger.warning("Pwanimate rate limit: %s", exc)
            return Response(
                {
                    "error": "AI service is temporarily rate limited. Please try again shortly.",
                    "conversation_id": str(conversation.id),
                    "user_message_id": user_msg.id,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except AIProviderTimeoutError as exc:
            logger.warning("Pwanimate timeout: %s", exc)
            return Response(
                {
                    "error": "AI service request timed out.",
                    "conversation_id": str(conversation.id),
                    "user_message_id": user_msg.id,
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except AIGatewayError as exc:
            logger.error("Pwanimate gateway error: %s", exc)
            return Response(
                {
                    "error": f"AI service error: {exc.message}",
                    "conversation_id": str(conversation.id),
                    "user_message_id": user_msg.id,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.error("Pwanimate unexpected error: %s", exc, exc_info=True)
            return Response(
                {
                    "error": "An unexpected error occurred while processing your request.",
                    "conversation_id": str(conversation.id),
                    "user_message_id": user_msg.id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PwanimateGeneratedResourceView(APIView):
    """Create a private library document from one of the user's assistant replies."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, message_id):
        message = get_object_or_404(
            PwanimateMessage.objects.select_related("conversation"),
            pk=message_id,
            role="assistant",
            conversation__user=request.user,
        )
        raw_format = request.data.get("format")
        if not isinstance(raw_format, str):
            return Response({"error": "Choose PDF or Word format."}, status=status.HTTP_400_BAD_REQUEST)
        file_format = raw_format.strip().lower()
        try:
            from pwanimate.services.generated_documents import create_generated_resource
            document, document_file, created = create_generated_resource(
                message=message,
                user=request.user,
                file_format=file_format,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Could not create Pwanimate resource from message %s", message_id)
            return Response(
                {"error": "The document could not be created. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token = TimestampSigner().sign_object(str(document.share_id))
        download_path = reverse("documents:serve_download", kwargs={"share_id": document.share_id})
        download_url = f"{download_path}?{urlencode({'t': token, 'file_id': document_file.id})}"
        return Response(
            {
                "document_id": document.id,
                "title": document.title,
                "format": file_format,
                "download_url": download_url,
                "library_url": reverse("documents:my_resources"),
                "created": created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PwanimateAttachmentUploadView(APIView):
    """
    Upload an attachment (image or document) for staging before sending in chat.
    Accepts multipart/form-data with 'file' field and optional 'conversation_id'.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"error": "No file uploaded. Expected 'file' multipart field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation_id = request.data.get("conversation_id") or None

        try:
            attachment = AttachmentService.create_attachment(
                user=request.user,
                uploaded_file=file_obj,
                conversation_id=conversation_id,
            )
            if attachment.attachment_type == "document":
                from pwanimate.tasks.attachments import process_pwanimate_attachment
                try:
                    process_pwanimate_attachment.delay(str(attachment.id))
                except Exception:
                    logger.exception("Could not queue processing for attachment %s; processing inline", attachment.id)
                    process_pwanimate_attachment(str(attachment.id))
            serializer = PwanimateAttachmentSerializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as exc:
            msg = exc.message if hasattr(exc, "message") else str(exc)
            return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.error("Failed to upload attachment: %s", exc, exc_info=True)
            return Response(
                {"error": "Failed to process attachment upload."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PwanimateContextDocumentSearchView(APIView):
    """Search repository documents the current student is allowed to open."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response({"results": []})

        documents = Document.objects.filter(
            status="ready",
            is_available=True,
        ).select_related("category", "uploaded_by").order_by("title")

        user = request.user
        is_admin_or_leader = (
            user.is_staff
            or user.is_superuser
            or getattr(user, "global_role", None) in {"PRESIDENT", "DELEGATE"}
        )
        if not is_admin_or_leader:
            visibility_q = Q(visibility="public") | Q(uploaded_by=user)
            restricted_q = Q(visibility="restricted")
            programme = getattr(user, "programme", None)
            if programme:
                visibility_q |= restricted_q & Q(
                    academic_units__academic_unit__programme_units__programme=programme
                )
            elif getattr(user, "course", None):
                visibility_q |= restricted_q & Q(
                    academic_units__academic_unit__code__icontains=user.course.name
                )
            documents = documents.filter(visibility_q).distinct()

        documents = documents.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:20]

        results = []
        for document in documents:
            version = document.latest_version
            document_file = version.files.first() if version else None
            if not document_file or not document_file.file:
                continue
            try:
                media_url = document_file.file.url
            except (ValueError, OSError):
                continue
            results.append({
                "document_id": str(document.share_id),
                "document_share_id": str(document.share_id),
                "document_version_id": str(version.id),
                "file_id": str(document_file.id),
                "title": document.title,
                "category": document.category.name if document.category_id else "Document",
                "file_type": (document_file.extension or "").lstrip(".").lower(),
                "media_url": media_url,
                "thumbnail_url": document_file.preview_url or "",
                "url": f"/documents/document/{document.share_id}/",
            })
        return Response({"results": results})


class PwanimateAttachmentStatusView(APIView):
    """Return processing status for an attachment owned by the current student."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = AttachmentService.get_authorized_attachment(request.user, attachment_id)
        if not attachment:
            return Response({"error": "Attachment not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "id": str(attachment.id),
            "processing_status": attachment.processing_status,
            "processing_error": attachment.processing_error,
            "chunk_count": attachment.chunks.count(),
        })


class PwanimateAttachmentMediaView(APIView):
    """
    Authorized private media view endpoint.
    Serves attachment content inline only to the owning user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = AttachmentService.get_authorized_attachment(
            user=request.user,
            attachment_id=attachment_id,
        )
        if not attachment:
            return Response(
                {"error": "Attachment not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not attachment.file:
            return Response(
                {"error": "Attachment file missing."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            file_handle = attachment.file.open("rb")
            response = FileResponse(file_handle, content_type=attachment.mime_type)
            response["Content-Disposition"] = f'inline; filename="{attachment.file_name}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception as exc:
            logger.error("Error serving attachment %s: %s", attachment_id, exc)
            return Response(
                {"error": "Could not read attachment file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PwanimateAttachmentDownloadView(APIView):
    """
    Authorized private media download endpoint.
    Serves attachment as forced download only to the owning user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = AttachmentService.get_authorized_attachment(
            user=request.user,
            attachment_id=attachment_id,
        )
        if not attachment:
            return Response(
                {"error": "Attachment not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not attachment.file:
            return Response(
                {"error": "Attachment file missing."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            file_handle = attachment.file.open("rb")
            response = FileResponse(file_handle, content_type=attachment.mime_type)
            response["Content-Disposition"] = f'attachment; filename="{attachment.file_name}"'
            response["X-Content-Type-Options"] = "nosniff"
            return response
        except Exception as exc:
            logger.error("Error downloading attachment %s: %s", attachment_id, exc)
            return Response(
                {"error": "Could not read attachment file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PwanimateConversationListView(APIView):
    """
    List all persistent conversations owned by the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations = PwanimateConversation.objects.filter(
            user=request.user
        ).order_by("-updated_at")
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PwanimateConversationDetailView(APIView):
    """
    Retrieve or delete an existing conversation thread owned by the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        conversation = ConversationService.get_owned_conversation(
            user=request.user,
            conversation_id=conversation_id,
        )
        if conversation is None:
            return Response(
                {"error": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversationDetailSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, conversation_id):
        conversation = ConversationService.get_owned_conversation(
            user=request.user,
            conversation_id=conversation_id,
        )
        if conversation is None:
            return Response(
                {"error": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PwanimateQuotaStatusView(APIView):
    """
    Returns the current provider quota status.

    Shows which AI providers are healthy, rate-limited, or in cooldown.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tracker = get_quota_tracker()
        return Response(
            {"quota_status": tracker.get_status()},
            status=status.HTTP_200_OK,
        )
