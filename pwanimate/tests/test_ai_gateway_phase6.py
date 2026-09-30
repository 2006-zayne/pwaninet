"""
AI Gateway Phase 6 Test Suite.

Tests compatibility of new ContextPackage structure with AI Gateway providers.
"""

from django.test import SimpleTestCase

from pwanimate.context import (
    ContextPackage,
    ContextItem,
    GroundingMode,
    IntentCategory,
    AuthorityLevel,
    StudentContext,
)


class ContextPackageGatewayCompatibilityTestCase(SimpleTestCase):
    """Test ContextPackage compatibility with AI Gateway."""

    def test_context_package_has_legacy_fields(self):
        """ContextPackage should have legacy fields for backward compatibility."""
        pkg = ContextPackage(query="test query")
        
        # Legacy fields should exist
        self.assertTrue(hasattr(pkg, 'items'))
        self.assertTrue(hasattr(pkg, 'citations'))
        self.assertTrue(hasattr(pkg, 'total_items'))
        self.assertTrue(hasattr(pkg, 'estimated_tokens'))
        self.assertTrue(hasattr(pkg, 'total_characters'))
        self.assertTrue(hasattr(pkg, 'truncated'))
        self.assertTrue(hasattr(pkg, 'source_counts'))
        self.assertTrue(hasattr(pkg, 'user_context'))
        self.assertTrue(hasattr(pkg, 'attachment_context'))

    def test_context_package_has_new_fields(self):
        """ContextPackage should have new fields for enhanced context."""
        pkg = ContextPackage(query="test query")
        
        # New fields should exist
        self.assertTrue(hasattr(pkg, 'intent'))
        self.assertTrue(hasattr(pkg, 'grounding_mode'))
        self.assertTrue(hasattr(pkg, 'student_context'))
        self.assertTrue(hasattr(pkg, 'explicit_resources'))
        self.assertTrue(hasattr(pkg, 'retrieved_context'))
        self.assertTrue(hasattr(pkg, 'tool_results'))
        self.assertTrue(hasattr(pkg, 'conversation'))
        self.assertTrue(hasattr(pkg, 'metadata'))

    def test_format_context_text_with_legacy_items(self):
        """format_context_text should work with legacy items field."""
        item = ContextItem(
            source="document",
            object_id="doc1",
            title="Test Document",
            content="Test content",
            citation="[Test Doc]",
            url="/documents/doc1/",
            relevance_score=0.9,
            metadata={},
            estimated_tokens=100,
            truncated=False,
        )
        
        pkg = ContextPackage(
            query="test query",
            items=[item],
        )
        
        context_text = pkg.format_context_text()
        self.assertIn("Test content", context_text)
        self.assertIn("<retrieved_context", context_text)
        self.assertIn("</retrieved_context>", context_text)

    def test_format_context_text_with_explicit_resources(self):
        """format_context_text should format explicit resources with XML tags."""
        item = ContextItem(
            source="document",
            object_id="doc1",
            title="Test Document",
            content="Test content",
            citation="[Test Doc]",
            url="/documents/doc1/",
            relevance_score=1.0,
            metadata={},
            estimated_tokens=100,
            truncated=False,
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        
        pkg = ContextPackage(
            query="test query",
            explicit_resources=[item],
        )
        
        context_text = pkg.format_context_text()
        self.assertIn("<explicit_resources", context_text)
        self.assertIn("</explicit_resources>", context_text)
        self.assertIn("Test content", context_text)

    def test_format_context_text_with_retrieved_context(self):
        """format_context_text should format retrieved context with XML tags."""
        item = ContextItem(
            source="document",
            object_id="doc1",
            title="Test Document",
            content="Test content",
            citation="[Test Doc]",
            url="/documents/doc1/",
            relevance_score=0.8,
            metadata={},
            estimated_tokens=100,
            truncated=False,
        )
        
        pkg = ContextPackage(
            query="test query",
            retrieved_context=[item],
        )
        
        context_text = pkg.format_context_text()
        self.assertIn("<retrieved_context", context_text)
        self.assertIn("</retrieved_context>", context_text)
        self.assertIn("Test content", context_text)

    def test_format_context_text_with_student_context(self):
        """format_context_text should format student context with XML tags."""
        student = StudentContext(
            programme_name="Computer Science",
            level="Undergraduate",
            relevant_interests=["AI", "Machine Learning"],
            relevant_skills=["Python", "JavaScript"],
            collaboration_status="Open to collaboration",
        )
        
        pkg = ContextPackage(
            query="test query",
            student_context=student,
        )
        
        context_text = pkg.format_context_text()
        self.assertIn("<student_context>", context_text)
        self.assertIn("</student_context>", context_text)
        self.assertIn("Computer Science", context_text)

    def test_format_context_text_with_all_fields(self):
        """format_context_text should handle all context fields together."""
        # Explicit resource
        explicit_item = ContextItem(
            source="document",
            object_id="doc1",
            title="Explicit Doc",
            content="Explicit content",
            citation="[Explicit]",
            url="/documents/doc1/",
            relevance_score=1.0,
            metadata={},
            estimated_tokens=100,
            truncated=False,
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        
        # Retrieved context
        retrieved_item = ContextItem(
            source="post",
            object_id="post1",
            title="Post",
            content="Post content",
            citation="[Post]",
            url="/posts/post1/",
            relevance_score=0.8,
            metadata={},
            estimated_tokens=50,
            truncated=False,
        )
        
        # Student context
        student = StudentContext(
            programme_name="Computer Science",
            level="Undergraduate",
        )
        
        pkg = ContextPackage(
            query="test query",
            intent=IntentCategory.DOCUMENT_ANALYSIS,
            grounding_mode=GroundingMode.EXPLICIT_RESOURCE,
            explicit_resources=[explicit_item],
            retrieved_context=[retrieved_item],
            student_context=student,
        )
        
        context_text = pkg.format_context_text()
        
        # Should have all sections
        self.assertIn("<student_context>", context_text)
        self.assertIn("</student_context>", context_text)
        self.assertIn("<explicit_resources", context_text)
        self.assertIn("</explicit_resources>", context_text)
        self.assertIn("<retrieved_context", context_text)
        self.assertIn("</retrieved_context>", context_text)
        
        # Explicit should come before retrieved (priority order)
        explicit_pos = context_text.find("<explicit_resources")
        retrieved_pos = context_text.find("<retrieved_context")
        self.assertLess(explicit_pos, retrieved_pos)

    def test_to_dict_serialization(self):
        """to_dict should serialize all fields including new ones."""
        pkg = ContextPackage(
            query="test query",
            intent=IntentCategory.GENERAL_KNOWLEDGE,
            grounding_mode=GroundingMode.NONE,
            metadata={"test": "value"},
        )
        
        data = pkg.to_dict()
        
        # Should have new fields
        self.assertIn("intent", data)
        self.assertIn("grounding_mode", data)
        self.assertIn("metadata", data)
        
        # Should have legacy fields
        self.assertIn("items", data)
        self.assertIn("citations", data)
        self.assertIn("total_items", data)

    def test_get_all_context_items_priority_order(self):
        """get_all_context_items should return items in priority order."""
        explicit_item = ContextItem(
            source="document",
            object_id="doc1",
            title="Explicit",
            content="",
            citation="",
            url="",
            relevance_score=1.0,
            metadata={},
            estimated_tokens=0,
            truncated=False,
            explicitly_selected=True,
            authority_level=AuthorityLevel.EXPLICIT,
        )
        
        retrieved_item = ContextItem(
            source="document",
            object_id="doc2",
            title="Retrieved",
            content="",
            citation="",
            url="",
            relevance_score=0.8,
            metadata={},
            estimated_tokens=0,
            truncated=False,
        )
        
        legacy_item = ContextItem(
            source="document",
            object_id="doc3",
            title="Legacy",
            content="",
            citation="",
            url="",
            relevance_score=0.7,
            metadata={},
            estimated_tokens=0,
            truncated=False,
        )
        
        pkg = ContextPackage(
            query="test query",
            explicit_resources=[explicit_item],
            retrieved_context=[retrieved_item],
            items=[legacy_item],
        )
        
        all_items = pkg.get_all_context_items()
        
        # Should be in priority order: explicit > retrieved > legacy
        self.assertEqual(len(all_items), 3)
        self.assertEqual(all_items[0].title, "Explicit")
        self.assertEqual(all_items[1].title, "Retrieved")
        self.assertEqual(all_items[2].title, "Legacy")

    def test_has_content_with_new_fields(self):
        """has_content should detect content in new fields."""
        # Empty package
        pkg = ContextPackage(query="test query")
        self.assertFalse(pkg.has_content())
        
        # With explicit resources
        pkg = ContextPackage(
            query="test query",
            explicit_resources=[ContextItem(
                source="document",
                object_id="doc1",
                title="Test",
                content="",
                citation="",
                url="",
                relevance_score=1.0,
                metadata={},
                estimated_tokens=0,
                truncated=False,
            )],
        )
        self.assertTrue(pkg.has_content())
        
        # With student context
        pkg = ContextPackage(
            query="test query",
            student_context=StudentContext(programme_name="CS"),
        )
        self.assertTrue(pkg.has_content())
