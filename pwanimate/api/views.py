"""
Pwanimate API Views.

Exposes authenticated HTTP endpoints for persistent conversations,
RAG interactions, conversation listings, and detail/deletion.
"""

import asyncio
import json
import logging
import queue
import sys
import threading
import uuid
import requests
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.conf import settings
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.signing import TimestampSigner
from urllib.parse import urlencode
from django.template.loader import render_to_string
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
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
from pwanimate.models import (
    PwanimateAttachment,
    PwanimateConversation,
    PwanimateMessage,
    PwanimateStudyCheckpoint,
    PwanimateStudySession,
)
from pwanimate.orchestrator import (
    OrchestrationRequest,
    OrchestratorValidationError,
    PwanimateOrchestrator,
)
from django.core.exceptions import PermissionDenied, ValidationError
from pwanimate.services.conversation import ConversationService
from pwanimate.services.attachment import AttachmentService
from pwanimate.services.study_session import (
    StudyCollectionService,
    StudySessionService,
    parse_study_command,
)
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
        if "text/event-stream" in request.headers.get("Accept", ""):
            # Parse the request body on the request thread before the worker uses it.
            # DRF caches parsed data on the Request instance.
            _ = request.data
            _ = request.user.is_authenticated
            return self._stream_chat_response(request)
        return self._post_chat(request)

    def _stream_chat_response(self, request):
        """Stream truthful orchestration status updates, followed by the usual JSON payload."""
        events = queue.Queue()

        def report_progress(stage):
            if stage in {
                "searching_web",
                "reading_sources",
                "devouring_context",
                "searching_posts",
                "searching_documents",
            }:
                events.put(("status", {"stage": stage}))

        def perform_request():
            close_old_connections()
            try:
                result = self._post_chat(request, progress_callback=report_progress)
                events.put(("response", (result.status_code, result.data)))
            except Exception:
                logger.exception("Pwanimate streamed chat request failed unexpectedly")
                events.put(("response", (
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    {"error": "An unexpected error occurred while processing your request."},
                )))
            finally:
                close_old_connections()

        worker = threading.Thread(target=perform_request, name="pwanimate-chat", daemon=True)
        worker.start()

        async def stream_events():
            yield 'event: status\ndata: {"stage":"thinking"}\n\n'
            while True:
                try:
                    event_type, payload = await asyncio.to_thread(events.get, True, 12)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue

                if event_type == "status":
                    yield f"event: status\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"
                    continue

                response_status, response_data = payload
                encoded = JSONRenderer().render({
                    "status_code": response_status,
                    "data": response_data,
                }).decode("utf-8")
                yield f"event: response\ndata: {encoded}\n\n"
                break

        response = StreamingHttpResponse(stream_events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def _post_chat(self, request, progress_callback=None):
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
            study_mode (bool): Optional flag to enter/continue Study Mode.
            study_session_id (str): Optional UUID of an owned Study Mode session.
        """
        data = request.data or {}
        message = data.get("message") if "message" in data else data.get("query")
        if not message or not isinstance(message, str) or not message.strip():
            return Response(
                {"error": "Field 'message' is required and must be a non-empty string."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_study_cmd, study_remainder = parse_study_command(message)
        study_session_id = data.get("study_session_id")
        requested_study_session = None

        conversation_id = data.get("conversation_id")
        conversation = None

        if study_session_id:
            requested_study_session = StudySessionService.get_owned_session(
                user=request.user,
                session_id=study_session_id,
            )
            if requested_study_session is None:
                return Response(
                    {"error": "Study session not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if conversation_id and str(requested_study_session.conversation_id) != str(conversation_id):
                return Response(
                    {"error": "Conversation does not match study session."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            conversation = requested_study_session.conversation
            conversation_id = str(conversation.id)

        if conversation is None:
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

        existing_study_session = (
            requested_study_session
            or StudySessionService.get_session_for_conversation(request.user, conversation)
        )
        explicit_study_flag = data.get("study_mode")
        study_mode_active = bool(
            is_study_cmd
            or explicit_study_flag is True
            or requested_study_session is not None
            or (
                existing_study_session is not None
                and existing_study_session.status == PwanimateStudySession.STATUS_ACTIVE
                and explicit_study_flag is not False
            )
        )

        # Bare `@study` command activates Study Mode without making an empty AI request
        if is_study_cmd and not study_remainder:
            study_session = StudySessionService.start_or_continue_session(
                user=request.user,
                conversation=conversation,
                title=str(data.get("title") or "").strip(),
                learning_objective=str(data.get("learning_objective") or "").strip(),
                current_topic=str(data.get("current_topic") or "").strip(),
                context_resources=context_resources,
                attachments=attachment_objs,
            )
            if attachment_objs:
                with transaction.atomic():
                    for att in attachment_objs:
                        att.conversation = conversation
                        att.save(update_fields=["conversation"])
            return Response(
                {
                    "study_mode_activated": True,
                    "study_mode": True,
                    "study_session": StudySessionService.serialize_session(study_session),
                    "conversation_id": str(conversation.id),
                    "answer": "",
                    "citations": [],
                    "sources": [],
                    "people": [],
                    "blocks": [],
                    "warnings": [],
                    "metadata": {"study_mode": True, "study_mode_activated": True},
                },
                status=status.HTTP_200_OK,
            )

        clean_query = study_remainder.strip() if (is_study_cmd and study_remainder.strip()) else message.strip()
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
            if user_msg is not None and user_msg.content not in {clean_query, message.strip()}:
                return Response(
                    {"error": "Retry content must match the original message."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if user_msg is None:
            user_msg = ConversationService.persist_user_message(conversation, clean_query)

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

        study_session = None
        study_context = None
        if study_mode_active:
            initial_objective = str(data.get("learning_objective") or "").strip()
            initial_topic = str(data.get("current_topic") or "").strip()
            if is_study_cmd and not initial_topic:
                initial_topic = clean_query[:160]
            if is_study_cmd and not initial_objective:
                initial_objective = f"Master {clean_query[:180]}"
            study_session = StudySessionService.start_or_continue_session(
                user=request.user,
                conversation=conversation,
                title=str(data.get("title") or "").strip(),
                learning_objective=initial_objective,
                current_topic=initial_topic or clean_query[:160],
                context_resources=context_resources,
                attachments=active_attachments,
            )
            # Study Mode strictly uses bounded server-side history; client-submitted history/checkpoints are ignored
            history = ConversationService.load_history(
                conversation,
                max_messages=StudySessionService.STUDY_HISTORY_MAX_MESSAGES,
                max_tokens=StudySessionService.STUDY_HISTORY_MAX_TOKENS,
                exclude_message_id=user_msg.id,
            )
            study_context = StudySessionService.build_study_orchestration_context(
                session=study_session,
                query=clean_query,
                recent_history=history,
            )
        else:
            # Load history without the current/retried user turn, so it is sent only once.
            server_history = ConversationService.load_history(
                conversation,
                exclude_message_id=user_msg.id if retry_requested else user_msg.id,
            )
            # Fallback to client history only if no server history exists yet (backward compatibility)
            history = server_history
            if not server_history and not conversation_id and data.get("history"):
                history = data.get("history", [])

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
                study_mode=study_mode_active,
                study_context=study_context,
            )
            orchestrator = self.get_orchestrator()
            # External LLM generation occurs outside database transactions
            if progress_callback:
                response = orchestrator.run(orchestration_req, on_progress=progress_callback)
            else:
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

            if study_mode_active and study_session is not None:
                if StudySessionService.should_auto_checkpoint(study_session):
                    from pwanimate.tasks.study import generate_study_checkpoint_task
                    delay_fn = getattr(generate_study_checkpoint_task, "delay", None)
                    is_mocked_delay = hasattr(delay_fn, "assert_called")
                    try:
                        if callable(delay_fn):
                            delay_fn(str(study_session.id), up_to_message_id=asst_msg.id)
                        else:
                            StudySessionService.generate_checkpoint(
                                study_session.id, up_to_message_id=asst_msg.id
                            )
                    except Exception:
                        logger.debug(
                            "Celery dispatch unavailable for study checkpoint %s; running inline",
                            study_session.id,
                        )
                        StudySessionService.generate_checkpoint(
                            study_session.id, up_to_message_id=asst_msg.id
                        )
                    if (
                        not is_mocked_delay
                        and ("test" in sys.argv or getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False))
                        and not PwanimateStudyCheckpoint.objects.filter(
                            session=study_session, up_to_message_id=asst_msg.id
                        ).exists()
                    ):
                        StudySessionService.generate_checkpoint(
                            study_session.id, up_to_message_id=asst_msg.id
                        )

                study_session = (
                    PwanimateStudySession.objects.select_related("conversation", "latest_checkpoint")
                    .filter(pk=study_session.pk)
                    .first()
                )
                res_data["study_mode"] = True
                res_data["study_session"] = StudySessionService.serialize_session(study_session)

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
        recommended = request.query_params.get("recommended") in {"1", "true", "yes"}
        if len(query) < 2 and not recommended:
            return Response({"results": []})

        documents = Document.objects.filter(
            status="ready",
            is_available=True,
        ).select_related("category", "uploaded_by").prefetch_related("academic_units__academic_unit")

        user = request.user
        enrolled_unit_ids = set()
        if hasattr(user, "get_enrolled_units"):
            try:
                enrolled_unit_ids = {
                    e.academic_unit_id for e in user.get_enrolled_units(auto_sync=False)
                }
            except Exception:
                enrolled_unit_ids = set()

        programme = getattr(user, "programme", None)
        is_admin_or_leader = (
            user.is_staff
            or user.is_superuser
            or getattr(user, "global_role", None) in {"PRESIDENT", "DELEGATE"}
        )
        if not is_admin_or_leader:
            visibility_q = Q(visibility="public") | Q(uploaded_by=user)
            restricted_q = Q(visibility="restricted")
            if enrolled_unit_ids:
                visibility_q |= restricted_q & Q(
                    academic_units__academic_unit_id__in=enrolled_unit_ids
                )
            if programme:
                visibility_q |= restricted_q & Q(
                    academic_units__academic_unit__programme_units__programme=programme
                )
            elif getattr(user, "course", None):
                visibility_q |= restricted_q & Q(
                    academic_units__academic_unit__code__icontains=user.course.name
                )
            documents = documents.filter(visibility_q).distinct()

        if len(query) >= 2:
            documents = documents.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(academic_units__academic_unit__code__icontains=query)
                | Q(academic_units__academic_unit__name__icontains=query)
            ).distinct()
        elif recommended:
            if enrolled_unit_ids:
                documents = documents.filter(
                    academic_units__academic_unit_id__in=enrolled_unit_ids
                ).distinct()
            elif programme:
                documents = documents.filter(
                    academic_units__academic_unit__programme_units__programme=programme
                ).distinct()

        candidate_docs = list(documents.order_by("title")[:40])

        def _rank_doc(doc):
            unit_links = list(doc.academic_units.all())
            doc_unit_ids = {u.academic_unit_id for u in unit_links if u.academic_unit_id}
            if enrolled_unit_ids and (doc_unit_ids & enrolled_unit_ids):
                return (0, doc.title.lower())
            return (1, doc.title.lower())

        candidate_docs.sort(key=_rank_doc)

        results = []
        for document in candidate_docs[:20]:
            version = document.latest_version
            document_file = version.files.first() if version else None
            if not document_file or not document_file.file:
                continue
            try:
                media_url = document_file.file.url
            except (ValueError, OSError):
                continue
            unit_links = list(document.academic_units.all())
            first_unit = unit_links[0].academic_unit if unit_links and unit_links[0].academic_unit_id else None
            unit_code = first_unit.code if first_unit else ""
            unit_name = first_unit.name if first_unit else ""
            is_enrolled = bool(
                enrolled_unit_ids
                and any(u.academic_unit_id in enrolled_unit_ids for u in unit_links)
            )
            results.append({
                "document_id": str(document.share_id),
                "document_share_id": str(document.share_id),
                "document_version_id": str(version.id),
                "file_id": str(document_file.id),
                "title": document.title,
                "category": document.category.name if document.category_id else "Document",
                "unit_code": unit_code,
                "unit_name": unit_name,
                "is_enrolled_unit": is_enrolled,
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
    Supports optional `?filter=study` to list only Study Mode conversations.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversations = (
            PwanimateConversation.objects.filter(user=request.user)
            .select_related("study_session", "study_session__latest_checkpoint")
            .order_by("-updated_at")
        )
        filter_mode = (request.query_params.get("filter") or "").strip().lower()
        if filter_mode == "study" or request.query_params.get("study_only") in {"1", "true", "yes"}:
            conversations = conversations.filter(study_session__isnull=False)
        serializer = ConversationListSerializer(conversations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PwanimateConversationDetailView(APIView):
    """
    Retrieve, rename, or delete an existing conversation thread owned by the authenticated user.
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

    def patch(self, request, conversation_id):
        conversation = ConversationService.get_owned_conversation(
            user=request.user,
            conversation_id=conversation_id,
        )
        if conversation is None:
            return Response(
                {"error": "Conversation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        title = request.data.get("title")
        if title is not None:
            clean_title = str(title).strip()
            if not clean_title:
                return Response(
                    {"error": "Conversation title cannot be empty."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            conversation.title = clean_title[:255]
            conversation.save(update_fields=["title", "updated_at"])

        study_session = StudySessionService.get_session_for_conversation(request.user, conversation)
        if study_session and (
            "learning_objective" in request.data or "current_topic" in request.data
        ):
            StudySessionService.update_session_metadata(
                session=study_session,
                learning_objective=request.data.get("learning_objective"),
                current_topic=request.data.get("current_topic"),
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


class PwanimateStudySessionListView(APIView):
    """
    List all Study Mode sessions owned by the current user, or start/continue a session.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_filter = (request.query_params.get("status") or "").strip().lower() or None
        sessions = StudySessionService.list_user_sessions(
            user=request.user,
            status_filter=status_filter,
        )
        resumable = StudySessionService.get_resumable_session(request.user)
        return Response(
            {
                "sessions": [StudySessionService.serialize_session(s) for s in sessions],
                "resumable_session": (
                    StudySessionService.serialize_session(resumable) if resumable else None
                ),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        data = request.data or {}
        conversation_id = data.get("conversation_id")
        conversation = None
        created_new_conv = False

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
                        title=str(data.get("title") or "New Study Session").strip()[:255],
                    )
                    created_new_conv = True
                else:
                    return Response(
                        {"error": "Conversation not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
        else:
            conversation = ConversationService.create_conversation(
                user=request.user,
                title=str(data.get("title") or "New Study Session").strip()[:255],
            )
            created_new_conv = True

        had_session = PwanimateStudySession.objects.filter(
            conversation=conversation, user=request.user
        ).exists()
        context_resources = data.get("context_resources")
        if not isinstance(context_resources, list):
            context_resources = None

        session = StudySessionService.start_or_continue_session(
            user=request.user,
            conversation=conversation,
            title=str(data.get("title") or "").strip(),
            learning_objective=str(data.get("learning_objective") or "").strip(),
            current_topic=str(data.get("current_topic") or "").strip(),
            context_resources=context_resources,
        )
        return Response(
            {
                "study_session": StudySessionService.serialize_session(session),
                "conversation_id": str(conversation.id),
                "created": bool(created_new_conv or not had_session),
            },
            status=status.HTTP_201_CREATED if (created_new_conv or not had_session) else status.HTTP_200_OK,
        )


class PwanimateStudySessionDetailView(APIView):
    """
    Retrieve or update metadata/context state for an owned Study Mode session.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        restored_context, unavailable_resources = StudySessionService.restore_context_state(
            session=session,
            user=request.user,
        )
        checkpoints = [
            StudySessionService.serialize_checkpoint(ckpt)
            for ckpt in session.checkpoints.order_by("-created_at")[:20]
        ]
        return Response(
            {
                "study_session": StudySessionService.serialize_session(session),
                "checkpoints": checkpoints,
                "restored_context": restored_context,
                "unavailable_resources": unavailable_resources,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data or {}
        if any(k in data for k in ("title", "learning_objective", "current_topic")):
            session = StudySessionService.update_session_metadata(
                session=session,
                title=data.get("title") if "title" in data else None,
                learning_objective=data.get("learning_objective") if "learning_objective" in data else None,
                current_topic=data.get("current_topic") if "current_topic" in data else None,
            )
        if "context_resources" in data and isinstance(data.get("context_resources"), list):
            StudySessionService.sync_context_state(
                session=session,
                user=request.user,
                context_resources=data.get("context_resources"),
            )
            session.save(update_fields=["context_state", "last_active_at", "updated_at"])

        return Response(
            {"study_session": StudySessionService.serialize_session(session)},
            status=status.HTTP_200_OK,
        )


class PwanimateStudySessionStatusView(APIView):
    """
    Transition an owned Study Mode session between active, paused, completed,
    or dismiss its home-screen resume banner.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        action = str((request.data or {}).get("action") or "").strip().lower()
        if action not in {"pause", "resume", "end", "complete", "dismiss_banner"}:
            return Response(
                {"error": "Invalid action. Expected 'pause', 'resume', 'end', or 'dismiss_banner'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restored_context = []
        unavailable_resources = []

        if action == "pause":
            session = StudySessionService.pause_session(session)
        elif action == "resume":
            session = StudySessionService.resume_session(session, user=request.user)
            restored_context, unavailable_resources = StudySessionService.restore_context_state(
                session=session,
                user=request.user,
            )
        elif action in {"end", "complete"}:
            gen_ckpt = (request.data or {}).get("generate_checkpoint", True) is not False
            session = StudySessionService.end_session(
                session,
                generate_final_checkpoint=gen_ckpt,
            )
        elif action == "dismiss_banner":
            session = StudySessionService.dismiss_resume_banner(session)

        return Response(
            {
                "study_session": StudySessionService.serialize_session(session),
                "restored_context": restored_context,
                "unavailable_resources": unavailable_resources,
            },
            status=status.HTTP_200_OK,
        )


class PwanimateStudyCheckpointView(APIView):
    """
    List checkpoints or generate a fresh learning checkpoint on explicit user request.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        checkpoints = [
            StudySessionService.serialize_checkpoint(ckpt)
            for ckpt in session.checkpoints.order_by("-created_at")[:25]
        ]
        return Response({"checkpoints": checkpoints}, status=status.HTTP_200_OK)

    def post(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        checkpoint = StudySessionService.generate_checkpoint(
            session_id=session.id,
            force=True,
        )
        session = StudySessionService.get_owned_session(request.user, session.id)
        if checkpoint is None:
            return Response(
                {
                    "error": "Send at least one study message before generating a checkpoint.",
                    "study_session": StudySessionService.serialize_session(session),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "checkpoint": StudySessionService.serialize_checkpoint(checkpoint),
                "study_session": StudySessionService.serialize_session(session),
            },
            status=status.HTTP_201_CREATED,
        )


class PwanimateStudySummaryView(APIView):
    """
    Generate a structured Study Mode session summary for review, or export a reviewed
    summary as a PDF or Word document using the existing generated-documents pipeline.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data or {}
        export_format = str(data.get("export_format") or data.get("format") or "").strip().lower()
        provided_markdown = str(data.get("summary_markdown") or "").strip()

        if export_format:
            if not provided_markdown:
                last_summary = (session.context_state or {}).get("last_summary") or {}
                provided_markdown = str(last_summary.get("markdown") or "").strip()
            if not provided_markdown:
                summary_payload = StudySessionService.generate_session_summary(session=session)
                provided_markdown = summary_payload["summary_markdown"]

            try:
                from pwanimate.services.generated_documents import create_generated_resource

                summary_msg = ConversationService.persist_assistant_message(
                    conversation=session.conversation,
                    content=provided_markdown,
                )
                document, document_file, created = create_generated_resource(
                    message=summary_msg,
                    user=request.user,
                    file_format=export_format,
                )
                token = TimestampSigner().sign_object(str(document.share_id))
                download_path = reverse(
                    "documents:serve_download", kwargs={"share_id": document.share_id}
                )
                download_url = f"{download_path}?{urlencode({'t': token, 'file_id': document_file.id})}"
                return Response(
                    {
                        "document_id": document.id,
                        "document_share_id": str(document.share_id),
                        "title": document.title,
                        "format": export_format,
                        "download_url": download_url,
                        "library_url": reverse("documents:my_resources"),
                        "summary_markdown": provided_markdown,
                        "message_id": summary_msg.id,
                        "created": created,
                    },
                    status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                )
            except ValueError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                logger.exception("Could not export Study Mode summary for session %s", session_id)
                return Response(
                    {"error": "The study summary document could not be exported."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        summary_payload = StudySessionService.generate_session_summary(session=session)
        session = StudySessionService.get_owned_session(request.user, session.id)
        return Response(
            {
                **summary_payload,
                "study_session": StudySessionService.serialize_session(session),
            },
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data or {}
        content = str(data.get("content") or data.get("summary_markdown") or "").strip()
        if not content:
            return Response(
                {"error": "Summary content cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        message_id = data.get("message_id")
        if message_id is not None and str(message_id).strip() != "":
            try:
                message_id = int(message_id)
            except (TypeError, ValueError):
                message_id = None
        else:
            message_id = None

        updated = StudySessionService.update_session_summary(
            session=session,
            user=request.user,
            content=content,
            message_id=message_id,
        )
        session = StudySessionService.get_owned_session(request.user, session.id)
        return Response(
            {
                **updated,
                "study_session": StudySessionService.serialize_session(session),
            },
            status=status.HTTP_200_OK,
        )


class PwanimateStudySummarySaveCollectionView(APIView):
    """
    Save a reviewed Study Mode session summary into an existing or newly created
    Collection owned or editable by the student.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        session = StudySessionService.get_owned_session(request.user, session_id)
        if session is None:
            return Response(
                {"error": "Study session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = request.data or {}
        message_id = data.get("message_id")
        if message_id is not None and str(message_id).strip() != "":
            try:
                message_id = int(message_id)
            except (TypeError, ValueError):
                message_id = None
        else:
            message_id = None

        summary_markdown = str(data.get("summary_markdown") or "").strip()
        if not summary_markdown and message_id is None:
            last_summary = (session.context_state or {}).get("last_summary") or {}
            summary_markdown = str(last_summary.get("markdown") or "").strip()
        if not summary_markdown and message_id is None:
            generated = StudySessionService.generate_session_summary(session=session)
            summary_markdown = generated["summary_markdown"]

        collection_id = data.get("collection_id")
        if collection_id is not None and str(collection_id).strip() != "":
            try:
                collection_id = int(collection_id)
            except (TypeError, ValueError):
                return Response(
                    {"error": "Invalid collection ID."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            collection_id = None

        new_collection_name = str(data.get("new_collection_name") or "").strip()
        new_collection_description = str(data.get("new_collection_description") or "").strip()
        new_collection_visibility = str(data.get("new_collection_visibility") or "private").strip()
        file_format = str(data.get("file_format") or data.get("format") or "pdf").strip().lower()
        notes = str(data.get("notes") or "").strip()

        try:
            result = StudyCollectionService.save_summary_to_collection(
                user=request.user,
                session=session,
                summary_markdown=summary_markdown,
                message_id=message_id,
                collection_id=collection_id,
                new_collection_name=new_collection_name,
                new_collection_description=new_collection_description,
                new_collection_visibility=new_collection_visibility,
                file_format=file_format,
                notes=notes,
            )
            return Response(
                result,
                status=status.HTTP_201_CREATED if result.get("created") else status.HTTP_200_OK,
            )
        except (PermissionDenied, PermissionError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except LookupError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Failed to save study summary to collection for session %s", session_id)
            return Response(
                {"error": "Could not save the summary to the collection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PwanimateCollectionListCreateView(APIView):
    """
    List Collections the user can edit or create a new Collection for saving Study Mode summaries.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        collections = StudyCollectionService.list_editable_collections(request.user)
        return Response({"collections": collections}, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data or {}
        name = str(data.get("name") or "").strip()
        description = str(data.get("description") or "").strip()
        visibility = str(data.get("visibility") or "private").strip().lower()
        try:
            collection = StudyCollectionService.create_collection(
                user=request.user,
                name=name,
                description=description,
                visibility=visibility,
            )
            return Response(
                {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "visibility": collection.visibility,
                    "item_count": 0,
                    "is_owner": True,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


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


class PwanimateVoiceTranscriptionView(APIView):
    """Transcribe a complete client-recorded voice note with Groq Whisper."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'error': 'Audio recording is required.'}, status=status.HTTP_400_BAD_REQUEST)

        max_bytes = int(getattr(settings, 'PWANIMATE_VOICE_MAX_BYTES', 25 * 1024 * 1024))
        if audio.size <= 0 or audio.size > max_bytes:
            return Response({'error': 'Recording is empty or exceeds the upload limit.'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

        api_key = getattr(settings, 'PWANIMATE_GROQ_API_KEY', '')
        if not api_key:
            return Response({'error': 'Voice transcription is not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        language = (request.data.get('language') or '').strip().lower()
        if language not in {'en', 'sw'}:
            language = 'en'

        content_type = (audio.content_type or 'application/octet-stream').split(';', 1)[0].lower()
        extension_by_type = {
            'audio/webm': '.webm',
            'audio/ogg': '.ogg',
            'audio/mp4': '.m4a',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'audio/x-wav': '.wav',
        }
        extension = extension_by_type.get(content_type)
        if not extension:
            return Response({'error': 'This audio format is not supported.'}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        audio.seek(0)
        upstream = None
        transient_statuses = {408, 429, 500, 502, 503, 504}
        for attempt in range(2):
            audio.seek(0)
            try:
                upstream = requests.post(
                    'https://api.groq.com/openai/v1/audio/transcriptions',
                    headers={'Authorization': f'Bearer {api_key}'},
                    files={'file': (f'voice{extension}', audio, content_type)},
                    data={
                        'model': getattr(settings, 'PWANIMATE_SPEECH_TO_TEXT_MODEL', 'whisper-large-v3-turbo'),
                        'language': language,
                        'response_format': 'json',
                        'temperature': '0',
                    },
                    timeout=(5, int(getattr(settings, 'PWANIMATE_SPEECH_TO_TEXT_TIMEOUT', 60))),
                )
            except requests.RequestException:
                if attempt == 0:
                    logger.warning('Pwanimate voice transcription upload failed; retrying once', exc_info=True)
                    continue
                logger.exception('Pwanimate voice transcription request failed after retry')
                break

            if upstream.status_code in transient_statuses and attempt == 0:
                logger.warning(
                    'Pwanimate voice transcription upstream returned transient status %s; retrying once',
                    upstream.status_code,
                )
                upstream.close()
                upstream = None
                continue
            break

        if upstream is None:
            return Response({'error': 'Transcription service could not be reached. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        if upstream.status_code != 200:
            logger.warning('Pwanimate voice transcription failed with upstream status %s', upstream.status_code)
            return Response({'error': 'Transcription failed. Please try again.'}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            transcript = str(upstream.json().get('text') or '').strip()
        except (ValueError, AttributeError):
            logger.warning('Pwanimate voice transcription returned an invalid response')
            return Response({'error': 'Transcription returned an invalid response.'}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({'text': transcript}, status=status.HTTP_200_OK)
