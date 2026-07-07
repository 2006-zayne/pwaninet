from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
import json
from .models import Release, ReleaseItem, UserReleaseView


class ReleaseItemInline(admin.TabularInline):
    """Inline admin for ReleaseItem to edit items directly from Release admin"""
    model = ReleaseItem
    extra = 0
    fields = ['category', 'title', 'description', 'display_order']
    ordering = ['display_order', 'category']


@admin.register(Release)
class ReleaseAdmin(admin.ModelAdmin):
    """Admin interface for Release model with custom actions"""
    list_display = [
        'version',
        'build_number',
        'release_title',
        'release_type',
        'published',
        'mandatory_update',
        'release_date',
        'is_latest_badge'
    ]
    list_filter = ['published', 'mandatory_update', 'release_type', 'release_channel']
    search_fields = ['version', 'release_title', 'release_summary']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ReleaseItemInline]
    
    fieldsets = (
        ('Release Information', {
            'fields': ('version', 'build_number', 'release_title', 'release_summary')
        }),
        ('Release Type & Channel', {
            'fields': ('release_type', 'release_channel')
        }),
        ('Release Flags', {
            'fields': ('published', 'mandatory_update', 'minimum_supported_version')
        }),
        ('Timestamps', {
            'fields': ('release_date', 'created_at', 'updated_at')
        }),
        ('Author', {
            'fields': ('created_by',)
        }),
    )
    
    actions = ['publish_releases', 'unpublish_releases', 'mark_mandatory']
    
    def is_latest_badge(self, obj):
        """Display a badge if this is the latest published release"""
        if obj.is_latest():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 8px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">LATEST</span>'
            )
        return ''
    is_latest_badge.short_description = 'Latest'
    
    def publish_releases(self, request, queryset):
        """Action to publish selected releases"""
        updated = queryset.update(published=True)
        self.message_user(request, f'{updated} release(s) published successfully.')
    publish_releases.short_description = 'Publish selected releases'
    
    def unpublish_releases(self, request, queryset):
        """Action to unpublish selected releases"""
        updated = queryset.update(published=False)
        self.message_user(request, f'{updated} release(s) unpublished successfully.')
    unpublish_releases.short_description = 'Unpublish selected releases'
    
    def mark_mandatory(self, request, queryset):
        """Action to mark selected releases as mandatory updates"""
        updated = queryset.update(mandatory_update=True)
        self.message_user(request, f'{updated} release(s) marked as mandatory.')
    mark_mandatory.short_description = 'Mark as mandatory update'
    
    def save_model(self, request, obj, form, change):
        """Auto-set created_by field on creation and handle publishing"""
        if not change:  # If creating a new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        
        # If this is being published, handle auto-versioning
        if obj.published:
            self.handle_publish_actions(request, obj)
    
    def handle_publish_actions(self, request, release):
        """Handle actions when a release is published"""
        try:
            # Update version.py with new version
            self.update_version_file(release)
            
            # Invalidate caches
            self.invalidate_release_caches()
            
            messages.success(
                request,
                f'Release {release.version} published successfully. '
                f'Version file updated and caches invalidated.'
            )
        except Exception as e:
            messages.error(
                request,
                f'Release published but auto-versioning failed: {str(e)}'
            )
    
    def update_version_file(self, release):
        """Update pwaninet/version.py with the new version"""
        from django.conf import settings
        version_file_path = os.path.join(settings.BASE_DIR, 'pwaninet', 'version.py')
        
        # Update version.py
        with open(version_file_path, 'w') as f:
            f.write(f'__version__ = "{release.version}"\n')
    
    def invalidate_release_caches(self):
        """Invalidate release-related caches"""
        from django.core.cache import cache
        cache_keys = [
            'releases:latest',
            'releases:history',
            'releases:version_check'
        ]
        for key in cache_keys:
            cache.delete(key)


@admin.register(ReleaseItem)
class ReleaseItemAdmin(admin.ModelAdmin):
    """Admin interface for ReleaseItem model"""
    list_display = ['release', 'category', 'title', 'display_order']
    list_filter = ['category', 'release']
    search_fields = ['title', 'description', 'release__version']
    ordering = ['release', 'display_order', 'category']


@admin.register(UserReleaseView)
class UserReleaseViewAdmin(admin.ModelAdmin):
    """Admin interface for UserReleaseView model"""
    list_display = ['user', 'release', 'viewed_at']
    list_filter = ['viewed_at', 'release']
    search_fields = ['user__username', 'user__email', 'release__version']
    readonly_fields = ['viewed_at']
