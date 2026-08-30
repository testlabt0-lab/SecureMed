"""
Admin for audit app.
"""
from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'event_type', 'severity', 'ip_address', 'path')
    list_filter = ('event_type', 'severity')
    search_fields = ('user__email', 'user__full_name', 'path', 'ip_address')
    readonly_fields = ('id', 'user', 'event_type', 'severity', 'ip_address',
                       'user_agent', 'path', 'method', 'details', 'timestamp')
    date_hierarchy = 'timestamp'
