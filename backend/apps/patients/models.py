"""
Patient and MedicalRecord models.
"""
import uuid
import datetime
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.security.crypto import encrypt_field, decrypt_field


def validate_file_extension(value):
    """Validate uploaded file extension."""
    import os
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.dicom', '.dcm']
    if ext not in valid_extensions:
        raise ValidationError(
            f'نوع الملف غير مدعوم. الأنواع المدعومة: {", ".join(valid_extensions)}'
        )


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
    Patient model with encrypted PII (Personal Identifiable Information).
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('مريض')
        verbose_name_plural = _('المرضى')
        ordering = ['-created_at']

    def __str__(self):
        return f'مريض: {self.full_name} ({self.date_of_birth})'

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
                import mimetypes
                self.mime_type = mimetypes.guess_type(self.file.name)[0] or 'application/octet-stream'
        super().save(*args, **kwargs)

    def record_access(self, user):
        """Record file access for audit."""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.last_accessed_by = user
        self.save(update_fields=['access_count', 'last_accessed', 'last_accessed_by'])


class Medication(models.Model):
    """
    Medication plan for a patient with daily dose times.

    Powers the mobile medication reminders: `dose_times` holds the daily
    schedule (HH:MM comma separated) that the Android app mirrors into
    local system alarms, while MedicationLog records adherence.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE,
        related_name='medications',
        verbose_name=_('المريض')
    )
    channel = models.ForeignKey(
        'channels.Channel', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='medications',
        verbose_name=_('القناة')
    )
    name = models.CharField(_('اسم الدواء'), max_length=255)
    dosage = models.CharField(
        _('الجرعة'), max_length=100,
        help_text=_('مثال: 500 ملغ، قرص واحد')
    )
    dose_times = models.CharField(
        _('أوقات الجرعات'), max_length=255, default='08:00',
        help_text=_('مواعيد الجرعات مفصولة بفواصل بصيغة HH:MM — مثال: 08:00,14:00,20:00')
    )
    start_date = models.DateField(_('تاريخ البدء'))
    end_date = models.DateField(_('تاريخ الانتهاء'), null=True, blank=True)
    instructions = models.TextField(_('التعليمات'), blank=True)
    prescribed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='prescribed_medications',
        verbose_name=_('الطبيب الواصف')
    )
    is_active = models.BooleanField(_('نشط'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('دواء')
        verbose_name_plural = _('الأدوية')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['is_active', 'start_date']),
        ]

    def __str__(self):
        return f'{self.name} — {self.patient.full_name}'

    @property
    def times(self):
        """Parsed dose times as a sorted list of HH:MM strings."""
        out = []
        for part in (self.dose_times or '').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                # normalize e.g. "8:5" -> "08:05"
                hour, minute = part.split(':')[:2]
                out.append(f'{int(hour):02d}:{int(minute):02d}')
            except (ValueError, TypeError):
                continue
        return sorted(set(out)) or ['08:00']

    def clean(self):
        from django.core.exceptions import ValidationError as DjValidationError
        errors = {}
        for part in (self.dose_times or '').split(','):
            part = part.strip()
            if not part:
                continue
            try:
                datetime.datetime.strptime(part, '%H:%M')
            except ValueError:
                errors['dose_times'] = f'صيغة وقت غير صالحة: {part} (المطلوب HH:MM)'
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = 'تاريخ الانتهاء يجب أن يكون بعد تاريخ البدء'
        if errors:
            raise DjValidationError(errors)

    def is_scheduled_today(self):
        today = timezone.localdate()
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return self.is_active


class MedicationLog(models.Model):
    """
    Adherence record for a single scheduled dose.
    """

    class Status(models.TextChoices):
        TAKEN = 'TAKEN', _('تم تناوله')
        SKIPPED = 'SKIPPED', _('تم تخطيه')
        MISSED = 'MISSED', _('فائت')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medication = models.ForeignKey(
        Medication, on_delete=models.CASCADE,
        related_name='logs',
        verbose_name=_('الدواء')
    )
    scheduled_for = models.DateTimeField(_('موعد الجرعة'))
    status = models.CharField(
        _('الحالة'), max_length=10,
        choices=Status.choices, default=Status.TAKEN
    )
    taken_at = models.DateTimeField(_('وقت التناول الفعلي'), null=True, blank=True)
    notes = models.TextField(_('ملاحظات'), blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='medication_logs',
        verbose_name=_('سجله')
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('سجل جرعة')
        verbose_name_plural = _('سجلات الجرعات')
        ordering = ['-scheduled_for']
        constraints = [
            models.UniqueConstraint(
                fields=['medication', 'scheduled_for'],
                name='unique_medication_scheduled_dose'
            )
        ]

    def __str__(self):
        return f'{self.medication.name} @ {self.scheduled_for:%Y-%m-%d %H:%M} — {self.get_status_display()}'

    def save(self, *args, **kwargs):
        if self.status == self.Status.TAKEN and self.taken_at is None:
            self.taken_at = timezone.now()
        super().save(*args, **kwargs)
