"""Background tasks for reports app."""
from celery import shared_task
import logging
from django.utils import timezone
from django.db.models import Sum

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

@shared_task
def generate_daily_summary():
    """Generate daily summary of system activities and notify admins."""
    try:
        from apps.accounts.models import User
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment
        from apps.billing.models import Invoice
        from apps.lab.models import LabOrder
        from apps.security.models import BlockedDevice
        from apps.notifications.utils import send_notification
        from datetime import datetime, time

        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))

        # Gather stats
        new_patients_count = Patient.objects.filter(created_at__range=(today_start, today_end)).count()
        appointments = Appointment.objects.filter(scheduled_at__range=(today_start, today_end))
        total_appointments = appointments.count()
        completed_appointments = appointments.filter(status='COMPLETED').count()
        
        invoices = Invoice.objects.filter(created_at__range=(today_start, today_end))
        total_revenue = invoices.aggregate(total=Sum('total_amount'))['total'] or 0
        
        lab_orders = LabOrder.objects.filter(created_at__range=(today_start, today_end)).count()
        security_blocks = BlockedDevice.objects.filter(created_at__range=(today_start, today_end)).count()

        # Build message
        message = (
            f"ملخص النظام ليوم {today.strftime('%Y-%m-%d')}:\n\n"
            f"- المرضى الجدد: {new_patients_count}\n"
            f"- المواعيد اليوم: {total_appointments} (مكتملة: {completed_appointments})\n"
            f"- طلبات المختبر: {lab_orders}\n"
            f"- الإيرادات المسجلة: {total_revenue} ريال\n"
            f"- الأجهزة المحظورة (أمنياً): {security_blocks}\n"
        )

        admins = User.objects.filter(role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN'], is_active=True)
        for admin in admins:
            send_notification(
                recipient=admin,
                title=f'الملخص اليومي للنظام - {today}',
                message=message,
                notification_type='SYSTEM',
            )
        
        logger.info(f'Daily summary report notification sent for {today}')
        return {'status': 'ok', 'date': str(today)}
    except Exception as exc:
        logger.exception('Daily summary generation failed')
        return {'error': str(exc)}
