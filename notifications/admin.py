from django.contrib import admin
from .models import Notifications, PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'endpoint', 'is_active', 'created_at', 'updated_at']
    search_fields = ['user__username', 'endpoint']
    list_filter = ['is_active', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


admin.site.register(Notifications)
