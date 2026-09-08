"""
Notifications model for SecureMed.
Real-time notifications system for security alerts, channel updates, etc.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """
    User notification system.
    Supports real-time delivery via WebSocket and email.
    """

    class Type(models.TextChoices):
        CHANNEL_INVITATION = 'CHANNEL_INVITATION', _('دعوة لقناة')
        CHANNEL_UPDATE = 'CHANNEL_UPDATE', _('تحديث قناة')
        CHANNEL_CLOSED = 'CHANNEL_CLOSED', _('إغلاق قناة')
        PERMISSION_GRANTED = 'PERMISSION_GRANTED', _('منح صلاحية')
        PERMISSION_REVOKED = 'PERMISSION_REVOKED', _('سحب صلاحية')
        NEW_MEDICAL_RECORD = 'NEW_MEDICAL_RECORD', _('سجل طبي جديد')
        CRITICAL_PATIENT = 'CRITICAL_PATIENT', _('حالة مريض حرجة')
        SECURITY_ALERT = 'SECURITY_ALERT', _('تنبيه أمني')
        BIOMETRIC_ENROLLED = 'BIOMETRIC_ENROLLED', _('تسجيل بصمة')
        LOGIN_ALERT = 'LOGIN_ALERT', _('تنبيه دخول')
        SYSTEM_ANNOUNCEMENT = 'SYSTEM_ANNOUNCEMENT', _('إعلان نظامي')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('منخفضة')
        MEDIUM = 'MEDIUM', _('متوسطة')
        HIGH = 'HIGH', _('عالية')
        CRITICAL = 'CRITICAL', _('حرجة')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('المستلم')
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_notifications',
        verbose_name=_('المرسل')
    )
    notification_type = models.CharField(
        _('النوع'), max_length=30, choices=Type.choices, db_index=True
    )
    priority = models.CharField(
        _('الأولوية'), max_length=10,
        choices=Priority.choices, default=Priority.MEDIUM
    )
    title = models.CharField(_('العنوان'), max_length=255)
    message = models.TextField(_('الرسالة'))
    data = models.JSONField(_('البيانات الإضافية'), default=dict, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.CharField(max_length=36, blank=True)
    is_read = models.BooleanField(_('مقروءة'), default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    is_email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('إشعار')
        verbose_name_plural = _('الإشعارات')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
        ]

    def __str__(self):
        return f'{self.title} → {self.recipient.email}'

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """User notification preferences."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    email_channel_updates = models.BooleanField(default=True)
    email_security_alerts = models.BooleanField(default=True)
    email_medical_records = models.BooleanField(default=False)
    push_channel_updates = models.BooleanField(default=True)
    push_security_alerts = models.BooleanField(default=True)
    push_medical_records = models.BooleanField(default=True)
    in_app_all = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('تفضيلات الإشعارات')
        verbose_name_plural = _('تفضيلات الإشعارات')


class PushToken(models.Model):
    """FCM device token registered by a client for push delivery.

    A device registers its token after login (and re-registers whenever FCM
    rotates it). Delivery is best-effort and only happens when FCM credentials
    are configured; the notification rows are the durable record either way.
    Tokens are stored hashed-indexed but retrievable — FCM needs the literal
    token to send — so uniqueness is enforced on the token itself and stale
    rows are simply replaced on re-registration.
    """
    platform = models.CharField(
        _('المنصة'), max_length=10,
        choices=[('ANDROID', 'Android'), ('WEB', 'Web'), ('IOS', 'iOS')],
        default='ANDROID',
    )
    token = models.TextField(_('رمز الإشعارات'), unique=True)
    device_fingerprint = models.CharField(_('بصمة الجهاز'), max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='push_tokens',
        verbose_name=_('المستخدم'),
    )
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('رمز إشعارات')
        verbose_name_plural = _('رموز الإشعارات')
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f'{self.platform} → {self.user.email} ({self.token[:16]}…)'


class EmailLog(models.Model):
    """Log of sent emails for audit purposes."""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('في الانتظار')
        SENT = 'SENT', _('مُرسل')
        FAILED = 'FAILED', _('فشل')
        DELIVERED = 'DELIVERED', _('تم التسليم')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='email_logs'
    )
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', '-created_at'])]
