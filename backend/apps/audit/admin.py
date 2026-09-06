from unfold.admin import ModelAdmin
"""
Admin for audit app.
"""
from django.contrib import admin
from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ('timestamp', 'user', 'event_type', 'severity', 'ip_address', 'path')
    list_filter = ('event_type', 'severity')
    search_fields = ('user__email', 'user__full_name', 'path', 'ip_address')
    readonly_fields = ('id', 'user', 'event_type', 'severity', 'ip_address',
                       'user_agent', 'path', 'method', 'details', 'timestamp',
                       'hash', 'previous_hash')
    date_hierarchy = 'timestamp'

    # An audit trail an administrator can edit or delete is not an audit trail.
    # The records carry a chained HMAC precisely so tampering is detectable, and
    # readonly_fields alone still leaves the add and delete buttons wired up —
    # which would break the chain at the deleted row and silently invalidate
    # every signature after it. Writes come from log_security_event() only.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
