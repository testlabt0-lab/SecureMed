"""
Audit logging middleware.
"""
import time
import logging
from apps.audit.models import AuditLog
from apps.audit.utils import log_security_event

logger = logging.getLogger('security')


class AuditLogMiddleware:
    """Log API requests to audit log."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # Log security-relevant endpoints
        if request.path.startswith('/api/') and hasattr(request, 'user') and request.user.is_authenticated:
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                # Determine event type based on action
                event_type = AuditLog.EventType.INFO
                if request.method == 'POST':
                    event_type = 'DATA_CREATED'
                elif request.method in ('PUT', 'PATCH'):
                    event_type = 'DATA_MODIFIED'
                elif request.method == 'DELETE':
                    event_type = 'DATA_DELETED'
                    
                # We can map specific URLs to specific events here if needed,
                # but for general audit we use CONFIG_CHANGED or similar generic if no specific matched
                if 'settings' in request.path or 'config' in request.path:
                    event_type = AuditLog.EventType.CONFIG_CHANGED

                # We don't want to double log things already logged in views explicitly,
                # but we'll log generic state changes here.
                # To avoid duplicate logs we could check request attribute.
                if not getattr(request, '_audit_logged', False):
                    severity = AuditLog.Severity.INFO
                    if response.status_code >= 400:
                        severity = AuditLog.Severity.WARNING

                    log_security_event(
                        user=request.user,
                        event_type=event_type if hasattr(AuditLog.EventType, event_type) else AuditLog.EventType.SUSPICIOUS_ACTIVITY, # fallback
                        request=request,
                        details={
                            'status_code': response.status_code,
                            'duration_ms': round(duration * 1000, 2)
                        },
                        severity=severity
                    )

        return response
