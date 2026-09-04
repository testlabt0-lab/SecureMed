from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.notifications.utils import send_notification
from apps.security.models import BlockedDevice
from apps.appointments.models import Appointment
from apps.telemedicine.models import Consultation
from apps.lab.models import LabOrder, LabResult
from apps.wards.models import BedAssignment
from apps.billing.models import Invoice
from apps.patients.models import Patient

User = get_user_model()

# Security: Device Blocked
@receiver(post_save, sender=BlockedDevice)
def notify_device_blocked(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(role__in=['SUPER_ADMIN', 'AUDITOR'])
        for admin in admins:
            send_notification(
                recipient=admin,
                title="تنبيه أمني: تم حظر جهاز",
                message=f"تم حظر جهاز جديد (بصمة: {instance.device_fingerprint}) للسبب: {instance.reason}",
                notification_type='SECURITY_ALERT'
            )

# Users: New user registered / Account activated
@receiver(pre_save, sender=User)
def capture_user_old_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            instance._old_is_active = old_instance.is_active
        except User.DoesNotExist:
            instance._old_is_active = None
    else:
        instance._old_is_active = None

@receiver(post_save, sender=User)
def notify_user_changes(sender, instance, created, **kwargs):
    if created:
        admins = User.objects.filter(role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN'])
        for admin in admins:
            send_notification(
                recipient=admin,
                title="مستخدم جديد",
                message=f"تم تسجيل مستخدم جديد في النظام: {instance.full_name} ({instance.get_role_display()})",
                notification_type='SYSTEM'
            )
    else:
        if hasattr(instance, '_old_is_active') and not instance._old_is_active and instance.is_active:
            send_notification(
                recipient=instance,
                title="تم تفعيل حسابك",
                message="مرحباً، تم تفعيل حسابك بنجاح. يمكنك الآن استخدام النظام.",
                notification_type='SYSTEM'
            )

# Appointments: New Appointment
@receiver(post_save, sender=Appointment)
def notify_new_appointment(sender, instance, created, **kwargs):
    if created:
        recipients = set([instance.doctor])
        admins_receptionists = User.objects.filter(role__in=['HOSPITAL_ADMIN', 'RECEPTIONIST'])
        recipients.update(list(admins_receptionists))
        
        for user in recipients:
            send_notification(
                recipient=user,
                title="موعد جديد",
                message=f"تم حجز موعد جديد للمريض {instance.patient} مع د. {instance.doctor.full_name}",
                notification_type='APPOINTMENT'
            )

# Telemedicine: New Consultation
@receiver(post_save, sender=Consultation)
def notify_new_consultation(sender, instance, created, **kwargs):
    if created:
        send_notification(
            recipient=instance.doctor,
            title="جلسة افتراضية جديدة",
            message=f"تم جدولة جلسة عن بعد مع المريض {instance.patient}",
            notification_type='SYSTEM'
        )
        if hasattr(instance.patient, 'user') and instance.patient.user:
            send_notification(
                recipient=instance.patient.user,
                title="تأكيد العيادة الافتراضية",
                message=f"تم تأكيد جلستك الافتراضية مع د. {instance.doctor.full_name}",
                notification_type='SYSTEM'
            )

# Lab: New Order & Result
@receiver(post_save, sender=LabOrder)
def notify_new_lab_order(sender, instance, created, **kwargs):
    if created:
        lab_techs = User.objects.filter(role='LAB_TECH')
        for tech in lab_techs:
            send_notification(
                recipient=tech,
                title="طلب تحليل جديد",
                message=f"طلب تحليل جديد للمريض {instance.patient} من قبل د. {instance.doctor.full_name}",
                notification_type='LAB_RESULT'
            )

@receiver(post_save, sender=LabResult)
def notify_new_lab_result(sender, instance, created, **kwargs):
    if created:
        send_notification(
            recipient=instance.order.doctor,
            title="نتيجة تحليل جاهزة",
            message=f"تم إصدار نتيجة التحليل للمريض {instance.order.patient}",
            notification_type='LAB_RESULT'
        )

# Wards: New Admission
@receiver(post_save, sender=BedAssignment)
def notify_new_admission(sender, instance, created, **kwargs):
    if created:
        nurses_admins = User.objects.filter(role__in=['NURSE', 'HOSPITAL_ADMIN'])
        for user in nurses_admins:
            send_notification(
                recipient=user,
                title="حالة تنويم جديدة",
                message=f"تم تخصيص السرير {instance.bed} للمريض {instance.patient}",
                notification_type='SYSTEM'
            )

# Billing: New Invoice
@receiver(post_save, sender=Invoice)
def notify_new_invoice(sender, instance, created, **kwargs):
    if created:
        accountants = User.objects.filter(role__in=['ACCOUNTANT', 'RECEPTIONIST'])
        for user in accountants:
            send_notification(
                recipient=user,
                title="فاتورة جديدة",
                message=f"تم إصدار فاتورة جديدة للمريض {instance.patient} بقيمة {instance.total_amount}",
                notification_type='SYSTEM'
            )

# Patients: New Patient
@receiver(post_save, sender=Patient)
def notify_new_patient(sender, instance, created, **kwargs):
    if created:
        receptionists = User.objects.filter(role__in=['RECEPTIONIST', 'HOSPITAL_ADMIN'])
        for user in receptionists:
            send_notification(
                recipient=user,
                title="تسجيل مريض جديد",
                message=f"تم تسجيل المريض {instance.full_name} في النظام",
                notification_type='SYSTEM'
            )
