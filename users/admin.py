from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import HeroShowcaseSet, User

class TheUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('course', 'year', 'global_role', 'profile_pic', 'cover_photo', 'bio')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('course', 'year', 'global_role')}),
    )

    list_display = ['first_name', 'second_name', 'last_name', 'username', 'email', 'global_role', 'is_staff']
    list_filter = ['global_role', 'course', 'year', 'is_staff']

admin.site.register(User, TheUserAdmin)


@admin.register(HeroShowcaseSet)
class HeroShowcaseSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'preview_center', 'preview_gate', 'preview_ai', 'preview_doc', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)

    def _preview(self, image, width, height):
        if not image:
            return '-'
        return format_html(
            '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:6px" />',
            image.url, width, height,
        )

    def preview_center(self, obj):
        return self._preview(obj.center_reel, 30, 50)
    preview_center.short_description = 'Reel'

    def preview_gate(self, obj):
        return self._preview(obj.pwani_gate, 50, 35)
    preview_gate.short_description = 'Campus Gate'

    def preview_ai(self, obj):
        return self._preview(obj.pwanimate, 32, 50)
    preview_ai.short_description = 'PwaniMate'

    def preview_doc(self, obj):
        return self._preview(obj.doc_repo, 35, 40)
    preview_doc.short_description = 'Doc Repo'

    def _superuser(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return self._superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._superuser(request)

    def has_add_permission(self, request):
        return self._superuser(request)

    def has_change_permission(self, request, obj=None):
        return self._superuser(request)

    def has_delete_permission(self, request, obj=None):
        return self._superuser(request)
