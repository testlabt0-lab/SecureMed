"""
Management command: python manage.py create_backup [--kind scheduled] [--note ...]
"""
from django.core.management.base import BaseCommand

from apps.backups.models import BackupRecord
from apps.backups.services import create_backup


class Command(BaseCommand):
    help = 'إنشاء نسخة احتياطية كاملة (قاعدة البيانات + الملفات) في أرشيف ZIP'

    def add_arguments(self, parser):
        parser.add_argument('--kind', choices=['MANUAL', 'SCHEDULED'],
                            default='MANUAL', help='نوع النسخة')
        parser.add_argument('--note', default='', help='ملاحظة تُحفظ مع النسخة')

    def handle(self, *args, **options):
        record = create_backup(kind=options['kind'], note=options['note'])
        self.stdout.write(self.style.SUCCESS(
            f'تم إنشاء النسخة الاحتياطية: {record.filename} '
            f'({record.size_bytes / 1024:.1f} KB، {record.duration_ms} ms، '
            f'بصمة: {record.checksum[:12]}...)'
        ))
        self.stdout.write(str(record.filepath))
