from celery import shared_task
import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger('security')
User = get_user_model()

@shared_task
def async_save_audit_log(log_data):
    """
    Asynchronously save an audit log to the database.
    """
    try:
        from apps.audit.models import AuditLog
        user_id = log_data.pop('user_id', None)
        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()
            
        AuditLog.objects.create(
            user=user,
            **log_data
        )
    except Exception as e:
        logger.error(f"Failed to asynchronously save audit log: {e}")
