from unfold.admin import ModelAdmin
"""
Admin for notifications app.
"""
from django.contrib import admin
from apps.notifications.models import (
    Notification, NotificationPreference, EmailLog
)


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'priority',
                    'is_read', 'created_at')
    list_filter = ('notification_type', 'priority', 'is_read')
    search_fields = ('title', 'message', 'recipient__email')
    readonly_fields = ('created_at', 'updated_at', 'read_at', 'email_sent_at')
    date_hierarchy = 'created_at'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(ModelAdmin):
    list_display = ('user', 'email_channel_updates', 'push_security_alerts')
    search_fields = ('user__email',)


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ('recipient_email', 'subject', 'status', 'sent_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('recipient_email', 'subject')
    readonly_fields = ('created_at', 'sent_at')
