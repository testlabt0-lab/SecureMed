"""
Management command: wire the Telegram bot to SecureMed in one run.

    python manage.py telegram_setup --token <BOTFATHER_TOKEN>

Steps it performs (each optional-but-defaulted):

1. validate the token against Bot API getMe (catches typos before saving);
2. discover TELEGRAM_ADMIN_CHAT_ID from the bot's recent updates — just send
   any message (e.g. «مرحبا») to the bot in Telegram first, and your chat id
   is the only one that appears;
3. save both values into .env (idempotent: existing correct lines are kept);
4. send a test notification so the human can confirm delivery;
5. with --webhook-url (a public HTTPS URL — ngrok works locally), register
   the webhook with a generated secret and store the secret, enabling the
   inline تفعيل/حظر buttons. Without it, outbound alerts still work; the
   buttons simply have nowhere to call home on a localhost deployment.

    python manage.py telegram_setup --token <TOKEN> --webhook-url https://x.ngrok-free.app
"""
import secrets as pysecrets
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import requests


class Command(BaseCommand):
    help = 'ربط بوت تيليجرام: التحقق من الرمز، اكتشاف chat_id، الحفظ في .env، ورسالة اختبار'

    def add_arguments(self, parser):
        parser.add_argument('--token', required=False,
                            help='رمز البوت من @BotFather (يُقرأ من .env إن أُهمل)')
        parser.add_argument('--chat-id', required=False,
                            help='معرف شات الإدارة (يُكتشف من آخر رسائل البوت إن أُهمل)')
        parser.add_argument('--webhook-url', required=False, default='',
                            help='عنوان HTTPS عام (ngrok مثلًا) لتسجيل webhook أزرار الموافقة')
        parser.add_argument('--skip-test', action='store_true',
                            help='لا ترسل رسالة اختبار')

    def handle(self, *args, **opts):
        # Windows consoles default to cp1252, which cannot encode the Arabic
        # guidance this command prints — force UTF-8 before any output.
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, 'reconfigure'):
                stream.reconfigure(encoding='utf-8')
        token = opts['token'] or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not token:
            raise CommandError(
                'لا يوجد رمز بوت. أنشئ بوتاً من @BotFather ثم مرر الرمز: '
                '--token <الرمز>'
            )

        # 1) validate the token — getMe never needs a chat, so a bad token
        # fails here instead of silently eating every later notification.
        me = self._api(token, 'getMe')
        bot_name = me['result'].get('username', '?')
        self.stdout.write(self.style.SUCCESS(
            f'✓ الرمز صالح — البوت: @{bot_name}'
        ))

        # 2) discover the admin chat id from recent updates
        chat_id = opts['chat_id']
        if not chat_id:
            chat_id = self._discover_chat_id(token)
            if not chat_id:
                raise CommandError(
                    'لم أجد رسائل للبوت. افتح محادثة مع البوت في تيليجرام '
                    f'(@{bot_name}) وأرسل أي رسالة (مثل: مرحبا) ثم أعد الأمر.'
                )
        self.stdout.write(self.style.SUCCESS(f'✓ معرف شات الإدارة: {chat_id}'))

        # 3) persist into .env
        env_path = settings.BASE_DIR / '.env'
        values = {
            'TELEGRAM_BOT_TOKEN': token,
            'TELEGRAM_ADMIN_CHAT_ID': str(chat_id),
        }
        secret = ''
        webhook_url = opts['webhook_url'].strip()
        if webhook_url:
            secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '') or (
                pysecrets.token_urlsafe(32))
            values['TELEGRAM_WEBHOOK_SECRET'] = secret

        for key, value in values.items():
            self._upsert_env_line(env_path, key, value)
        self.stdout.write(self.style.SUCCESS(f'✓ حُفظت الإعدادات في {env_path}'))

        # 4) test message
        if not opts['skip_test']:
            sent = self._api(token, 'sendMessage', {
                'chat_id': chat_id,
                'text': '✅ <b>تم ربط SecureMed بنجاح</b>\n'
                        'ستصلك هنا: طلبات تفعيل الأجهزة، تنبيهات الأمان، '
                        'والملخص اليومي.',
                'parse_mode': 'HTML',
            })
            self.stdout.write(self.style.SUCCESS('✓ وصلت رسالة الاختبار — تحقق من تيليجرام'))

        # 5) webhook for the inline buttons (public URL required)
        if webhook_url:
            self._api(token, 'setWebhook', {
                'url': f'{webhook_url.rstrip("/")}/api/v1/security/telegram-webhook/',
                'secret_token': secret,
                'allowed_updates': ['callback_query'],
            })
            self.stdout.write(self.style.SUCCESS(
                f'✓ سُجّل webhook: {webhook_url} — أزرار تفعيل/حظر الجهاز صارت تعمل'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '⚠ بلا webhook: الإشعارات تصلك، لكن أزرار الموافقة داخل '
                'تيليجرام لن تعمل على localhost — الموافقة من لوحة التحكم '
                '(/security/devices) أو مرر --webhook-url لاحقاً.'
            ))

        self.stdout.write(self.style.SUCCESS(
            'أعد تشغيل خادم Django لالتقاط الإعدادات الجديدة.'
        ))

    def _api(self, token, method, payload=None):
        url = f'https://api.telegram.org/bot{token}/{method}'
        try:
            response = (requests.post(url, json=payload or {}, timeout=10)
                        if payload else requests.get(url, timeout=10))
        except requests.RequestException as e:
            raise CommandError(f'تعذر الاتصال بتيليجرام: {e}')
        data = response.json()
        if not data.get('ok'):
            desc = data.get('description', response.text[:200])
            raise CommandError(f'رفض تيليجرام {method}: {desc}')
        return data

    def _discover_chat_id(self, token):
        data = self._api(token, 'getUpdates', {'limit': 10})
        ids = []
        for update in data.get('result', []):
            chat = (update.get('message') or update.get('edited_message') or {}).get('chat')
            if chat and chat.get('id') not in ids:
                ids.append(chat['id'])
                who = chat.get('username') or chat.get('first_name', '?')
                self.stdout.write(f'  رسالة من: {who} (chat_id={chat["id"]})')
        return str(ids[0]) if ids else ''

    def _upsert_env_line(self, env_path, key, value):
        lines = []
        if env_path.exists():
            lines = env_path.read_text(encoding='utf-8').splitlines()
        replaced = False
        out = []
        for line in lines:
            if line.strip().startswith(f'{key}='):
                out.append(f'{key}={value}')
                replaced = True
            else:
                out.append(line)
        if not replaced:
            if out and out[-1].strip():
                out.append('')
            out.append(f'# SecureMed Telegram bot (added by telegram_setup)')
            out.append(f'{key}={value}')
        env_path.write_text('\n'.join(out) + '\n', encoding='utf-8')
