"""
Comprehensive Offline Test Suite for Pwanimate Phase 6 Orchestrator and API.

Tests contracts, prompt policies, intent classification, conversational turns,
grounded RAG turns, empty retrieval handling, error normalization, and the
authenticated chat API endpoint.
"""

from unittest.mock import MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from pwanimate.ai.exceptions import (
    AIProviderRateLimitError,
    AIProviderTimeoutError,
)
from pwanimate.ai.gateway import AIGateway, ChatMessage, LLMRequest, LLMResponse, LLMRouter
from pwanimate.ai.providers import MockLLMProvider
from pwanimate.context import ContextEngine, ContextItem, ContextPackage, ContextRequest
from pwanimate.orchestrator import (
    OrchestrationRequest,
    OrchestrationResponse,
    OrchestratorValidationError,
    PwanimateOrchestrator,
    SYSTEM_INSTRUCTION_CONVERSATIONAL,
    SYSTEM_INSTRUCTION_TUTOR,
)
from pwanimate.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    SourceType,
    UnifiedRetrievalService,
)

User = get_user_model()


class OrchestratorContractsTestCase(SimpleTestCase):
    """Test OrchestrationRequest and OrchestrationResponse data contracts."""

    def test_request_validation_valid(self):
        req = OrchestrationRequest(
            query="What is packet switching?",
            history=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}],
            temperature=0.3,
            max_tokens=500,
        )
        self.assertEqual(req.query, "What is packet switching?")
        self.assertEqual(len(req.history), 2)
        self.assertIsInstance(req.history[0], ChatMessage)
        self.assertEqual(req.history[0].role, "user")
        self.assertEqual(req.temperature, 0.3)
        self.assertEqual(req.max_tokens, 500)

    def test_request_validation_empty_query(self):
        with self.assertRaises(OrchestratorValidationError):
            OrchestrationRequest(query="   ")

    def test_request_validation_invalid_temperature(self):
        with self.assertRaises(OrchestratorValidationError):
            OrchestrationRequest(query="Test", temperature=2.5)

    def test_request_validation_invalid_max_tokens(self):
        with self.assertRaises(OrchestratorValidationError):
            OrchestrationRequest(query="Test", max_tokens=0)

    def test_response_to_dict(self):
        resp = OrchestrationResponse(
            answer="Packet switching breaks data into packets.",
            citations=["[Networks, v1: p. 5]"],
            sources=[{"title": "Networks", "citation": "[Networks, v1: p. 5]", "url": "/doc/1/"}],
            provider="mock",
            model="mock-llm-v1",
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            retrieval_time_ms=12.5,
            generation_time_ms=45.0,
            total_time_ms=58.0,
            metadata={"intent": "rag"},
        )
        data = resp.to_dict()
        self.assertEqual(data["answer"], "Packet switching breaks data into packets.")
        self.assertEqual(data["citations"], ["[Networks, v1: p. 5]"])
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["provider"], "mock")
        self.assertEqual(data["timing"]["retrieval_ms"], 12.5)
        self.assertEqual(data["timing"]["generation_ms"], 45.0)
        self.assertEqual(data["timing"]["total_ms"], 58.0)


class OrchestratorPromptsTestCase(SimpleTestCase):
    """Test system prompt policies."""

    def test_tutor_prompt_contains_grounding_rules(self):
        self.assertIn("Pwanimate", SYSTEM_INSTRUCTION_TUTOR)
        self.assertIn("<retrieved_context>", SYSTEM_INSTRUCTION_TUTOR)
        self.assertIn("bracketed citations", SYSTEM_INSTRUCTION_TUTOR)
        self.assertIn("Untrusted Data Boundary", SYSTEM_INSTRUCTION_TUTOR)

    def test_conversational_prompt_contains_friendly_instructions(self):
        self.assertIn("Pwanimate", SYSTEM_INSTRUCTION_CONVERSATIONAL)
        self.assertIn("greetings", SYSTEM_INSTRUCTION_CONVERSATIONAL)


