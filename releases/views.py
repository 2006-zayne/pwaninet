from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from .models import Release, ReleaseItem, UserReleaseView
from .serializers import (
    ReleaseSerializer,
    ReleaseListSerializer,
    VersionCheckSerializer,
    UserReleaseViewSerializer
)


class ReleaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Release model.
    Provides endpoints for accessing release information.
    """
    queryset = Release.objects.all()
    serializer_class = ReleaseSerializer
    lookup_field = 'version'
    
    def get_queryset(self):
        """Filter queryset based on published status"""
        queryset = super().get_queryset()
        # Only show published releases by default
        return queryset.filter(published=True)
    
    def get_serializer_class(self):
        """Use different serializers for list vs detail"""
        if self.action == 'list':
            return ReleaseListSerializer
        return ReleaseSerializer
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get the latest published release with full details.
        Endpoint: GET /api/releases/latest/
        """
        cache_key = 'releases:latest'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        latest_release = self.get_queryset().order_by('-build_number').first()
        
        if not latest_release:
            return Response(
                {'error': 'No published releases found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(latest_release)
        data = serializer.data
        
        # Cache for 5 minutes
        cache.set(cache_key, data, timeout=300)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get release history (all published releases).
        Endpoint: GET /api/releases/history/
        """
        cache_key = 'releases:history'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        releases = self.get_queryset().order_by('-build_number')
        serializer = self.get_serializer(releases, many=True)
        data = serializer.data
        
        # Cache for 10 minutes
        cache.set(cache_key, data, timeout=600)
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def version_check(self, request):
        """
        Lightweight endpoint for periodic polling to check for updates.
        Returns current version, latest version, and update status.
        Endpoint: GET /api/releases/version_check/
        """
        # Get current version from pwaninet/version.py
        try:
            from pwaninet import version
            current_version = version.__version__
        except ImportError:
            current_version = '0.0.0'
        
        # Extract build number from version (assuming format like 0.99.07)
        try:
            current_build_number = int(current_version.replace('.', ''))
        except (ValueError, AttributeError):
            current_build_number = 0
        
        # Get latest published release
        cache_key = 'releases:version_check'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        latest_release = self.get_queryset().order_by('-build_number').first()
        
        if not latest_release:
            # No releases published yet
            data = {
                'current_version': current_version,
                'current_build_number': current_build_number,
                'latest_version': current_version,
                'latest_build_number': current_build_number,
                'update_available': False,
                'mandatory_update': False,
                'minimum_supported_version': None,
                'release_date': None,
                'release_title': 'No releases published',
                'release_summary': '',
                'release_url': None
            }
            return Response(data)
        
        # Determine if update is available
        update_available = latest_release.build_number > current_build_number
        
        data = {
            'current_version': current_version,
            'current_build_number': current_build_number,
            'latest_version': latest_release.version,
            'latest_build_number': latest_release.build_number,
            'update_available': update_available,
            'mandatory_update': latest_release.mandatory_update,
            'minimum_supported_version': latest_release.minimum_supported_version,
            'release_date': latest_release.release_date,
            'release_title': latest_release.release_title,
            'release_summary': latest_release.release_summary,
            'release_url': f'/api/releases/{latest_release.version}/'
        }
        
        # Cache for 1 minute (lightweight polling)
        cache.set(cache_key, data, timeout=60)
        
        return Response(data)


class UserReleaseViewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for UserReleaseView model.
    Tracks which releases users have viewed for the "What's New" experience.
    """
    serializer_class = UserReleaseViewSerializer
    
    def get_queryset(self):
        """Filter by current user"""
        if self.request.user.is_authenticated:
            return UserReleaseView.objects.filter(user=self.request.user)
        return UserReleaseView.objects.none()
    
    def perform_create(self, serializer):
        """Auto-set user on creation"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def unviewed(self, request):
        """
        Get releases that the current user hasn't viewed yet.
        Endpoint: GET /api/user-release-views/unviewed/
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get all published releases
        all_releases = Release.objects.filter(published=True).order_by('-build_number')
        
        # Get releases the user has viewed
        viewed_release_ids = UserReleaseView.objects.filter(
            user=request.user
        ).values_list('release_id', flat=True)
        
        # Get unviewed releases
        unviewed_releases = all_releases.exclude(id__in=viewed_release_ids)
        
        serializer = ReleaseListSerializer(unviewed_releases, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_viewed(self, request):
        """
        Mark a release as viewed by the current user.
        Endpoint: POST /api/user-release-views/mark_viewed/
        Body: {"release_id": 123} or {"release_version": "1.0.0"}
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        release_id = request.data.get('release_id')
        release_version = request.data.get('release_version')
        
        if release_id:
            release = get_object_or_404(Release, id=release_id)
        elif release_version:
            release = get_object_or_404(Release, version=release_version)
        else:
            return Response(
                {'error': 'Either release_id or release_version required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or get the user release view
        user_release_view, created = UserReleaseView.objects.get_or_create(
            user=request.user,
            release=release
        )
        
        serializer = self.get_serializer(user_release_view)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
