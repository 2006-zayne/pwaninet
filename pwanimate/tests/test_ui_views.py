"""
Tests for Pwanimate UI Views and Template Routing.

Verifies:
- Authentication enforcement (anonymous redirected to login)
- Authenticated rendering (200 OK)
- Dual-mode rendering: standard request (full page) vs HX-Request (partial)
- Conversation URL routing: owned conversation accessible, nonexistent 404, other user's conversation 404
- Initial prompt query parameter handling
"""

import uuid
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from pwanimate.models import PwanimateConversation, PwanimateMessage

User = get_user_model()


class PwanimateUIViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="student_alice",
            email="alice@pwaninet.local",
            password="testpassword123",
            first_name="Alice",
            last_name="Student",
        )
        self.other_user = User.objects.create_user(
            username="student_bob",
            email="bob@pwaninet.local",
            password="testpassword123",
            first_name="Bob",
            last_name="Student",
        )

        self.user_conversation = PwanimateConversation.objects.create(
            user=self.user,
            title="Alice Calculus Chat",
        )
        self.user_message_1 = PwanimateMessage.objects.create(
            conversation=self.user_conversation,
            role="user",
            content="What is the derivative of x^2?",
        )
        self.user_message_2 = PwanimateMessage.objects.create(
            conversation=self.user_conversation,
            role="assistant",
            content="The derivative of x^2 with respect to x is 2x.",
            citations=["Calculus I Notes, p. 10"],
            sources=[
                {
                    "source": "document",
                    "id": "doc-1",
                    "title": "Calculus I Notes",
                    "citation": "Calculus I Notes, p. 10",
                    "url": "/documents/document/calc-1/",
                }
            ],
        )

        self.bob_conversation = PwanimateConversation.objects.create(
            user=self.other_user,
            title="Bob Private Chat",
        )

    def test_anonymous_user_redirected_to_login(self):
        """Anonymous access to /pwanimate/ must redirect to login."""
        url = reverse("pwanimate:index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.url)

    def test_authenticated_user_accesses_index_full_page(self):
        """Authenticated access with normal request returns full HTML page."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:index")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pwanimate/index.html")
        self.assertTemplateUsed(response, "pwanimate/partials/chat_content.html")
        self.assertContains(response, "Pwanimate")
        self.assertContains(response, "Alice Calculus Chat")
        self.assertNotContains(response, "Bob Private Chat")

    def test_htmx_request_renders_partial_only(self):
        """Request with HX-Request header returns only the partial workspace."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:index")
        response = self.client.get(url, HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pwanimate/partials/chat_content.html")
        self.assertTemplateNotUsed(response, "pwanimate/index.html")
        self.assertContains(response, "pwanimate-workspace")
        self.assertContains(response, "Alice Calculus Chat")

    def test_owned_conversation_detail_url_accessible(self):
        """Authenticated user can load their own conversation by UUID."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:conversation_detail", kwargs={"conversation_id": self.user_conversation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is the derivative of x^2?")
        self.assertContains(response, "The derivative of x^2 with respect to x is 2x.")
        self.assertContains(response, "Calculus I Notes")
        self.assertContains(response, "/documents/document/calc-1/")

    def test_nonexistent_conversation_returns_404(self):
        """Accessing a nonexistent UUID returns 404."""
        self.client.force_login(self.user)
        random_id = uuid.uuid4()
        url = reverse("pwanimate:conversation_detail", kwargs={"conversation_id": random_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_other_user_conversation_returns_404(self):
        """Attempting to access another student's conversation returns 404 (does not disclose existence)."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:conversation_detail", kwargs={"conversation_id": self.bob_conversation.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_initial_prompt_query_param_populates_textarea(self):
        """Query parameter ?prompt=... pre-populates composer textarea."""
        self.client.force_login(self.user)
        url = f"{reverse('pwanimate:index')}?prompt=Explain%20Big-O%20notation"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Explain Big-O notation")
