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

    def lock_account(self, minutes=30):
        """Lock the account for failed login attempts."""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])

    def reset_failed_attempts(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class LoginAttempt(models.Model):
    """
    Track all login attempts for forensic analysis and security monitoring.
    
    This model stores detailed information about every login attempt,
    including device fingerprint data, to help identify and prove
    malicious activity in case of a security incident.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User association (null for failed attempts with wrong email)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_attempts',
        help_text="User account (if authentication reached this stage)"
    )
    
    # Attempt result
    success = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the login attempt was successful"
    )
    
    failure_reason = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        choices=[
            ('INVALID_EMAIL', 'Email not found'),
            ('INVALID_PASSWORD', 'Wrong password'),
            ('ACCOUNT_LOCKED', 'Account locked'),
            ('ACCOUNT_DISABLED', 'Account disabled'),
            ('MFA_REQUIRED', 'MFA verification required'),
            ('MFA_FAILED', 'MFA verification failed'),
            ('BIOMETRIC_FAILED', 'Biometric verification failed'),
            ('DEVICE_BLACKLISTED', 'Device blacklisted'),
            ('SUSPICIOUS_ACTIVITY', 'Suspicious activity detected'),
            ('RATE_LIMITED', 'Rate limit exceeded'),
        ],
        help_text="Reason for failure (if applicable)"
    )
    
    # === Device Fingerprint Data ===
    # These fields are populated from DeviceFingerprint middleware
    device_fingerprint = models.ForeignKey(
        'security.DeviceFingerprint',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_attempts',
        help_text="Associated device fingerprint"
    )
    
    mac_address = models.CharField(
        max_length=17,
        null=True,
        blank=True,
        db_index=True,
        help_text="MAC address (critical forensic evidence)"
    )
    
    ip_address = models.GenericIPAddressField(
        protocol='both',
        db_index=True,
        help_text="Client IP address"
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User-Agent string"
    )
    
    platform = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Operating system platform"
    )
    
    browser = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Browser name"
    )
    
    screen_resolution = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Screen resolution"
    )
    
    browser_timezone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Browser timezone"
    )
    
    language = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Browser language"
    )
    
    canvas_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Canvas fingerprint hash"
    )
    
    webrtc_ip = models.GenericIPAddressField(
        protocol='both',
        null=True,
        blank=True,
        help_text="WebRTC leaked IP"
    )
    
    tls_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="TLS fingerprint (JA3)"
    )
    
    # === Authentication Method ===
    auth_method = models.CharField(
        max_length=50,
        choices=[
            ('PASSWORD', 'Password'),
            ('MFA', 'Multi-Factor Authentication'),
            ('BIOMETRIC', 'Biometric'),
            ('RECOVERY', 'Recovery Code'),
        ],
        help_text="Authentication method used"
    )
    
    # === Email/Identity Attempted ===
    email_attempted = models.EmailField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Email address used in login attempt"
    )
    
    # === Timestamps ===
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the attempt occurred"
    )
    
    # === Risk Assessment ===
    risk_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="Risk score 0-100 (calculated based on various factors)"
    )
    
    risk_factors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of risk factors detected"
    )
    
    # === Additional Evidence ===
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata about the login attempt"
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['success', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['mac_address']),
            models.Index(fields=['email_attempted', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['auth_method']),
            models.Index(fields=['risk_score']),
        ]
        verbose_name = "Login Attempt"
        verbose_name_plural = "Login Attempts"
    
    def __str__(self):
        status = "SUCCESS" if self.success else f"FAILED ({self.failure_reason})"
        return f"{self.email_attempted or 'Unknown'} - {status} at {self.timestamp}"
    
    def calculate_risk_score(self):
        """
        Calculate risk score based on various factors.
        This helps identify suspicious login attempts.
        """
        score = 0
        factors = []
        
        # Failed attempt
        if not self.success:
            score += 10
            factors.append('failed_attempt')
        
        # Check if MAC address is associated with previous failures
        if self.mac_address:
            failed_count = LoginAttempt.objects.filter(
                mac_address=self.mac_address,
                success=False,
                timestamp__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            if failed_count > 3:
                score += 20
                factors.append(f'multiple_failures_same_device ({failed_count})')
        
        # Check IP reputation (multiple failed attempts from same IP)
        if self.ip_address:
            ip_failures = LoginAttempt.objects.filter(
                ip_address=self.ip_address,
                success=False,
                timestamp__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            if ip_failures > 5:
                score += 25
                factors.append(f'suspicious_ip ({ip_failures} failures)')
        
        # Bot detection
        if self.user_agent:
            ua_lower = self.user_agent.lower()
            bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
            if any(pattern in ua_lower for pattern in bot_patterns):
                score += 15
                factors.append('bot_detected')
        
        # Unusual timezone (optional: compare with user's historical timezones)
        if self.browser_timezone and self.user:
            # Could add logic to check if timezone differs from user's norm
            pass
        
        # Missing critical fingerprint data (evasion attempt)
        missing_data = []
        if not self.mac_address:
            missing_data.append('mac_address')
        if not self.canvas_fingerprint:
            missing_data.append('canvas_fingerprint')
        if not self.tls_fingerprint:
            missing_data.append('tls_fingerprint')
        
        if len(missing_data) >= 2:
            score += 10
            factors.append(f'missing_fingerprint_data ({len(missing_data)} fields)')
        
        # Cap score at 100
        self.risk_score = min(100, score)
        self.risk_factors = factors
        
        return self.risk_score, self.risk_factors
    
    @classmethod
    def log_attempt(cls, request, success, email=None, user=None, 
                   failure_reason=None, auth_method='PASSWORD',
                   device_fp=None, extra_metadata=None):
        """
        Log a login attempt with comprehensive device fingerprint data.
        
        Args:
            request: Django request object
            success: Boolean indicating success
            email: Email attempted
            user: User object (if authenticated)
            failure_reason: Reason for failure
            auth_method: Authentication method used
            device_fp: DeviceFingerprint object from middleware
            extra_metadata: Additional metadata dict
        
        Returns:
            LoginAttempt instance
        """
        from apps.security.models import DeviceFingerprint
        
        # Extract device fingerprint data
        mac_address = None
        canvas_fp = None
        webrtc_ip = None
        tls_fp = None
        screen_res = None
        tz_offset = None
        language = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',')[0] if request else None
        
        # Try to get from headers (set by frontend JS)
        if request:
            mac_address = request.META.get('HTTP_X_DEVICE_MAC')
            canvas_fp = request.META.get('HTTP_X_CANVAS_FP')
            webrtc_ip = request.META.get('HTTP_X_WEBRTC_IP')
            tls_fp = request.META.get('HTTP_X_TLS_FP')
            screen_res = request.META.get('HTTP_X_SCREEN_RES')
            tz_offset = request.META.get('HTTP_X_TIMEZONE')
        
        # If we have a device fingerprint object, use its data
        if device_fp:
            mac_address = mac_address or device_fp.mac_address
            canvas_fp = canvas_fp or device_fp.canvas_fingerprint
            webrtc_ip = webrtc_ip or device_fp.webrtc_ip
            tls_fp = tls_fp or device_fp.tls_fingerprint
            screen_res = screen_res or device_fp.screen_resolution
            tz_offset = tz_offset or device_fp.browser_timezone
        
        # Get IP and User-Agent
        ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0') if request else '0.0.0.0'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        # Parse UA for platform/browser
        platform = 'Unknown'
        browser = 'Unknown'
        if request and hasattr(request, 'device_fp') and request.device_fp:
            platform = request.device_fp.platform
            browser = request.device_fp.browser
        else:
            ua_lower = user_agent.lower()
            if 'windows' in ua_lower:
                platform = 'Windows'
            elif 'mac os' in ua_lower or 'macos' in ua_lower:
                platform = 'macOS'
            elif 'linux' in ua_lower:
                platform = 'Linux'
            elif 'android' in ua_lower:
                platform = 'Android'
            elif 'iphone' in ua_lower or 'ipad' in ua_lower:
                platform = 'iOS'
            
            if 'chrome' in ua_lower and 'edg' not in ua_lower:
                browser = 'Chrome'
            elif 'firefox' in ua_lower:
                browser = 'Firefox'
            elif 'safari' in ua_lower and 'chrome' not in ua_lower:
                browser = 'Safari'
            elif 'edg' in ua_lower:
                browser = 'Edge'
        
        # Create login attempt record
        attempt = cls.objects.create(
            user=user,
            success=success,
            failure_reason=failure_reason,
            device_fingerprint=device_fp,
            mac_address=mac_address,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            platform=platform,
            browser=browser,
            screen_resolution=screen_res,
            browser_timezone=tz_offset,
            language=language,
            canvas_fingerprint=canvas_fp,
            webrtc_ip=webrtc_ip,
            tls_fingerprint=tls_fp,
            auth_method=auth_method,
            email_attempted=email,
            metadata=extra_metadata or {},
        )
        
        # Calculate and update risk score
        attempt.calculate_risk_score()
        attempt.save(update_fields=['risk_score', 'risk_factors'])
        
        return attempt


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
