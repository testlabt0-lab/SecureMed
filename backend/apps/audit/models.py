"""
Audit log model for tracking all security events.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class AuditLog(models.Model):
    """
    Audit log for all security-relevant actions.
    Required for HIPAA compliance and DevSecOps monitoring.
    """

    class EventType(models.TextChoices):
        # Authentication events
        LOGIN_SUCCESS = 'LOGIN_SUCCESS', _('تسجيل دخول ناجح')
        LOGIN_FAILED = 'LOGIN_FAILED', _('فشل تسجيل الدخول')
        LOGOUT = 'LOGOUT', _('تسجيل خروج')
        BIOMETRIC_LOGIN_SUCCESS = 'BIOMETRIC_LOGIN_SUCCESS', _('دخول بيوميتري ناجح')
        BIOMETRIC_ENROLLMENT = 'BIOMETRIC_ENROLLMENT', _('تسجيل بصمة')
        BIOMETRIC_CHALLENGE_REQUESTED = 'BIOMETRIC_CHALLENGE_REQUESTED', _('طلب تحدي بيوميتري')
        BIOMETRIC_REVOKED = 'BIOMETRIC_REVOKED', _('إلغاء بصمة')
        PASSWORD_CHANGED = 'PASSWORD_CHANGED', _('تغيير كلمة المرور')

        # Authorization events
        PERMISSION_GRANTED = 'PERMISSION_GRANTED', _('منح صلاحية')
        PERMISSION_MODIFIED = 'PERMISSION_MODIFIED', _('تعديل صلاحية')
        PERMISSION_REVOKED = 'PERMISSION_REVOKED', _('سحب صلاحية')
        MEMBERSHIP_CANCELLED = 'MEMBERSHIP_CANCELLED', _('إلغاء عضوية')

        # Channel events
        CHANNEL_CREATED = 'CHANNEL_CREATED', _('إنشاء قناة')
        CHANNEL_CLOSED = 'CHANNEL_CLOSED', _('إغلاق قناة')
        CHANNEL_MESSAGE_SENT = 'CHANNEL_MESSAGE_SENT', _('إرسال رسالة في قناة')

        # Data access events
        PATIENT_DATA_ACCESSED = 'PATIENT_DATA_ACCESSED', _('الوصول لبيانات مريض')
        MEDICAL_RECORD_CREATED = 'MEDICAL_RECORD_CREATED', _('إنشاء سجل طبي')

        # Security tool events
        PORT_SCAN_EXECUTED = 'PORT_SCAN_EXECUTED', _('تنفيذ مسح منافذ')
        VULN_SCAN_EXECUTED = 'VULN_SCAN_EXECUTED', _('تنفيذ فحص ثغرات')
        WAF_BLOCKED = 'WAF_BLOCKED', _('حظر WAF')

        # Invitation events
        INVITATION_SENT = 'INVITATION_SENT', _('إرسال دعوة')
        INVITATION_ACCEPTED = 'INVITATION_ACCEPTED', _('قبول دعوة')
        INVITATION_REJECTED = 'INVITATION_REJECTED', _('رفض دعوة')

        # User management
        USER_DEACTIVATED = 'USER_DEACTIVATED', _('إلغاء تفعيل مستخدم')

        # Two-factor authentication
        MFA_ENABLED = 'MFA_ENABLED', _('تفعيل التحقق بخطوتين')
        MFA_DISABLED = 'MFA_DISABLED', _('تعطيل التحقق بخطوتين')
        MFA_LOGIN_SUCCESS = 'MFA_LOGIN_SUCCESS', _('دخول ناجح بالتحقق بخطوتين')
        MFA_LOGIN_FAILED = 'MFA_LOGIN_FAILED', _('فشل التحقق بخطوتين')

        # Password reset flow
        PASSWORD_RESET_REQUESTED = 'PASSWORD_RESET_REQUESTED', _('طلب استعادة كلمة المرور')
        PASSWORD_RESET_COMPLETED = 'PASSWORD_RESET_COMPLETED', _('إتمام استعادة كلمة المرور')

    class Severity(models.TextChoices):
        INFO = 'INFO', _('معلومة')
        WARNING = 'WARNING', _('تحذير')
        CRITICAL = 'CRITICAL', _('حرج')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='audit_logs',
        verbose_name=_('المستخدم')
    )
    event_type = models.CharField(
        _('نوع الحدث'), max_length=40,
        choices=EventType.choices, db_index=True
    )
    severity = models.CharField(
        _('الخطورة'), max_length=10,
        choices=Severity.choices, default=Severity.INFO
    )
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    path = models.CharField(_('المسار'), max_length=255, blank=True)
    method = models.CharField(_('الطريقة'), max_length=10, blank=True)
    details = models.JSONField(_('التفاصيل'), default=dict)
    timestamp = models.DateTimeField(_('الوقت'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('سجل تدقيق')
        verbose_name_plural = _('سجلات التدقيق')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['severity', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.timestamp}'
