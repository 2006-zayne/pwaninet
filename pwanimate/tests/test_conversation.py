"""
Comprehensive Offline Test Suite for Pwanimate Phase 7: Persistent Conversations.

Tests PwanimateConversation and PwanimateMessage models, ConversationService,
bounded history loading, chat API with conversation persistence, ownership enforcement,
conversation list/detail/delete endpoints, and failure semantics.
"""

import uuid
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from pwanimate.ai.exceptions import AIProviderRateLimitError, AIProviderTimeoutError
from pwanimate.ai.gateway import AIGateway, ChatMessage, LLMRouter
from pwanimate.ai.providers import MockLLMProvider
from pwanimate.models import PwanimateConversation, PwanimateMessage
from pwanimate.orchestrator import PwanimateOrchestrator
from pwanimate.services.conversation import ConversationService, derive_title

User = get_user_model()


class ConversationModelTestCase(TestCase):
    """Test PwanimateConversation and PwanimateMessage models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student_model_test",
            email="student_model@pwaninet.local",
            password="pass",
        )

    def test_conversation_creation_and_uuid(self):
        conv = PwanimateConversation.objects.create(
            user=self.user,
            title="Study Session",
        )
        self.assertIsInstance(conv.id, uuid.UUID)
        self.assertEqual(conv.title, "Study Session")
        self.assertEqual(conv.user, self.user)
        self.assertIn("Study Session", str(conv))

    def test_message_creation_and_ordering(self):
        conv = PwanimateConversation.objects.create(user=self.user, title="Thread")
        msg1 = PwanimateMessage.objects.create(
            conversation=conv,
            role="user",
            content="First question",
        )
        msg2 = PwanimateMessage.objects.create(
            conversation=conv,
            role="assistant",
            content="First answer",
            citations=["[Doc1, p. 1]"],
            sources=[{"title": "Doc1", "url": "/doc1/"}],
        )

        messages = list(conv.messages.all())
        self.assertEqual(messages, [msg1, msg2])
        self.assertEqual(messages[1].citations, ["[Doc1, p. 1]"])
        self.assertEqual(messages[1].sources, [{"title": "Doc1", "url": "/doc1/"}])

    def test_message_validation_rejects_invalid_role(self):
        conv = PwanimateConversation.objects.create(user=self.user)
        with self.assertRaises(ValidationError):
            msg = PwanimateMessage(conversation=conv, role="invalid_role", content="text")
            msg.full_clean()

    def test_message_validation_rejects_empty_content(self):
        conv = PwanimateConversation.objects.create(user=self.user)
        with self.assertRaises(ValidationError):
            msg = PwanimateMessage(conversation=conv, role="user", content="   ")
            msg.full_clean()

    def test_cascade_delete_user_deletes_conversations(self):
        conv = PwanimateConversation.objects.create(user=self.user, title="To Delete")
        PwanimateMessage.objects.create(conversation=conv, role="user", content="Hello")

        self.user.delete()
        self.assertFalse(PwanimateConversation.objects.filter(id=conv.id).exists())
        self.assertEqual(PwanimateMessage.objects.count(), 0)

    def test_cascade_delete_conversation_deletes_messages(self):
        conv = PwanimateConversation.objects.create(user=self.user, title="To Delete")
        PwanimateMessage.objects.create(conversation=conv, role="user", content="Hello")

        conv.delete()
        self.assertEqual(PwanimateMessage.objects.count(), 0)


class ConversationServiceTestCase(TestCase):
    """Test ConversationService business logic and history loading."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student_service_test",
            email="student_service@pwaninet.local",
            password="pass",
        )
        self.other_user = User.objects.create_user(
            username="other_student",
            email="other@pwaninet.local",
            password="pass",
        )

    def test_derive_title(self):
        self.assertEqual(derive_title(""), "Conversation")
        self.assertEqual(derive_title("   "), "Conversation")
        self.assertEqual(
            derive_title("   What   is   the   exam   schedule?  "),
            "What is the exam schedule?",
        )
        long_query = "a" * 100
        truncated = derive_title(long_query, max_length=50)
        self.assertEqual(len(truncated), 50)
        self.assertTrue(truncated.endswith("..."))

    def test_get_owned_conversation_enforces_ownership(self):
        conv = ConversationService.create_conversation(self.user, title="My Thread")

        # Owner can retrieve
        retrieved = ConversationService.get_owned_conversation(self.user, conv.id)
        self.assertEqual(retrieved, conv)

        # Other user cannot retrieve
        unauthorized = ConversationService.get_owned_conversation(self.other_user, conv.id)
        self.assertIsNone(unauthorized)

        # Invalid UUID returns None
        self.assertIsNone(ConversationService.get_owned_conversation(self.user, "invalid-uuid"))

    def test_persist_user_and_assistant_messages(self):
        conv = ConversationService.create_conversation(self.user)
        self.assertEqual(conv.title, "")

        # Persist user message sets title
        user_msg = ConversationService.persist_user_message(conv, "Explain packet switching")
        conv.refresh_from_db()
        self.assertEqual(conv.title, "Explain packet switching")
        self.assertEqual(user_msg.role, "user")
        self.assertEqual(user_msg.content, "Explain packet switching")

        # Persist assistant message
        asst_msg = ConversationService.persist_assistant_message(
            conv,
            content="Packet switching is...",
            citations=["[Networks, v1: p. 2]"],
            sources=[{"title": "Networks", "url": "/net/"}],
        )
        self.assertEqual(asst_msg.role, "assistant")
        self.assertEqual(asst_msg.citations, ["[Networks, v1: p. 2]"])

    def test_load_history_bounds_messages_and_tokens(self):
        conv = ConversationService.create_conversation(self.user)

        # Create 15 turns (30 messages)
        for i in range(15):
            ConversationService.persist_user_message(conv, f"User question {i}")
            ConversationService.persist_assistant_message(conv, f"Assistant answer {i}")

        # Bounded by max_messages=6
        history_6 = ConversationService.load_history(conv, max_messages=6, max_tokens=5000)
        self.assertEqual(len(history_6), 6)
        # Verify chronological ordering: the last message should be the latest assistant answer
        self.assertEqual(history_6[-1].content, "Assistant answer 14")
        self.assertEqual(history_6[0].content, "User question 12")

        # Bounded by token budget
        # Let's create a conversation with long messages and verify token truncation
        conv_long = ConversationService.create_conversation(self.user)
        for i in range(5):
            ConversationService.persist_user_message(conv_long, "x" * 400)      # ~100 tokens
            ConversationService.persist_assistant_message(conv_long, "y" * 400) # ~100 tokens

        # With 10 messages total (~1000 tokens), restrict budget to ~350 tokens
        history_budget = ConversationService.load_history(conv_long, max_messages=10, max_tokens=350)
        self.assertLessEqual(len(history_budget), 4)
        # Should retain the newest turns
        self.assertEqual(history_budget[-1].content, "y" * 400)


