"""
Management command: python manage.py restore_backup <path.zip> [--force]
Without --force it only verifies the archive (safe plan mode).
"""
from django.core.management.base import BaseCommand, CommandError

from apps.backups.services import restore_backup, verify_backup


class Command(BaseCommand):
    help = 'استعادة نسخة احتياطية (قاعدة البيانات + الملفات) من أرشيف ZIP'

    def add_arguments(self, parser):
        parser.add_argument('archive', help='مسار ملف النسخة الاحتياطية')
        parser.add_argument(
            '--force', action='store_true',
            help='تنفيذ الاستعادة فعلياً (يمسح البيانات الحالية!)'
        )

    def handle(self, *args, **options):
        archive = options['archive']
        if not options['force']:
            try:
                manifest = verify_backup(archive)
            except Exception as e:
                raise CommandError(f'فشل التحقق: {e}')
            self.stdout.write(self.style.SUCCESS(
                'الأرشيف سليم ✓ — أضف --force لتنفيذ الاستعادة الفعلية '
                f'(تحتوي على {manifest.get("row_counts", {}).get("accounts.User", "?")} مستخدم)'
            ))
            return

        try:
            result = restore_backup(archive, force=True)
        except Exception as e:
            raise CommandError(f'فشلت الاستعادة: {e}')
        self.stdout.write(self.style.SUCCESS(
            result.get('detail', 'تمت الاستعادة') +
            f" — ملفات مستعادة: {result.get('restored_media_files', 0)}"
        ))
