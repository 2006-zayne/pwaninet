"""
Pwanimate Persistent Study Mode — Comprehensive Automated Test Suite.

Covers all 12 required verification areas across Phases 1–4:
  1. Study session creation via `@study` and via UI/API control.
  2. Rejection of mid-sentence `@study` and `@studybuddy` as mode-activation commands.
  3. Bare `@study` handling without an empty AI call.
  4. Single-active-session enforcement and pausing of previous active session.
  5. Resuming a paused session and handling of any other active session.
  6. Ending a session while preserving conversation history, messages, attachments, and checkpoints.
  7. Cross-user access rejection for sessions, conversations, checkpoints, attachments, documents, and collections.
  8. Checkpoint creation, idempotency, failure handling, and separation of explained vs. demonstrated vs. inferred concepts.
  9. Bounded prompt assembly using recent messages, latest checkpoint, and relevant older context.
 10. Document/page context persistence and restoration, including deleted or unauthorized documents.
 11. Unextracted or empty page/document handling without fabricated content.
 12. Summary generation, export, and saving to an existing or newly created collection with permission checks.
"""

import json
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import (
    Category,
    Collection,
    CollectionItem,
    CollectionShare,
    Document,
    DocumentVersion,
)
from pwanimate.ai.gateway.types import LLMResponse
from pwanimate.api.views import PwanimateChatView
from pwanimate.models import (
    DocumentChunk,
    PwanimateAttachment,
    PwanimateConversation,
    PwanimateMessage,
    PwanimateStudyCheckpoint,
    PwanimateStudySession,
)
from pwanimate.orchestrator.types import OrchestrationResponse
from pwanimate.services.attachment import AttachmentService
from pwanimate.services.conversation import ConversationService
from pwanimate.services.study_session import (
    StudyCollectionService,
    StudySessionService,
    inspect_open_document_availability,
    is_user_authorized_for_document,
    parse_study_command,
)

User = get_user_model()

PDF_MAGIC = b"%PDF-1.4\n%Test PDF\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n" + b"\x00" * 40


def make_mock_orchestrator(answer: str = "Let's explore this concept step by step.") -> MagicMock:
    """Create a mock PwanimateOrchestrator returning a structured OrchestrationResponse."""
    mock_orch = MagicMock()
    resp = OrchestrationResponse(
        answer=answer,
        provider="gemini",
        model="gemini-2.5-flash",
        citations=[],
        sources=[],
        warnings=[],
    )
    mock_orch.run.return_value = resp
    return mock_orch


# ===========================================================================
# 1–3. Command Parsing, Entry Points, & Bare @study Handling
# ===========================================================================


class StudyCommandAndEntryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="study_entry_user",
            email="study_entry@pwaninet.local",
            password="testpassword123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_parse_study_command_recognizes_leading_study_case_insensitive(self):
        parsed = parse_study_command("@study Probability and Statistics")
        self.assertTrue(parsed.is_study_command)
        self.assertFalse(parsed.is_bare_command)
        self.assertEqual(parsed.remainder, "Probability and Statistics")

        parsed_upper = parse_study_command("   @STUDY    Bayes Theorem  ")
        self.assertTrue(parsed_upper.is_study_command)
        self.assertFalse(parsed_upper.is_bare_command)
        self.assertEqual(parsed_upper.remainder, "Bayes Theorem")

        parsed_punct = parse_study_command("@study: Linear Algebra")
        self.assertTrue(parsed_punct.is_study_command)
        self.assertEqual(parsed_punct.remainder, "Linear Algebra")

    def test_parse_study_command_rejects_mid_sentence_and_studybuddy(self):
        mid = parse_study_command("Can you help me @study for my exam tomorrow?")
        self.assertFalse(mid.is_study_command)
        self.assertFalse(mid.is_bare_command)

        buddy = parse_study_command("@studybuddy help me with calculus")
        self.assertFalse(buddy.is_study_command)

        hyphen = parse_study_command("@study-group meeting notes")
        self.assertFalse(hyphen.is_study_command)

        underscore = parse_study_command("@study_mode test")
        self.assertFalse(underscore.is_study_command)

    def test_parse_study_command_recognizes_bare_study(self):
        bare = parse_study_command("  @study  ")
        self.assertTrue(bare.is_study_command)
        self.assertTrue(bare.is_bare_command)
        self.assertEqual(bare.remainder, "")

    def test_bare_study_command_activates_study_mode_without_ai_call(self):
        mock_orch = make_mock_orchestrator()
        with patch.object(PwanimateChatView, "get_orchestrator", return_value=mock_orch):
            response = self.client.post(
                "/api/pwanimate/chat/",
                data=json.dumps({"message": "@study"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data.get("study_mode_activated"))
        self.assertIsNotNone(data.get("study_session"))
        self.assertEqual(data["study_session"]["status"], "active")
        # Must NOT have invoked the AI orchestrator or created empty messages
        mock_orch.run.assert_not_called()
        conv = PwanimateConversation.objects.get(id=data["conversation_id"])
        self.assertEqual(conv.messages.count(), 0)

    def test_chat_creates_study_session_via_leading_study_command(self):
        mock_orch = make_mock_orchestrator("Here is an introduction to eigenvalues.")
        with patch.object(PwanimateChatView, "get_orchestrator", return_value=mock_orch):
            response = self.client.post(
                "/api/pwanimate/chat/",
                data=json.dumps({"message": "@study Eigenvalues and Eigenvectors"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("study_session", data)
        self.assertEqual(data["study_session"]["status"], "active")
        self.assertIn("Eigenvalues", data["study_session"]["learning_objective"])
        mock_orch.run.assert_called_once()
        orch_req = mock_orch.run.call_args[0][0]
        self.assertTrue(orch_req.study_mode)
        self.assertEqual(orch_req.query, "Eigenvalues and Eigenvectors")

    def test_chat_creates_study_session_via_ui_toggle_flag(self):
        mock_orch = make_mock_orchestrator()
        with patch.object(PwanimateChatView, "get_orchestrator", return_value=mock_orch):
            response = self.client.post(
                "/api/pwanimate/chat/",
                data=json.dumps(
                    {
                        "message": "Teach me Organic Chemistry nomenclature",
                        "study_mode": True,
                    }
                ),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsNotNone(data.get("study_session"))
        self.assertEqual(data["study_session"]["status"], "active")

    def test_mid_sentence_study_does_not_activate_study_mode(self):
        mock_orch = make_mock_orchestrator()
        with patch.object(PwanimateChatView, "get_orchestrator", return_value=mock_orch):
            response = self.client.post(
                "/api/pwanimate/chat/",
                data=json.dumps({"message": "Where on campus can I @study quietly?"}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertNotIn("study_session", data)
        self.assertEqual(PwanimateStudySession.objects.filter(user=self.user).count(), 0)


# ===========================================================================
# 4–6. Session Lifecycle, Single-Active Invariant, Resume, & End Preservation
# ===========================================================================


class StudySessionLifecycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="lifecycle_user",
            email="lifecycle@pwaninet.local",
            password="testpassword123",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_single_active_session_pauses_previous_active_session(self):
        s1 = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Master Thermodynamics",
            current_topic="First Law",
        )
        self.assertEqual(s1.status, PwanimateStudySession.STATUS_ACTIVE)

        s2 = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Master Quantum Mechanics",
            current_topic="Wavefunctions",
        )
        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertEqual(s1.status, PwanimateStudySession.STATUS_PAUSED)
        self.assertEqual(s2.status, PwanimateStudySession.STATUS_ACTIVE)

    def test_db_unique_constraint_enforces_at_most_one_active_session_per_user(self):
        s1 = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Session 1",
        )
        conv2 = ConversationService.create_conversation(user=self.user, title="Conv 2")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PwanimateStudySession.objects.create(
                    user=self.user,
                    conversation=conv2,
                    status=PwanimateStudySession.STATUS_ACTIVE,
                )

    def test_resuming_paused_session_pauses_current_active_session(self):
        s1 = StudySessionService.start_or_continue_session(
            user=self.user, learning_objective="Session 1"
        )
        s2 = StudySessionService.start_or_continue_session(
            user=self.user, learning_objective="Session 2"
        )
        s1.refresh_from_db()
        self.assertEqual(s1.status, PwanimateStudySession.STATUS_PAUSED)
        self.assertEqual(s2.status, PwanimateStudySession.STATUS_ACTIVE)

        resp = self.client.post(
            f"/api/pwanimate/study-sessions/{s1.id}/status/",
            data=json.dumps({"action": "resume"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        s1.refresh_from_db()
        s2.refresh_from_db()
        self.assertEqual(s1.status, PwanimateStudySession.STATUS_ACTIVE)
        self.assertEqual(s2.status, PwanimateStudySession.STATUS_PAUSED)

    def test_ending_session_preserves_conversation_messages_attachments_and_checkpoints(self):
        session = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Cell Biology",
            current_topic="Mitosis",
        )
        conv = session.conversation
        u_msg = ConversationService.persist_user_message(
            conversation=conv, content="Mitosis divides somatic cells into two identical daughter cells."
        )
        a_msg = ConversationService.persist_assistant_message(
            conversation=conv, content="Spot on! Let's examine the phases: prophase, metaphase, anaphase, telophase."
        )
        uploaded = SimpleUploadedFile("notes.pdf", PDF_MAGIC, content_type="application/pdf")
        att = AttachmentService.create_attachment(user=self.user, uploaded_file=uploaded)
        AttachmentService.link_attachments_to_message([att], u_msg, conv)

        with patch.object(StudySessionService, "_synthesize_checkpoint_via_llm", return_value=None):
            ckpt = StudySessionService.generate_checkpoint(session=session, force=True)
        self.assertIsNotNone(ckpt)

        resp = self.client.post(
            f"/api/pwanimate/study-sessions/{session.id}/status/",
            data=json.dumps({"action": "end"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertEqual(session.status, PwanimateStudySession.STATUS_COMPLETED)
        self.assertIsNotNone(session.ended_at)

        # Verify all underlying records are preserved intact
        self.assertTrue(PwanimateConversation.objects.filter(id=conv.id).exists())
        self.assertEqual(conv.messages.count(), 2)
        self.assertEqual(conv.attachments.count(), 1)
        self.assertTrue(session.checkpoints.filter(id=ckpt.id).exists())

    def test_resume_banner_dismissal_and_new_activity_reeligibility(self):
        session = StudySessionService.start_or_continue_session(
            user=self.user, learning_objective="Graph Theory"
        )
        self.assertEqual(StudySessionService.get_resumable_session(self.user).id, session.id)

        # Dismiss banner
        StudySessionService.dismiss_resume_banner(self.user, session.id)
        self.assertIsNone(StudySessionService.get_resumable_session(self.user))

        # Subsequent activity makes it eligible again
        session.last_active_at = timezone.now() + timedelta(seconds=10)
        session.save(update_fields=["last_active_at"])
        self.assertEqual(StudySessionService.get_resumable_session(self.user).id, session.id)

    def test_conversation_list_filter_study_only(self):
        normal_conv = ConversationService.create_conversation(user=self.user, title="Normal Chat")
        study_session = StudySessionService.start_or_continue_session(
            user=self.user, learning_objective="Study Chat"
        )
        resp_all = self.client.get("/api/pwanimate/conversations/")
        self.assertEqual(resp_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_all.json()), 2)

        resp_study = self.client.get("/api/pwanimate/conversations/?filter=study")
        self.assertEqual(resp_study.status_code, status.HTTP_200_OK)
        study_list = resp_study.json()
        self.assertEqual(len(study_list), 1)
        self.assertEqual(study_list[0]["id"], str(study_session.conversation_id))
        self.assertIsNotNone(study_list[0]["study_session"])


# ===========================================================================
# 7. Cross-User Access Rejection (Security & Authorization Boundaries)
# ===========================================================================


class CrossUserSecurityTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice_study", email="alice@pwaninet.local", password="password123"
        )
        self.bob = User.objects.create_user(
            username="bob_study", email="bob@pwaninet.local", password="password123"
        )
        self.alice_session = StudySessionService.start_or_continue_session(
            user=self.alice,
            learning_objective="Alice Secret Study",
            current_topic="Cryptography",
        )
        ConversationService.persist_user_message(
            self.alice_session.conversation, "Explain RSA encryption because prime factorization is hard."
        )
        ConversationService.persist_assistant_message(
            self.alice_session.conversation, "RSA relies on the trapdoor difficulty of factoring large semiprimes."
        )
        self.bob_client = APIClient()
        self.bob_client.force_authenticate(user=self.bob)

    def test_cross_user_cannot_access_or_mutate_study_session_endpoints(self):
        sid = self.alice_session.id
        self.assertEqual(
            self.bob_client.get(f"/api/pwanimate/study-sessions/{sid}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.bob_client.patch(
                f"/api/pwanimate/study-sessions/{sid}/",
                data=json.dumps({"learning_objective": "Hacked"}),
                content_type="application/json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.bob_client.post(
                f"/api/pwanimate/study-sessions/{sid}/status/",
                data=json.dumps({"action": "end"}),
                content_type="application/json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.bob_client.post(f"/api/pwanimate/study-sessions/{sid}/checkpoints/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.bob_client.post(f"/api/pwanimate/study-sessions/{sid}/summary/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_cross_user_cannot_chat_with_another_users_study_session_or_conversation(self):
        mock_orch = make_mock_orchestrator()
        with patch.object(PwanimateChatView, "get_orchestrator", return_value=mock_orch):
            resp = self.bob_client.post(
                "/api/pwanimate/chat/",
                data=json.dumps(
                    {
                        "message": "Continue Alice's session",
                        "study_mode": True,
                        "study_session_id": str(self.alice_session.id),
                        "conversation_id": str(self.alice_session.conversation_id),
                    }
                ),
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_orch.run.assert_not_called()


# ===========================================================================
# 8–9. Checkpoints, Anti-Sycophancy Verification, & Bounded Prompt Assembly
# ===========================================================================


class StudyCheckpointAndBoundedContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ckpt_user", email="ckpt@pwaninet.local", password="password123"
        )
        self.session = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Understand Acid-Base Equilibria",
            current_topic="Buffer Solutions",
        )
        self.conv = self.session.conversation

    def test_anti_sycophancy_rejects_agreement_only_messages_from_concepts_demonstrated(self):
        # User 1 only agrees ("ok got it thanks")
        u1 = ConversationService.persist_user_message(self.conv, "ok got it thanks")
        a1 = ConversationService.persist_assistant_message(
            self.conv, "Buffers resist pH change via weak acid/conjugate base pairs."
        )
        # User 2 provides a substantive explanation
        u2 = ConversationService.persist_user_message(
            self.conv,
            "A buffer resists pH changes because adding H+ shifts equilibrium toward the weak acid HA.",
        )
        a2 = ConversationService.persist_assistant_message(
            self.conv, "Exactly right! That is Le Chatelier's principle in action."
        )

        # Simulate an LLM checkpoint response that tries to credit BOTH u1 (agreement) and u2 (substantive)
        fake_llm_checkpoint = {
            "learning_objective": "Understand Acid-Base Equilibria",
            "current_topic": "Buffer Solutions",
            "concepts_explained": ["Henderson-Hasselbalch equation", "Conjugate acid-base pairs"],
            "concepts_demonstrated": [
                {
                    "concept": "Sycophantic false positive on agreement",
                    "evidence_message_id": str(u1.id),
                    "evidence_summary": "Student said ok got it",
                },
                {
                    "concept": "Equilibrium shift upon H+ addition in buffers",
                    "evidence_message_id": str(u2.id),
                    "evidence_summary": "Explained shift toward weak acid HA",
                },
            ],
            "inferred_understanding": ["Familiar with Le Chatelier's principle"],
            "misconceptions": [],
            "key_discoveries": ["Buffers require both weak acid and conjugate base"],
            "recommended_next_step": "Calculate buffer pH using Henderson-Hasselbalch.",
        }

        with patch.object(
            StudySessionService, "_synthesize_checkpoint_via_llm", return_value=fake_llm_checkpoint
        ):
            ckpt = StudySessionService.generate_checkpoint(session=self.session, force=True)

        self.assertIsNotNone(ckpt)
        self.assertEqual(len(ckpt.concepts_demonstrated), 1)
        self.assertEqual(
            ckpt.concepts_demonstrated[0]["concept"],
            "Equilibrium shift upon H+ addition in buffers",
        )
        self.assertEqual(ckpt.concepts_demonstrated[0]["evidence_message_id"], str(u2.id))
        # The rejected agreement-only item must be downgraded to inferred_understanding
        self.assertIn("Sycophantic false positive", ckpt.inferred_understanding)

    def test_checkpoint_idempotency_and_failure_preserves_previous_checkpoint(self):
        u1 = ConversationService.persist_user_message(
            self.conv, "Because buffer capacity depends on molar concentration of HA and A-."
        )
        a1 = ConversationService.persist_assistant_message(
            self.conv, "Correct, higher concentrations yield higher buffer capacity."
        )

        with patch.object(StudySessionService, "_synthesize_checkpoint_via_llm", return_value=None):
            ckpt1 = StudySessionService.generate_checkpoint(session=self.session, force=True)
            ckpt_dup = StudySessionService.generate_checkpoint(session=self.session, force=False)

        self.assertEqual(ckpt1.id, ckpt_dup.id)
        self.assertEqual(self.session.checkpoints.count(), 1)

        # Add another turn and simulate an unexpected exception inside checkpoint synthesis
        ConversationService.persist_user_message(self.conv, "What happens when we dilute a buffer?")
        ConversationService.persist_assistant_message(self.conv, "The pH stays nearly constant, but capacity drops.")

        with patch.object(
            StudySessionService,
            "_synthesize_checkpoint_via_llm",
            side_effect=RuntimeError("Simulated AI provider outage"),
        ):
            # Fallback checkpoint still succeeds or preserves previous without crashing
            ckpt2 = StudySessionService.generate_checkpoint(session=self.session, force=True)

        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.latest_checkpoint)
        self.assertEqual(self.session.latest_checkpoint_id, ckpt2.id)

    def test_bounded_prompt_assembly_includes_recent_window_checkpoint_and_older_excerpts(self):
        # Create 16 messages (8 turns) so messages exist both before and after the recent 8-message window
        for i in range(1, 9):
            ConversationService.persist_user_message(
                self.conv,
                f"Turn {i} question about thermodynamics entropy and enthalpy calculation #{i}?",
            )
            ConversationService.persist_assistant_message(
                self.conv,
                f"Turn {i} detailed explanation of entropy and Gibbs free energy step #{i}.",
            )

        with patch.object(StudySessionService, "_synthesize_checkpoint_via_llm", return_value=None):
            StudySessionService.generate_checkpoint(session=self.session, force=True)
        self.session.refresh_from_db()

        recent_history = StudySessionService.build_bounded_recent_history(self.session, max_messages=8)
        self.assertEqual(len(recent_history), 8)

        orch_ctx = StudySessionService.build_orchestration_context(
            session=self.session,
            user=self.user,
            current_query="Can we revisit turn 1 entropy and enthalpy calculation?",
        )
        prompt_block = orch_ctx.to_prompt_block()
        self.assertIn("[STUDY MODE ACTIVE]", prompt_block)
        self.assertIn("Latest Learning Checkpoint", prompt_block)
        self.assertIn("Relevant Earlier Session Excerpts", prompt_block)
        self.assertLessEqual(len(orch_ctx.older_relevant_excerpts), 3)

        from pwanimate.orchestrator.prompts import (
            STUDY_MODE_ADAPTIVE_TEACHING_ADDENDUM,
            STUDY_MODE_INSTRUCTION_ADDENDUM,
        )
        from pwanimate.orchestrator.service import PwanimateOrchestrator
        from pwanimate.orchestrator.types import OrchestrationRequest

        orch = PwanimateOrchestrator()
        req = OrchestrationRequest(
            query="Can we revisit turn 1 entropy and enthalpy calculation?",
            user=self.user,
            study_mode=True,
            study_context=orch_ctx,
        )
        _pkg, sys_inst = orch._apply_study_and_warning_context(
            request=req,
            query=req.query,
            context_pkg=None,
            system_instruction="BASE",
            source_warnings=[],
        )
        self.assertIn(STUDY_MODE_INSTRUCTION_ADDENDUM, sys_inst)
        self.assertIn(STUDY_MODE_ADAPTIVE_TEACHING_ADDENDUM, sys_inst)
        self.assertIn("ADAPTIVE TEACHING AND STUDENT-CENTERED LEARNING:", sys_inst)


# ===========================================================================
# 10–11. Document/Page Context Persistence, Deleted/Unauthorized Docs, & Empty/Unextracted Pages
# ===========================================================================


class StudyDocumentContextAndExtractionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="doc_study_user", email="doc_study@pwaninet.local", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="other_doc_user", email="other_doc@pwaninet.local", password="password123"
        )
        self.category = Category.objects.create(code="lecture_notes", name="Lecture Notes")
        self.public_doc = Document.objects.create(
            title="Introduction to Algorithms",
            slug="intro-to-algorithms",
            category=self.category,
            visibility="public",
            status="ready",
            is_available=True,
            uploaded_by=self.other_user,
        )
        self.private_other_doc = Document.objects.create(
            title="Secret Exam Paper",
            slug="secret-exam-paper",
            category=self.category,
            visibility="private",
            status="ready",
            is_available=True,
            uploaded_by=self.other_user,
        )
        self.session = StudySessionService.start_or_continue_session(
            user=self.user,
            learning_objective="Master Dynamic Programming",
            current_topic="Bellman-Ford",
        )

    def test_document_and_page_context_persistence_and_restoration_filters_unauthorized_and_deleted(self):
        deleted_doc_id = 999999
        context_resources = [
            {
                "documentId": self.public_doc.id,
                "documentShareId": str(self.public_doc.share_id),
                "title": self.public_doc.title,
                "previewType": "document",
                "fileType": "pdf",
                "pageNumber": 42,
                "totalPages": 120,
            },
            # Attempt to inject another user's private document into context_resources
            {
                "documentId": self.private_other_doc.id,
                "title": self.private_other_doc.title,
                "previewType": "document",
                "pageNumber": 5,
            },
        ]
        state = StudySessionService.sync_context_state(
            self.session, self.user, context_resources, active_index=0
        )
        # Only the authorized public_doc should be persisted
        self.assertEqual(len(state["resources"]), 1)
        self.assertEqual(state["resources"][0]["documentId"], str(self.public_doc.id))
        self.assertEqual(state["resources"][0]["pageNumber"], 42)
        self.assertEqual(state["active_document"]["page_number"], 42)

        # Now simulate a previously persisted document that later became unavailable/deleted
        self.session.context_state["resources"].append(
            {
                "documentId": str(deleted_doc_id),
                "title": "Deleted Lecture Slides",
                "previewType": "document",
                "pageNumber": 7,
            }
        )
        self.session.save(update_fields=["context_state"])

        restored = StudySessionService.restore_context_state(self.session, self.user)
        self.assertEqual(len(restored["resources"]), 1)
        self.assertEqual(restored["resources"][0]["pageNumber"], 42)
        self.assertEqual(len(restored["unavailable_notices"]), 1)
        self.assertIn("Deleted Lecture Slides", restored["unavailable_notices"][0])

    def test_unextracted_document_and_empty_page_return_explicit_warnings_without_fabrication(self):
        # 1. Public doc currently has 0 DocumentChunks -> should warn that no text is indexed
        warnings_no_chunks = inspect_open_document_availability(
            user=self.user,
            context_resources=[
                {
                    "documentId": self.public_doc.id,
                    "title": self.public_doc.title,
                    "pageNumber": 10,
                }
            ],
        )
        self.assertEqual(len(warnings_no_chunks), 1)
        self.assertIn("no indexed or extractable text", warnings_no_chunks[0])

        # 2. Add a chunk on page 1, then view page 15 (which has 0 chunks)
        ver = DocumentVersion.objects.create(
            document=self.public_doc,
            version_number=1,
            created_by=self.other_user,
            is_latest=True,
        )
        DocumentChunk.objects.create(
            document=self.public_doc,
            document_version=ver,
            chunk_index=0,
            page_number=1,
            section_heading="Chapter 1",
            content="Dynamic programming solves subproblems once and memoizes their results.",
            is_active=True,
        )
        warnings_empty_page = inspect_open_document_availability(
            user=self.user,
            context_resources=[
                {
                    "documentId": self.public_doc.id,
                    "title": self.public_doc.title,
                    "pageNumber": 15,
                }
            ],
        )
        self.assertEqual(len(warnings_empty_page), 1)
        self.assertIn("Page 15", warnings_empty_page[0])
        self.assertIn("no extractable text", warnings_empty_page[0])

        # 3. Viewing page 1 (which HAS extracted text) produces 0 warnings
        warnings_valid_page = inspect_open_document_availability(
            user=self.user,
            context_resources=[
                {
                    "documentId": self.public_doc.id,
                    "title": self.public_doc.title,
                    "pageNumber": 1,
                }
            ],
        )
        self.assertEqual(len(warnings_valid_page), 0)


# ===========================================================================
# 12. Summary Generation, Editing, Export, & Saving to Collections
# ===========================================================================


class StudySummaryAndCollectionIntegrationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="col_owner", email="col_owner@pwaninet.local", password="password123"
        )
        self.editor = User.objects.create_user(
            username="col_editor", email="col_editor@pwaninet.local", password="password123"
        )
        self.viewer = User.objects.create_user(
            username="col_viewer", email="col_viewer@pwaninet.local", password="password123"
        )
        self.stranger = User.objects.create_user(
            username="col_stranger", email="col_stranger@pwaninet.local", password="password123"
        )

        self.session = StudySessionService.start_or_continue_session(
            user=self.owner,
            learning_objective="Understand Fourier Transforms",
            current_topic="Discrete Fourier Transform (DFT)",
        )
        ConversationService.persist_user_message(
            self.session.conversation,
            "The DFT decomposes a finite discrete signal into its constituent frequency components.",
        )
        ConversationService.persist_assistant_message(
            self.session.conversation,
            "Yes! And the Fast Fourier Transform (FFT) computes the DFT in O(N log N) operations.",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_generate_edit_and_save_summary_to_new_and_existing_collection(self):
        # 1. Generate summary via API (using deterministic fallback when LLM is mocked out)
        with patch.object(StudySessionService, "_synthesize_checkpoint_via_llm", return_value=None):
            with patch("pwanimate.ai.gateway.AIGateway.generate", side_effect=RuntimeError("Use fallback")):
                gen_resp = self.client.post(
                    f"/api/pwanimate/study-sessions/{self.session.id}/summary/"
                )
        self.assertEqual(gen_resp.status_code, status.HTTP_201_CREATED)
        summary_data = gen_resp.json()["summary"]
        summary_msg_id = summary_data["message_id"]
        self.assertIn("Learning Objective & Scope", summary_data["content"])
        self.assertIn("Verified Student Progress", summary_data["content"])

        # 2. Edit/review the summary markdown via PATCH
        edited_markdown = summary_data["content"] + "\n\n### Personal Review Note\nRemember Cooley-Tukey radix-2."
        edit_resp = self.client.patch(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/",
            data=json.dumps({"message_id": summary_msg_id, "content": edited_markdown}),
            content_type="application/json",
        )
        self.assertEqual(edit_resp.status_code, status.HTTP_200_OK)
        self.assertIn("Cooley-Tukey radix-2", edit_resp.json()["summary"]["content"])

        # 3. Save summary to a newly created collection (PDF format)
        save_new_resp = self.client.post(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/save-to-collection/",
            data=json.dumps(
                {
                    "message_id": summary_msg_id,
                    "new_collection_name": "Signal Processing Revision",
                    "format": "pdf",
                    "notes": "Midterm review sheet",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(save_new_resp.status_code, status.HTTP_201_CREATED)
        saved_payload = save_new_resp.json()
        self.assertTrue(saved_payload["collection"]["created"])
        self.assertEqual(saved_payload["collection"]["visibility"], "private")
        self.assertEqual(saved_payload["document"]["visibility"], "private")
        col_id = saved_payload["collection"]["id"]
        doc_id = saved_payload["document"]["id"]

        # 4. Saving the same summary to the same collection again is idempotent (no duplicate Document or CollectionItem)
        save_again_resp = self.client.post(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/save-to-collection/",
            data=json.dumps(
                {
                    "message_id": summary_msg_id,
                    "collection_id": col_id,
                    "format": "pdf",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(save_again_resp.status_code, status.HTTP_200_OK)
        again_payload = save_again_resp.json()
        self.assertFalse(again_payload["collection_item"]["created"])
        self.assertFalse(again_payload["document"]["created"])
        self.assertEqual(again_payload["document"]["id"], doc_id)
        self.assertEqual(CollectionItem.objects.filter(collection_id=col_id).count(), 1)

    def test_collection_permission_enforcement_for_shared_and_unauthorized_collections(self):
        with patch.object(StudySessionService, "_synthesize_checkpoint_via_llm", return_value=None):
            with patch("pwanimate.ai.gateway.AIGateway.generate", side_effect=RuntimeError("Use fallback")):
                _, summary_msg = StudySessionService.generate_session_summary(self.session, self.owner)

        # Collection owned by stranger (not shared with owner) -> must be rejected
        stranger_col = StudyCollectionService.create_collection(
            user=self.stranger, name="Stranger Private Collection"
        )
        resp_forbidden = self.client.post(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/save-to-collection/",
            data=json.dumps(
                {
                    "message_id": summary_msg.id,
                    "collection_id": stranger_col.id,
                    "format": "pdf",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Collection shared with owner with can_edit=False -> must be rejected
        CollectionShare.objects.create(
            collection=stranger_col,
            shared_with=self.owner,
            shared_by=self.stranger,
            can_edit=False,
        )
        resp_read_only = self.client.post(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/save-to-collection/",
            data=json.dumps(
                {
                    "message_id": summary_msg.id,
                    "collection_id": stranger_col.id,
                    "format": "pdf",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp_read_only.status_code, status.HTTP_403_FORBIDDEN)

        # Upgrade share to can_edit=True -> now allowed!
        CollectionShare.objects.filter(collection=stranger_col, shared_with=self.owner).update(
            can_edit=True
        )
        resp_editable = self.client.post(
            f"/api/pwanimate/study-sessions/{self.session.id}/summary/save-to-collection/",
            data=json.dumps(
                {
                    "message_id": summary_msg.id,
                    "collection_id": stranger_col.id,
                    "format": "docx",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp_editable.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_editable.json()["document"]["format"], "docx")
        self.assertEqual(resp_editable.json()["document"]["visibility"], "private")

    def test_ui_view_renders_non_study_and_study_conversations_without_template_errors(self):
        self.client.force_login(self.owner)
        regular_conv = ConversationService.create_conversation(
            user=self.owner, title="Regular Non-Study Chat"
        )
        ConversationService.persist_user_message(regular_conv, "Hello Pwanimate")
        ConversationService.persist_assistant_message(
            regular_conv,
            "Hi! Here is a reference.",
            sources=[{"source": "document", "title": "Course Outline", "url": "/documents/1/"}],
        )

        # Render non-study conversation (active_study_session is None)
        resp_regular = self.client.get(f"/pwanimate/{regular_conv.id}/")
        self.assertEqual(resp_regular.status_code, status.HTTP_200_OK)

        # Render study conversation (active_study_session is present)
        resp_study = self.client.get(f"/pwanimate/{self.session.conversation_id}/")
        self.assertEqual(resp_study.status_code, status.HTTP_200_OK)

