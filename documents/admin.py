"""Admin interface configuration for Document Repository models."""

from django.contrib import admin
from .models import (
    # Academic Domain
    AcademicYear,
    Semester,
    AcademicLevel,
    Faculty,
    School,
    Department,
    Programme,
    AcademicUnit,
    ProgrammeUnit,
    # Document Domain
    Category,
    Tag,
    Document,
    DocumentVersion,
    DocumentFile,
    DocumentAuthor,
    DocumentAcademicUnit,
    DocumentTag,
    # Moderation Domain
    ModerationStatus,
    DocumentModeration,
    # Collections Domain
    Collection,
    CollectionItem,
    # Engagement Domain
    DocumentReport,
    DocumentShare,
)


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ('version_number', 'change_notes', 'created_by', 'is_latest', 'created_at')
    readonly_fields = ('created_at',)


class DocumentAcademicUnitInline(admin.TabularInline):
    model = DocumentAcademicUnit
    extra = 0


class DocumentTagInline(admin.TabularInline):
    model = DocumentTag
    extra = 0


class DocumentAuthorInline(admin.TabularInline):
    model = DocumentAuthor
    extra = 0


class DocumentFileInline(admin.TabularInline):
    model = DocumentFile
    extra = 0
    fields = ('original_filename', 'extension', 'size_bytes', 'storage_provider', 'processing_status', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'visibility', 'uploaded_by', 'created_at', 'version_count')
    list_filter = ('status', 'visibility', 'category', 'created_at')
    search_fields = ('title', 'description', 'uploaded_by__username', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [DocumentVersionInline, DocumentAcademicUnitInline, DocumentTagInline, DocumentAuthorInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ('document', 'version_number', 'created_by', 'is_latest', 'created_at')
    list_filter = ('is_latest', 'created_at')
    search_fields = ('document__title', 'change_notes', 'created_by__username')
    inlines = [DocumentFileInline]


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'document_version', 'mime_type', 'size_mb', 'storage_provider', 'processing_status', 'uploaded_at')
    list_filter = ('processing_status', 'storage_provider', 'extension')
    search_fields = ('original_filename', 'checksum', 'storage_path')
    readonly_fields = ('uploaded_at', 'processed_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'usage_count', 'created_at')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ModerationStatus)
class ModerationStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_public', 'is_searchable', 'is_downloadable', 'order')
    list_filter = ('is_public', 'is_searchable', 'is_downloadable')


@admin.register(DocumentModeration)
class DocumentModerationAdmin(admin.ModelAdmin):
    list_display = ('document', 'status', 'moderated_by', 'status_changed_at')
    list_filter = ('status',)
    search_fields = ('document__title', 'moderated_by__username', 'moderation_notes')


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'visibility', 'is_featured', 'created_at')
    list_filter = ('visibility', 'is_featured')
    search_fields = ('name', 'owner__username', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CollectionItemInline]


# Academic Structure Admin Registrations
@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_current', 'start_date', 'end_date')
    list_filter = ('is_current',)


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'number', 'is_current', 'start_date', 'end_date')
    list_filter = ('is_current', 'academic_year')


@admin.register(AcademicLevel)
class AcademicLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'is_active')
    list_filter = ('is_active',)


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'faculty')
    list_filter = ('faculty',)
    search_fields = ('name', 'code')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'school')
    list_filter = ('school',)
    search_fields = ('name', 'code')


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'department', 'degree_type', 'duration_years', 'is_active')
    list_filter = ('is_active', 'department', 'degree_type')
    search_fields = ('name', 'code')


@admin.register(AcademicUnit)
class AcademicUnitAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'credit_hours', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')


@admin.register(ProgrammeUnit)
class ProgrammeUnitAdmin(admin.ModelAdmin):
    list_display = ('programme', 'academic_unit', 'academic_level', 'semester', 'is_core')
    list_filter = ('is_core', 'programme', 'academic_level')
    search_fields = ('programme__name', 'academic_unit__code', 'academic_unit__name')


@admin.register(DocumentReport)
class DocumentReportAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status')
    search_fields = ('document__title', 'user__username', 'description')


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'platform', 'shared_at')
    list_filter = ('platform', 'shared_at')
    search_fields = ('document__title', 'user__username')
