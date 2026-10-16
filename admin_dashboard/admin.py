from django.contrib import admin

from .models import PageMaintenance


@admin.register(PageMaintenance)
class PageMaintenanceAdmin(admin.ModelAdmin):
    change_list_template = 'admin/admin_dashboard/pagemaintenance/change_list.html'
    list_display = ('name', 'path_prefix', 'is_active', 'show_eta', 'eta', 'updated_at')
    list_display_links = ('name',)
    list_filter = ('is_active', 'show_eta')
    search_fields = ('name', 'path_prefix')
    list_editable = ('is_active', 'show_eta')
    actions = ('activate_locks', 'deactivate_locks')

    @admin.action(description='Activate selected locks')
    def activate_locks(self, request, queryset):
        queryset.update(is_active=True)
        PageMaintenance._bust_lock_cache()

    @admin.action(description='Deactivate selected locks')
    def deactivate_locks(self, request, queryset):
        queryset.update(is_active=False)
        PageMaintenance._bust_lock_cache()
