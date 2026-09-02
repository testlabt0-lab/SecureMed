"""
Ward management models — Wards, Rooms, Beds, and Patient Assignments.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class Ward(models.Model):
    """A hospital ward (e.g., General, Maternity, ICU, ER)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('اسم الجناح'), max_length=100, unique=True)
    floor = models.CharField(_('الطابق'), max_length=50, blank=True)
    description = models.TextField(_('الوصف'), blank=True)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('جناح')
        verbose_name_plural = _('الأجنحة')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (الطابق {self.floor})"


class Room(models.Model):
    """A room within a ward."""

    class RoomType(models.TextChoices):
        GENERAL = 'GENERAL', _('عامة')
        PRIVATE = 'PRIVATE', _('خاصة')
        ISOLATION = 'ISOLATION', _('عزل')
        ICU = 'ICU', _('عناية مركزة')
        VIP = 'VIP', _('VIP')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='rooms', verbose_name=_('الجناح'))
    room_number = models.CharField(_('رقم الغرفة'), max_length=50)
    room_type = models.CharField(_('نوع الغرفة'), max_length=20, choices=RoomType.choices, default=RoomType.GENERAL)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('غرفة')
        verbose_name_plural = _('الغرف')
        ordering = ['ward', 'room_number']
        unique_together = ('ward', 'room_number')

    def __str__(self):
        return f"غرفة {self.room_number} - {self.ward.name}"


class Bed(models.Model):
    """A specific bed inside a room."""

    class Status(models.TextChoices):
        FREE = 'FREE', _('متاح')
        OCCUPIED = 'OCCUPIED', _('مشغول')
        MAINTENANCE = 'MAINTENANCE', _('صيانة')
        CLEANING = 'CLEANING', _('قيد التنظيف')
        RESERVED = 'RESERVED', _('محجوز')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds', verbose_name=_('الغرفة'))
    bed_number = models.CharField(_('رقم السرير'), max_length=50)
    status = models.CharField(_('حالة السرير'), max_length=20, choices=Status.choices, default=Status.FREE)
    notes = models.TextField(_('ملاحظات'), blank=True)

    class Meta:
        verbose_name = _('سرير')
        verbose_name_plural = _('الأسرّة')
        ordering = ['room', 'bed_number']
        unique_together = ('room', 'bed_number')

    def __str__(self):
        return f"سرير {self.bed_number} - {self.room}"


class BedAssignment(models.Model):
    """Assignment of a patient to a bed over time (Admission)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name='assignments', verbose_name=_('السرير'))
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='bed_assignments', verbose_name=_('المريض'))
    admitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='admissions_created', verbose_name=_('موظف الدخول')
    )
    admission_date = models.DateTimeField(_('تاريخ ووقت الدخول'), default=timezone.now)
    discharge_date = models.DateTimeField(_('تاريخ ووقت الخروج'), null=True, blank=True)
    diagnosis_on_admission = models.TextField(_('التشخيص عند الدخول'), blank=True)
    is_active = models.BooleanField(_('حالي/نشط'), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('تخصيص سرير (دخول مريض)')
        verbose_name_plural = _('تخصيص الأسرّة')
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['patient', 'is_active']),
            models.Index(fields=['bed', 'is_active']),
        ]

    def __str__(self):
        status_str = 'نشط' if self.is_active else 'مكتمل (خروج)'
        return f"{self.patient} -> {self.bed} [{status_str}]"
