"""
Telemedicine models — Video consultations and chat messages.
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class Consultation(models.Model):
    """A virtual consultation session between a doctor and a patient."""

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('مجدول')
        IN_PROGRESS = 'IN_PROGRESS', _('قيد التقدم')
        COMPLETED = 'COMPLETED', _('مكتمل')
        CANCELLED = 'CANCELLED', _('ملغى')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='consultations', verbose_name=_('المريض'))
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='consultations', verbose_name=_('الطبيب'))
    appointment = models.OneToOneField('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation', verbose_name=_('الموعد المرتبط'))
    
    scheduled_time = models.DateTimeField(_('وقت الجلسة المجدول'), default=timezone.now)
    status = models.CharField(_('الحالة'), max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    
    # WebRTC / Video Room Info
    room_id = models.CharField(_('معرف الغرفة'), max_length=100, unique=True, default=uuid.uuid4)
    join_url = models.URLField(_('رابط الانضمام'), blank=True)
    
    notes = models.TextField(_('ملاحظات الطبيب'), blank=True)
    diagnosis = models.TextField(_('التشخيص المبدئي'), blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('جلسة استشارة عن بعد')
        verbose_name_plural = _('جلسات الاستشارة عن بعد')
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"استشارة: {self.patient} مع {self.doctor} ({self.get_status_display()})"


class ChatMessage(models.Model):
    """Chat message exchanged during a consultation."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='messages', verbose_name=_('الاستشارة'))
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', verbose_name=_('المرسل'))
    
    content = models.TextField(_('المحتوى'))
    attachment = models.FileField(_('مرفق'), upload_to='telemedicine/attachments/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('رسالة دردشة')
        verbose_name_plural = _('رسائل الدردشة')
        ordering = ['created_at']

    def __str__(self):
        return f"رسالة من {self.sender} في {self.created_at}"
