"""
Context Contract Test Suite for Phase 1.

Tests the new grounding modes, intent categories, and extended ContextPackage/ContextItem structures.
"""

from django.test import SimpleTestCase

from pwanimate.context import (
    GroundingMode,
    IntentCategory,
    AuthorityLevel,
    StudentContext,
    ToolResult,
    ContextItem,
    ContextPackage,
    ContextRequest,
    estimate_tokens,
)


class GroundingModeTestCase(SimpleTestCase):
    """Test GroundingMode enum values and behavior."""

    def test_grounding_mode_none(self):
        mode = GroundingMode.NONE
        self.assertEqual(mode.value, "none")

    def test_grounding_mode_optional(self):
        mode = GroundingMode.OPTIONAL
        self.assertEqual(mode.value, "optional")

    def test_grounding_mode_required(self):
        mode = GroundingMode.REQUIRED
        self.assertEqual(mode.value, "required")

    def test_grounding_mode_explicit_resource(self):
        mode = GroundingMode.EXPLICIT_RESOURCE
        self.assertEqual(mode.value, "explicit_resource")


class IntentCategoryTestCase(SimpleTestCase):
    """Test IntentCategory enum values and behavior."""

    def test_intent_conversational(self):
        intent = IntentCategory.CONVERSATIONAL
        self.assertEqual(intent.value, "conversational")

    def test_intent_general_knowledge(self):
        intent = IntentCategory.GENERAL_KNOWLEDGE
        self.assertEqual(intent.value, "general_knowledge")

    def test_intent_document_analysis(self):
        intent = IntentCategory.DOCUMENT_ANALYSIS
        self.assertEqual(intent.value, "document_analysis")

    def test_intent_pwaninet_knowledge(self):
        intent = IntentCategory.PWANINET_KNOWLEDGE
        self.assertEqual(intent.value, "pwaninet_knowledge")

    def test_intent_personalized_discovery(self):
        intent = IntentCategory.PERSONALIZED_DISCOVERY
        self.assertEqual(intent.value, "personalized_discovery")

    def test_intent_mixed(self):
        intent = IntentCategory.MIXED
        self.assertEqual(intent.value, "mixed")


class AuthorityLevelTestCase(SimpleTestCase):
    """Test AuthorityLevel enum values and behavior."""

    def test_authority_explicit(self):
        level = AuthorityLevel.EXPLICIT
        self.assertEqual(level.value, "explicit")

    def test_authority_platform(self):
        level = AuthorityLevel.PLATFORM
        self.assertEqual(level.value, "platform")

    def test_authority_user_generated(self):
        level = AuthorityLevel.USER_GENERATED
        self.assertEqual(level.value, "user_generated")

    def test_authority_profile(self):
        level = AuthorityLevel.PROFILE
        self.assertEqual(level.value, "profile")


class StudentContextTestCase(SimpleTestCase):
    """Test StudentContext dataclass."""

    def test_empty_student_context(self):
        ctx = StudentContext()
        self.assertFalse(ctx.has_content())
        self.assertEqual(ctx.programme_name, None)
        self.assertEqual(ctx.level, None)
        self.assertEqual(ctx.relevant_interests, [])
        self.assertEqual(ctx.relevant_skills, [])

    def test_populated_student_context(self):
        ctx = StudentContext(
            programme_name="Computer Science",
            level="Year 2",
            relevant_interests=["AI", "Machine Learning"],
            relevant_skills=["Python", "Django"],
            collaboration_status="open_to_projects",
            nickname="Dev",
            tone="friendly",
            response_style="concise",
        )
        self.assertTrue(ctx.has_content())
        self.assertEqual(ctx.programme_name, "Computer Science")
        self.assertEqual(ctx.level, "Year 2")
        self.assertEqual(len(ctx.relevant_interests), 2)
        self.assertEqual(len(ctx.relevant_skills), 2)

    def test_student_context_to_dict(self):
        ctx = StudentContext(
            programme_name="Computer Science",
            relevant_interests=["AI"],
        )
        data = ctx.to_dict()
        self.assertEqual(data["programme_name"], "Computer Science")
        self.assertEqual(data["relevant_interests"], ["AI"])

    def test_student_context_format_context_block(self):
        ctx = StudentContext(
            programme_name="Computer Science",
            level="Year 2",
            relevant_interests=["AI"],
        )
        block = ctx.format_context_block()
        self.assertIn("<student_context>", block)
        self.assertIn("Programme: Computer Science", block)
        self.assertIn("Level: Year 2", block)
        self.assertIn("Interests: AI", block)
        self.assertIn("</student_context>", block)


