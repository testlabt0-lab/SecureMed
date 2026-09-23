"""
Background tasks for backups: scheduled daily backup with off-site delivery.

The scheduled run mirrors the plan requirement «اوتو باك اب للنسخ الاحتياطي»:
Celery beat fires it daily, and its outcome — success *or* failure — is pushed
to the admin Telegram chat so a silently broken backup pipeline is discovered
the morning it breaks, not the day a restore is needed.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def run_scheduled_backup(self, scope='FULL'):
    """Run a scheduled backup of *scope*, then report the outcome to Telegram.

    The beat schedule pairs a small daily DATABASE archive (cheap to ship
    off-site, covers the data that changes every day) with a weekly FULL
    archive (media included) — the classic cadence for medical records.
    """
    try:
        from apps.backups.services import create_backup

        record = create_backup(kind='SCHEDULED', note='scheduled-daily', scope=scope)
        logger.info(
            f'Scheduled backup completed: {record.filename} '
            f'(scope={record.scope}, delivery={record.delivery_status})'
        )
        _notify_result(record, success=True)
        return {
            'status': 'success',
            'filename': record.filename,
            'scope': record.scope,
            'delivery_status': record.delivery_status,
        }
    except Exception as exc:
        logger.exception('Scheduled backup failed')
        _notify_result(None, success=False, detail=str(exc))
        raise self.retry(exc=exc)


def _notify_result(record, success, detail=''):
    """Push the run's outcome to the admin chat. Must never raise: the retry
    path re-raises the original error and this helper sits on that path."""
    try:
        from apps.security.telegram_service import send_backup_result_notification
        send_backup_result_notification(record=record, success=success, detail=detail)
    except Exception as e:
        logger.error(f"Failed to send backup result notification: {e}")