class ConversationAPITestCase(TestCase):
    """Test Chat API, Conversation List, Detail, and Delete endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="student_api",
            email="student_api@pwaninet.local",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other_api",
            email="other_api@pwaninet.local",
            password="pass123",
        )

        # Configure mock orchestrator on view
        from pwanimate.ai.embeddings.mock import MockEmbeddingProvider
        from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService
        from pwanimate.retrieval import UnifiedRetrievalService

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

    def test_start_conversation_without_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        payload = {"message": "What is the capital of Kenya?"}
        resp = self.client.post(url, payload, format="json")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("conversation_id", data)
        self.assertIn("message_id", data)
        self.assertIn("answer", data)

        conv_id = data["conversation_id"]
        conv = PwanimateConversation.objects.get(id=conv_id)
        self.assertEqual(conv.user, self.user)
        self.assertEqual(conv.title, "What is the capital of Kenya?")
        self.assertEqual(conv.messages.count(), 2)
        self.assertEqual(conv.messages.first().role, "user")
        self.assertEqual(conv.messages.last().role, "assistant")

    def test_continue_conversation_with_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        # Turn 1
        resp1 = self.client.post(url, {"message": "Hello Pwanimate"}, format="json")
        self.assertEqual(resp1.status_code, 200)
        conv_id = resp1.json()["conversation_id"]

        # Turn 2 using conversation_id
        resp2 = self.client.post(
            url,
            {"conversation_id": conv_id, "message": "Can you help me with Operating Systems?"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["conversation_id"], conv_id)

        conv = PwanimateConversation.objects.get(id=conv_id)
        self.assertEqual(conv.messages.count(), 4)

    def test_unauthorized_conversation_id_returns_404(self):
        # User 1 creates conversation
        conv = ConversationService.create_conversation(self.user, title="Private")

        # User 2 attempts to continue User 1's conversation
        self.client.force_authenticate(user=self.other_user)
        url = reverse("pwanimate_api:chat")

        resp = self.client.post(
            url,
            {"conversation_id": str(conv.id), "message": "Intrusion attempt"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["error"].lower())

    def test_generation_failure_preserves_user_message_and_returns_error(self):
        self.client.force_authenticate(user=self.user)

        # Setup orchestrator with error provider
        error_provider = MockLLMProvider(
            simulated_error=AIProviderRateLimitError("Rate limit exceeded", provider="mock")
        )
        router = LLMRouter(providers={"mock": error_provider}, default_provider="mock")
        gateway = AIGateway(router=router)
        custom_orchestrator = PwanimateOrchestrator(gateway=gateway)

        from pwanimate.api.views import PwanimateChatView
        PwanimateChatView.orchestrator = custom_orchestrator

        url = reverse("pwanimate_api:chat")
        resp = self.client.post(url, {"message": "What is threading?"}, format="json")

        self.assertEqual(resp.status_code, 429)
        data = resp.json()
        self.assertIn("conversation_id", data)
        conv_id = data["conversation_id"]

        # Verify user message was preserved and no fake assistant message was created
        conv = PwanimateConversation.objects.get(id=conv_id)
        self.assertEqual(conv.messages.count(), 1)
        self.assertEqual(conv.messages.first().role, "user")
        self.assertEqual(conv.messages.first().content, "What is threading?")

    def test_conversation_list_api(self):
        self.client.force_authenticate(user=self.user)
        conv1 = ConversationService.create_conversation(self.user, title="Thread 1")
        conv2 = ConversationService.create_conversation(self.user, title="Thread 2")
        # Other user's conversation should not appear
        ConversationService.create_conversation(self.other_user, title="Other Thread")

        url = reverse("pwanimate_api:conversation_list")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        titles = [c["title"] for c in data]
        self.assertIn("Thread 1", titles)
        self.assertIn("Thread 2", titles)
        self.assertNotIn("Other Thread", titles)

    def test_conversation_detail_api(self):
        self.client.force_authenticate(user=self.user)
        conv = ConversationService.create_conversation(self.user, title="Detail Thread")
        ConversationService.persist_user_message(conv, "Question 1")
        ConversationService.persist_assistant_message(
            conv,
            content="Answer 1",
            citations=["[Doc1, p. 5]"],
            sources=[{"title": "Doc1", "citation": "[Doc1, p. 5]", "url": "/doc1/"}],
        )

        url = reverse("pwanimate_api:conversation_detail", kwargs={"conversation_id": conv.id})
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["title"], "Detail Thread")
        self.assertEqual(len(data["messages"]), 2)
        self.assertEqual(data["messages"][1]["citations"], ["[Doc1, p. 5]"])
        self.assertEqual(len(data["messages"][1]["sources"]), 1)

    def test_conversation_detail_unauthorized_returns_404(self):
        conv = ConversationService.create_conversation(self.user, title="Private Thread")
        self.client.force_authenticate(user=self.other_user)

        url = reverse("pwanimate_api:conversation_detail", kwargs={"conversation_id": conv.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_conversation_delete_api(self):
        self.client.force_authenticate(user=self.user)
        conv = ConversationService.create_conversation(self.user, title="To Delete")
        ConversationService.persist_user_message(conv, "Question")

        url = reverse("pwanimate_api:conversation_detail", kwargs={"conversation_id": conv.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(PwanimateConversation.objects.filter(id=conv.id).exists())

    def test_conversation_delete_unauthorized_returns_404(self):
        conv = ConversationService.create_conversation(self.user, title="Private")
        self.client.force_authenticate(user=self.other_user)

        url = reverse("pwanimate_api:conversation_detail", kwargs={"conversation_id": conv.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(PwanimateConversation.objects.filter(id=conv.id).exists())
