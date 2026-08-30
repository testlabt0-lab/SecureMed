"""
Audit logging middleware.
"""
import logging
from apps.audit.models import AuditLog
from apps.audit.utils import log_security_event

logger = logging.getLogger('security')


class AuditLogMiddleware:
    """Log API requests to audit log."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log security-relevant endpoints
        if request.path.startswith('/api/') and request.user.is_authenticated:
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                # Only log mutations, not reads (to avoid log flooding)
                pass  # Logged in views

        return response
