"""
Comprehensive Test Suite for Pwanimate Preferences Foundation (Phase B).

Verifies:
1. Model: strict 1-to-1 relationship, default values, controlled choices, field length validation, cascade deletion.
2. Service: get/create, safe in-memory defaults, idempotent initialization, partial updates, whitespace normalization,
   server-side choice validation, 500-char limit enforcement, cross-user isolation, authorization.
3. Compatibility: existing users without preferences work seamlessly without eager database writes.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from pwanimate.models import (
    PwanimateConversation,
    PwanimatePreferences,
    PwanimateResponseStyle,
    PwanimateTone,
)
from pwanimate.services.preferences import PwanimatePreferenceService

User = get_user_model()


class PwanimatePreferencesModelTests(TestCase):
    """Unit tests for the PwanimatePreferences persistent model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student_alice",
            email="alice@pwaninet.local",
            password="testpassword123",
            first_name="Alice",
            last_name="Student",
        )

    def test_preference_can_be_created_with_defaults(self):
        """Verify clean model creation with expected neutral defaults."""
        pref = PwanimatePreferences.objects.create(user=self.user)
        self.assertEqual(pref.pk, self.user.pk)
        self.assertEqual(pref.user, self.user)
        self.assertEqual(pref.nickname, "")
        self.assertEqual(pref.tone, PwanimateTone.NEUTRAL)
        self.assertEqual(pref.response_style, PwanimateResponseStyle.BALANCED)
        self.assertEqual(pref.personal_instructions, "")
        self.assertIsNotNone(pref.created_at)
        self.assertIsNotNone(pref.updated_at)
        self.assertIn("PwanimatePreferences", str(pref))
        self.assertIn("student_alice", str(pref))

    def test_one_user_cannot_have_two_preference_rows(self):
        """Verify database-level 1-to-1 uniqueness constraint."""
        PwanimatePreferences.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            PwanimatePreferences.objects.create(user=self.user)

    def test_controlled_tone_choices_validation(self):
        """Verify invalid tone values are rejected by model validation."""
        pref = PwanimatePreferences(
            user=self.user,
            tone="invalid_tone",
        )
        with self.assertRaises(ValidationError) as ctx:
            pref.full_clean()
        self.assertIn("tone", ctx.exception.message_dict)

    def test_valid_tone_choices(self):
        """Verify all defined tone choices are accepted."""
        for tone_choice in PwanimateTone.values:
            pref = PwanimatePreferences(
                user=self.user,
                tone=tone_choice,
            )
            pref.full_clean()  # Should not raise

    def test_controlled_response_style_choices_validation(self):
        """Verify invalid response style values are rejected by model validation."""
        pref = PwanimatePreferences(
            user=self.user,
            response_style="unsupported_style",
        )
        with self.assertRaises(ValidationError) as ctx:
            pref.full_clean()
        self.assertIn("response_style", ctx.exception.message_dict)

    def test_valid_response_style_choices(self):
        """Verify all defined response style choices are accepted."""
        for style_choice in PwanimateResponseStyle.values:
            pref = PwanimatePreferences(
                user=self.user,
                response_style=style_choice,
            )
            pref.full_clean()  # Should not raise

    def test_nickname_length_validation(self):
        """Verify 50-character limit on nickname."""
        # 50 chars - OK
        valid_nick = "A" * 50
        pref = PwanimatePreferences(user=self.user, nickname=valid_nick)
        pref.full_clean()

        # 51 chars - ValidationError
        invalid_nick = "A" * 51
        pref_invalid = PwanimatePreferences(user=self.user, nickname=invalid_nick)
        with self.assertRaises(ValidationError) as ctx:
            pref_invalid.full_clean()
        self.assertIn("nickname", ctx.exception.message_dict)

    def test_personal_instructions_maximum_length(self):
        """Verify 500-character limit on personal instructions."""
        # 500 chars - OK
        valid_instructions = "I" * 500
        pref = PwanimatePreferences(user=self.user, personal_instructions=valid_instructions)
        pref.full_clean()

        # 501 chars - ValidationError
        invalid_instructions = "I" * 501
        pref_invalid = PwanimatePreferences(user=self.user, personal_instructions=invalid_instructions)
        with self.assertRaises(ValidationError) as ctx:
            pref_invalid.full_clean()
        self.assertIn("personal_instructions", ctx.exception.message_dict)

    def test_cascade_delete_with_user(self):
        """Verify preferences row is removed when the parent user is deleted."""
        PwanimatePreferences.objects.create(user=self.user)
        self.assertEqual(PwanimatePreferences.objects.count(), 1)
        self.user.delete()
        self.assertEqual(PwanimatePreferences.objects.count(), 0)


