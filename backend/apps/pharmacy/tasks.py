from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import models
from datetime import timedelta
from apps.pharmacy.models import Medication
from apps.notifications.utils import send_notification

User = get_user_model()

@shared_task
def check_pharmacy_inventory():
    """
    Checks the pharmacy inventory for medications that are low in stock
    or expiring soon, and notifies pharmacists and admins.
    """
    low_stock_meds = Medication.objects.filter(stock_quantity__lte=models.F('reorder_level'), is_active=True)
    
    thirty_days_from_now = timezone.now().date() + timedelta(days=30)
    expiring_meds = Medication.objects.filter(expiry_date__lte=thirty_days_from_now, is_active=True)
    
    if not low_stock_meds.exists() and not expiring_meds.exists():
        return "No notifications needed."

    message_parts = []
    
    if low_stock_meds.exists():
        message_parts.append("الأدوية التي أوشكت على النفاد:")
        for med in low_stock_meds:
            message_parts.append(f"- {med.name} (الكمية: {med.stock_quantity})")
            
    if expiring_meds.exists():
        message_parts.append("\nالأدوية القريبة من الانتهاء:")
        for med in expiring_meds:
            message_parts.append(f"- {med.name} (تاريخ الانتهاء: {med.expiry_date})")

    final_message = "\n".join(message_parts)

    recipients = User.objects.filter(role__in=['PHARMACIST', 'HOSPITAL_ADMIN', 'SUPER_ADMIN'])
    
    for user in recipients:
        send_notification(
            recipient=user,
            title="تنبيه المخزون والصلاحية (الصيدلية)",
            message=final_message,
            notification_type='SYSTEM'
        )

    return f"Sent inventory alerts to {recipients.count()} users."