class IntentClassificationTestCase(SimpleTestCase):
    """Test intent classification between chitchat and RAG."""

    def setUp(self):
        self.orchestrator = PwanimateOrchestrator()

    def test_conversational_greetings(self):
        self.assertTrue(self.orchestrator.is_conversational_intent("Hello"))
        self.assertTrue(self.orchestrator.is_conversational_intent("hi!"))
        self.assertTrue(self.orchestrator.is_conversational_intent("Good morning"))
        self.assertTrue(self.orchestrator.is_conversational_intent("Habari"))
        self.assertTrue(self.orchestrator.is_conversational_intent("Thanks"))
        self.assertTrue(self.orchestrator.is_conversational_intent("who are you?"))
        self.assertTrue(self.orchestrator.is_conversational_intent("What can you do"))

    def test_substantive_academic_queries(self):
        self.assertFalse(self.orchestrator.is_conversational_intent("Explain how TCP three-way handshake works"))
        self.assertFalse(self.orchestrator.is_conversational_intent("What is the fee payment deadline for semester 2?"))
        self.assertFalse(self.orchestrator.is_conversational_intent("Summarize chapter 3 of operating systems"))
        self.assertFalse(self.orchestrator.is_conversational_intent("Who is the lecturer for COM 210?"))


class OrchestratorExecutionTestCase(SimpleTestCase):
    """Test PwanimateOrchestrator service execution with mock components."""

    def setUp(self):
        self.mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": self.mock_provider}, default_provider="mock")
        self.gateway = AIGateway(router=router)

    def test_conversational_turn_skips_retrieval(self):
        mock_retrieval = MagicMock(spec=UnifiedRetrievalService)
        mock_context = MagicMock(spec=ContextEngine)

        orchestrator = PwanimateOrchestrator(
            retrieval_service=mock_retrieval,
            context_engine=mock_context,
            gateway=self.gateway,
        )

        req = OrchestrationRequest(query="Hello there!")
        resp = orchestrator.run(req)

        # Retrieval & Context Engine must NOT be called for conversational greeting
        mock_retrieval.retrieve.assert_not_called()
        mock_context.build_context.assert_not_called()

        self.assertEqual(resp.provider, "mock")
        self.assertEqual(resp.citations, [])
        self.assertEqual(resp.retrieval_time_ms, 0.0)
        self.assertGreaterEqual(resp.total_time_ms, 0.0)
        self.assertEqual(resp.metadata.get("intent"), "conversational")

    def test_grounded_rag_turn_executes_pipeline(self):
        mock_retrieval = MagicMock(spec=UnifiedRetrievalService)
        mock_context = MagicMock(spec=ContextEngine)

        # Upstream retrieval returns 1 result
        sample_result = RetrievalResult(
            source=SourceType.DOCUMENT,
            object_id=10,
            title="Computer Networks Notes",
            snippet="Packet switching routes packets dynamically over networks.",
            score=0.95,
            url="/documents/document/net-10/",
            citation="[Networks Notes, v1: p. 12]",
        )
        mock_retrieval.retrieve.return_value = RetrievalResponse(
            query="packet switching",
            results=[sample_result],
            total_count=1,
            execution_time_ms=5.0,
        )

        # Context Engine builds ContextPackage
        context_item = ContextItem(
            source="document",
            object_id=10,
            title="Computer Networks Notes",
            content="Packet switching routes packets dynamically over networks.",
            citation="[Networks Notes, v1: p. 12]",
            url="/documents/document/net-10/",
        )
        mock_context.build_context.return_value = ContextPackage(
            query="packet switching",
            items=[context_item],
            citations=["[Networks Notes, v1: p. 12]"],
            total_items=1,
            estimated_tokens=20,
            total_characters=80,
        )

        orchestrator = PwanimateOrchestrator(
            retrieval_service=mock_retrieval,
            context_engine=mock_context,
            gateway=self.gateway,
        )

        req = OrchestrationRequest(
            query="Explain packet switching from my notes",
            task="rag",
        )
        resp = orchestrator.run(req)

        # Retrieval & Context Engine were invoked
        mock_retrieval.retrieve.assert_called_once()
        mock_context.build_context.assert_called_once()

        # Citations and sources preserved
        self.assertIn("[Networks Notes, v1: p. 12]", resp.citations)
        self.assertEqual(len(resp.sources), 1)
        self.assertEqual(resp.sources[0]["title"], "Computer Networks Notes")
        self.assertEqual(resp.sources[0]["url"], "/documents/document/net-10/")
        self.assertEqual(resp.metadata.get("intent"), "rag")
        self.assertGreater(resp.total_time_ms, 0.0)

    def test_rag_with_empty_retrieval_results(self):
        mock_retrieval = MagicMock(spec=UnifiedRetrievalService)
        mock_retrieval.retrieve.return_value = RetrievalResponse(
            query="unmatched query",
            results=[],
            total_count=0,
            execution_time_ms=2.0,
        )

        context_engine = ContextEngine()
        orchestrator = PwanimateOrchestrator(
            retrieval_service=mock_retrieval,
            context_engine=context_engine,
            gateway=self.gateway,
        )

        req = OrchestrationRequest(query="Quantum physics in medieval literature")
        resp = orchestrator.run(req)

        self.assertEqual(resp.citations, [])
        self.assertEqual(resp.sources, [])
        self.assertIn("Processed task 'rag'", resp.answer)


