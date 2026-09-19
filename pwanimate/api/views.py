"""
Pwanimate API Views.

Exposes authenticated HTTP endpoints for persistent conversations,
RAG interactions, conversation listings, and detail/deletion.
"""

import logging
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from pwanimate.ai.exceptions import (
    AIGatewayError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from pwanimate.api.serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
)
from pwanimate.models import PwanimateConversation
from pwanimate.orchestrator import (
    OrchestrationRequest,
    OrchestratorValidationError,
    PwanimateOrchestrator,
)
from django.core.exceptions import ValidationError
from pwanimate.services.conversation import ConversationService
from pwanimate.ai.gateway.quota_tracker import get_quota_tracker

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
                return Response(
                    {"error": "Conversation not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = ConversationService.create_conversation(user=request.user)

        # Load bounded history from server persistence
        server_history = ConversationService.load_history(conversation)

        # Fallback to client history only if no server history exists yet (backward compatibility)
        history = server_history
        if not server_history and not conversation_id and data.get("history"):
            history = data.get("history", [])

        # Persist user message turn
        clean_query = message.strip()
        user_msg = ConversationService.persist_user_message(conversation, clean_query)

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
            res_data["conversation_id"] = str(conversation.id)
            res_data["message_id"] = asst_msg.id
            res_data["user_message_id"] = user_msg.id

            # Include fallback info and quota status
            fallback_info = {
                "fallback_used": response.metadata.get("fallback_used", False),
                "original_provider": response.metadata.get("original_provider", response.provider),
                "provider_used": response.provider,
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
                {"error": str(exc), "conversation_id": str(conversation.id)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as exc:
            logger.warning("Pwanimate validation error: %s", exc)
            return Response(
                {
                    "error": str(exc.messages if hasattr(exc, "messages") else exc),
                    "conversation_id": str(conversation.id),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AIProviderRateLimitError as exc:
            logger.warning("Pwanimate rate limit: %s", exc)
            return Response(
                {
                    "error": "AI service is temporarily rate limited. Please try again shortly.",
                    "conversation_id": str(conversation.id),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except AIProviderTimeoutError as exc:
            logger.warning("Pwanimate timeout: %s", exc)
            return Response(
                {
                    "error": "AI service request timed out.",
                    "conversation_id": str(conversation.id),
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except AIGatewayError as exc:
            logger.error("Pwanimate gateway error: %s", exc)
            return Response(
                {
                    "error": f"AI service error: {exc.message}",
                    "conversation_id": str(conversation.id),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.error("Pwanimate unexpected error: %s", exc, exc_info=True)
            return Response(
                {
                    "error": "An unexpected error occurred while processing your request.",
                    "conversation_id": str(conversation.id),
                },
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
