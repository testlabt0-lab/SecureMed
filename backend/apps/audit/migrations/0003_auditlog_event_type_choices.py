# Expands AuditLog.EventType with the ~25 event types the application was already
# emitting but never declared. CharField.choices is not a database constraint, so
# this is a state-only change at the SQL level — no data migration is needed and the
# column keeps max_length=40. The point is that the admin filters, the
# get_event_type_display() labels and every report built from the choices now see
# the events that actually exist.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_auditlog_hash_auditlog_previous_hash'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='event_type',
            field=models.CharField(choices=[
                ('LOGIN_SUCCESS', 'تسجيل دخول ناجح'),
                ('LOGIN_FAILED', 'فشل تسجيل الدخول'),
                ('LOGOUT', 'تسجيل خروج'),
                ('BIOMETRIC_LOGIN_SUCCESS', 'دخول بيوميتري ناجح'),
                ('BIOMETRIC_ENROLLMENT', 'تسجيل بصمة'),
                ('BIOMETRIC_CHALLENGE_REQUESTED', 'طلب تحدي بيوميتري'),
                ('BIOMETRIC_REVOKED', 'إلغاء بصمة'),
                ('PASSWORD_CHANGED', 'تغيير كلمة المرور'),
                ('PERMISSION_GRANTED', 'منح صلاحية'),
                ('PERMISSION_MODIFIED', 'تعديل صلاحية'),
                ('PERMISSION_REVOKED', 'سحب صلاحية'),
                ('MEMBERSHIP_CANCELLED', 'إلغاء عضوية'),
                ('CHANNEL_CREATED', 'إنشاء قناة'),
                ('CHANNEL_CLOSED', 'إغلاق قناة'),
                ('CHANNEL_MESSAGE_SENT', 'إرسال رسالة في قناة'),
                ('PATIENT_DATA_ACCESSED', 'الوصول لبيانات مريض'),
                ('MEDICAL_RECORD_CREATED', 'إنشاء سجل طبي'),
                ('PORT_SCAN_EXECUTED', 'تنفيذ مسح منافذ'),
                ('VULN_SCAN_EXECUTED', 'تنفيذ فحص ثغرات'),
                ('WAF_BLOCKED', 'حظر WAF'),
                ('INVITATION_SENT', 'إرسال دعوة'),
                ('INVITATION_ACCEPTED', 'قبول دعوة'),
                ('INVITATION_REJECTED', 'رفض دعوة'),
                ('USER_DEACTIVATED', 'إلغاء تفعيل مستخدم'),
                ('MFA_ENABLED', 'تفعيل التحقق بخطوتين'),
                ('MFA_DISABLED', 'تعطيل التحقق بخطوتين'),
                ('MFA_LOGIN_SUCCESS', 'دخول ناجح بالتحقق بخطوتين'),
                ('MFA_LOGIN_FAILED', 'فشل التحقق بخطوتين'),
                ('PASSWORD_RESET_REQUESTED', 'طلب استعادة كلمة المرور'),
                ('PASSWORD_RESET_COMPLETED', 'إتمام استعادة كلمة المرور'),
                ('DEVICE_BLOCKED', 'حظر جهاز'),
                ('SUSPICIOUS_ACTIVITY', 'نشاط مشبوه'),
                ('SESSION_HIJACK_DETECTED', 'اكتشاف سرقة جلسة'),
                ('DATA_EXPORT', 'تصدير بيانات'),
                ('BULK_DELETE', 'حذف جماعي'),
                ('CONFIG_CHANGED', 'تغيير إعدادات'),
                ('BACKUP_CREATED', 'إنشاء نسخة احتياطية'),
                ('BACKUP_RESTORED', 'استعادة نسخة احتياطية'),
                ('FILE_UPLOADED', 'رفع ملف'),
                ('FILE_DOWNLOADED', 'تحميل ملف'),
                ('DATA_CREATED', 'إنشاء بيانات'),
                ('DATA_MODIFIED', 'تعديل بيانات'),
                ('DATA_DELETED', 'حذف بيانات'),
                ('DATA_ACCESSED', 'قراءة بيانات'),
                ('SYSTEM_EVENT', 'حدث نظام'),
                ('LOGIN_CHALLENGE', 'طلب تحقق إضافي عند الدخول'),
                ('USER_ACTIVATED', 'تفعيل مستخدم'),
                ('BASIN_CREATED', 'إنشاء حوض صحي'),
                ('BASIN_UPDATED', 'تعديل حوض صحي'),
                ('BASIN_DELETED', 'حذف حوض صحي'),
                ('BASIN_MODULE_TOGGLED', 'تفعيل/تعطيل وحدة في حوض'),
                ('BASIN_TYPE_DEFAULTS_APPLIED', 'تطبيق إعدادات نوع الحوض'),
                ('APPOINTMENT_CREATED', 'إنشاء موعد'),
                ('APPOINTMENT_CONFIRMED', 'تأكيد موعد'),
                ('APPOINTMENT_COMPLETED', 'إكمال موعد'),
                ('APPOINTMENT_CANCELLED', 'إلغاء موعد'),
                ('APPOINTMENT_DELETED', 'حذف موعد'),
                ('PRESCRIPTION_DISPENSED', 'صرف وصفة طبية'),
                ('PHARMACY_STOCK_CHANGE', 'تغيير مخزون الصيدلية'),
                ('INVOICE_PAID', 'سداد فاتورة'),
                ('FHIR_PATIENT_EXPORT', 'تصدير مريض بصيغة FHIR'),
                ('AI_ASSISTANT_QUERY', 'استعلام المساعد الذكي'),
                ('AI_ASSISTANT_FAILED', 'فشل المساعد الذكي'),
                ('AI_SUMMARY_GENERATED', 'توليد ملخص ذكي'),
                ('AI_SUMMARY_FAILED', 'فشل توليد الملخص الذكي'),
                ('MONTHLY_REPORT_EMAILED', 'إرسال التقرير الشهري'),
                ('SCHEDULED_REPORT_SENT', 'إرسال تقرير مجدول'),
                ('TEST_EMAIL_SENT', 'إرسال بريد اختباري'),
            ], db_index=True, max_length=40, verbose_name='نوع الحدث'),
        ),
    ]
