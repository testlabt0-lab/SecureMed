"""
Serializers and Views for audit log.
"""
from rest_framework import serializers, viewsets, permissions, filters
from django_filters import rest_framework as django_filters

from apps.audit.models import AuditLog
from apps.security.permissions import IsAdmin, IsAuditor


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog."""

    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    event_type_display = serializers.CharField(
        source='get_event_type_display', read_only=True
    )
    severity_display = serializers.CharField(
        source='get_severity_display', read_only=True
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'event_type', 'event_type_display',
            'severity', 'severity_display',
            'ip_address', 'user_agent', 'path', 'method',
            'details', 'timestamp',
        ]
        read_only_fields = fields


class AuditLogFilter(django_filters.FilterSet):
    """Filter for audit logs."""

    class Meta:
        model = AuditLog
        fields = {
            'event_type': ['exact'],
            'severity': ['exact'],
            'user': ['exact'],
            'timestamp': ['date', 'gte', 'lte'],
        }


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """View audit logs (admin/auditor only)."""
    queryset = AuditLog.objects.all().order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin | IsAuditor]
    filterset_class = AuditLogFilter
    search_fields = ['user__email', 'user__full_name', 'path']
    ordering_fields = ['timestamp', 'severity', 'event_type']
