"""
Utility functions for audit logging.
"""
import json
import logging
import uuid
from django .conf import settings
from django .utils import timezone
from apps .audit .models import AuditLog

logger =logging .getLogger (__name__ )


def log_security_event (user ,event_type ,request =None ,details =None ,severity ='INFO'):
    """
    Log a security event to the audit log.

    Args:
        user: User object (can be None for unauthenticated events)
        event_type: AuditLog.EventType value
        request: Django request object (for IP, user agent)
        details: dict with additional event details
        severity: AuditLog.Severity value
    """
    ip_address =None 
    user_agent =''
    path =''
    method =''
    mac_address =''
    device_fingerprint =''
    os_info =''
    browser_info =''
    screen_resolution =''
    timezone_offset =''
    language =''
    session_id =''

    if request :
        # One resolver for every IP the system records or acts on: reading the
        # leftmost X-Forwarded-For entry here let a client forge the address in
        # its own audit trail. See apps.core.net.
        from apps .core .net import get_client_ip
        ip_address =get_client_ip (request )

        user_agent =request .META .get ('HTTP_USER_AGENT','')[:500 ]
        path =request .path [:255 ]
        method =request .method 

        # Extract custom headers
        mac_address =request .META .get ('HTTP_X_MAC_ADDRESS','')[:100 ]
        device_fingerprint =request .META .get ('HTTP_X_DEVICE_FINGERPRINT','')[:255 ]
        screen_resolution =request .META .get ('HTTP_X_SCREEN_RESOLUTION','')[:50 ]
        timezone_offset =request .META .get ('HTTP_X_TIMEZONE_OFFSET','')[:50 ]
        language =request .META .get ('HTTP_ACCEPT_LANGUAGE','')[:50 ]
        session_id =request .session .session_key if hasattr (request ,'session')and request .session .session_key else ''

        # Parse user agent if possible
        try :
            from user_agents import parse 
            ua =parse (user_agent )
            os_info =f"{ua .os .family } {ua .os .version_string }".strip ()
            browser_info =f"{ua .browser .family } {ua .browser .version_string }".strip ()
        except ImportError :
            os_info ='Unknown'
            browser_info ='Unknown'

    log_data = {
        'id': str(uuid.uuid4()),
        'user_id': str(user.id) if user else None,
        'event_type': event_type,
        'severity': severity,
        'ip_address': ip_address,
        'user_agent': user_agent,
        'path': path,
        'method': method,
        'mac_address': mac_address,
        'device_fingerprint': device_fingerprint,
        'os_info': os_info,
        'browser_info': browser_info,
        'screen_resolution': screen_resolution,
        'timezone_offset': timezone_offset,
        'language': language,
        'session_id': session_id,
        'details': details or {},
    }

    def _write_now ():
        """Same row, written in-process, and only if the task did not already write it.

        The id is minted here rather than left to the model default so this write
        is idempotent. It has to be: with CELERY_TASK_ALWAYS_EAGER the task runs
        inside `.delay()`, and an error *after* it returns — a result backend that
        is unreachable, for instance — surfaces as an exception from `.delay()`
        even though the row exists. Without the guard every audit event was
        written twice, which is worse than useless on a hash-chained table.
        `user` is passed as the object rather than user_id so the FK is set
        without a second query.
        """
        fields ={k :v for k ,v in log_data .items ()if k not in ('user_id','id')}
        event_id =log_data ['id']
        if AuditLog .objects .filter (pk =event_id ).exists ():
            return
        AuditLog .objects .create (id =event_id ,user =user ,**fields )

    # A worker is not guaranteed to exist. `.delay()` only proves the broker took the
    # message, so on a deployment with Redis but no Celery process every audit event
    # would queue up and never be written — and nothing would report an error.
    # AUDIT_LOG_ASYNC=False writes inline instead.
    if not getattr (settings ,'AUDIT_LOG_ASYNC',True ):
        _write_now ()
        return

    try:
        from apps.audit.tasks import async_save_audit_log
        async_save_audit_log.delay(log_data)
    except Exception as e:
        # Reached when the broker itself is unreachable. Losing the event is not an
        # option, so fall back to a synchronous write.
        logger.warning(f"Failed to queue async audit log: {e}")
        try :
            _write_now ()
        except Exception as write_error :
            # The audit write must not take the caller's request down with it —
            # a failed login would 500 instead of returning 401. Report it at
            # CRITICAL so the loss is visible in the application log, which is
            # the only remaining record of the event.
            logger .critical (
            'AUDIT_WRITE_FAILED event_type=%s user_id=%s error=%s',
            event_type ,log_data ['user_id'],write_error ,
            )
