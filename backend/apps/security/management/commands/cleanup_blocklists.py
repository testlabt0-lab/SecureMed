"""
Management command: expire stale blocklist rows and untrust stale devices.

python manage.py cleanup_blocklists [--untrust-days 180] [--dry-run]

Two cleanups, both about lists that only grow:

1. Expired blocks: a BlockedDevice/BlockedIP with expires_at in the past is
   already unenforced (BlocklistQuerySet.enforceable ignores it) but stayed in
   the table forever, which made the blacklist unreadable for auditors.
2. Long-idle devices: a DeviceRegistry row untouched for months is an entry
   door nobody should still be using. --untrust-days revokes its trust —
   the device then has to re-request activation like any new one. The row is
   kept (not deleted) so the login history that references it stays readable.
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.security.models import BlockedDevice, BlockedIP, DeviceRegistry

logger = logging.getLogger('security')


class Command(BaseCommand):
    help = 'تنظيف الحظر المنتهي وسحب ثقة الأجهزة الخاملة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--untrust-days', type=int, default=180,
            help='سحب ثقة الأجهزة التي لم تسجل دخولاً منذ هذا العدد من الأيام (0 = تعطيل)',
        )
        parser.add_argument('--dry-run', action='store_true',
                            help='اعرض ما سيحدث دون تنفيذه')

    def handle(self, *args, **options):
        dry = options['dry_run']
        now = timezone.now()

        expired_devices = BlockedDevice.objects.expired()
        expired_ips = BlockedIP.objects.expired()
        self.stdout.write(
            f'حظر أجهزة منتهٍ: {expired_devices.count()} — حظر عناوين منتهٍ: {expired_ips.count()}'
        )
        if not dry:
            d_count = expired_devices.delete()[0]
            i_count = expired_ips.delete()[0]
            self.stdout.write(self.style.SUCCESS(
                f'تم حذف {d_count} حظر جهاز منتهٍ و{i_count} حظر عنوان منتهٍ'
            ))

        days = options['untrust_days']
        if days > 0:
            cutoff = now - timezone.timedelta(days=days)
            stale = DeviceRegistry.objects.filter(
                is_trusted=True, last_login__lt=cutoff,
            )
            stale_count = stale.count()
            self.stdout.write(
                f'أجهزة موثوقة خاملة أكثر من {days} يوماً: {stale_count}'
            )
            if not dry and stale_count:
                fingerprints = list(stale.values_list(
                    'device_fingerprint', flat=True,
                ))
                stale.update(is_trusted=False)
                self.stdout.write(self.style.SUCCESS(
                    f'تم سحب ثقة {len(fingerprints)} جهازاً خاملاً '
                    f'(ستحتاج طلب تفعيل جديد)'
                ))
                for fp in fingerprints:
                    logger.info(
                        f"STALE_DEVICE_UNTRUSTED fingerprint={fp[:64]} "
                        f"idle_days={days}"
                    )

        if dry:
            self.stdout.write(self.style.WARNING('وضع المعاينة — لم يُنفّذ شيء'))