class PwanimatePreferenceServiceTests(TestCase):
    """Unit tests for PwanimatePreferenceService operations, validation, and authorization."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="alice",
            email="alice@pwaninet.local",
            password="testpassword123",
        )
        self.user_b = User.objects.create_user(
            username="bob",
            email="bob@pwaninet.local",
            password="testpassword123",
        )

    def test_get_preferences_returns_none_when_uninitialized(self):
        """Verify get_preferences returns None without modifying the database."""
        prefs = PwanimatePreferenceService.get_preferences(self.user_a)
        self.assertIsNone(prefs)
        self.assertEqual(PwanimatePreferences.objects.count(), 0)

    def test_get_preferences_or_defaults_returns_defaults_without_saving(self):
        """Verify get_preferences_or_defaults provides safe fallback without DB write."""
        prefs = PwanimatePreferenceService.get_preferences_or_defaults(self.user_a)
        self.assertIsNotNone(prefs)
        self.assertEqual(prefs.tone, PwanimateTone.NEUTRAL)
        self.assertEqual(prefs.response_style, PwanimateResponseStyle.BALANCED)
        self.assertEqual(prefs.nickname, "")
        self.assertEqual(prefs.personal_instructions, "")
        # Zero DB writes
        self.assertEqual(PwanimatePreferences.objects.count(), 0)

    def test_get_preferences_or_defaults_returns_persisted_when_exists(self):
        """Verify get_preferences_or_defaults returns existing record when present."""
        PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="Ali",
            tone=PwanimateTone.FRIENDLY,
        )
        prefs = PwanimatePreferenceService.get_preferences_or_defaults(self.user_a)
        self.assertEqual(prefs.nickname, "Ali")
        self.assertEqual(prefs.tone, PwanimateTone.FRIENDLY)

    def test_get_or_create_preferences_creates_row(self):
        """Verify get_or_create_preferences safely initializes a persistent row."""
        prefs = PwanimatePreferenceService.get_or_create_preferences(self.user_a)
        self.assertEqual(PwanimatePreferences.objects.count(), 1)
        self.assertEqual(prefs.user, self.user_a)
        self.assertEqual(prefs.tone, PwanimateTone.NEUTRAL)
        self.assertEqual(prefs.response_style, PwanimateResponseStyle.BALANCED)

    def test_get_or_create_preferences_idempotent(self):
        """Verify repeated get_or_create calls do not create duplicates."""
        prefs1 = PwanimatePreferenceService.get_or_create_preferences(self.user_a)
        prefs2 = PwanimatePreferenceService.get_or_create_preferences(self.user_a)
        self.assertEqual(prefs1.pk, prefs2.pk)
        self.assertEqual(PwanimatePreferences.objects.count(), 1)

    def test_update_preferences_all_fields(self):
        """Verify full update of all preference concepts."""
        prefs = PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="Alice W.",
            tone=PwanimateTone.ACADEMIC,
            response_style=PwanimateResponseStyle.DETAILED,
            personal_instructions="Give formal definitions before code.",
        )
        self.assertEqual(prefs.nickname, "Alice W.")
        self.assertEqual(prefs.tone, PwanimateTone.ACADEMIC)
        self.assertEqual(prefs.response_style, PwanimateResponseStyle.DETAILED)
        self.assertEqual(prefs.personal_instructions, "Give formal definitions before code.")

        # Re-fetch to verify persistence
        reloaded = PwanimatePreferenceService.get_preferences(self.user_a)
        self.assertEqual(reloaded.nickname, "Alice W.")
        self.assertEqual(reloaded.tone, PwanimateTone.ACADEMIC)
        self.assertEqual(reloaded.response_style, PwanimateResponseStyle.DETAILED)
        self.assertEqual(reloaded.personal_instructions, "Give formal definitions before code.")

    def test_update_preferences_partial_update(self):
        """Verify partial update leaves unspecified fields unchanged."""
        PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="InitialNick",
            tone=PwanimateTone.FRIENDLY,
            response_style=PwanimateResponseStyle.CONCISE,
            personal_instructions="Explain concisely.",
        )

        # Update only tone
        updated = PwanimatePreferenceService.update_preferences(
            self.user_a,
            tone=PwanimateTone.PROFESSIONAL,
        )
        self.assertEqual(updated.tone, PwanimateTone.PROFESSIONAL)
        self.assertEqual(updated.nickname, "InitialNick")
        self.assertEqual(updated.response_style, PwanimateResponseStyle.CONCISE)
        self.assertEqual(updated.personal_instructions, "Explain concisely.")

    def test_whitespace_normalization(self):
        """Verify surrounding whitespace is trimmed on nickname and personal instructions."""
        prefs = PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="   Trimmed Nick   ",
            personal_instructions="   Keep it practical.   ",
        )
        self.assertEqual(prefs.nickname, "Trimmed Nick")
        self.assertEqual(prefs.personal_instructions, "Keep it practical.")

    def test_whitespace_only_nickname_normalizes_to_empty(self):
        """Verify whitespace-only nickname normalizes to empty string."""
        prefs = PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="     ",
        )
        self.assertEqual(prefs.nickname, "")

    def test_reject_invalid_tone(self):
        """Verify invalid tone raises ValidationError in service."""
        with self.assertRaises(ValidationError) as ctx:
            PwanimatePreferenceService.update_preferences(
                self.user_a,
                tone="pirate",
            )
        self.assertIn("tone", ctx.exception.message_dict)

    def test_reject_invalid_response_style(self):
        """Verify invalid response style raises ValidationError in service."""
        with self.assertRaises(ValidationError) as ctx:
            PwanimatePreferenceService.update_preferences(
                self.user_a,
                response_style="bulleted_only",
            )
        self.assertIn("response_style", ctx.exception.message_dict)

    def test_reject_excessive_instructions(self):
        """Verify instructions exceeding 500 characters raise ValidationError."""
        too_long = "X" * 501
        with self.assertRaises(ValidationError) as ctx:
            PwanimatePreferenceService.update_preferences(
                self.user_a,
                personal_instructions=too_long,
            )
        self.assertIn("personal_instructions", ctx.exception.message_dict)

    def test_cross_user_isolation(self):
        """Verify updates to User A's preferences cannot affect User B."""
        PwanimatePreferenceService.update_preferences(
            self.user_a,
            nickname="Alice A.",
            tone=PwanimateTone.FRIENDLY,
        )
        PwanimatePreferenceService.update_preferences(
            self.user_b,
            nickname="Bob B.",
            tone=PwanimateTone.PROFESSIONAL,
        )

        prefs_a = PwanimatePreferenceService.get_preferences(self.user_a)
        prefs_b = PwanimatePreferenceService.get_preferences(self.user_b)

        self.assertEqual(prefs_a.nickname, "Alice A.")
        self.assertEqual(prefs_a.tone, PwanimateTone.FRIENDLY)
        self.assertEqual(prefs_b.nickname, "Bob B.")
        self.assertEqual(prefs_b.tone, PwanimateTone.PROFESSIONAL)

    def test_unauthenticated_user_rejected(self):
        """Verify None or unauthenticated user raises ValueError."""
        with self.assertRaises(ValueError):
            PwanimatePreferenceService.get_preferences(None)

        with self.assertRaises(ValueError):
            PwanimatePreferenceService.get_or_create_preferences(None)

        with self.assertRaises(ValueError):
            PwanimatePreferenceService.update_preferences(None, tone=PwanimateTone.NEUTRAL)


