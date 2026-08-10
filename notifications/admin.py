from django.contrib import admin
from .models import NotificationObject, PushSubscription, NotificationAction


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'is_active', 'created_at', 'updated_at']
    search_fields = ['user__username', 'endpoint']
    list_filter = ['is_active', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NotificationObject)
class NotificationObjectAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'recipient', 'notification_type', 'status', 'priority', 'created_at']
    search_fields = ['recipient__username', 'notification_type']
    list_filter = ['notification_type', 'status', 'priority', 'created_at']
    readonly_fields = ['notification_id', 'created_at', 'updated_at']


@admin.register(NotificationAction)
class NotificationActionAdmin(admin.ModelAdmin):
    list_display = ['id', 'notification', 'action_type', 'label', 'is_primary', 'order']
    search_fields = ['action_type', 'label']
    list_filter = ['action_type', 'is_primary']
    readonly_fields = ['id']
