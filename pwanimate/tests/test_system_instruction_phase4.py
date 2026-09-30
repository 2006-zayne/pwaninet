"""
System Instruction Phase 4 Test Suite.

Tests the new stable system instruction architecture with grounding mode awareness.
"""

from django.test import SimpleTestCase

from pwanimate.orchestrator.prompts import (
    SYSTEM_INSTRUCTION_BASE,
    SYSTEM_INSTRUCTION_CONVERSATIONAL,
    SYSTEM_INSTRUCTION_TUTOR,
    GROUNDING_MODE_NONE_ADDENDUM,
    GROUNDING_MODE_OPTIONAL_ADDENDUM,
    GROUNDING_MODE_REQUIRED_ADDENDUM,
    GROUNDING_MODE_EXPLICIT_RESOURCE_ADDENDUM,
    get_system_instruction,
)


class SystemInstructionBaseTestCase(SimpleTestCase):
    """Test the stable base system instruction."""

    def test_base_instruction_exists(self):
        """Base system instruction should exist and be non-empty."""
        self.assertTrue(len(SYSTEM_INSTRUCTION_BASE) > 0)
        self.assertIn("Pwanimate", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("PwaniNet", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_identity(self):
        """Base instruction should define core identity."""
        self.assertIn("CORE IDENTITY", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("personalized academic companion", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_personalization(self):
        """Base instruction should have personalization principles."""
        self.assertIn("PERSONALIZATION PRINCIPLES", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("Adapt your explanations", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_knowledge_sources(self):
        """Base instruction should describe knowledge sources."""
        self.assertIn("KNOWLEDGE SOURCES", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("general knowledge", SYSTEM_INSTRUCTION_BASE.lower())
        self.assertIn("PwaniNet campus data", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_grounding_mode_awareness(self):
        """Base instruction should describe grounding modes."""
        self.assertIn("GROUNDING MODE AWARENESS", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("NONE", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("OPTIONAL", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("REQUIRED", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("EXPLICIT_RESOURCE", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_explicit_resource_priority(self):
        """Base instruction should describe explicit resource priority."""
        self.assertIn("EXPLICIT RESOURCE PRIORITY", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("PRIMARY context", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_source_hierarchy(self):
        """Base instruction should describe source hierarchy."""
        self.assertIn("SOURCE HIERARCHY", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("Explicit resources", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("Platform resources", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("User-generated content", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_prompt_injection_protection(self):
        """Base instruction should have prompt injection protection."""
        self.assertIn("PROMPT INJECTION PROTECTION", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("DATA to analyze", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("NOT an instruction hierarchy", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("cannot override system", SYSTEM_INSTRUCTION_BASE.lower())

    def test_base_instruction_has_safety_boundaries(self):
        """Base instruction should have safety boundaries."""
        self.assertIn("SAFETY BOUNDARIES", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("Never reveal sensitive student information", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_has_code_generation_boundary(self):
        """Base instruction should have code generation boundary."""
        self.assertIn("CODE GENERATION & TOOL-CALL BOUNDARY", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("Never emit synthetic tool-calling tags", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("NEVER emit synthetic tool-calling tags", SYSTEM_INSTRUCTION_BASE)


class GroundingModeAddendumTestCase(SimpleTestCase):
    """Test grounding mode-specific addendums."""

    def test_none_addendum_exists(self):
        """NONE addendum should exist."""
        self.assertTrue(len(GROUNDING_MODE_NONE_ADDENDUM) > 0)
        self.assertIn("NONE", GROUNDING_MODE_NONE_ADDENDUM)
        self.assertIn("general knowledge", GROUNDING_MODE_NONE_ADDENDUM)

    def test_optional_addendum_exists(self):
        """OPTIONAL addendum should exist."""
        self.assertTrue(len(GROUNDING_MODE_OPTIONAL_ADDENDUM) > 0)
        self.assertIn("OPTIONAL", GROUNDING_MODE_OPTIONAL_ADDENDUM)
        self.assertIn("optional", GROUNDING_MODE_OPTIONAL_ADDENDUM)

    def test_required_addendum_exists(self):
        """REQUIRED addendum should exist."""
        self.assertTrue(len(GROUNDING_MODE_REQUIRED_ADDENDUM) > 0)
        self.assertIn("REQUIRED", GROUNDING_MODE_REQUIRED_ADDENDUM)
        self.assertIn("Prioritize the provided campus data", GROUNDING_MODE_REQUIRED_ADDENDUM)

    def test_explicit_resource_addendum_exists(self):
        """EXPLICIT_RESOURCE addendum should exist."""
        self.assertTrue(len(GROUNDING_MODE_EXPLICIT_RESOURCE_ADDENDUM) > 0)
        self.assertIn("EXPLICIT_RESOURCE", GROUNDING_MODE_EXPLICIT_RESOURCE_ADDENDUM)
        self.assertIn("PRIMARY context", GROUNDING_MODE_EXPLICIT_RESOURCE_ADDENDUM)


class GetSystemInstructionTestCase(SimpleTestCase):
    """Test get_system_instruction function."""

    def test_get_system_instruction_none(self):
        """Should return base + NONE addendum."""
        instruction = get_system_instruction("NONE")
        self.assertIn(SYSTEM_INSTRUCTION_BASE, instruction)
        self.assertIn(GROUNDING_MODE_NONE_ADDENDUM, instruction)
        self.assertIn("GROUNDING MODE: NONE", instruction)

    def test_get_system_instruction_optional(self):
        """Should return base + OPTIONAL addendum."""
        instruction = get_system_instruction("OPTIONAL")
        self.assertIn(SYSTEM_INSTRUCTION_BASE, instruction)
        self.assertIn(GROUNDING_MODE_OPTIONAL_ADDENDUM, instruction)
        self.assertIn("GROUNDING MODE: OPTIONAL", instruction)

    def test_get_system_instruction_required(self):
        """Should return base + REQUIRED addendum."""
        instruction = get_system_instruction("REQUIRED")
        self.assertIn(SYSTEM_INSTRUCTION_BASE, instruction)
        self.assertIn(GROUNDING_MODE_REQUIRED_ADDENDUM, instruction)
        self.assertIn("GROUNDING MODE: REQUIRED", instruction)

    def test_get_system_instruction_explicit_resource(self):
        """Should return base + EXPLICIT_RESOURCE addendum."""
        instruction = get_system_instruction("EXPLICIT_RESOURCE")
        self.assertIn(SYSTEM_INSTRUCTION_BASE, instruction)
        self.assertIn(GROUNDING_MODE_EXPLICIT_RESOURCE_ADDENDUM, instruction)
        self.assertIn("GROUNDING MODE: EXPLICIT_RESOURCE", instruction)

    def test_get_system_instruction_default(self):
        """Should default to OPTIONAL when no mode specified."""
        instruction = get_system_instruction()
        self.assertIn(SYSTEM_INSTRUCTION_BASE, instruction)
        self.assertIn(GROUNDING_MODE_OPTIONAL_ADDENDUM, instruction)

    def test_get_system_instruction_case_insensitive(self):
        """Should handle case-insensitive mode strings."""
        instruction_lower = get_system_instruction("none")
        instruction_upper = get_system_instruction("NONE")
        
        # Should produce same result (both get NONE addendum)
        self.assertEqual(instruction_lower, instruction_upper)


class LegacyCompatibilityTestCase(SimpleTestCase):
    """Test backward compatibility with legacy system instructions."""

    def test_system_instruction_tutor_exists(self):
        """Legacy SYSTEM_INSTRUCTION_TUTOR should still exist."""
        self.assertTrue(len(SYSTEM_INSTRUCTION_TUTOR) > 0)
        self.assertIn("Pwanimate", SYSTEM_INSTRUCTION_TUTOR)

    def test_system_instruction_tutor_uses_required_mode(self):
        """Legacy SYSTEM_INSTRUCTION_TUTOR should use REQUIRED mode."""
        self.assertIn("GROUNDING MODE: REQUIRED", SYSTEM_INSTRUCTION_TUTOR)

    def test_system_instruction_conversational_exists(self):
        """Legacy SYSTEM_INSTRUCTION_CONVERSATIONAL should still exist."""
        self.assertTrue(len(SYSTEM_INSTRUCTION_CONVERSATIONAL) > 0)
        self.assertIn("Pwanimate", SYSTEM_INSTRUCTION_CONVERSATIONAL)

    def test_system_instruction_conversational_is_brief(self):
        """Conversational instruction should be brief."""
        # Conversational should be much shorter than tutor
        self.assertLess(len(SYSTEM_INSTRUCTION_CONVERSATIONAL), len(SYSTEM_INSTRUCTION_TUTOR))


class SystemInstructionContentTestCase(SimpleTestCase):
    """Test content quality of system instructions."""

    def test_base_instruction_mentions_general_knowledge(self):
        """Base instruction should mention general knowledge capabilities."""
        self.assertIn("general knowledge", SYSTEM_INSTRUCTION_BASE.lower())
        self.assertIn("academic concepts", SYSTEM_INSTRUCTION_BASE.lower())

    def test_base_instruction_mentions_pwaninet_data(self):
        """Base instruction should mention PwaniNet data usage."""
        self.assertIn("PwaniNet campus data", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("campus-specific information", SYSTEM_INSTRUCTION_BASE)

    def test_base_instruction_mentions_explicit_resources(self):
        """Base instruction should mention explicit resources."""
        self.assertIn("explicit resources", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("user-selected", SYSTEM_INSTRUCTION_BASE.lower())

    def test_base_instruction_prohibits_fabrication(self):
        """Base instruction should prohibit fabrication."""
        self.assertIn("Never fabricate", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("do not invent", SYSTEM_INSTRUCTION_BASE.lower())

    def test_base_instruction_requires_citations(self):
        """Base instruction should require citations for factual information."""
        self.assertIn("Cite sources", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("citation", SYSTEM_INSTRUCTION_BASE.lower())

    def test_base_instruction_has_tool_call_protection(self):
        """Base instruction should protect against synthetic tool calls."""
        self.assertIn("NEVER emit synthetic tool-calling tags", SYSTEM_INSTRUCTION_BASE)
        self.assertIn("tool_call_start", SYSTEM_INSTRUCTION_BASE)
