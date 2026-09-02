"""
Background tasks for audit: daily security digest email to admins.
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_security_digest():
    """Send daily security digest to SUPER_ADMIN and AUDITOR users."""
    try:
        from apps.accounts.models import User
        from apps.audit.models import AuditLog
        from django.core.mail import send_mail
        from django.conf import settings

        yesterday = timezone.now() - timedelta(days=1)
        logs = AuditLog.objects.filter(created_at__gte=yesterday)

        total = logs.count()
        critical = logs.filter(severity='CRITICAL').count()
        high = logs.filter(severity='HIGH').count()
        failed_logins = logs.filter(event_type='LOGIN_FAILURE').count()
        blocked_attacks = logs.filter(event_type='WAF_BLOCK').count()

        subject = f'[SecureMed] تقرير أمان يومي — {timezone.now().date()}'
        message = f"""
تقرير الأمان اليومي — SecureMed
تاريخ: {timezone.now().date()}

ملخص الأحداث (آخر 24 ساعة):
━━━━━━━━━━━━━━━━━━━━━━━━━
• إجمالي الأحداث: {total}
• أحداث حرجة (CRITICAL): {critical}
• أحداث عالية (HIGH): {high}
• محاولات دخول فاشلة: {failed_logins}
• هجمات محظورة (WAF): {blocked_attacks}

للتفاصيل الكاملة: راجع لوحة سجلات التدقيق.
        """.strip()

        admins = User.objects.filter(
            role__in=['SUPER_ADMIN', 'AUDITOR'],
            is_active=True,
        ).values_list('email', flat=True)

        for email in admins:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )

        logger.info(f'Security digest sent to {len(list(admins))} admins')
        return {'status': 'sent', 'events': total}
    except Exception as exc:
        logger.exception('Security digest failed')
        return {'error': str(exc)}
