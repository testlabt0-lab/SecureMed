"""
Tests for the Telegram admin console (telegram_bot) — commands via text
messages plus the shared callback processor.
"""
import json
import uuid
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.backups.models import BackupRecord
from apps.notifications.models import Notification
from apps.security.models import BlockedDevice, DeviceRegistry
from tests.factories import AdminUserFactory, UserFactory

pytestmark = pytest.mark.django_db

ADMIN_CHAT = '4242'


@pytest.fixture
def tg_settings(settings):
    settings.AUDIT_LOG_ASYNC = False
    settings.TELEGRAM_WEBHOOK_SECRET = 's3cr3t'
    settings.TELEGRAM_ADMIN_CHAT_ID = ADMIN_CHAT
    settings.TELEGRAM_BOT_TOKEN = '123:abc'
    return settings


def _post_message(text, chat_id=ADMIN_CHAT, secret='s3cr3t'):
    client = APIClient()
    return client.post(
        '/api/v1/security/telegram-webhook/',
        {'message': {'message_id': 1, 'chat': {'id': chat_id}, 'text': text}},
        format='json',
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret,
    )


class TestCommandAuthorization:
    def test_admin_chat_gets_command_reply(self, tg_settings):
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            res = _post_message('/help')
        assert res.status_code == 200
        send.assert_called_once()
        assert 'وحدة تحكم الإدارة' in send.call_args.args[1]

    def test_stranger_chat_gets_refusal_only(self, tg_settings):
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            res = _post_message('/users', chat_id='9999')
        assert res.status_code == 200
        assert UNAUTHORIZED in send.call_args.args[1]
        # and absolutely no user data leaked
        assert '@' not in send.call_args.args[1]

    def test_non_command_ignored(self, tg_settings):
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('مرحبا كيف الحال')
        send.assert_not_called()


UNAUTHORIZED = "هذا البوت مخصص لإدارة النظام فقط"


class TestDeviceCommands:
    def test_pending_lists_untrusted(self, tg_settings):
        user = UserFactory()
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-wait-9', is_trusted=False,
        )
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('/pending')
        body = send.call_args.args[1]
        assert 'بانتظار الموافقة (1)' in body
        assert user.email in body

    def test_approve_by_id_trusts_and_notifies(self, tg_settings):
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-ap-1', is_trusted=False,
        )
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ):
            _post_message(f'/approve {device.id}')
        device.refresh_from_db()
        assert device.is_trusted is True
        assert Notification.objects.filter(
            recipient=user, title='تم تفعيل جهاز جديد',
        ).exists()
        assert AuditLog.objects.filter(
            event_type='DEVICE_TRUSTED',
            details__granted_by='telegram-command',
        ).exists()

    def test_block_revokes_blocks_and_kills_session(self, tg_settings):
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-bl-1', is_trusted=True,
        )
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ), mock.patch(
            'apps.security.telegram_service.send_device_deactivated_notification',
            return_value=True,
        ):
            _post_message(f'/block {device.id}')
        device.refresh_from_db()
        assert device.is_trusted is False
        assert BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-bl-1'
        ).exists()
        assert cache.get(f'token_denylist:{user.id}')

    def test_unblock_by_fingerprint_prefix(self, tg_settings):
        BlockedDevice.objects.create(
            device_fingerprint='AND-ub-77', reason='test',
        )
        cache.set('waf_device_blacklist:AND-ub-77', True, 600)
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ):
            _post_message('/unblock AND-ub-77')
        assert not BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-ub-77'
        ).exists()
        assert cache.get('waf_device_blacklist:AND-ub-77') is None

    def test_unknown_id_reported(self, tg_settings):
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message(f'/approve {uuid.uuid4()}')
        assert 'لم أجد جهازاً' in send.call_args.args[1]


class TestPlatformCommands:
    def test_users_lists_with_roles(self, tg_settings):
        user = UserFactory(email='visible@securemed.app')
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('/users visible')
        body = send.call_args.args[1]
        assert 'visible@securemed.app' in body
        assert u'نشط' in body

    def test_stats_counts(self, tg_settings):
        UserFactory()
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('/stats')
        assert 'إحصاءات المنصة' in send.call_args.args[1]

    def test_backups_lists_delivery_status(self, tg_settings, tmp_path):
        settings = tg_settings
        settings.BACKUP_DIR = tmp_path / 'b'
        archive = tmp_path / 'b' / 'x.zip'
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b'PK\x03\x04')
        BackupRecord.objects.create(
            filename=archive.name, filepath=str(archive),
            size_bytes=4, checksum='a' * 64,
            delivery_status=BackupRecord.DeliveryStatus.TELEGRAM,
        )
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('/backups')
        assert 'أُرسلت عبر تلجرام' in send.call_args.args[1]

    def test_backup_now_creates_and_delivers(self, tg_settings, tmp_path):
        tg_settings.BACKUP_DIR = tmp_path / 'b'
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send, mock.patch(
            'apps.backups.offsite.deliver_backup',
            side_effect=lambda rec: rec,
        ):
            _post_message('/backup DATABASE')
        assert 'اكتملت النسخة' in send.call_args.args[1]
        assert BackupRecord.objects.filter(
            scope=BackupRecord.Scope.DATABASE, note='telegram-command',
        ).exists()

    def test_unknown_command_shows_help(self, tg_settings):
        with mock.patch(
            'apps.security.telegram_service._send_html', return_value=True,
        ) as send:
            _post_message('/make_me_coffee')
        assert 'أمر غير معروف' in send.call_args.args[1]
        assert '/pending' in send.call_args.args[1]


class TestPollingCommand:
    def test_polling_processes_updates(self, tg_settings):
        from django.core.management import call_command
        from io import StringIO

        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-poll-1', is_trusted=False,
        )
        update = {
            'update_id': 101,
            'callback_query': {
                'id': 'cb1',
                'data': f'approve_{device.id}',
                'message': {'message_id': 5, 'text': 'طلب جهاز',
                            'chat': {'id': ADMIN_CHAT}},
            },
        }

        def fake_get(url, *a, **kw):
            class Resp:
                status_code = 200
                def json(self):
                    if 'getWebhookInfo' in url:
                        return {'ok': True, 'result': {}}
                    return {'ok': True, 'result': [update]}
            return Resp()

        with mock.patch(
            'requests.get', side_effect=fake_get,
        ) as get_updates, mock.patch(
            'time.sleep', side_effect=KeyboardInterrupt,
        ):
            out = StringIO()
            call_command('telegram_bot', stdout=out)
        device.refresh_from_db()
        assert device.is_trusted is True
        assert get_updates.called

    def test_polling_refuses_when_webhook_registered(self, tg_settings):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        class Hooked:
            status_code = 200
            def json(self):
                return {'ok': True, 'result': {
                    'url': 'https://prod.example/telegram-webhook/'}}

        with mock.patch('requests.get', return_value=Hooked()):
            with pytest.raises(CommandError, match='webhook'):
                call_command('telegram_bot')
