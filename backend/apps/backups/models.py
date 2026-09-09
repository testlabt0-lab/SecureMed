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

    class Scope(models.TextChoices):
        """ماذا يغطي الأرشيف — فصل قاعدة البيانات عن الملفات.

        FULL = كل شيء، DATABASE = dump القاعدة فقط، MEDIA = ملفات الرفع فقط.
        الاستعادة تقرأ النطاق من الـ manifest: نسخة media لا تلمس قاعدة
        البيانات، ونسخة database لا تلمس الملفات.
        """
        FULL = 'FULL', _('كامل (قاعدة + ملفات)')
        DATABASE = 'DATABASE', _('قاعدة البيانات فقط')
        MEDIA = 'MEDIA', _('الملفات المرفوعة فقط')

    class DeliveryStatus(models.TextChoices):
        """Where an off-site copy of the archive went.

        Tracked per archive because the delivery channel is chosen per run:
        Telegram caps uploads at 50 MB, S3 does not, and either leg can fail
        while the local archive itself is fine.
        """
        NOT_SENT = 'NOT_SENT', _('لم تُرسل')
        TELEGRAM = 'TELEGRAM', _('أُرسلت عبر تلجرام')
        CLOUD = 'CLOUD', _('أُرسلت للتخزين السحابي')
        BOTH = 'BOTH', _('تلجرام + سحابي')
        FAILED = 'DELIVERY_FAILED', _('فشل التسليم الخارجي')

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
    scope = models.CharField(
        _('النطاق'), max_length=10,
        choices=Scope.choices, default=Scope.FULL, db_index=True,
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

    # Off-site delivery (Telegram document / cloud bucket)
    delivery_status = models.CharField(
        _('التسليم الخارجي'), max_length=20,
        choices=DeliveryStatus.choices, default=DeliveryStatus.NOT_SENT,
        db_index=True,
    )
    delivery_detail = models.JSONField(
        _('تفاصيل التسليم'), default=dict, blank=True,
        help_text=_('نتيجة كل قناة تسليم، مثل {"telegram": {...}, "cloud": {...}}'),
    )
    offsite_key = models.CharField(
        _('مفتاح النسخة في التخزين السحابي'), max_length=500, blank=True,
    )
    delivered_at = models.DateTimeField(
        _('وقت التسليم'), null=True, blank=True,
    )

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

    @property
    def delivered_offsite(self) -> bool:
        return self.delivery_status in (
            self.DeliveryStatus.TELEGRAM,
            self.DeliveryStatus.CLOUD,
            self.DeliveryStatus.BOTH,
        )
