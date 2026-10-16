from django.contrib import admin

from .models import UploadEvent, UploadPostGroup, UploadRecord, UploadSession


class UploadEventInline(admin.TabularInline):
    model = UploadEvent
    extra = 0
    readonly_fields = ("event_type", "detail", "created_at")
    can_delete = False


@admin.register(UploadRecord)
class UploadRecordAdmin(admin.ModelAdmin):
    list_display = (
        "filename", "user", "status", "progress_bytes",
        "total_bytes", "retry_count", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("filename", "user__username", "client_upload_id")
    readonly_fields = ("client_upload_id", "created_at", "updated_at")
    inlines = [UploadEventInline]


@admin.register(UploadSession)
class UploadSessionAdmin(admin.ModelAdmin):
    list_display = ("record", "protocol", "total_parts", "finalized", "expires_at")
    list_filter = ("protocol", "finalized")


@admin.register(UploadPostGroup)
class UploadPostGroupAdmin(admin.ModelAdmin):
    list_display = ("group_id", "user", "post", "created_at")
    search_fields = ("group_id", "user__username")


@admin.register(UploadEvent)
class UploadEventAdmin(admin.ModelAdmin):
    list_display = ("record", "event_type", "created_at")
    list_filter = ("event_type",)
