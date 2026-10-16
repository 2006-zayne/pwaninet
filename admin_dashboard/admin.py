from django.contrib import admin

from .models import PageMaintenance


@admin.register(PageMaintenance)
class PageMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('name', 'path_prefix', 'is_active', 'eta', 'show_eta', 'updated_at')
    list_filter = ('is_active', 'show_eta')
    search_fields = ('name', 'path_prefix')
    list_editable = ('is_active',)
