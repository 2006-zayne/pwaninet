from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

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
