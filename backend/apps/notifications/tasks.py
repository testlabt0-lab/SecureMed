"""
Background tasks for notifications: flush pending email queue.
"""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_notification_email(self, user_id: str, subject: str, message: str):
    """Send a single notification email."""
    try:
        from apps.accounts.models import User
        user = User.objects.get(id=user_id)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f'Email sent to {user.email}: {subject}')
        return {'status': 'sent', 'recipient': user.email}
    except Exception as exc:
        logger.exception(f'Failed to send email to user {user_id}')
        raise self.retry(exc=exc)


@shared_task
def flush_pending_emails():
    """Flush queued email notifications (CRITICAL/HIGH priority)."""
    from apps.notifications.models import Notification
    pending = Notification.objects.filter(
        email_sent=False,
        priority__in=['CRITICAL', 'HIGH'],
    ).select_related('user')[:50]

    sent = 0
    for notif in pending:
        if notif.user.email:
            send_notification_email.delay(
                str(notif.user.id),
                f'SecureMed: {notif.title}',
                notif.message,
            )
            Notification.objects.filter(pk=notif.pk).update(email_sent=True)
            sent += 1

    logger.info(f'Queued {sent} email notifications')
    return {'queued': sent}
