"""
Unit and Integration Tests for Pwanimate Final UI Polish:
- Safe conversation deletion endpoint (PwanimateConversationDeleteView)
- Smart deterministic conversation auto-naming & greeting deferral
- Stability across multi-turn exchanges
"""

import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from pwanimate.models import PwanimateConversation, PwanimateMessage
from pwanimate.services.conversation import ConversationService, derive_title

User = get_user_model()


class ConversationDeletionTestCase(TestCase):
    """Test safe conversation deletion view and permissions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="delete_test_user",
            email="delete_user@pwaninet.local",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            username="other_delete_user",
            email="other_delete@pwaninet.local",
            password="testpassword123",
        )
        self.conversation = ConversationService.create_conversation(
            user=self.user,
            title="Study Notes Discussion",
        )

    def test_anonymous_user_redirected_to_login(self):
        url = reverse("pwanimate:delete_conversation", kwargs={"conversation_id": self.conversation.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/accounts/login", res.headers.get("Location", ""))

    def test_user_cannot_delete_another_users_conversation(self):
        self.client.force_login(self.other_user)
        url = reverse("pwanimate:delete_conversation", kwargs={"conversation_id": self.conversation.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 404)
        # Verify conversation still exists
        self.assertTrue(PwanimateConversation.objects.filter(id=self.conversation.id).exists())

    def test_nonexistent_conversation_returns_404(self):
        self.client.force_login(self.user)
        random_id = uuid.uuid4()
        url = reverse("pwanimate:delete_conversation", kwargs={"conversation_id": random_id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 404)

    def test_owner_can_delete_conversation_via_delete_method(self):
        self.client.force_login(self.user)
        # Add messages
        ConversationService.persist_user_message(self.conversation, "Question 1")
        ConversationService.persist_assistant_message(self.conversation, "Answer 1")

        url = reverse("pwanimate:delete_conversation", kwargs={"conversation_id": self.conversation.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)

        # Verify conversation and cascade messages deleted
        self.assertFalse(PwanimateConversation.objects.filter(id=self.conversation.id).exists())
        self.assertEqual(PwanimateMessage.objects.filter(conversation_id=self.conversation.id).count(), 0)

    def test_owner_can_delete_conversation_via_post_method(self):
        self.client.force_login(self.user)
        url = reverse("pwanimate:delete_conversation", kwargs={"conversation_id": self.conversation.id})
        res = self.client.post(url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(PwanimateConversation.objects.filter(id=self.conversation.id).exists())


class ConversationAutoNamingTestCase(TestCase):
    """Test deterministic auto-naming, greeting deferral, and stability."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="naming_test_user",
            email="naming_user@pwaninet.local",
            password="testpassword123",
        )

    def test_greetings_return_empty_string(self):
        greetings = [
            "hi",
            "Hello",
            "hey there",
            "Hi there!",
            "Good morning",
            "Habari",
            "Jambo",
            "hello pwanimate",
        ]
        for g in greetings:
            self.assertEqual(derive_title(g), "", f"Failed for greeting: {g}")

    def test_conversational_filler_prefix_stripped(self):
        pairs = [
            (
                "Can you help me understand packet switching in computer networks?",
                "Packet switching in computer networks?",
            ),
            (
                "Could you please tell me about student accommodation hostels?",
                "Student accommodation hostels?",
            ),
            (
                "I need help finding past exam papers for year 2",
                "Past exam papers for year 2",
            ),
            (
                "Please explain how Dijkstra's algorithm works",
                "How Dijkstra's algorithm works",
            ),
        ]
        for query, expected in pairs:
            self.assertEqual(derive_title(query), expected)

    def test_title_words_capped_at_max_words(self):
        query = "one two three four five six seven eight nine ten eleven twelve"
        title = derive_title(query, max_words=5)
        self.assertEqual(title, "One two three four five")

    def test_deferral_and_multi_turn_stability(self):
        conv = ConversationService.create_conversation(user=self.user)
        self.assertEqual(conv.title, "")

        # Turn 1: User says greeting -> title should remain empty
        ConversationService.persist_user_message(conv, "Hello!")
        conv.refresh_from_db()
        self.assertEqual(conv.title, "")

        # Turn 1: Assistant replies
        ConversationService.persist_assistant_message(conv, "Hello! How can I help you today?")

        # Turn 2: User asks real question -> title should now be derived
        ConversationService.persist_user_message(
            conv,
            "Can you help me understand packet switching in computer networks?",
        )
        conv.refresh_from_db()
        self.assertEqual(conv.title, "Packet switching in computer networks?")

        # Turn 3: User asks another question -> title must remain stable, NOT overwritten
        ConversationService.persist_user_message(conv, "What about circuit switching?")
        conv.refresh_from_db()
        self.assertEqual(conv.title, "Packet switching in computer networks?")


class ConversationHistoryPaginationTestCase(TestCase):
    """Test paginated lazy-loading for conversation history (infinite scroll)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="history_page_user",
            email="history_page@pwaninet.local",
            password="testpassword123",
        )
        self.other_user = User.objects.create_user(
            username="other_history_user",
            email="other_hist@pwaninet.local",
            password="testpassword123",
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse("pwanimate:conversation_history")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/accounts/login", res.headers.get("Location", ""))

    def test_lazy_loading_pagination(self):
        self.client.force_login(self.user)
        # Create 22 conversations for this user
        created_convs = []
        for i in range(22):
            c = ConversationService.create_conversation(
                user=self.user,
                title=f"Conversation {i+1}",
            )
            created_convs.append(c)

        # 1. Main UI view loads the first chunk of 15
        ui_res = self.client.get(reverse("pwanimate:index"))
        self.assertEqual(ui_res.status_code, 200)
        self.assertEqual(len(ui_res.context["conversations"]), 15)
        self.assertTrue(ui_res.context["has_next"])
        self.assertEqual(ui_res.context["next_page"], 2)
        self.assertContains(ui_res, 'hx-get="/pwanimate/history/?page=2"')

        # 2. History endpoint fetches page 2
        history_url = reverse("pwanimate:conversation_history") + "?page=2"
        hist_res = self.client.get(history_url)
        self.assertEqual(hist_res.status_code, 200)
        self.assertEqual(len(hist_res.context["conversations"]), 7)
        self.assertFalse(hist_res.context["has_next"])
        self.assertIsNone(hist_res.context["next_page"])
        self.assertNotContains(hist_res, "pwanimate-history-sentinel")

    def test_active_conversation_highlighting_in_history_chunk(self):
        self.client.force_login(self.user)
        convs = [
            ConversationService.create_conversation(user=self.user, title=f"Conv {i}")
            for i in range(20)
        ]
        # Target conversation on page 2 (index 18)
        target = convs[0]  # Created earliest, will be on page 2 since ordered -updated_at
        history_url = f"{reverse('pwanimate:conversation_history')}?page=2&active_id={target.id}"
        res = self.client.get(history_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f'data-id="{target.id}"')
        self.assertContains(res, "pwanimate-conversation-item active")

