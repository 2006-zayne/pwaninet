"""Django REST Framework serializers for the Document Repository."""

from rest_framework import serializers
from .models import (
    # Academic Domain
    AcademicYear,
    Semester,
    Faculty,
    School,
    Department,
    Programme,
    AcademicUnit,
    # Document Domain
    Category,
    Tag,
    Document,
    DocumentVersion,
    DocumentFile,
    DocumentAuthor,
    DocumentAcademicUnit,
    # Engagement Domain
    DocumentView,
    DocumentDownload,
    DocumentBookmark,
    DocumentRating,
)


# Academic Domain Serializers

class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = ['id', 'code', 'name', 'start_date', 'end_date', 'is_current']


class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = ['id', 'code', 'name', 'academic_year', 'order']


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = ['id', 'code', 'name', 'description']


class SchoolSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    
    class Meta:
        model = School
        fields = ['id', 'code', 'name', 'faculty', 'faculty_name', 'description']


class DepartmentSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = Department
        fields = ['id', 'code', 'name', 'school', 'school_name', 'description']


class ProgrammeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    
    class Meta:
        model = Programme
        fields = ['id', 'code', 'name', 'department', 'department_name', 'description']


class AcademicUnitSerializer(serializers.ModelSerializer):
    programme_name = serializers.CharField(source='programme.name', read_only=True)
    
    class Meta:
        model = AcademicUnit
        fields = ['id', 'code', 'name', 'programme', 'programme_name', 'credits', 'description']


# Document Domain Serializers

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'code', 'name', 'description', 'icon', 'is_active']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'description', 'usage_count']


class DocumentAuthorSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentAuthor
        fields = ['id', 'user', 'name', 'author_type', 'contribution_notes']
    
    def get_author_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return obj.name


class DocumentFileSerializer(serializers.ModelSerializer):
    size_mb = serializers.ReadOnlyField()
    
    class Meta:
        model = DocumentFile
        fields = [
            'id', 'original_filename', 'mime_type', 'extension',
            'size_bytes', 'size_mb', 'checksum', 'thumbnail_path',
            'preview_path', 'processing_status', 'uploaded_at'
        ]


class DocumentVersionSerializer(serializers.ModelSerializer):
    files = DocumentFileSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'version_number', 'change_notes', 'created_by',
            'created_by_name', 'created_at', 'is_latest', 'files'
        ]


class DocumentAcademicUnitSerializer(serializers.ModelSerializer):
    academic_unit_code = serializers.CharField(source='academic_unit.code', read_only=True)
    academic_unit_name = serializers.CharField(source='academic_unit.name', read_only=True)
    semester_code = serializers.CharField(source='semester.code', read_only=True)
    semester_name = serializers.CharField(source='semester.name', read_only=True)
    academic_year_code = serializers.CharField(source='academic_year.code', read_only=True)
    
    class Meta:
        model = DocumentAcademicUnit
        fields = [
            'id', 'academic_unit', 'academic_unit_code', 'academic_unit_name',
            'semester', 'semester_code', 'semester_name',
            'academic_year', 'academic_year_code', 'is_primary'
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    """Lightweight serializer for document lists."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    primary_unit = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'category_name',
            'category_icon', 'uploaded_by', 'uploaded_by_name', 'uploaded_by_username',
            'visibility', 'status', 'language', 'created_at', 'updated_at',
            'published_at', 'primary_unit', 'view_count', 'download_count'
        ]
    
    def get_primary_unit(self, obj):
        primary = obj.academic_units.filter(is_primary=True).first()
        if primary:
            return {
                'code': primary.academic_unit.code,
                'name': primary.academic_unit.name,
            }
        return None
    
    def get_view_count(self, obj):
        return obj.views.count()
    
    def get_download_count(self, obj):
        return obj.downloads.count()


class DocumentDetailSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    """Detailed serializer for single document view."""
    category = CategorySerializer(read_only=True)
    uploaded_by = serializers.SerializerMethodField()
    academic_units = DocumentAcademicUnitSerializer(many=True, read_only=True)
    tags = TagSerializer(source='document_tags.tag', many=True, read_only=True)
    authors = DocumentAuthorSerializer(many=True, read_only=True)
    latest_version = DocumentVersionSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    view_count = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()
    bookmark_count = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'uploaded_by',
            'visibility', 'status', 'language', 'created_at', 'updated_at',
            'published_at', 'academic_units', 'tags', 'authors', 'latest_version',
            'versions', 'view_count', 'download_count', 'bookmark_count',
            'rating_count', 'average_rating'
        ]
    
    def get_uploaded_by(self, obj):
        return {
            'id': obj.uploaded_by.id,
            'username': obj.uploaded_by.username,
            'full_name': obj.uploaded_by.get_full_name(),
        }
    
    def get_view_count(self, obj):
        return obj.views.count()
    
    def get_download_count(self, obj):
        return obj.downloads.count()
    
    def get_bookmark_count(self, obj):
        return obj.bookmarks.count()
    
    def get_rating_count(self, obj):
        return obj.ratings.count()
    
    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings.exists():
            return sum(r.rating for r in ratings) / len(ratings)
        return None


class DocumentCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="share_id", read_only=True)
    """Serializer for creating documents."""
    tags = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    academic_unit_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    semester_id = serializers.IntegerField(write_only=True)
    academic_year_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'category', 'visibility', 'language',
            'tags', 'academic_unit_ids', 'semester_id', 'academic_year_id',
            'uploaded_by', 'status'
        ]
        read_only_fields = ['id', 'uploaded_by', 'status']
    
    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        academic_unit_ids = validated_data.pop('academic_unit_ids', [])
        semester_id = validated_data.pop('semester_id')
        academic_year_id = validated_data.pop('academic_year_id')
        
        if 'uploaded_by' not in validated_data and 'request' in self.context:
            validated_data['uploaded_by'] = self.context['request'].user
            
        document = Document.objects.create(**validated_data)
        
        # Add academic units
        for unit_id in academic_unit_ids:
            DocumentAcademicUnit.objects.create(
                document=document,
                academic_unit_id=unit_id,
                semester_id=semester_id,
                academic_year_id=academic_year_id,
                is_primary=(unit_id == academic_unit_ids[0]),
            )
        
        # Add tags
        for tag_name in tags:
            tag, _ = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': tag_name.lower().replace(' ', '-')}
            )
            document.document_tags.create(tag=tag)
        
        return document


# Engagement Serializers

class DocumentBookmarkSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = DocumentBookmark
        fields = ['id', 'document', 'document_title', 'notes', 'is_favorite', 'created_at']


class DocumentRatingSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = DocumentRating
        fields = ['id', 'document', 'document_title', 'rating', 'review', 'created_at']
