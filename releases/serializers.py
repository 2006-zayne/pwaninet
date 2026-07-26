from rest_framework import serializers
from .models import Release, ReleaseItem, UserReleaseView


class ReleaseItemSerializer(serializers.ModelSerializer):
    """Serializer for ReleaseItem model"""
    
    class Meta:
        model = ReleaseItem
        fields = ['id', 'category', 'title', 'description', 'display_order']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReleaseSerializer(serializers.ModelSerializer):
    """Serializer for Release model with nested items"""
    items = ReleaseItemSerializer(many=True, read_only=True)
    is_latest = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Release
        fields = [
            'id',
            'version',
            'build_number',
            'release_title',
            'release_summary',
            'release_type',
            'release_date',
            'mandatory_update',
            'published',
            'minimum_supported_version',
            'release_channel',
            'created_at',
            'updated_at',
            'created_by',
            'items',
            'is_latest'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'is_latest']


class ReleaseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for release lists (without nested items)"""
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Release
        fields = [
            'id',
            'version',
            'build_number',
            'release_title',
            'release_summary',
            'release_type',
            'release_date',
            'mandatory_update',
            'published',
            'release_channel',
            'item_count'
        ]
        read_only_fields = ['id', 'release_date']
    
    def get_item_count(self, obj):
        return obj.items.count()


class VersionCheckSerializer(serializers.Serializer):
    """Serializer for version check response"""
    current_version = serializers.CharField(help_text="Current app version from pwaninet/version.py")
    current_build_number = serializers.IntegerField(help_text="Current build number")
    latest_version = serializers.CharField(help_text="Latest published version")
    latest_build_number = serializers.IntegerField(help_text="Latest build number")
    update_available = serializers.BooleanField(help_text="Whether an update is available")
    mandatory_update = serializers.BooleanField(help_text="Whether the update is mandatory")
    minimum_supported_version = serializers.CharField(
        allow_null=True,
        help_text="Minimum supported version"
    )
    release_date = serializers.DateTimeField(help_text="Release date of latest version")
    release_title = serializers.CharField(help_text="Title of latest release")
    release_summary = serializers.CharField(help_text="Summary of latest release")
    release_url = serializers.CharField(help_text="URL to latest release details")


class UserReleaseViewSerializer(serializers.ModelSerializer):
    """Serializer for UserReleaseView model"""
    release_version = serializers.CharField(source='release.version', read_only=True)
    release_title = serializers.CharField(source='release.release_title', read_only=True)

    class Meta:
        model = UserReleaseView
        fields = ['id', 'release', 'release_version', 'release_title', 'viewed_at']
        read_only_fields = ['id', 'viewed_at']


class CreateReleaseSerializer(serializers.Serializer):
    """Serializer for creating releases with automatic version increment"""
    release_type = serializers.ChoiceField(
        choices=['MAJOR', 'MINOR', 'PATCH', 'HOTFIX'],
        help_text="Semantic version increment type"
    )
    release_title = serializers.CharField(max_length=200, help_text="User-friendly title for this release")
    release_summary = serializers.CharField(help_text="Brief summary of this release")
    mandatory_update = serializers.BooleanField(default=False, help_text="Whether this update is mandatory")
    release_channel = serializers.ChoiceField(
        choices=['STABLE', 'BETA', 'ALPHA'],
        default='STABLE',
        help_text="Release channel"
    )
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of release items with category, title, description"
    )
    minimum_supported_version = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="Minimum supported version for this release"
    )
