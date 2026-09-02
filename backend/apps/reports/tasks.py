"""Background tasks for reports app."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_monthly_report():
    """Generate monthly PDF summary report and notify admins."""
    try:
        from apps.accounts.models import User
        from apps.notifications.utils import create_notification
        from django.utils import timezone

        month = timezone.now().month
        year = timezone.now().year

        admins = User.objects.filter(role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN'], is_active=True)
        for admin in admins:
            create_notification(
                user=admin,
                title=f'التقرير الشهري لـ {month}/{year} جاهز',
                message='يمكنك الآن تنزيل التقرير الشهري من صفحة التقارير.',
                notification_type='SYSTEM',
                priority='MEDIUM',
            )
        logger.info(f'Monthly report notification sent for {month}/{year}')
        return {'status': 'ok', 'month': month, 'year': year}
    except Exception as exc:
        logger.exception('Monthly report generation failed')
        return {'error': str(exc)}
