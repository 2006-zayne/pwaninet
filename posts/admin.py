from django.contrib import admin
from django.utils import timezone
from .models import Post, Report

admin.site.register(Post)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reason', 'status', 'reporter', 'post', 'created_at', 'reviewed_by')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__username', 'post__content', 'description')
    readonly_fields = ('reporter', 'post', 'reason', 'description', 'created_at', 'reviewed_by', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if obj.status != Report.Status.PENDING and obj.reviewed_at is None:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        if obj.status == Report.Status.PENDING:
            obj.reviewed_at = None
            obj.reviewed_by = None
        super().save_model(request, obj, form, change)
