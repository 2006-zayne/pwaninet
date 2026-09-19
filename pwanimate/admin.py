"""Django admin configuration for Pwanimate."""

from django.contrib import admin
from .models import DocumentChunk, PwanimatePreferences


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'document_version',
        'chunk_index',
        'chunk_type',
        'page_number',
        'slide_number',
        'is_active',
        'embedding_status',
        'created_at',
    )
    list_filter = (
        'is_active',
        'chunk_type',
        'embedding_status',
        'created_at',
    )
    search_fields = (
        'content',
        'section_heading',
        'document__title',
        'content_hash',
    )
    raw_id_fields = (
        'document',
        'document_version',
    )
    readonly_fields = (
        'content_hash',
        'created_at',
        'updated_at',
    )


@admin.register(PwanimatePreferences)
class PwanimatePreferencesAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'nickname',
        'tone',
        'response_style',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'tone',
        'response_style',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__email',
        'nickname',
        'personal_instructions',
    )
    raw_id_fields = (
        'user',
    )
    readonly_fields = (
        'created_at',
        'updated_at',
    )
