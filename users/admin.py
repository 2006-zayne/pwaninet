from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import GoogleAccount, HeroShowcaseSet, RecoveryCode, User, UserTwoFactor

class TheUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('course', 'year', 'global_role', 'profile_pic', 'cover_photo', 'bio')}),
        ('Academic setup', {'fields': ('institution', 'programme', 'academic_level', 'academic_year', 'semester')}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Profile', {'fields': ('course', 'year', 'global_role')}),
    )

    list_display = ['first_name', 'second_name', 'last_name', 'username', 'email', 'global_role', 'is_staff']
    list_filter = ['global_role', 'institution', 'course', 'year', 'is_staff']

admin.site.register(User, TheUserAdmin)


@admin.register(UserTwoFactor)
class UserTwoFactorAdmin(admin.ModelAdmin):
    list_display = ('username', 'status', 'enrolled_at', 'updated_at')
    list_filter = ('is_enabled',)
    search_fields = ('user__username', 'user__email')
    actions = ('reset_two_factor',)
    readonly_fields = ('user', 'is_enabled', 'enrolled_at', 'last_used_timestep', 'created_at', 'updated_at')

    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'

    def status(self, obj):
        return 'enabled' if obj.is_enabled else 'pending'
    status.short_description = 'Status'

    def reset_two_factor(self, request, queryset):
        from users.services.two_factor_service import disable_two_factor
        import logging
        reset_log = logging.getLogger('users.auth')
        count = 0
        for two_factor in queryset.select_related('user'):
            username = two_factor.user.username
            if disable_two_factor(two_factor.user):
                count += 1
                reset_log.warning(
                    f"[SECURITY-2FA] ADMIN RESET: 2FA reset for user '{username}' by admin '{request.user.username}'"
                )
        self.message_user(request, f"2FA reset for {count} account(s). Recovery codes purged.")
    reset_two_factor.short_description = "Reset 2FA (disable + purge recovery codes)"

    def _superuser(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return self._superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._superuser(request)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return self._superuser(request)

    def has_delete_permission(self, request, obj=None):
        return self._superuser(request)


@admin.register(RecoveryCode)
class RecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ('username', 'is_consumed', 'consumed_at', 'created_at')
    list_filter = ('is_consumed',)
    search_fields = ('user__username',)

    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'

    def _superuser(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return self._superuser(request)

    def has_view_permission(self, request, obj=None):
        return self._superuser(request)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return self._superuser(request)


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


@admin.register(GoogleAccount)
class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'email_verified', 'link_method', 'created_at', 'last_login_at')
    list_filter = ('email_verified', 'link_method')
    search_fields = ('user__username', 'user__email', 'email', 'sub')
    readonly_fields = ('user', 'sub', 'email', 'email_verified', 'hosted_domain', 'link_method', 'created_at', 'last_login_at')

    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'

    def has_add_permission(self, request):
        return False
