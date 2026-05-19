#!/usr/bin/env python3
"""
Test script for link preview functionality.
Tests the LinkPreviewService with various URLs.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings')
django.setup()

from messaging.services.link_preview_service import LinkPreviewService
from messaging.models import Message, LinkPreview, Conversation
from users.models import User

def test_url_extraction():
    """Test URL extraction from text."""
    print("\n=== Testing URL Extraction ===")
    
    test_cases = [
        "Check out https://example.com",
        "Visit www.google.com",
        "No links here",
        "Multiple: https://site1.com and https://site2.com",
        "http://old-site.org/path"
    ]
    
    for text in test_cases:
        urls = LinkPreviewService.extract_urls(text)
        print(f"Text: {text}")
        print(f"Extracted URLs: {urls}")
        print()

def test_preview_generation():
    """Test preview generation for sample URLs."""
    print("\n=== Testing Preview Generation ===")
    
    test_urls = [
        "https://github.com",
        "https://www.youtube.com",
        "https://example.com",
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            preview = LinkPreviewService.get_or_create_preview(url)
            print(f"✓ Preview created/retrieved")
            print(f"  Title: {preview.title}")
            print(f"  Description: {preview.description[:100] if preview.description else 'None'}...")
            print(f"  Site Name: {preview.site_name}")
            print(f"  Domain: {preview.domain}")
            print(f"  Has Thumbnail: {preview.has_thumbnail()}")
            print(f"  Has Favicon: {preview.has_favicon()}")
            print(f"  Fetch Failed: {preview.fetch_failed}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")

def test_message_integration():
    """Test link preview generation on message creation."""
    print("\n=== Testing Message Integration ===")
    
    # Get or create test user
    try:
        user = User.objects.first()
        if not user:
            print("✗ No users found. Create a test user first.")
            return
    except Exception as e:
        print(f"✗ Error getting user: {str(e)}")
        return
    
    # Get or create test conversation
    try:
        conversation = Conversation.objects.first()
        if not conversation:
            print("✗ No conversations found. Create a test conversation first.")
            return
    except Exception as e:
        print(f"✗ Error getting conversation: {str(e)}")
        return
    
    # Create test message with URL
    test_message = Message(
        conversation=conversation,
        sender=user,
        content="Check out this cool site: https://github.com"
    )
    test_message.save()
    
    print(f"Created message ID: {test_message.id}")
    print(f"Content: {test_message.content}")
    
    # Generate preview
    try:
        preview = LinkPreviewService.generate_preview_for_message(test_message)
        if preview:
            print(f"✓ Preview generated")
            print(f"  URL: {preview.url}")
            print(f"  Title: {preview.title}")
            print(f"  Has Thumbnail: {preview.has_thumbnail()}")
        else:
            print("✗ No preview generated")
    except Exception as e:
        print(f"✗ Error generating preview: {str(e)}")
    
    # Cleanup
    test_message.delete()

def test_cache_behavior():
    """Test that caching works correctly."""
    print("\n=== Testing Cache Behavior ===")
    
    url = "https://example.com"
    
    # First call - should create new preview
    print(f"First call for {url}")
    preview1 = LinkPreviewService.get_or_create_preview(url)
    print(f"Preview ID: {preview1.id}")
    
    # Second call - should reuse cached preview
    print(f"Second call for {url}")
    preview2 = LinkPreviewService.get_or_create_preview(url)
    print(f"Preview ID: {preview2.id}")
    
    if preview1.id == preview2.id:
        print("✓ Cache working correctly - same preview reused")
    else:
        print("✗ Cache not working - different previews created")

if __name__ == "__main__":
    print("=" * 60)
    print("Link Preview System Test Suite")
    print("=" * 60)
    
    try:
        test_url_extraction()
        test_preview_generation()
        test_message_integration()
        test_cache_behavior()
        
        print("\n" + "=" * 60)
        print("Test Suite Complete")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()
