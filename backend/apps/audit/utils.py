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
    mac_address = ''
    device_fingerprint = ''
    os_info = ''
    browser_info = ''
    screen_resolution = ''
    timezone_offset = ''
    language = ''
    session_id = ''
    
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            ip_address = x_forwarded.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        path = request.path[:255]
        method = request.method
        
        # Extract custom headers
        mac_address = request.META.get('HTTP_X_MAC_ADDRESS', '')[:100]
        device_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')[:255]
        screen_resolution = request.META.get('HTTP_X_SCREEN_RESOLUTION', '')[:50]
        timezone_offset = request.META.get('HTTP_X_TIMEZONE_OFFSET', '')[:50]
        language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')[:50]
        session_id = request.session.session_key if hasattr(request, 'session') and request.session.session_key else ''

        # Parse user agent if possible
        try:
            from user_agents import parse
            ua = parse(user_agent)
            os_info = f"{ua.os.family} {ua.os.version_string}".strip()
            browser_info = f"{ua.browser.family} {ua.browser.version_string}".strip()
        except ImportError:
            os_info = 'Unknown'
            browser_info = 'Unknown'

    AuditLog.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        ip_address=ip_address,
        user_agent=user_agent,
        path=path,
        method=method,
        mac_address=mac_address,
        device_fingerprint=device_fingerprint,
        os_info=os_info,
        browser_info=browser_info,
        screen_resolution=screen_resolution,
        timezone_offset=timezone_offset,
        language=language,
        session_id=session_id,
        details=details or {},
    )
