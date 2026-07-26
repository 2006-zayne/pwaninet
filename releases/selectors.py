"""
Release selectors for PwaniNet Release Center.

Provides reusable query methods for retrieving releases.
Separates query logic from services and views.
"""
from django.db.models import Q, Count, Max
from typing import Optional, List
from .models import Release, ReleaseItem


class ReleaseSelector:
    """
    Selector for Release queries.
    
    Provides reusable query methods for retrieving releases.
    """
    
    @staticmethod
    def all():
        """Get all releases."""
        return Release.objects.all()
    
    @staticmethod
    def published():
        """Get all published releases."""
        return Release.objects.filter(published=True, status='PUBLISHED')
    
    @staticmethod
    def drafts():
        """Get all draft releases."""
        return Release.objects.filter(status='DRAFT')
    
    @staticmethod
    def testing():
        """Get all releases in testing."""
        return Release.objects.filter(status='TESTING')
    
    @staticmethod
    def archived():
        """Get all archived releases."""
        return Release.objects.filter(status='ARCHIVED')
    
    @staticmethod
    def by_status(status: str):
        """Get releases by status."""
        return Release.objects.filter(status=status)
    
    @staticmethod
    def by_channel(channel: str):
        """Get releases by channel."""
        return Release.objects.filter(release_channel=channel)
    
    @staticmethod
    def by_version(version: str) -> Optional[Release]:
        """Get release by version."""
        try:
            return Release.objects.get(version=version)
        except Release.DoesNotExist:
            return None
    
    @staticmethod
    def by_build_number(build_number: int) -> Optional[Release]:
        """Get release by build number."""
        try:
            return Release.objects.get(build_number=build_number)
        except Release.DoesNotExist:
            return None
    
    @staticmethod
    def by_id(release_id: int) -> Optional[Release]:
        """Get release by ID."""
        try:
            return Release.objects.get(id=release_id)
        except Release.DoesNotExist:
            return None
    
    @staticmethod
    def current() -> Optional[Release]:
        """Get the current release."""
        return Release.objects.filter(is_current_release=True).first()
    
    @staticmethod
    def latest() -> Optional[Release]:
        """Get the latest release by build number."""
        return Release.objects.order_by('-build_number').first()
    
    @staticmethod
    def latest_published() -> Optional[Release]:
        """Get the latest published release."""
        return Release.objects.filter(
            published=True,
            status='PUBLISHED'
        ).order_by('-build_number').first()
    
    @staticmethod
    def latest_stable() -> Optional[Release]:
        """Get the latest stable release."""
        return Release.objects.filter(
            published=True,
            status='PUBLISHED',
            release_channel='STABLE'
        ).order_by('-build_number').first()
    
    @staticmethod
    def latest_beta() -> Optional[Release]:
        """Get the latest beta release."""
        return Release.objects.filter(
            published=True,
            status='PUBLISHED',
            release_channel='BETA'
        ).order_by('-build_number').first()
    
    @staticmethod
    def latest_alpha() -> Optional[Release]:
        """Get the latest alpha release."""
        return Release.objects.filter(
            published=True,
            status='PUBLISHED',
            release_channel='ALPHA'
        ).order_by('-build_number').first()
    
    @staticmethod
    def search(query: str):
        """Search releases by title or summary."""
        return Release.objects.filter(
            Q(release_title__icontains=query) |
            Q(release_summary__icontains=query) |
            Q(version__icontains=query)
        )
    
    @staticmethod
    def by_created_by(user):
        """Get releases created by a specific user."""
        return Release.objects.filter(created_by=user)
    
    @staticmethod
    def by_published_by(user):
        """Get releases published by a specific user."""
        return Release.objects.filter(published_by=user)
    
    @staticmethod
    def with_items():
        """Get releases with their items prefetched."""
        return Release.objects.prefetch_related('items')
    
    @staticmethod
    def with_item_count():
        """Get releases annotated with item count."""
        return Release.objects.annotate(
            item_count=Count('items')
        )
    
    @staticmethod
    def recent(limit: int = 10):
        """Get recent releases."""
        return Release.objects.order_by('-created_at')[:limit]
    
    @staticmethod
    def recent_published(limit: int = 10):
        """Get recent published releases."""
        return Release.objects.filter(
            published=True,
            status='PUBLISHED'
        ).order_by('-published_at')[:limit]


class ReleaseItemSelector:
    """
    Selector for ReleaseItem queries.
    """
    
    @staticmethod
    def all():
        """Get all release items."""
        return ReleaseItem.objects.all()
    
    @staticmethod
    def by_release(release: Release):
        """Get items for a specific release."""
        return ReleaseItem.objects.filter(release=release)
    
    @staticmethod
    def by_category(category: str):
        """Get items by category."""
        return ReleaseItem.objects.filter(category=category)
    
    @staticmethod
    def by_id(item_id: int) -> Optional[ReleaseItem]:
        """Get item by ID."""
        try:
            return ReleaseItem.objects.get(id=item_id)
        except ReleaseItem.DoesNotExist:
            return None
    
    @staticmethod
    def ordered():
        """Get items ordered by display order."""
        return ReleaseItem.objects.order_by('display_order', 'category', 'id')
    
    @staticmethod
    def by_release_ordered(release: Release):
        """Get items for a release, ordered."""
        return ReleaseItem.objects.filter(
            release=release
        ).order_by('display_order', 'category', 'id')
