"""
Utility functions for audit logging.
"""
import json
from django.utils import timezone
from apps.audit.models import AuditLog


def log_security_event(user, event_type, request=None, details=None, severity='INFO'):
    """
    Log a security event to the audit log.

    Args:
        user: User object (can be None for unauthenticated events)
        event_type: AuditLog.EventType value
        request: Django request object (for IP, user agent)
        details: dict with additional event details
        severity: AuditLog.Severity value
    """
    ip_address = None
    user_agent = ''
    path = ''
    method = ''

    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip_address = x_forwarded.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        path = request.path[:255]
        method = request.method

    AuditLog.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent,
        path=path,
        method=method,
        details=details or {},
    )
