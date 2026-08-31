"""
Backup models — metadata about every database+media backup archive.

Dev requirement: «تتضمن آلية للنسخ الاحتياطي»
Every backup is a ZIP containing:
  db.json       → full data dump (excluding transient tables)
  manifest.json → metadata + SHA-256 checksum of db.json
  media/        → uploaded medical files
"""
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class BackupRecord(models.Model):
    """One successful (or failed) backup archive on disk."""

    class Status(models.TextChoices):
        COMPLETED = 'COMPLETED', _('مكتمل')
        FAILED = 'FAILED', _('فاشل')

    class Kind(models.TextChoices):
        MANUAL = 'MANUAL', _('يدوي')
        SCHEDULED = 'SCHEDULED', _('مجدول')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(_('اسم الملف'), max_length=255, unique=True)
    filepath = models.CharField(_('المسار'), max_length=500)
    size_bytes = models.BigIntegerField(_('الحجم (بايت)'), default=0)
    checksum = models.CharField(_('بصمة SHA-256'), max_length=64, blank=True)
    status = models.CharField(
        _('الحالة'), max_length=10,
        choices=Status.choices, default=Status.COMPLETED,
    )
    kind = models.CharField(
        _('النوع'), max_length=10,
        choices=Kind.choices, default=Kind.MANUAL,
    )
    row_counts = models.JSONField(_('عدد السجلات'), default=dict, blank=True)
    media_files = models.PositiveIntegerField(_('عدد الملفات المرفقة'), default=0)
    duration_ms = models.PositiveIntegerField(_('المدة (مللي ثانية)'), default=0)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_backups', verbose_name=_('أنشئ بواسطة'),
    )
    note = models.CharField(_('ملاحظة'), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('نسخة احتياطية')
        verbose_name_plural = _('النسخ الاحتياطية')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.filename} ({self.get_status_display()})'

    @property
    def exists_on_disk(self) -> bool:
        import os
        return os.path.exists(self.filepath)
