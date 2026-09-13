"""
Patient and MedicalRecord models.
"""
import uuid
import os
import mimetypes
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.security.crypto import encrypt_field, decrypt_field

VALID_UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.dicom', '.dcm']


def validate_file_extension(value):
    """Validate an upload by extension *and* by actual content.

    Kept under its original name on purpose: the name is recorded in migration
    patients.0001_initial as part of the file field definition, so extending
    the body adds content validation without making the model state diverge from the
    migrations — no makemigrations run is needed.
    """
    from apps.core.uploads import validate_upload_content
    validate_upload_content(value, VALID_UPLOAD_EXTENSIONS)


def _read_head(value):
    """First bytes of an upload, leaving the file positioned back at the start.

    Kept for sniff_mime_type(); the actual reading logic lives in apps.core.uploads.
    """
    from apps.core.uploads import _read_head as _shared_read_head
    return _shared_read_head(value)


def sniff_mime_type(value):
    """MIME type from content, falling back to the extension."""
    head = _read_head(value)
    if head:
        if head.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if head.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if head.startswith((b'GIF87a', b'GIF89a')):
            return 'image/gif'
        if head.startswith(b'%PDF-'):
            return 'application/pdf'
        if len(head) >= 132 and head[128:132] == b'DICM':
            return 'application/dicom'
    ext = os.path.splitext(value.name or '')[1].lower()
    if ext in ('.dcm', '.dicom'):
        return 'application/dicom'
    return mimetypes.guess_type(value.name or '')[0] or 'application/octet-stream'


def validate_file_size(value):
    """Validate uploaded file size (max 20MB)."""
    limit = 20 * 1024 * 1024  # 20MB
    if value.size > limit:
        raise ValidationError(f'حجم الملف كبير جداً. الحد الأقصى: 20 ميجابايت')


def medical_file_upload_path(instance, filename):
    """Generate secure upload path for medical files."""
    ext = filename.split('.')[-1].lower()
    new_filename = f'{uuid.uuid4().hex}.{ext}'
    return f'medical_files/{instance.channel.id}/{new_filename}'


class Patient(models.Model):
    """
    Patient model with encrypted PII (Personal Identifiable Information)
    and Blind Indexing for fast SQL search without compromising encryption.
    Security requirement #6: تشفير الاتصال DV <-> DB
    """

    class Gender(models.TextChoices):
        MALE = 'M', _('ذكر')
        FEMALE = 'F', _('أنثى')
        OTHER = 'O', _('أخرى')

    class BloodType(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Encrypted PII fields (AES-256)
    _full_name = models.TextField(_('الاسم الكامل المشفر'), db_column='full_name')
    _national_id = models.TextField(_('رقم الهوية المشفر'), db_column='national_id', blank=True)
    _phone = models.TextField(_('الهاتف المشفر'), db_column='phone', blank=True)
    _address = models.TextField(_('العنوان المشفر'), db_column='address', blank=True)

    # Blind Index fields for fast, privacy-preserving SQL search
    name_bindex = models.TextField(_('فهرس الاسم الأعمى'), blank=True, default='')
    national_id_bindex = models.CharField(
        _('فهرس الهوية الأعمى'), max_length=64, blank=True, default='', db_index=True
    )
    phone_bindex = models.CharField(
        _('فهرس الهاتف الأعمى'), max_length=64, blank=True, default='', db_index=True
    )

    # Non-encrypted fields
    date_of_birth = models.DateField(_('تاريخ الميلاد'))
    gender = models.CharField(_('الجنس'), max_length=1, choices=Gender.choices)
    blood_type = models.CharField(
        _('فصيلة الدم'), max_length=3,
        choices=BloodType.choices, blank=True
    )
    height = models.PositiveIntegerField(_('الطول (سم)'), null=True, blank=True)
    weight = models.PositiveIntegerField(_('الوزن (كجم)'), null=True, blank=True)

    # Medical info
    allergies = models.TextField(_('الحساسية'), blank=True)
    chronic_conditions = models.TextField(_('الأمراض المزمنة'), blank=True)
    current_medications = models.TextField(_('الأدوية الحالية'), blank=True)

    # Emergency contact (encrypted)
    _emergency_contact = models.TextField(
        _('جهة الاتصال الطارئة المشفرة'), db_column='emergency_contact', blank=True
    )

    # Basin linkage (plan requirement: patients belong to a health basin)
    basin = models.ForeignKey(
        'basins.Basin', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='patients', verbose_name=_('الحوض الصحي'),
    )

    # Portal account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='patient_record', verbose_name=_('حساب المريض'),
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('مريض')
        verbose_name_plural = _('المرضى')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['basin', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['national_id_bindex']),
            models.Index(fields=['phone_bindex']),
        ]

    def __str__(self):
        return f'مريض: {self.full_name} ({self.date_of_birth})'

    def save(self, *args, **kwargs):
        from apps.security.blind_index import compute_blind_index, compute_search_tokens
        try:
            raw_name = self.full_name
            self.name_bindex = compute_search_tokens(raw_name) if raw_name else ''
        except Exception:
            pass

        try:
            raw_nid = self.national_id
            self.national_id_bindex = compute_blind_index(raw_nid) if raw_nid else ''
        except Exception:
            pass

        try:
            raw_phone = self.phone
            self.phone_bindex = compute_blind_index(raw_phone) if raw_phone else ''
        except Exception:
            pass

        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return decrypt_field(self._full_name)

    @full_name.setter
    def full_name(self, value):
        self._full_name = encrypt_field(value)

    @property
    def national_id(self):
        return decrypt_field(self._national_id) if self._national_id else None

    @national_id.setter
    def national_id(self, value):
        self._national_id = encrypt_field(value) if value else ''

    @property
    def phone(self):
        return decrypt_field(self._phone) if self._phone else None

    @phone.setter
    def phone(self, value):
        self._phone = encrypt_field(value) if value else ''

    @property
    def address(self):
        return decrypt_field(self._address) if self._address else None

    @address.setter
    def address(self, value):
        self._address = encrypt_field(value) if value else ''

    @property
    def emergency_contact(self):
        return decrypt_field(self._emergency_contact) if self._emergency_contact else None

    @emergency_contact.setter
    def emergency_contact(self, value):
        self._emergency_contact = encrypt_field(value) if value else ''

    @property
    def age(self):
        from datetime import date
        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - (
            (today.month, today.day) < (born.month, born.day)
        )


