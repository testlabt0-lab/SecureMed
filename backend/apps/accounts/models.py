"""
User models for SecureMed.

Implements:
- Custom User model with role-based access
- Biometric authentication storage (security requirement #4: fingerprint login)
- Per-channel role assignment (DV requirement: single role per user per channel)
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.security.crypto import encrypt_field, decrypt_field


class UserManager(BaseUserManager):
    """Custom manager for User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email is required'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'SUPER_ADMIN')
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with role-based access control.

    Implements the DV requirement: each user has exactly ONE system-level role
    (per-channel roles are managed through ChannelMembership).
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', _('مدير النظام')
        HOSPITAL_ADMIN = 'HOSPITAL_ADMIN', _('مدير المستشفى')
        DOCTOR = 'DOCTOR', _('طبيب')
        NURSE = 'NURSE', _('ممرض/ممرضة')
        LAB_TECH = 'LAB_TECH', _('فني مختبر')
        PHARMACIST = 'PHARMACIST', _('صيدلي')
        AUDITOR = 'AUDITOR', _('مراجع أمني')
        PATIENT = 'PATIENT', _('مريض')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Use email instead
    email = models.EmailField(_('البريد الإلكتروني'), unique=True, db_index=True)
    full_name = models.CharField(_('الاسم الكامل'), max_length=255)
    phone = models.CharField(_('الهاتف'), max_length=20, blank=True)
    role = models.CharField(
        _('الدور'), max_length=20, choices=Role.choices, default=Role.PATIENT
    )
    license_number = models.CharField(
        _('رقم الترخيص الطبي'), max_length=50, blank=True, null=True
    )
    department = models.CharField(_('القسم'), max_length=100, blank=True)
    specialization = models.CharField(_('التخصص'), max_length=100, blank=True)

    # Basin linkage (plan requirement: the system must be linked to basins)
    basin = models.ForeignKey(
        'basins.Basin', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='users', verbose_name=_('الحوض الصحي'),
    )

    # Security fields
    is_biometric_enabled = models.BooleanField(
        _('المصادقة البيومترية مفعلة'), default=False
    )
    biometric_enrolled_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    mfa_secret = models.CharField(max_length=255, blank=True)  # Encrypted

    # Two-factor authentication (TOTP)
    mfa_enabled = models.BooleanField(_('التحقق بخطوتين مفعل'), default=False)
    mfa_created_at = models.DateTimeField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'role']

    objects = UserManager()

    class Meta:
        verbose_name = _('مستخدم')
        verbose_name_plural = _('المستخدمون')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def is_medical_staff(self):
        return self.role in [
            self.Role.DOCTOR, self.Role.NURSE,
            self.Role.LAB_TECH, self.Role.PHARMACIST
        ]

    @property
    def is_locked(self):
        if self.locked_until and self.locked_until > timezone.now():
            return True
        return False

    def lock_account(self):
        """Lock the account using exponential backoff based on failed attempts."""
        # Base lock time is 5 minutes, doubling each time after the 3rd attempt
        # 3 attempts -> 5 mins, 4 attempts -> 10 mins, 5 attempts -> 20 mins, etc.
        power = max(0, self.failed_login_attempts - 3)
        minutes = 5 * (2 ** power)
        
        # Max lock out time of 24 hours
        minutes = min(minutes, 1440)
        
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])

    def reset_failed_attempts(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class BiometricProfile(models.Model):
    """
    Stores biometric authentication data.

    Security requirement #4: تسجيل الدخول بالبصمة + الاعتماد على البصمة
    Implements secure biometric authentication using:
    - Salted hash of fingerprint template (never store raw biometric data)
    - Challenge-response mechanism
    - Per-device binding
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='biometric_profiles',
        verbose_name=_('المستخدم')
    )
    device_id = models.CharField(_('معرف الجهاز'), max_length=255)
    device_name = models.CharField(_('اسم الجهاز'), max_length=255, blank=True)
    platform = models.CharField(
        _('المنصة'), max_length=20,
        choices=[('ANDROID', 'Android'), ('IOS', 'iOS'), ('WEB', 'Web')]
    )

    # Encrypted biometric template hash (NEVER store raw biometric data)
    biometric_hash = models.TextField(_('الهاش البيوميتري المشفر'))
    salt = models.CharField(_('الملح'), max_length=64)

    # Challenge-response keys (for secure authentication)
    public_key = models.TextField(_('المفتاح العام'), blank=True)
    private_key_encrypted = models.TextField(_('المفتاح الخاص المشفر'), blank=True)

    is_active = models.BooleanField(_('نشط'), default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('الملف البيوميتري')
        verbose_name_plural = _('الملفات البيومترية')
        unique_together = ['user', 'device_id']
        indexes = [
            models.Index(fields=['user', 'device_id']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f'{self.user.full_name} - {self.platform} ({self.device_name})'


class BiometricChallenge(models.Model):
    """
    One-time challenge for biometric authentication.
    Prevents replay attacks by using challenge-response mechanism.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='biometric_challenges'
    )
    challenge = models.TextField(_('التحدي'))
    expected_response = models.TextField(_('الرد المتوقع المشفر'))
    expires_at = models.DateTimeField(_('تنتهي في'))
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'used', 'expires_at'])]

    @property
    def is_valid(self):
        return (
            not self.used and
            self.expires_at > timezone.now()
        )

    def mark_used(self):
        self.used = True
        self.save(update_fields=['used'])