class PwanimatePreferencesCompatibilityTests(TestCase):
    """Compatibility tests verifying existing Pwanimate systems are unaffected."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="existing_student",
            email="existing@pwaninet.local",
            password="testpassword123",
        )

    def test_existing_user_without_preferences_safely_handled(self):
        """Existing user has no preference row; service provides safe fallback."""
        self.assertFalse(PwanimatePreferences.objects.filter(user=self.user).exists())
        fallback = PwanimatePreferenceService.get_preferences_or_defaults(self.user)
        self.assertEqual(fallback.tone, PwanimateTone.NEUTRAL)
        self.assertEqual(fallback.response_style, PwanimateResponseStyle.BALANCED)
        self.assertEqual(fallback.nickname, "")
        self.assertEqual(fallback.personal_instructions, "")

    def test_creating_preferences_does_not_interfere_with_conversations(self):
        """Verify conversation lifecycle works seamlessly alongside preferences."""
        pref = PwanimatePreferenceService.get_or_create_preferences(self.user)
        conv = PwanimateConversation.objects.create(
            user=self.user,
            title="Bioinformatics Q&A",
        )
        self.assertEqual(conv.user, self.user)
        self.assertEqual(self.user.pwanimate_preferences, pref)
        self.assertEqual(self.user.pwanimate_conversations.count(), 1)