class MedicalRecord(models.Model):
    """
    Medical record attached to a patient case (channel).
    """

    class RecordType(models.TextChoices):
        DIAGNOSIS = 'DIAGNOSIS', _('تشخيص')
        PRESCRIPTION = 'PRESCRIPTION', _('وصفة طبية')
        LAB_ORDER = 'LAB_ORDER', _('طلب تحاليل')
        LAB_RESULT = 'LAB_RESULT', _('نتيجة تحاليل')
        IMAGING = 'IMAGING', _('تصوير طبي')
        NOTES = 'NOTES', _('ملاحظات')
        VITALS = 'VITALS', _('علامات حيوية')
        PROCEDURE = 'PROCEDURE', _('إجراء طبي')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        'channels.Channel', on_delete=models.CASCADE,
        related_name='records',
        verbose_name=_('القناة')
    )
    record_type = models.CharField(
        _('نوع السجل'), max_length=20,
        choices=RecordType.choices
    )
    title = models.CharField(_('العنوان'), max_length=255)

    # Encrypted content (medical data is highly sensitive)
    _content = models.TextField(_('المحتوى المشفر'), db_column='content')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='created_records',
        verbose_name=_('أنشئ بواسطة')
    )

    # Vital signs (if record_type == VITALS)
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True)
    temperature = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True
    )
    respiratory_rate = models.PositiveIntegerField(null=True, blank=True)
    oxygen_saturation = models.PositiveIntegerField(null=True, blank=True)

    is_critical = models.BooleanField(_('حرج'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('سجل طبي')
        verbose_name_plural = _('السجلات الطبية')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['channel', 'record_type']),
            models.Index(fields=['is_critical']),
        ]

    def __str__(self):
        return f'{self.title} - {self.channel.name}'

    @property
    def content(self):
        return decrypt_field(self._content)

    @content.setter
    def content(self, value):
        self._content = encrypt_field(value)


class MedicalFile(models.Model):
    """
    Medical file (X-ray, MRI, CT scan, lab report, etc.)
    Files are access-controlled and access is audited.
    """

    class FileType(models.TextChoices):
        XRAY = 'XRAY', _('أشعة سينية')
        MRI = 'MRI', _('رنين مغناطيسي')
        CT_SCAN = 'CT_SCAN', _('تصوير مقطعي')
        ULTRASOUND = 'ULTRASOUND', _('موجات صوتية')
        LAB_REPORT = 'LAB_REPORT', _('تقرير مختبر')
        DOCUMENT = 'DOCUMENT', _('مستند')
        OTHER = 'OTHER', _('أخرى')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(
        'channels.Channel', on_delete=models.CASCADE,
        related_name='medical_files', verbose_name=_('القناة')
    )
    patient = models.ForeignKey(
        'Patient', on_delete=models.CASCADE,
        related_name='medical_files', verbose_name=_('المريض')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='uploaded_medical_files', verbose_name=_('رُفع بواسطة')
    )
    file = models.FileField(
        _('الملف'),
        upload_to=medical_file_upload_path,
        validators=[validate_file_extension, validate_file_size],
        max_length=500,
    )
    original_filename = models.CharField(_('اسم الملف الأصلي'), max_length=255)
    file_type = models.CharField(
        _('نوع الملف'), max_length=20, choices=FileType.choices
    )
    file_size = models.PositiveIntegerField(_('حجم الملف (بايت)'), default=0)
    mime_type = models.CharField(_('نوع MIME'), max_length=100, blank=True)
    title = models.CharField(_('العنوان'), max_length=255)
    description = models.TextField(_('الوصف'), blank=True)
    study_date = models.DateField(_('تاريخ الفحص'), null=True, blank=True)
    body_part = models.CharField(_('العضو المفحوص'), max_length=100, blank=True)
    modality = models.CharField(_('طريقة الفحص'), max_length=50, blank=True)
    is_critical = models.BooleanField(_('حرج'), default=False)
    access_count = models.PositiveIntegerField(_('عدد الوصول'), default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    last_accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='last_accessed_files'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('ملف طبي')
        verbose_name_plural = _('الملفات الطبية')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['channel', 'file_type']),
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['is_critical']),
        ]

    def __str__(self):
        return f'{self.title} - {self.patient.full_name}'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            if not self.mime_type:
                self.mime_type = sniff_mime_type(self.file)
        super().save(*args, **kwargs)

    def record_access(self, user):
        """Record file access for audit."""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.last_accessed_by = user
        self.save(update_fields=['access_count', 'last_accessed', 'last_accessed_by'])
