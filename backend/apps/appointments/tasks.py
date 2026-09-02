"""
Appointment background tasks (Celery).
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_appointment_reminders(self, hours_before: int = 24):
    """Send reminder notifications for upcoming appointments."""
    try:
        from apps.appointments.models import Appointment
        from apps.notifications.utils import create_notification

        now = timezone.now()
        window_start = now + timedelta(hours=hours_before - 0.25)
        window_end = now + timedelta(hours=hours_before + 0.25)

        field = 'reminder_sent_24h' if hours_before == 24 else 'reminder_sent_1h'

        appointments = Appointment.objects.filter(
            scheduled_at__gte=window_start,
            scheduled_at__lte=window_end,
            status__in=['SCHEDULED', 'CONFIRMED'],
            **{field: False},
        ).select_related('patient', 'doctor')

        count = 0
        for appt in appointments:
            # Notify doctor
            create_notification(
                user=appt.doctor,
                title=f'تذكير: موعد خلال {hours_before} ساعة',
                message=(
                    f'لديك موعد مع المريض {appt.patient.full_name} '
                    f'بتاريخ {appt.scheduled_at.strftime("%Y-%m-%d %H:%M")}'
                ),
                notification_type='APPOINTMENT_REMINDER',
                priority='HIGH' if hours_before == 1 else 'MEDIUM',
                related_object_type='appointment',
                related_object_id=str(appt.id),
            )
            Appointment.objects.filter(pk=appt.pk).update(**{field: True})
            count += 1

        logger.info(f'Sent {count} appointment reminders ({hours_before}h before)')
        return {'reminders_sent': count, 'hours_before': hours_before}

    except Exception as exc:
        logger.exception('Failed to send appointment reminders')
        raise self.retry(exc=exc)


@shared_task
def cancel_no_show_appointments():
    """Mark appointments as no-show if they passed 30 minutes without being started."""
    from apps.appointments.models import Appointment

    cutoff = timezone.now() - timedelta(minutes=30)
    updated = Appointment.objects.filter(
        scheduled_at__lt=cutoff,
        status__in=['SCHEDULED', 'CONFIRMED'],
    ).update(status='NO_SHOW')

    logger.info(f'Marked {updated} appointments as NO_SHOW')
    return {'no_show_marked': updated}