class ToolResultTestCase(SimpleTestCase):
    """Test ToolResult dataclass."""

    def test_successful_tool_result(self):
        result = ToolResult(
            tool_name="people_discovery",
            success=True,
            data=[{"username": "john", "skills": ["Python"]}],
        )
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "people_discovery")
        self.assertEqual(len(result.data), 1)

    def test_failed_tool_result(self):
        result = ToolResult(
            tool_name="people_discovery",
            success=False,
            metadata={"error": "Rate limit exceeded"},
        )
        self.assertFalse(result.success)
        self.assertEqual(result.metadata["error"], "Rate limit exceeded")

    def test_tool_result_to_dict(self):
        result = ToolResult(
            tool_name="test_tool",
            success=True,
            data="test_data",
        )
        data = result.to_dict()
        self.assertEqual(data["tool_name"], "test_tool")
        self.assertTrue(data["success"])
        self.assertEqual(data["data"], "test_data")


class ContextItemExtensionTestCase(SimpleTestCase):
    """Test extended ContextItem with new fields."""

    def test_context_item_with_defaults(self):
        item = ContextItem(
            source="document",
            object_id=1,
            title="Test Document",
            content="Test content",
        )
        self.assertFalse(item.explicitly_selected)
        self.assertEqual(item.authority_level, AuthorityLevel.USER_GENERATED)
        self.assertEqual(item.citation_metadata, {})

    def test_context_item_explicit_resource(self):
        item = ContextItem(
            source="document",
            object_id=1,
            title="Test Document",
            content="Test content",
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
            citation_metadata={"document_id": 1, "page_number": 5},
        )
        self.assertTrue(item.explicitly_selected)
        self.assertEqual(item.authority_level, AuthorityLevel.EXPLICIT)
        self.assertEqual(item.citation_metadata["document_id"], 1)

    def test_context_item_to_dict_includes_new_fields(self):
        item = ContextItem(
            source="document",
            object_id=1,
            title="Test Document",
            content="Test content",
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        data = item.to_dict()
        self.assertTrue(data["explicitly_selected"])
        self.assertEqual(data["authority_level"], "explicit")

    def test_context_item_format_data_block_includes_new_attributes(self):
        item = ContextItem(
            source="document",
            object_id=1,
            title="Test Document",
            content="Test content",
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        block = item.format_data_block()
        self.assertIn('explicitly_selected="true"', block)
        self.assertIn('authority="explicit"', block)


class ContextPackageExtensionTestCase(SimpleTestCase):
    """Test extended ContextPackage with new fields."""

    def test_context_package_with_defaults(self):
        pkg = ContextPackage(query="test query")
        self.assertEqual(pkg.query, "test query")
        self.assertEqual(pkg.intent, IntentCategory.MIXED)
        self.assertEqual(pkg.grounding_mode, GroundingMode.OPTIONAL)
        self.assertEqual(pkg.explicit_resources, [])
        self.assertEqual(pkg.retrieved_context, [])
        self.assertEqual(pkg.tool_results, [])
        self.assertEqual(pkg.conversation, [])
        self.assertIsNone(pkg.student_context)

    def test_context_package_with_new_fields(self):
        pkg = ContextPackage(
            query="test query",
            intent=IntentCategory.GENERAL_KNOWLEDGE,
            grounding_mode=GroundingMode.NONE,
            student_context=StudentContext(programme_name="CS"),
            explicit_resources=[],
            retrieved_context=[],
            tool_results=[],
            conversation=[],
        )
        self.assertEqual(pkg.intent, IntentCategory.GENERAL_KNOWLEDGE)
        self.assertEqual(pkg.grounding_mode, GroundingMode.NONE)
        self.assertIsNotNone(pkg.student_context)

    def test_context_package_to_dict_includes_new_fields(self):
        pkg = ContextPackage(
            query="test query",
            intent=IntentCategory.DOCUMENT_ANALYSIS,
            grounding_mode=GroundingMode.EXPLICIT_RESOURCE,
            student_context=StudentContext(programme_name="CS"),
        )
        data = pkg.to_dict()
        self.assertEqual(data["intent"], "document_analysis")
        self.assertEqual(data["grounding_mode"], "explicit_resource")
        self.assertIn("student_context", data)

    def test_context_package_format_context_text_with_student_context(self):
        pkg = ContextPackage(
            query="test query",
            student_context=StudentContext(
                programme_name="Computer Science",
                relevant_interests=["AI"],
            ),
        )
        text = pkg.format_context_text()
        self.assertIn("<student_context>", text)
        self.assertIn("Programme: Computer Science", text)

    def test_context_package_format_context_text_with_explicit_resources(self):
        explicit_item = ContextItem(
            source="document",
            object_id=1,
            title="Explicit Doc",
            content="Explicit content",
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        pkg = ContextPackage(
            query="test query",
            explicit_resources=[explicit_item],
        )
        text = pkg.format_context_text()
        self.assertIn("<explicit_resources", text)
        self.assertIn("Explicit Doc", text)

    def test_context_package_format_context_text_with_retrieved_context(self):
        retrieved_item = ContextItem(
            source="document",
            object_id=2,
            title="Retrieved Doc",
            content="Retrieved content",
            authority_level=AuthorityLevel.PLATFORM,
        )
        pkg = ContextPackage(
            query="test query",
            retrieved_context=[retrieved_item],
        )
        text = pkg.format_context_text()
        self.assertIn("<retrieved_context", text)
        self.assertIn("Retrieved Doc", text)

    def test_context_package_get_all_context_items_priority(self):
        explicit_item = ContextItem(
            source="document",
            object_id=1,
            title="Explicit",
            content="Explicit content",
            explicitly_selected=True,
        )
        retrieved_item = ContextItem(
            source="document",
            object_id=2,
            title="Retrieved",
            content="Retrieved content",
        )
        legacy_item = ContextItem(
            source="document",
            object_id=3,
            title="Legacy",
            content="Legacy content",
        )
        pkg = ContextPackage(
            query="test query",
            explicit_resources=[explicit_item],
            retrieved_context=[retrieved_item],
            items=[legacy_item],
        )
        all_items = pkg.get_all_context_items()
        self.assertEqual(len(all_items), 3)
        self.assertEqual(all_items[0].title, "Explicit")
        self.assertEqual(all_items[1].title, "Retrieved")
        self.assertEqual(all_items[2].title, "Legacy")

    def test_context_package_has_content_with_new_fields(self):
        pkg = ContextPackage(
            query="test query",
            student_context=StudentContext(programme_name="CS"),
        )
        self.assertTrue(pkg.has_content())

    def test_context_package_backward_compatibility(self):
        """Test that old ContextPackage usage still works."""
        pkg = ContextPackage(
            query="test query",
            items=[
                ContextItem(
                    source="document",
                    object_id=1,
                    title="Legacy Item",
                    content="Legacy content",
                )
            ],
            user_context=None,
            attachment_context="<attachment>test</attachment>",
        )
        self.assertTrue(pkg.has_content())
        text = pkg.format_context_text()
        self.assertIn("Legacy Item", text)
        self.assertIn("<attachment>", text)


class ContextRequestExtensionTestCase(SimpleTestCase):
    """Test extended ContextRequest with new fields."""

    def test_context_request_with_defaults(self):
        req = ContextRequest(query="test query")
        self.assertEqual(req.query, "test query")
        self.assertEqual(req.intent, IntentCategory.MIXED)
        self.assertEqual(req.grounding_mode, GroundingMode.OPTIONAL)
        self.assertIsNone(req.explicit_resources)
        self.assertIsNone(req.student_context)
        self.assertIsNone(req.conversation)
        self.assertIsNone(req.tool_results)

    def test_context_request_with_new_fields(self):
        req = ContextRequest(
            query="test query",
            intent=IntentCategory.DOCUMENT_ANALYSIS,
            grounding_mode=GroundingMode.EXPLICIT_RESOURCE,
            explicit_resources=[],
            student_context=StudentContext(programme_name="CS"),
            conversation=[],
            tool_results=[],
        )
        self.assertEqual(req.intent, IntentCategory.DOCUMENT_ANALYSIS)
        self.assertEqual(req.grounding_mode, GroundingMode.EXPLICIT_RESOURCE)
        self.assertIsNotNone(req.student_context)

    def test_context_request_get_raw_results_empty(self):
        req = ContextRequest(query="test query")
        results = req.get_raw_results()
        self.assertEqual(results, [])
