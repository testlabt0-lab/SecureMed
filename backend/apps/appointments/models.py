"""
Appointments models for SecureMed.

Implements a full appointment scheduling system:
- Appointment booking (patients, doctors, channels)
- Recurring appointments support
- Conflict detection
- Reminder notifications
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


class Appointment(models.Model):
    """Represents a scheduled appointment between a patient and a doctor."""

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('مجدول')
        CONFIRMED = 'CONFIRMED', _('مؤكد')
        IN_PROGRESS = 'IN_PROGRESS', _('جارٍ')
        COMPLETED = 'COMPLETED', _('مكتمل')
        CANCELLED = 'CANCELLED', _('ملغى')
        NO_SHOW = 'NO_SHOW', _('لم يحضر')
        RESCHEDULED = 'RESCHEDULED', _('أُعيد جدولته')

    class AppointmentType(models.TextChoices):
        INITIAL = 'INITIAL', _('كشف أول')
        FOLLOW_UP = 'FOLLOW_UP', _('متابعة')
        CONSULTATION = 'CONSULTATION', _('استشارة')
        LAB = 'LAB', _('تحاليل مختبر')
        IMAGING = 'IMAGING', _('أشعة / تصوير')
        PROCEDURE = 'PROCEDURE', _('إجراء طبي')
        EMERGENCY = 'EMERGENCY', _('طارئة')
        TELEMEDICINE = 'TELEMEDICINE', _('طب عن بُعد')

    class Priority(models.TextChoices):
        LOW = 'LOW', _('منخفضة')
        MEDIUM = 'MEDIUM', _('متوسطة')
        HIGH = 'HIGH', _('عالية')
        URGENT = 'URGENT', _('عاجلة')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core relations

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('المريض'),
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='doctor_appointments',
        verbose_name=_('الطبيب'),
        limit_choices_to={'role__in': ['DOCTOR', 'SUPER_ADMIN', 'HOSPITAL_ADMIN']},
    )
    channel = models.ForeignKey(
        'app_channels.Channel',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='appointments',
        verbose_name=_('القناة / الحالة'),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_appointments',
        verbose_name=_('أنشأه'),
    )

    # Basin linkage
    basin = models.ForeignKey(
        'basins.Basin',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='appointments',
        verbose_name=_('الحوض الصحي'),
    )

    # Scheduling
    appointment_type = models.CharField(
        _('نوع الموعد'), max_length=20,
        choices=AppointmentType.choices, default=AppointmentType.FOLLOW_UP,
    )
    priority = models.CharField(
        _('الأولوية'), max_length=10,
        choices=Priority.choices, default=Priority.MEDIUM,
    )
    status = models.CharField(
        _('الحالة'), max_length=15,
        choices=Status.choices, default=Status.SCHEDULED,
    )

    scheduled_at = models.DateTimeField(_('وقت الموعد'))
    duration_minutes = models.PositiveIntegerField(_('المدة (دقائق)'), default=30)

    # Location
    location = models.CharField(_('المكان'), max_length=255, blank=True)
    room_number = models.CharField(_('رقم الغرفة'), max_length=50, blank=True)
    is_virtual = models.BooleanField(_('موعد افتراضي'), default=False)
    virtual_link = models.URLField(_('رابط الموعد الافتراضي'), blank=True)

    # Content
    title = models.CharField(_('العنوان'), max_length=255)
    notes = models.TextField(_('ملاحظات'), blank=True)
    instructions = models.TextField(_('تعليمات للمريض'), blank=True)

    # Post-appointment
    summary = models.TextField(_('ملخص الموعد'), blank=True)
    follow_up_needed = models.BooleanField(_('يحتاج متابعة'), default=False)
    follow_up_date = models.DateField(_('تاريخ المتابعة'), null=True, blank=True)

    # Cancellation
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(_('سبب الإلغاء'), blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cancelled_appointments',
    )

    # Reminders
    reminder_sent_24h = models.BooleanField(default=False)
    reminder_sent_1h = models.BooleanField(default=False)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('موعد')
        verbose_name_plural = _('المواعيد')
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['doctor', 'scheduled_at']),
            models.Index(fields=['patient', 'scheduled_at']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['scheduled_at']),
        ]

    def __str__(self):
        return (
            f'{self.get_appointment_type_display()} — '
            f'{self.patient} مع {self.doctor.full_name} '
            f'@ {self.scheduled_at.strftime("%Y-%m-%d %H:%M")}'
        )

    @property
    def end_time(self):
        """Calculate appointment end time."""
        from datetime import timedelta
        return self.scheduled_at + timedelta(minutes=self.duration_minutes)

    @property
    def is_past(self):
        return self.scheduled_at < timezone.now()

    @property
    def is_upcoming(self):
        return self.scheduled_at >= timezone.now() and self.status in [
            self.Status.SCHEDULED, self.Status.CONFIRMED
        ]

    def clean(self):
        """Validate appointment — no double-booking for the same doctor at the same time."""
        if self.scheduled_at and self.doctor_id:
            from datetime import timedelta
            end = self.scheduled_at + timedelta(minutes=self.duration_minutes or 30)
            conflicts = Appointment.objects.filter(
                doctor=self.doctor_id,
                status__in=[self.Status.SCHEDULED, self.Status.CONFIRMED, self.Status.IN_PROGRESS],
                scheduled_at__lt=end,
            ).exclude(pk=self.pk)

            for conflict in conflicts:
                if conflict.end_time > self.scheduled_at:
                    raise ValidationError(
                        _('الطبيب لديه موعد آخر في هذا الوقت: %(title)s'),
                        params={'title': conflict.title},
                    )

    def cancel(self, cancelled_by, reason=''):
        """Cancel this appointment."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason'])

    def complete(self, summary=''):
        """Mark appointment as completed."""
        self.status = self.Status.COMPLETED
        self.summary = summary
        self.save(update_fields=['status', 'summary'])


class AppointmentSlot(models.Model):
    """Defines available time slots for a doctor (working hours / availability)."""

    DAYS = [
        (0, _('الأحد')),
        (1, _('الاثنين')),
        (2, _('الثلاثاء')),
        (3, _('الأربعاء')),
        (4, _('الخميس')),
        (5, _('الجمعة')),
        (6, _('السبت')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='available_slots',
        verbose_name=_('الطبيب'),
    )
    day_of_week = models.IntegerField(_('اليوم'), choices=DAYS)
    start_time = models.TimeField(_('وقت البدء'))
    end_time = models.TimeField(_('وقت الانتهاء'))
    slot_duration_minutes = models.PositiveIntegerField(_('مدة الموعد الواحد (دق)'), default=30)
    is_active = models.BooleanField(_('نشط'), default=True)

    class Meta:
        verbose_name = _('فترة إتاحة')
        verbose_name_plural = _('فترات الإتاحة')
        ordering = ['day_of_week', 'start_time']
        unique_together = ['doctor', 'day_of_week', 'start_time']

    def __str__(self):
        day_name = dict(self.DAYS).get(self.day_of_week, '')
        return f'د.{self.doctor.full_name} — {day_name} {self.start_time}–{self.end_time}'
