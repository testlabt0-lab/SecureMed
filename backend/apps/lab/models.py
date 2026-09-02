"""
Laboratory models — Test catalog, orders, results, and critical alerts.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class LabTest(models.Model):
    """Catalog of available laboratory tests."""

    class Category(models.TextChoices):
        HEMATOLOGY = 'HEMATOLOGY', _('أمراض الدم')
        CHEMISTRY = 'CHEMISTRY', _('كيمياء حيوية')
        MICROBIOLOGY = 'MICROBIOLOGY', _('أحياء دقيقة')
        IMMUNOLOGY = 'IMMUNOLOGY', _('مناعة')
        URINALYSIS = 'URINALYSIS', _('تحليل بول')
        COAGULATION = 'COAGULATION', _('تخثر')
        HORMONES = 'HORMONES', _('هرمونات')
        OTHER = 'OTHER', _('أخرى')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم التحليل'), max_length=255, db_index=True)
    code = models.CharField(_('الرمز (LOINC)'), max_length=50, unique=True, blank=True)
    category = models.CharField(_('التصنيف'), max_length=20, choices=Category.choices, default=Category.CHEMISTRY)
    description = models.TextField(_('الوصف'), blank=True)
    unit = models.CharField(_('الوحدة'), max_length=50, blank=True, help_text=_('مثل: mg/dL, mmol/L'))
    normal_range_min = models.DecimalField(_('الحد الأدنى الطبيعي'), max_digits=10, decimal_places=3, null=True, blank=True)
    normal_range_max = models.DecimalField(_('الحد الأقصى الطبيعي'), max_digits=10, decimal_places=3, null=True, blank=True)
    normal_range_text = models.CharField(_('النطاق الطبيعي (نص)'), max_length=100, blank=True, help_text=_('مثل: سلبي/إيجابي'))
    price = models.DecimalField(_('السعر'), max_digits=10, decimal_places=2, default=0.00)
    turnaround_hours = models.PositiveIntegerField(_('وقت النتيجة (ساعات)'), default=24)
    requires_fasting = models.BooleanField(_('يتطلب صيام'), default=False)
    sample_type = models.CharField(_('نوع العينة'), max_length=100, blank=True, help_text=_('دم، بول، براز...'))
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('تحليل مختبري')
        verbose_name_plural = _('التحاليل المختبرية')
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class LabOrder(models.Model):
    """A lab test order from a doctor for a patient."""

    class Status(models.TextChoices):
        ORDERED = 'ORDERED', _('مطلوب')
        SAMPLE_COLLECTED = 'SAMPLE_COLLECTED', _('تم جمع العينة')
        IN_PROGRESS = 'IN_PROGRESS', _('قيد التنفيذ')
        COMPLETED = 'COMPLETED', _('مكتمل')
        VALIDATED = 'VALIDATED', _('مصادق عليه')
        CANCELLED = 'CANCELLED', _('ملغى')

    class Priority(models.TextChoices):
        ROUTINE = 'ROUTINE', _('عادي')
        URGENT = 'URGENT', _('مستعجل')
        STAT = 'STAT', _('فوري')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='lab_orders', verbose_name=_('المريض'))
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='lab_orders_issued', verbose_name=_('الطبيب الطالب'))
    channel = models.ForeignKey('app_channels.Channel', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_orders', verbose_name=_('القناة'))
    test = models.ForeignKey(LabTest, on_delete=models.PROTECT, related_name='orders', verbose_name=_('التحليل'))

    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.ORDERED)
    priority = models.CharField(_('الأولوية'), max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    clinical_notes = models.TextField(_('ملاحظات سريرية'), blank=True)
    fasting_confirmed = models.BooleanField(_('تأكيد الصيام'), default=False)

    collected_at = models.DateTimeField(_('وقت جمع العينة'), null=True, blank=True)
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lab_samples_collected', verbose_name=_('جامع العينة'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('طلب تحليل')
        verbose_name_plural = _('طلبات التحاليل')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', '-created_at']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f'{self.test.name} — {self.patient} [{self.get_status_display()}]'


class LabResult(models.Model):
    """Result of a lab order — numeric or text value."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(LabOrder, on_delete=models.CASCADE, related_name='result', verbose_name=_('الطلب'))
    numeric_value = models.DecimalField(_('القيمة الرقمية'), max_digits=10, decimal_places=3, null=True, blank=True)
    text_value = models.TextField(_('القيمة النصية'), blank=True, help_text=_('للنتائج غير الرقمية مثل: إيجابي/سلبي'))
    is_abnormal = models.BooleanField(_('غير طبيعي'), default=False)
    is_critical = models.BooleanField(_('حرج'), default=False)
    notes = models.TextField(_('ملاحظات الفني'), blank=True)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='lab_results_performed', verbose_name=_('فني المختبر'),
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lab_results_validated', verbose_name=_('المصادق'),
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('نتيجة تحليل')
        verbose_name_plural = _('نتائج التحاليل')
        ordering = ['-created_at']

    def __str__(self):
        val = self.numeric_value if self.numeric_value is not None else self.text_value
        return f'{self.order.test.name}: {val}'

    def save(self, *args, **kwargs):
        # Auto-detect abnormal / critical values
        test = self.order.test
        if self.numeric_value is not None and test.normal_range_min is not None and test.normal_range_max is not None:
            self.is_abnormal = not (test.normal_range_min <= self.numeric_value <= test.normal_range_max)
            # Critical if >2x above max or <0.5x below min
            if self.numeric_value > float(test.normal_range_max) * 2 or self.numeric_value < float(test.normal_range_min) * 0.5:
                self.is_critical = True
        super().save(*args, **kwargs)
