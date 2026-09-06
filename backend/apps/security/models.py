import uuid
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class BlocklistQuerySet(models.QuerySet):
    """Shared filtering for the two blocklists.

    ``is_active`` alone is not enough: a block with ``expires_at`` in the past is
    still ``is_active=True`` in the database, so filtering on the flag by itself
    keeps enforcing blocks that were meant to be temporary. Every enforcement
    path must go through :meth:`enforceable`.
    """

    def enforceable(self, at=None):
        """Blocks that should be enforced right now."""
        moment = at or timezone.now()
        return self.filter(is_active=True).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=moment)
        )

    def expired(self, at=None):
        moment = at or timezone.now()
        return self.filter(expires_at__isnull=False, expires_at__lte=moment)


class DeviceRegistry(models.Model):
    """Registry of known devices for a user."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registered_devices'
    )
    device_fingerprint = models.CharField(_('بصمة الجهاز'), max_length=255, db_index=True)
    mac_address = models.CharField(_('عنوان MAC'), max_length=100, blank=True)
    os_info = models.CharField(_('نظام التشغيل'), max_length=255, blank=True)
    browser_info = models.CharField(_('المتصفح'), max_length=255, blank=True)
    last_ip_address = models.GenericIPAddressField(_('آخر عنوان IP'), null=True, blank=True)
    location = models.CharField(_('الموقع الجغرافي'), max_length=255, blank=True)
    is_trusted = models.BooleanField(_('موثوق'), default=False)
    modules_activated = models.JSONField(_('مModules مففعل'), default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('جهاز مسجل')
        verbose_name_plural = _('الأجهزة المسجلة')
        unique_together = ['user', 'device_fingerprint']
        ordering = ['-last_login']

    def __str__(self):
        return f"{self.user.email} - {self.os_info} - {self.browser_info}"


class BlockedDevice(models.Model):
    """Blocked devices (by fingerprint or MAC).

    A block created by the automatic failed-login lockout used to be permanent —
    the model had no expiry at all — so a shared browser fingerprint or a typo'd
    password could lock a legitimate device out forever with no automatic path
    back. ``expires_at`` is now honoured the same way ``BlockedIP`` honours it;
    ``null`` still means "until an administrator lifts it".
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_fingerprint = models.CharField(_('بصمة الجهاز'), max_length=255, blank=True, db_index=True)
    mac_address = models.CharField(_('عنوان MAC'), max_length=100, blank=True, db_index=True)
    reason = models.TextField(_('سبب الحظر'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_devices'
    )

    objects = BlocklistQuerySet.as_manager()

    class Meta:
        verbose_name = _('جهاز محظور')
        verbose_name_plural = _('الأجهزة المحظورة')
        ordering = ['-created_at']

    def __str__(self):
        return f"Blocked: {self.device_fingerprint or self.mac_address}"

    @property
    def is_enforceable(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())


class BlockedIP(models.Model):
    """Blocked IP addresses."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), unique=True, db_index=True)
    reason = models.TextField(_('سبب الحظر'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = BlocklistQuerySet.as_manager()

    class Meta:
        verbose_name = _('IP محظور')
        verbose_name_plural = _('عناوين IP المحظورة')

    def __str__(self):
        return f"Blocked IP: {self.ip_address}"

    @property
    def is_enforceable(self):
        return self.is_active and (self.expires_at is None or self.expires_at > timezone.now())


class LoginHistory(models.Model):
    """Detailed login history for security auditing."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_history'
    )
    ip_address = models.GenericIPAddressField(_('عنوان IP'), null=True, blank=True)
    device_fingerprint = models.CharField(_('بصمة الجهاز'), max_length=255, blank=True)
    os_info = models.CharField(_('نظام التشغيل'), max_length=255, blank=True)
    browser_info = models.CharField(_('المتصفح'), max_length=255, blank=True)
    location = models.CharField(_('الموقع الجغرافي'), max_length=255, blank=True)
    is_success = models.BooleanField(_('ناجح'), default=True)
    failure_reason = models.CharField(_('سبب الفشل'), max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('سجل دخول')
        verbose_name_plural = _('تاريخ تسجيل الدخول')
        ordering = ['-timestamp']

    def __str__(self):
        status = 'Success' if self.is_success else f'Failed: {self.failure_reason}'
        return f"{self.user.email} - {status} at {self.timestamp}"


class DeviceVerificationOTP(models.Model):
    """OTP codes for device/location verification."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    device_fingerprint = models.CharField(max_length=255)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        from django.utils import timezone
        import datetime
        return not self.is_used and (timezone.now() - self.created_at) < datetime.timedelta(minutes=10)
