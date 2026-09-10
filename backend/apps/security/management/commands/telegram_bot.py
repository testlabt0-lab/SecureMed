"""
Management command: run the Telegram admin console via long polling.

    python manage.py telegram_bot

This is how a localhost deployment receives commands without a public webhook:
the process dials Telegram's getUpdates every few seconds and feeds each
update into apps.security.telegram_bot.process_update — the same processor the
webhook uses in production. The approve/reject/deactivate inline buttons and
the /commands work identically.

Conflicts: getUpdates returns 409 while a webhook is registered — the command
detects that and says so (deleteWebhook, or stop the webhook deployment).
Stop with Ctrl+C.
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests


class Command(BaseCommand):
    help = 'تشغيل وحدة تحكم تيليجرام (polling) — الأوامر تعمل على localhost بلا webhook'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=3,
                            help='ثوانٍ الانتظار بين دورات getUpdates')

    def handle(self, *args, **opts):
        for stream in (__import__('sys').stdout, __import__('sys').stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8')

        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise CommandError(
                'TELEGRAM_BOT_TOKEN غير مضبوط — شغّل telegram_setup أولاً.'
            )
        base = f'https://api.telegram.org/bot{token}'
        offset = 0

        # A registered webhook blocks getUpdates (409) — fail fast with the fix.
        info = requests.get(f'{base}/getWebhookInfo', timeout=10).json()
        hook = info.get('result') if isinstance(info.get('result'), dict) else {}
        if info.get('ok') and hook.get('url'):
            raise CommandError(
                "webhook مسجّل على: "
                f"{hook['url']}\n"
                "احذفه أولاً لتشغيل polling: "
                f"requests.get('{base}/deleteWebhook') — أو أوقف خدمة الـ webhook."
            )

        admin = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', '')
        self.stdout.write(self.style.SUCCESS(
            f'🤖 بوت الإدارة يعمل (polling كل {opts["interval"]}s) — '
            f'شات الإدارة: {admin or "غير مضبوط!"}'
        ))
        self.stdout.write('الأوامر: /pending /approve /block /unblock /devices '
                          '/users /stats /backups /backup — أوقف بـ Ctrl+C')

        from apps.security.telegram_bot import process_update

        while True:
            try:
                response = requests.get(
                    f'{base}/getUpdates',
                    params={'offset': offset, 'timeout': 25,
                            'allowed_updates': ['message', 'callback_query']},
                    timeout=35,
                )
                data = response.json()
                if not data.get('ok'):
                    desc = data.get('description', '')
                    if '409' in desc or 'Conflict' in desc:
                        self.stderr.write(self.style.ERROR(
                            'تعارض: webhook مسجّل. احذفه أو أوقف polling.'
                        ))
                        time.sleep(10)
                        continue
                    self.stderr.write(f'getUpdates error: {desc[:200]}')
                    time.sleep(opts['interval'])
                    continue

                for update in data.get('result', []):
                    offset = update['update_id'] + 1
                    try:
                        handled = process_update(update)
                        if handled:
                            self.stdout.write(f'↳ handled update {update["update_id"]}')
                    except Exception:
                        import logging
                        logging.getLogger('security').exception(
                            'telegram update failed'
                        )
                        self.stderr.write('⚠ فشل معالجة تحديث — راجع السجل')
            except requests.RequestException as e:
                self.stderr.write(f'network: {e}')
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS('أُوقفت وحدة التحكم.'))
                return
            time.sleep(opts['interval'])
