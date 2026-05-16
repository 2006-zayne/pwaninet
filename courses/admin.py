from django.contrib import admin
from .models import School, Course, Year, Unit


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at', 'updated_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


admin.site.register(Course)
admin.site.register(Year)
admin.site.register(Unit)