class PwanimateChatAPITestCase(TestCase):
    """Test the authenticated /api/pwanimate/chat/ HTTP endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="test_student",
            email="student@pwaninet.local",
            password="testpassword123",
        )
        # Setup mock orchestrator with mock embedding and LLM providers
        from pwanimate.ai.embeddings.mock import MockEmbeddingProvider
        from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService
        mock_emb = MockEmbeddingProvider(dimensions=768)
        doc_service = DocumentSemanticRetrievalService(embedding_provider=mock_emb)
        retrieval_service = UnifiedRetrievalService(document_service=doc_service)

        self.mock_provider = MockLLMProvider()
        router = LLMRouter(providers={"mock": self.mock_provider}, default_provider="mock")
        self.gateway = AIGateway(router=router)
        self.orchestrator = PwanimateOrchestrator(
            retrieval_service=retrieval_service,
            gateway=self.gateway,
        )
        from pwanimate.api.views import PwanimateChatView
        PwanimateChatView.orchestrator = self.orchestrator

    def tearDown(self):
        from pwanimate.api.views import PwanimateChatView
        PwanimateChatView.orchestrator = None

    def test_unauthenticated_request_rejected(self):
        url = reverse("pwanimate_api:chat")
        resp = self.client.post(url, {"message": "Hello"}, format="json")
        self.assertIn(resp.status_code, [401, 403])

    def test_authenticated_valid_greeting(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        resp = self.client.post(url, {"message": "Hello Pwanimate!"}, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("timing", data)
        self.assertEqual(data["metadata"]["intent"], "conversational")

    def test_authenticated_empty_message_returns_400(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        resp = self.client.post(url, {"message": "  "}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_authenticated_rag_query_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        payload = {
            "message": "What is packet switching in computer networks?",
            "history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello! How can I help?"},
            ],
            "task": "rag",
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("citations", data)
        self.assertIn("sources", data)
        self.assertEqual(data["provider"], "mock")

    def test_gateway_rate_limit_maps_to_429(self):
        error_provider = MockLLMProvider(
            simulated_error=AIProviderRateLimitError("Quota hit", provider="mock")
        )
        router = LLMRouter(providers={"mock": error_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        custom_orchestrator = PwanimateOrchestrator(gateway=gateway)

        from pwanimate.api.views import PwanimateChatView
        view = PwanimateChatView.as_view(orchestrator=custom_orchestrator)

        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post(
            "/api/pwanimate/chat/",
            {"message": "Hello"},
            format="json",
        )
        request.user = self.user

        response = view(request)
        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limited", response.data["error"])

    def test_gateway_timeout_maps_to_504(self):
        error_provider = MockLLMProvider(
            simulated_error=AIProviderTimeoutError("Read timed out", provider="mock")
        )
        router = LLMRouter(providers={"mock": error_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        custom_orchestrator = PwanimateOrchestrator(gateway=gateway)

        from pwanimate.api.views import PwanimateChatView
        view = PwanimateChatView.as_view(orchestrator=custom_orchestrator)

        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post(
            "/api/pwanimate/chat/",
            {"message": "Hello"},
            format="json",
        )
        request.user = self.user

        response = view(request)
        self.assertEqual(response.status_code, 504)
        self.assertIn("timed out", response.data["error"])
