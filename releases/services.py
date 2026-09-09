"""
Release service for PwaniNet Release Center.

Contains all business logic for release management.
Views should remain thin and delegate to this service.
"""
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from typing import Optional, Dict, List
from .models import Release, ReleaseItem
from .utils import (
    parse_version,
    increment_version,
    get_next_build_number,
    validate_version,
    format_version_with_channel
)


class ReleaseService:
    """
    Service for managing releases.
    
    All business logic for release operations should be here.
    Views should be thin and delegate to this service.
    """
    
    @staticmethod
    def create_draft(
        title: str,
        summary: str,
        release_type: str,
        release_channel: str = 'STABLE',
        created_by=None,
        minimum_supported_version: Optional[str] = None,
        mandatory_update: bool = False
    ) -> Release:
        """
        Create a new draft release.
        
        Args:
            title: Release title
            summary: Release summary
            release_type: One of 'MAJOR', 'MINOR', 'PATCH', 'HOTFIX'
            release_channel: One of 'DEVELOPMENT', 'ALPHA', 'BETA', 'RELEASE_CANDIDATE', 'STABLE'
            created_by: User who created the release
            minimum_supported_version: Minimum supported version for this release
            mandatory_update: Whether this is a mandatory update
        
        Returns:
            Created Release instance with DRAFT status
        """
        # Get the latest release to determine next version and build
        latest_release = Release.objects.order_by('-build_number').first()
        
        if latest_release:
            next_build = get_next_build_number(latest_release.build_number)
            next_version = increment_version(latest_release.version, release_type)
        else:
            # First release
            next_build = 1
            next_version = '1.0.0'
        
        # Format version with channel if not stable
        if release_channel != 'STABLE':
            next_version = format_version_with_channel(next_version, release_channel)
        
        # Create the release
        release = Release.objects.create(
            version=next_version,
            build_number=next_build,
            release_title=title,
            release_summary=summary,
            release_type=release_type,
            release_channel=release_channel,
            status='DRAFT',
            created_by=created_by,
            minimum_supported_version=minimum_supported_version,
            mandatory_update=mandatory_update,
            environment_snapshot=ReleaseService._capture_environment_snapshot()
        )
        
        return release
    
    @staticmethod
    def publish_release(release: Release, published_by) -> Release:
        """
        Publish a release.
        
        Args:
            release: Release to publish
            published_by: User publishing the release
        
        Returns:
            Updated Release instance
        
        Raises:
            ValueError: If release is not in a publishable state
        """
        if release.status not in ['DRAFT', 'TESTING']:
            raise ValueError(f"Cannot publish release with status: {release.status}")
        
        with transaction.atomic():
            # Update release status and metadata
            release.status = 'PUBLISHED'
            release.published = True
            release.published_by = published_by
            release.published_at = timezone.now()
            release.release_date = timezone.now()
            release.save()
            
            # Invalidate caches
            ReleaseService._invalidate_release_caches()
        
        return release
    
    @staticmethod
    def archive_release(release: Release) -> Release:
        """
        Archive a release.
        
        Args:
            release: Release to archive
        
        Returns:
            Updated Release instance
        
        Raises:
            ValueError: If release is the current release
        """
        if release.is_current_release:
            raise ValueError("Cannot archive the current release")
        
        release.status = 'ARCHIVED'
        release.published = False
        release.save()
        
        # Invalidate caches
        ReleaseService._invalidate_release_caches()
        
        return release
    
    @staticmethod
    def set_current_release(release: Release) -> Release:
        """
        Mark a release as the current release.
        
        Args:
            release: Release to mark as current
        
        Returns:
            Updated Release instance
        """
        if release.status != 'PUBLISHED':
            raise ValueError("Only published releases can be marked as current")
        
        with transaction.atomic():
            # Unset current flag from all releases using save() to trigger signals
            for current_release in Release.objects.filter(is_current_release=True):
                current_release.is_current_release = False
                current_release.save()
            
            # Set current flag on this release using save() to trigger signals
            release.is_current_release = True
            release.save()
        
        return release
    
    @staticmethod
    def ensure_git_release_in_db(target_version: Optional[str] = None, target_build: Optional[int] = None, title: Optional[str] = None, summary: Optional[str] = None) -> Optional[Release]:
        """
        Synchronize the Git/GitHub release version to the database Release model.
        Acts as the bridge between Git/mobile releases and the Django database.

        If a Release record for the target/latest version does not exist,
        it automatically creates one, marks it PUBLISHED, and sets is_current_release=True.
        """
        from pwaninet import version as app_version
        git_ver = target_version or getattr(app_version, 'resolve_latest_version', app_version.resolve_version)()
        git_ver = git_ver.lstrip('v').strip()
        git_build = target_build or app_version.resolve_build_number()

        cache_key = f'release:current_git_release:{git_ver}'
        try:
            cached_release = cache.get(cache_key)
            if cached_release:
                return cached_release
        except Exception:
            pass

        try:
            with transaction.atomic():
                from releases.utils import parse_version
                active_current = Release.objects.filter(is_current_release=True).first()
                should_be_current = True
                if active_current:
                    try:
                        if parse_version(active_current.version) > parse_version(git_ver):
                            should_be_current = False
                    except Exception:
                        pass

                release = Release.objects.filter(version=git_ver).first()
                if not release:
                    # Prevent duplicate build_number unique constraint errors
                    if Release.objects.filter(build_number=git_build).exists():
                        highest_rel = Release.objects.order_by('-build_number').first()
                        git_build = (highest_rel.build_number + 1) if highest_rel else (git_build + 1)

                    # Auto-create release record for this git tag
                    release = Release.objects.create(
                        version=git_ver,
                        build_number=git_build,
                        release_title=title or f"Release {git_ver}",
                        release_summary=summary or f"PwaniNet Release {git_ver}",
                        release_type='PATCH' if git_ver.count('.') == 2 and git_ver.split('.')[-1] != '0' else 'MINOR',
                        status='PUBLISHED',
                        published=True,
                        release_channel='STABLE',
                        is_current_release=should_be_current,
                    )
                    if should_be_current:
                        Release.objects.filter(is_current_release=True).exclude(id=release.id).update(is_current_release=False)
                elif should_be_current and not release.is_current_release:
                    Release.objects.filter(is_current_release=True).exclude(id=release.id).update(is_current_release=False)
                    release.is_current_release = True
                    Release.objects.filter(id=release.id).update(is_current_release=True)

                ReleaseService.invalidate_all_version_caches()

                try:
                    cache.set(cache_key, release, timeout=300)
                except Exception:
                    pass

                return release
        except Exception:
            # If DB is not ready or connection fails, return None gracefully
            return None

    @staticmethod
    def invalidate_all_version_caches():
        """
        Invalidate all application, service worker, and release caches.
        """
        from pwaninet import version as app_version
        if hasattr(app_version, 'clear_version_cache'):
            try:
                app_version.clear_version_cache()
            except Exception:
                pass
        
        try:
            ReleaseService._invalidate_release_caches()
        except Exception:
            pass

    @staticmethod
    def get_current_release() -> Optional[Release]:
        """
        Get the current release matching the active Git release.
        Ensures the Git version exists in the DB, then returns it.
        Falls back to any is_current_release=True if DB sync fails.
        """
        try:
            release = ReleaseService.ensure_git_release_in_db()
            if release:
                return release
            return Release.objects.filter(is_current_release=True).first()
        except Exception:
            return None
    
    @staticmethod
    def get_latest_release() -> Optional[Release]:
        """
        Get the latest published release.
        Looks up published releases ordered by build_number desc.
        If Git / GitHub has a higher release version than the DB,
        automatically synchronizes and returns the newer release.
        Falls back to current release if no published release is found.
        """
        from pwaninet import version as app_version
        from releases.utils import parse_version

        latest_external_ver = getattr(app_version, 'resolve_latest_version', app_version.resolve_version)()
        if latest_external_ver:
            latest_external_ver = latest_external_ver.lstrip('v').strip()

        try:
            latest = Release.objects.filter(
                status='PUBLISHED',
                published=True
            ).order_by('-build_number').first()

            if latest and latest_external_ver:
                if parse_version(latest.version) >= parse_version(latest_external_ver):
                    return latest
        except Exception:
            pass

        # If DB is behind or missing, sync and ensure latest external release
        synced = ReleaseService.ensure_git_release_in_db(target_version=latest_external_ver)
        if synced:
            return synced

        try:
            return Release.objects.filter(status='PUBLISHED', published=True).order_by('-build_number').first()
        except Exception:
            pass
        return ReleaseService.get_current_release()


    @staticmethod
    def get_latest_stable() -> Optional[Release]:
        """
        Get the latest stable release.
        
        Returns:
            Latest stable Release instance or None
        """
        return Release.objects.filter(
            status='PUBLISHED',
            release_channel='STABLE',
            published=True
        ).order_by('-build_number').first()
    
    @staticmethod
    def get_latest_beta() -> Optional[Release]:
        """
        Get the latest beta release.
        
        Returns:
            Latest beta Release instance or None
        """
        return Release.objects.filter(
            status='PUBLISHED',
            release_channel='BETA',
            published=True
        ).order_by('-build_number').first()
    
    @staticmethod
    def get_latest_by_channel(channel: str) -> Optional[Release]:
        """
        Get the latest release for a specific channel.
        
        Args:
            channel: Release channel
        
        Returns:
            Latest Release instance for the channel or None
        """
        return Release.objects.filter(
            status='PUBLISHED',
            release_channel=channel,
            published=True
        ).order_by('-build_number').first()
    
    @staticmethod
    def validate_release(release: Release) -> Dict[str, List[str]]:
        """
        Validate a release before publishing.
        
        Args:
            release: Release to validate
        
        Returns:
            Dictionary with validation errors (empty if valid)
        """
        errors = {}
        
        # Validate version format
        if not validate_version(release.version):
            errors['version'] = ['Invalid version format']
        
        # Validate that version is unique
        if Release.objects.filter(version=release.version).exclude(id=release.id).exists():
            errors['version'] = ['Version already exists']
        
        # Validate build number is unique
        if Release.objects.filter(build_number=release.build_number).exclude(id=release.id).exists():
            errors['build_number'] = ['Build number already exists']
        
        # Validate that build number is higher than previous
        latest_build = Release.objects.order_by('-build_number').first()
        if latest_build and release.build_number <= latest_build.build_number:
            errors['build_number'] = ['Build number must be higher than previous releases']
        
        # Validate release has at least a title and summary
        if not release.release_title:
            errors['release_title'] = ['Title is required']
        
        if not release.release_summary:
            errors['release_summary'] = ['Summary is required']
        
        return errors
    
    @staticmethod
    def generate_next_version(release_type: str, current_version: Optional[str] = None) -> str:
        """
        Generate the next version based on release type.
        
        Args:
            release_type: One of 'MAJOR', 'MINOR', 'PATCH', 'HOTFIX'
            current_version: Current version (if None, uses latest from database)
        
        Returns:
            Next version string
        """
        if current_version is None:
            latest_release = Release.objects.order_by('-build_number').first()
            current_version = latest_release.version if latest_release else '0.0.0'
        
        return increment_version(current_version, release_type)
    
    @staticmethod
    def generate_next_build() -> int:
        """
        Generate the next build number.
        
        Returns:
            Next build number
        """
        latest_release = Release.objects.order_by('-build_number').first()
        if latest_release:
            return get_next_build_number(latest_release.build_number)
        return 1
    
    @staticmethod
    def add_release_item(
        release: Release,
        category: str,
        title: str,
        description: str = '',
        display_order: int = 0
    ) -> ReleaseItem:
        """
        Add an item to a release.
        
        Args:
            release: Release to add item to
            category: Item category
            title: Item title
            description: Item description
            display_order: Display order
        
        Returns:
            Created ReleaseItem instance
        """
        return ReleaseItem.objects.create(
            release=release,
            category=category,
            title=title,
            description=description,
            display_order=display_order
        )
    
    @staticmethod
    def get_release_statistics() -> Dict:
        """
        Get release statistics for dashboard.
        
        Returns:
            Dictionary with release statistics
        """
        total_releases = Release.objects.count()
        draft_releases = Release.objects.filter(status='DRAFT').count()
        published_releases = Release.objects.filter(status='PUBLISHED').count()
        archived_releases = Release.objects.filter(status='ARCHIVED').count()
        
        current_release = ReleaseService.get_current_release()
        latest_stable = ReleaseService.get_latest_stable()
        latest_beta = ReleaseService.get_latest_beta()
        
        return {
            'total_releases': total_releases,
            'draft_releases': draft_releases,
            'published_releases': published_releases,
            'archived_releases': archived_releases,
            'current_version': current_release.version if current_release else None,
            'current_build': current_release.build_number if current_release else None,
            'latest_stable': latest_stable.version if latest_stable else None,
            'latest_beta': latest_beta.version if latest_beta else None,
        }
    
    @staticmethod
    def _capture_environment_snapshot() -> Dict:
        """
        Capture current environment configuration.
        
        Returns:
            Dictionary with environment snapshot
        """
        return {
            'environment': getattr(settings, 'APP_ENVIRONMENT', 'unknown'),
            'debug': settings.DEBUG,
            'allowed_hosts': settings.ALLOWED_HOSTS,
            'database_engine': settings.DATABASES['default']['ENGINE'],
        }
    
    @staticmethod
    def _invalidate_release_caches():
        """Invalidate release-related caches."""
        cache_keys = [
            'releases:latest',
            'releases:history',
            'releases:version_check',
            'releases:current',
        ]
        for key in cache_keys:
            cache.delete(key)
