import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


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
    """Blocked devices (by fingerprint or MAC)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_fingerprint = models.CharField(_('بصمة الجهاز'), max_length=255, blank=True, db_index=True)
    mac_address = models.CharField(_('عنوان MAC'), max_length=100, blank=True, db_index=True)
    reason = models.TextField(_('سبب الحظر'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blocked_devices'
    )

    class Meta:
        verbose_name = _('جهاز محظور')
        verbose_name_plural = _('الأجهزة المحظورة')
        ordering = ['-created_at']

    def __str__(self):
        return f"Blocked: {self.device_fingerprint or self.mac_address}"


class BlockedIP(models.Model):
    """Blocked IP addresses."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField(_('عنوان IP'), unique=True, db_index=True)
    reason = models.TextField(_('سبب الحظر'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)
    expires_at = models.DateTimeField(_('ينتهي في'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('IP محظور')
        verbose_name_plural = _('عناوين IP المحظورة')

    def __str__(self):
        return f"Blocked IP: {self.ip_address}"


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
