"""
Tests for Pwanimate Rendering Layer, Chat UX, and Presentation Contracts.

Verifies:
- Chat API response includes user_message_id and message_id
- Sources summary deduplicates multiple chunks from the same resource
- Enriched metadata (resource_type, media_url, author) is preserved in sources
- SSR templates render data-message-id, action bars, and polymorphic preview hosts
- Redundant user citations are suppressed when people cards are present
- Person cards use line clamping and responsive columns
- Static vendor assets for DOMPurify, KaTeX, and Prism exist on disk
"""

import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from pwanimate.ai.gateway import AIGateway, LLMRouter
from pwanimate.ai.providers import MockLLMProvider
from pwanimate.context import ContextItem
from pwanimate.models import PwanimateConversation, PwanimateMessage
from pwanimate.orchestrator.service import PwanimateOrchestrator
from pwanimate.retrieval import SourceType, UnifiedRetrievalService
from pwanimate.retrieval.services.document_retrieval import DocumentSemanticRetrievalService
from pwanimate.ai.embeddings.mock import MockEmbeddingProvider

User = get_user_model()


class PwanimateRenderingApiTests(TestCase):
    """Test API response contracts for message IDs and source enrichment."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="student_render_test",
            email="render_test@pwaninet.local",
            password="testpassword123",
        )

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

    def test_chat_response_includes_user_and_assistant_message_ids(self):
        """Chat API must return both user_message_id and message_id for DOM message action binding."""
        self.client.force_authenticate(user=self.user)
        url = reverse("pwanimate_api:chat")

        resp = self.client.post(url, {"message": "Hello Pwanimate"}, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("conversation_id", data)
        self.assertIn("user_message_id", data)
        self.assertIn("message_id", data)

        conv = PwanimateConversation.objects.get(id=data["conversation_id"])
        user_msg = conv.messages.filter(role="user").first()
        asst_msg = conv.messages.filter(role="assistant").first()

        self.assertIsNotNone(user_msg)
        self.assertIsNotNone(asst_msg)
        self.assertEqual(data["user_message_id"], user_msg.id)
        self.assertEqual(data["message_id"], asst_msg.id)

    def test_sources_summary_deduplication_and_enrichment(self):
        """Context chunks from the same document should be deduplicated to a single badge."""
        item1 = ContextItem(
            source=SourceType.DOCUMENT,
            object_id="doc-1-chunk-1",
            title="Calculus Notes Vol 1",
            content="Derivative of sin(x) is cos(x)",
            citation="Calculus Notes, p. 12",
            url="/documents/preview/calc-1/",
            metadata={
                "resource_type": "document",
                "author": "Dr. Smith",
                "media_url": "/media/calc1.pdf",
                "thumbnail_url": "/media/calc1_thumb.png",
                "hls_url": "/media/calc1/master.m3u8",
            },
        )
        item2 = ContextItem(
            source=SourceType.DOCUMENT,
            object_id="doc-1-chunk-2",
            title="Calculus Notes Vol 1",
            content="Derivative of cos(x) is -sin(x)",
            citation="Calculus Notes, p. 13",
            url="/documents/preview/calc-1/",
            metadata={
                "resource_type": "document",
                "author": "Dr. Smith",
                "media_url": "/media/calc1.pdf",
                "thumbnail_url": "/media/calc1_thumb.png",
                "hls_url": "/media/calc1/master.m3u8",
            },
        )
        item3 = ContextItem(
            source=SourceType.DOCUMENT,
            object_id="doc-2-chunk-1",
            title="Linear Algebra Notes",
            content="Matrix multiplication is associative",
            citation="LinAlg Notes, p. 5",
            url="/documents/preview/linalg-1/",
            metadata={"resource_type": "document", "author": "Prof. Jones"},
        )

        sources = self.orchestrator._build_sources_summary([item1, item2, item3])

        # Exactly 2 sources after deduplicating the two chunks of doc-1
        self.assertEqual(len(sources), 2)
        urls = [s["url"] for s in sources]
        self.assertIn("/documents/preview/calc-1/", urls)
        self.assertIn("/documents/preview/linalg-1/", urls)

        # Enriched metadata contract
        calc_source = next(s for s in sources if s["url"] == "/documents/preview/calc-1/")
        self.assertEqual(calc_source["resource_type"], "document")
        self.assertEqual(calc_source["author"], "Dr. Smith")
        self.assertEqual(calc_source["media_url"], "/media/calc1.pdf")
        self.assertEqual(calc_source["thumbnail_url"], "/media/calc1_thumb.png")
        self.assertEqual(calc_source["hls_url"], "/media/calc1/master.m3u8")


class PwanimateTemplateRenderingTests(TestCase):
    """Test SSR template markup for message actions, clamping, and preview containers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student_template_test",
            email="template_test@pwaninet.local",
            password="testpassword123",
        )
        self.conversation = PwanimateConversation.objects.create(
            user=self.user,
            title="Math and Student Discovery",
        )
        self.user_msg = PwanimateMessage.objects.create(
            conversation=self.conversation,
            role="user",
            content="Who can help with Linear Algebra and $$x^2 + y^2 = r^2$$?",
        )
        person_data = {
            "username": "student_charlie",
            "display_name": "Charlie Student",
            "profile_url": "/users/user/student_charlie/",
            "headline": "Enthusiastic about mathematics and algorithms",
            "academic_level": "Year 2",
            "programme_name": "BSc Computer Science",
            "collaboration_status": "open_to_study_groups",
            "matched_skills": ["Linear Algebra", "Calculus"],
            "matched_interests": ["Machine Learning"],
            "evidence": {"mutual_connections_count": 3},
        }
        self.asst_msg = PwanimateMessage.objects.create(
            conversation=self.conversation,
            role="assistant",
            content="Here are study resources and students:\n\n$$\\int x dx = \\frac{1}{2}x^2 + C$$",
            sources=[
                {
                    "source": "document",
                    "id": "doc-linalg",
                    "title": "Linear Algebra Outline",
                    "url": "/documents/preview/linalg/",
                    "resource_type": "document",
                },
                {
                    "source": "user",
                    "id": "user-charlie",
                    "title": "Charlie Student",
                    "url": "/users/user/student_charlie/",
                    "person": person_data,
                },
            ],
        )

    def test_ssr_message_rows_contain_data_message_id_and_actions(self):
        """SSR rendered conversation detail must include data-message-id and action buttons for both roles."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:conversation_detail", kwargs={"conversation_id": self.conversation.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # User row assertions
        self.assertContains(response, f'data-message-id="{self.user_msg.id}"')
        self.assertContains(response, "pwanimate-user-bubble-wrapper")
        self.assertContains(response, "pwanimate-message-actions user-actions")
        self.assertContains(response, "edit-btn")

        # Assistant row assertions
        self.assertContains(response, f'data-message-id="{self.asst_msg.id}"')
        self.assertContains(response, "pwanimate-message-actions assistant-actions")
        self.assertContains(response, "copy-btn")

        # People card multiline clamping and responsive column
        self.assertContains(response, "col-12 col-xl-6 pwanimate-person-col")
        self.assertContains(response, "pwanimate-line-clamp-2")
        self.assertContains(response, "Charlie Student")

        # Deduplication: Charlie was presented in people cards, so source='user' is omitted from sources list
        self.assertContains(response, "Linear Algebra Outline")
        # In the citations badge area, user-charlie should NOT appear as a citation badge
        self.assertNotContains(response, 'data-source-type="user"')
        self.assertContains(response, 'data-hls-url=""')

    def test_polymorphic_preview_hosts_rendered(self):
        """Both desktop context rail and mobile preview sheet must have polymorphic preview hosts."""
        self.client.force_login(self.user)
        url = reverse("pwanimate:index")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Desktop context rail polymorphic elements
        self.assertContains(response, "desktopPreviewVideo")
        self.assertContains(response, "desktopPreviewImageContainer")
        self.assertContains(response, "desktopPreviewIframe")
        self.assertContains(response, "desktopPreviewSpinner")
        self.assertContains(response, "desktopPreviewDocThumbnail")

        # Mobile preview sheet polymorphic elements
        self.assertContains(response, "previewSheetVideo")
        self.assertContains(response, "previewSheetImageContainer")
        self.assertContains(response, "previewSheetIframe")
        self.assertContains(response, "previewSheetSpinner")
        self.assertContains(response, "previewSheetDocThumbnail")


class PwanimateStaticAssetsTests(SimpleTestCase):
    """Test that all required vendor JS/CSS assets exist locally in the static folder."""

    def test_vendor_assets_exist(self):
        static_dir = os.path.join(settings.BASE_DIR, "static")

        required_files = [
            "vendor/dompurify/purify.min.js",
            "vendor/katex/katex.min.js",
            "vendor/katex/katex.min.css",
            "vendor/prism/prism.min.js",
            "vendor/prism/prism.min.css",
            "vendor/prism/prism-autoloader.min.js",
            "vendor/prism/prism-python.min.js",
            "vendor/prism/prism-sql.min.js",
            "vendor/prism/prism-bash.min.js",
            "vendor/prism/prism-json.min.js",
            "css/pwanimate/pwanimate.css",
            "js/pwanimate/pwanimate-chat.js",
        ]

        for rel_path in required_files:
            abs_path = os.path.join(static_dir, rel_path)
            self.assertTrue(os.path.isfile(abs_path), f"Missing required asset: {rel_path}")
            self.assertGreater(os.path.getsize(abs_path), 0, f"Asset is empty: {rel_path}")

    def test_dynamic_thinking_loader_assets(self):
        """Verify dynamic thinking loader styles, keyframes, and script structures exist."""
        static_dir = os.path.join(settings.BASE_DIR, "static")
        css_path = os.path.join(static_dir, "css/pwanimate/pwanimate.css")
        js_path = os.path.join(static_dir, "js/pwanimate/pwanimate-chat.js")

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        self.assertIn(".pwanimate-thinking-loader", css_content)
        self.assertIn(".pwanimate-thinking-animation", css_content)
        self.assertIn(".pwanimate-thinking-dot", css_content)
        self.assertIn(".pwanimate-thinking-text", css_content)
        self.assertIn("@keyframes pwanimate-thinking-orbit", css_content)
        self.assertIn("@keyframes pwanimate-dot-1", css_content)
        self.assertIn("@keyframes pwanimate-dot-2", css_content)
        self.assertIn("@keyframes pwanimate-dot-3", css_content)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css_content)
        self.assertIn("@media (max-width: 767.98px)", css_content)
        self.assertIn("vertical-align: middle", css_content)

        with open(js_path, "r", encoding="utf-8") as f:
            js_content = f.read()

        self.assertIn("pwanimate-thinking-loader", js_content)
        self.assertIn("pwanimate-thinking-animation", js_content)
        self.assertIn("pwanimate-thinking-text", js_content)
        self.assertIn("getThinkingPhrases", js_content)
        self.assertIn("Devouring the details…", js_content)
        self.assertIn("thinkingTextInterval", js_content)
