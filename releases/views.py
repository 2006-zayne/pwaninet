from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from pwaninet import version
from .models import Release, ReleaseItem, UserReleaseView
from .serializers import (
    ReleaseSerializer,
    ReleaseListSerializer,
    VersionCheckSerializer,
    UserReleaseViewSerializer,
    CreateReleaseSerializer
)


class ReleaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Release model.
    Provides endpoints for accessing release information.
    """
    queryset = Release.objects.all()
    serializer_class = ReleaseSerializer
    lookup_field = 'id'
    
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
        Uses current Release model as source of truth.
        Endpoint: GET /api/releases/version_check/
        """
        from .services import ReleaseService
        
        # Get current release (source of truth)
        current_release = ReleaseService.get_current_release()
        
        if current_release:
            current_version = current_release.version
            current_build_number = current_release.build_number
        else:
            # Fallback to version.py if no current release
            try:
                from pwaninet import version
                current_version = version.__version__
                current_build_number = version.__build_number__
            except ImportError:
                current_version = '0.0.0'
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
            'release_url': f'/system/releases/{latest_release.id}/',
            'is_current': latest_release.is_current_release
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


class VersionAPIView(APIView):
    """
    API endpoint for current application version information.
    Returns version, build, environment, and release date from current Release model.
    This is the single source of truth for version information.
    Endpoint: GET /api/version/
    """
    def get(self, request):
        """Return current version metadata from Release model"""
        from .services import ReleaseService
        
        # Get current release (source of truth)
        current_release = ReleaseService.get_current_release()
        
        if current_release:
            # Get release notes
            release_notes = []
            for item in current_release.items.all().order_by('display_order', 'category'):
                release_notes.append({
                    'category': item.get_category_display(),
                    'title': item.title,
                    'description': item.description,
                })
            
            data = {
                'version': current_release.version,
                'build': current_release.build_number,
                'environment': version.__environment__,  # Still use version.py for environment
                'release_date': current_release.release_date,
                'git_commit': version.__git_commit__,
                'git_branch': version.__git_branch__,
                'release_id': current_release.id,
                'release_title': current_release.release_title,
                'release_summary': current_release.release_summary,
                'release_channel': current_release.get_release_channel_display(),
                'mandatory': current_release.mandatory_update,
                'minimum_supported_version': current_release.minimum_supported_version,
                'release_notes': release_notes,
                'is_current': current_release.is_current_release,
            }
        else:
            # Fallback to version.py if no current release
            data = {
                'version': version.__version__,
                'build': version.__build_number__,
                'environment': version.__environment__,
                'release_date': version.__release_date__,
                'git_commit': version.__git_commit__,
                'git_branch': version.__git_branch__,
                'release_id': None,
                'release_title': None,
                'release_summary': None,
                'release_channel': None,
                'mandatory': False,
                'minimum_supported_version': None,
                'release_notes': [],
                'is_current': False,
            }
        
        return Response(data)


class CreateReleaseView(APIView):
    """
    API endpoint for creating releases with automatic version increment.
    Accepts semantic version type and automatically increments version.
    Also updates pwaninet/version.py with new version.
    Endpoint: POST /api/releases/create/
    """
    def post(self, request):
        """Create a new release with automatic version increment"""
        serializer = CreateReleaseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        release_type = serializer.validated_data['release_type']
        release_title = serializer.validated_data['release_title']
        release_summary = serializer.validated_data['release_summary']
        mandatory_update = serializer.validated_data.get('mandatory_update', False)
        release_channel = serializer.validated_data.get('release_channel', 'STABLE')
        items_data = serializer.validated_data.get('items', [])
        minimum_supported_version = serializer.validated_data.get('minimum_supported_version')

        # Calculate new version
        new_version = self.increment_version(version.__version__, release_type)
        new_build_number = version.__build_number__ + 1

        # Update pwaninet/version.py
        self.update_version_file(new_version, new_build_number)

        # Create release in database
        release = Release.objects.create(
            version=new_version,
            build_number=new_build_number,
            release_title=release_title,
            release_summary=release_summary,
            release_type=release_type,
            release_date=timezone.now(),
            mandatory_update=mandatory_update,
            published=True,
            release_channel=release_channel,
            minimum_supported_version=minimum_supported_version,
            created_by=request.user if request.user.is_authenticated else None
        )

        # Create release items
        for item_data in items_data:
            ReleaseItem.objects.create(
                release=release,
                category=item_data.get('category', 'IMPROVEMENT'),
                title=item_data.get('title', ''),
                description=item_data.get('description', ''),
                display_order=item_data.get('display_order', 0)
            )

        # Clear cache
        cache.delete('releases:latest')
        cache.delete('releases:history')
        cache.delete('releases:version_check')

        return Response({
            'version': new_version,
            'build_number': new_build_number,
            'release_id': release.id,
            'message': 'Release created successfully'
        }, status=status.HTTP_201_CREATED)

    def increment_version(self, current_version, release_type):
        """
        Increment version based on semantic versioning rules.
        Supports formats: X.Y.Z, X.Y.Z-beta.N, X.Y.Z-rc.N, X.Y.Z-alpha.N
        """
        # Remove pre-release tags for calculation
        base_version = current_version.split('-')[0]
        parts = base_version.split('.')

        if len(parts) != 3:
            raise ValueError(f"Invalid version format: {current_version}")

        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if release_type == 'MAJOR':
            major += 1
            minor = 0
            patch = 0
        elif release_type == 'MINOR':
            minor += 1
            patch = 0
        elif release_type == 'PATCH':
            patch += 1
        elif release_type == 'HOTFIX':
            patch += 1
        else:
            raise ValueError(f"Invalid release type: {release_type}")

        # Preserve pre-release tag if it exists
        pre_release_tag = ''
        if '-' in current_version:
            pre_release_tag = current_version.split('-')[1]

        if pre_release_tag:
            return f"{major}.{minor}.{patch}-{pre_release_tag}"
        return f"{major}.{minor}.{patch}"

    def update_version_file(self, new_version, new_build_number):
        """Update pwaninet/version.py with new version and build number"""
        version_file_path = '/home/zayne/projects/pwaninet/pwaninet/version.py'

        with open(version_file_path, 'r') as f:
            content = f.read()

        # Update version
        content = content.replace(
            f'__version__ = "{version.__version__}"',
            f'__version__ = "{new_version}"'
        )

        # Update build number
        content = content.replace(
            f'__build_number__ = {version.__build_number__}',
            f'__build_number__ = {new_build_number}'
        )

        # Update release date
        new_release_date = timezone.now().isoformat() + 'Z'
        content = content.replace(
            f'__release_date__ = "{version.__release_date__}"',
            f'__release_date__ = "{new_release_date}"'
        )

        with open(version_file_path, 'w') as f:
            f.write(content)
