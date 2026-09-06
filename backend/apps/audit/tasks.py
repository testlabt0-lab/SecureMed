from celery import shared_task
import logging
from django.contrib.auth import get_user_model

logger = logging.getLogger('security')
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def async_save_audit_log(self, log_data):
    """Persist one audit event queued by apps.audit.utils.log_security_event.

    The row's id travels in log_data, so a retry (or the caller's synchronous
    fallback) re-runs this without inserting a second copy — audit rows are
    hash-chained and duplicates make the chain's counts meaningless.

    Failures are retried and then re-raised. Swallowing them meant a broken
    write dropped a security event with nothing but a log line to show for it,
    which is the one outcome an audit trail may not have.
    """
    from apps.audit.models import AuditLog

    data = dict(log_data)
    event_id = data.pop('id', None)
    user_id = data.pop('user_id', None)

    try:
        if event_id and AuditLog.objects.filter(pk=event_id).exists():
            return None

        user = User.objects.filter(id=user_id).first() if user_id else None
        log = AuditLog.objects.create(
            **({'id': event_id} if event_id else {}),
            user=user,
            **data
        )
        return str(log.pk)
    except Exception as exc:
        logger.error(f"Failed to asynchronously save audit log: {exc}")
        raise self.retry(exc=exc)
