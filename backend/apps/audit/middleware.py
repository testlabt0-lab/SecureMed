"""
Audit logging middleware.
"""
import time 
import logging 
from apps .audit .models import AuditLog 
from apps .audit .utils import log_security_event 

logger =logging .getLogger ('security')


class AuditLogMiddleware :
    """Log API requests to audit log."""

    def __init__ (self ,get_response ):
        self .get_response =get_response 

    def __call__ (self ,request ):
        start_time =time .time ()
        response =self .get_response (request )
        duration =time .time ()-start_time 

        # Log security-relevant endpoints
        if self ._should_audit (request , response ):
            # Determine event type based on action
            if request.method == 'POST':
                event_type = 'DATA_CREATED'
            elif request.method in ('PUT', 'PATCH'):
                event_type = 'DATA_MODIFIED'
            elif request.method == 'DELETE':
                event_type = 'DATA_DELETED'
            elif request.method == 'GET':
                event_type = 'DATA_ACCESSED'
            else:
                event_type = 'SYSTEM_EVENT'

            # We can map specific URLs to specific events here if needed
            if 'settings' in request.path or 'config' in request.path:
                event_type = 'CONFIG_CHANGED'

            # Everything below used to sit inside the `settings`/`config` branch
            # above, one indent level too deep. The effect was that the only API
            # requests this middleware ever audited were the handful whose path
            # contained "settings" or "config" — and those were all recorded as
            # CONFIG_CHANGED regardless of method. Every read of patient data, every
            # create, every delete on every other endpoint went unlogged, which is
            # exactly the coverage HIPAA-style access logging exists to provide.
            if not getattr (request ,'_audit_logged',False ):
                severity =AuditLog .Severity .INFO
                if response .status_code >=400 :
                    severity =AuditLog .Severity .WARNING

                current_user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                log_security_event (
                    user =current_user ,
                    event_type =event_type if hasattr (AuditLog .EventType ,event_type )else AuditLog .EventType .SUSPICIOUS_ACTIVITY ,# fallback
                    request =request ,
                    details ={
                        'status_code':response .status_code ,
                        'duration_ms':round (duration *1000 ,2 )
                    },
                    severity =severity
                )

        return response

    # Paths that should not trigger audit records on read/poll/metrics (noise and DB lock congestion)
    EXEMPT_PREFIXES =(
        '/api/schema',
        '/api/docs',
        '/api/redoc',
        '/health/',
        '/api/v1/notifications/unread_count',
        '/api/v1/notifications/unread-count',
        '/api/v1/notifications/poll',
        '/api/v1/security/stats',
        '/api/v1/security/activity',
        '/api/v1/security/dashboard',
        '/api/v1/security/check-device',
        '/api/v1/security/device-types',
        '/api/v1/security/ztna-status',
        '/api/v1/security/ztna-request',
        '/api/v1/security/ws-token',
        '/api/v1/auth/session',
        '/api/v1/auth/csrf',
        '/api/v1/audit/stats',
    )

    def _should_audit (self ,request ,response =None ):
        if not request .path .startswith ('/api/'):
            return False
        if request .method =='OPTIONS'or request .path .startswith (self .EXEMPT_PREFIXES ):
            return False

        # Always audit errors and suspicious responses (4xx, 5xx)
        if response is not None and response .status_code >=400 :
            return True

        # Only audit authenticated requests for routine traffic
        if not (hasattr (request ,'user')and request .user .is_authenticated ):
            return False

        # Mutating operations (POST, PUT, PATCH, DELETE) MUST always be audited
        if request .method in ('POST','PUT','PATCH','DELETE'):
            return True

        # Settings or configuration changes/access
        if 'settings' in request .path or 'config' in request .path :
            return True

        # Routine 200 OK GET requests are NOT audited in middleware to prevent
        # serializing pg_advisory_xact_lock across concurrent reads.
        # Sensitive PHI access (Patient details, medical records, exports) is
        # audited directly at the view level with full patient context.
        return False
