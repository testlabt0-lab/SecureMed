"""
Tests for the new backup-delivery and device-deactivation features:

* off-site delivery (Telegram document / S3 cloud copy) — points 3+4 of
  «اوتو باك اب + تشفير + تسليم تلجرام/سحابي»
* device deactivation via Telegram callback and dashboard API — إدارة
  التفعيل وإلغاء التفعيل المرتبطة بالتلجرام
"""
import uuid
from unittest import mock

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.backups.models import BackupRecord
from apps.backups.offsite import deliver_backup
from apps.security.models import BlockedDevice, DeviceRegistry
from tests.factories import AdminUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def _make_record(tmp_path, settings) -> BackupRecord:
    settings.BACKUP_DIR = tmp_path / 'backups'
    archive = tmp_path / 'backups' / 'securemed_backup_test.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    archive.write_bytes(b'PK\x03\x04 encrypted-but-fake-archive')
    return BackupRecord.objects.create(
        filename=archive.name,
        filepath=str(archive),
        size_bytes=archive.stat().st_size,
        checksum='a' * 64,
        kind=BackupRecord.Kind.SCHEDULED,
    )


class TestOffsiteDelivery:
    def test_no_channels_configured_stays_not_sent(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        settings.BACKUP_SEND_TO_TELEGRAM = False
        settings.BACKUP_OFFSITE_ENABLED = False
        result = deliver_backup(record)
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.NOT_SENT
        record.refresh_from_db()
        assert record.delivery_status == BackupRecord.DeliveryStatus.NOT_SENT
        assert record.delivered_at is None

    def test_telegram_delivery_success(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        settings.BACKUP_SEND_TO_TELEGRAM = True
        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        with mock.patch(
            'apps.security.telegram_service.send_backup_document',
            return_value=True,
        ) as send_doc:
            result = deliver_backup(record)
        send_doc.assert_called_once()
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.TELEGRAM
        record.refresh_from_db()
        assert record.delivered_offsite
        assert record.delivered_at is not None

    def test_telegram_delivery_too_big_skips(self, tmp_path, settings):
        """An archive over the Bot API 50 MB cap must not be attempted."""
        record = _make_record(tmp_path, settings)
        record.size_bytes = 51 * 1024 * 1024
        record.save(update_fields=['size_bytes'])
        settings.BACKUP_SEND_TO_TELEGRAM = True
        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        with mock.patch(
            'apps.security.telegram_service.requests.post'
        ) as tg_post:
            result = deliver_backup(record)
        tg_post.assert_not_called()
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.FAILED

    def test_cloud_delivery_success(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        settings.BACKUP_OFFSITE_ENABLED = True
        settings.BACKUP_OFFSITE_BUCKET = 'med-backups'
        settings.BACKUP_OFFSITE_ACCESS_KEY_ID = 'k'
        settings.BACKUP_OFFSITE_SECRET_ACCESS_KEY = 's'
        with mock.patch('boto3.client') as client_factory:
            client_factory.return_value.upload_file.return_value = None
            result = deliver_backup(record)
        client_factory.return_value.upload_file.assert_called_once()
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.CLOUD
        record.refresh_from_db()
        assert record.offsite_key.endswith(record.filename)
        assert record.delivered_offsite

    def test_both_channels_sets_both(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        settings.BACKUP_SEND_TO_TELEGRAM = True
        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        settings.BACKUP_OFFSITE_ENABLED = True
        settings.BACKUP_OFFSITE_BUCKET = 'med-backups'
        settings.BACKUP_OFFSITE_ACCESS_KEY_ID = 'k'
        settings.BACKUP_OFFSITE_SECRET_ACCESS_KEY = 's'
        with mock.patch(
            'apps.security.telegram_service.send_backup_document',
            return_value=True,
        ), mock.patch('boto3.client') as client_factory:
            client_factory.return_value.upload_file.return_value = None
            result = deliver_backup(record)
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.BOTH

    def test_all_enabled_channels_failing_marks_failed(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        settings.BACKUP_SEND_TO_TELEGRAM = True
        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        with mock.patch(
            'apps.security.telegram_service.send_backup_document',
            return_value=False,
        ):
            result = deliver_backup(record)
        assert result['delivery_status'] == BackupRecord.DeliveryStatus.FAILED
        record.refresh_from_db()
        assert not record.delivered_offsite

    def test_deliver_offsite_api(self, tmp_path, settings):
        record = _make_record(tmp_path, settings)
        client = APIClient()
        admin = AdminUserFactory()
        client.force_authenticate(user=admin)

        def _fake_deliver(rec):
            rec.delivery_status = BackupRecord.DeliveryStatus.TELEGRAM
            rec.save(update_fields=['delivery_status'])
            return {'delivery_status': 'TELEGRAM', 'results': {}}

        with mock.patch(
            'apps.backups.offsite.deliver_backup',
            side_effect=_fake_deliver,
        ):
            res = client.post(f'/api/v1/backups/{record.id}/deliver_offsite/')
        assert res.status_code == 200
        assert res.data['delivery_status'] == 'TELEGRAM'

        # non-admin refused
        client.force_authenticate(user=UserFactory())
        res = client.post(f'/api/v1/backups/{record.id}/deliver_offsite/')
        assert res.status_code == 403


class TestTelegramWebhookDeactivate:
    def _post_callback(self, client, device, settings, secret='s3cr3t'):
        settings.TELEGRAM_WEBHOOK_SECRET = secret
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        return client.post(
            '/api/v1/security/telegram-webhook/',
            {
                'callback_query': {
                    'id': str(uuid.uuid4()),
                    'data': f'deactivate_{device.id}',
                    'message': {
                        'message_id': 7,
                        'text': 'طلب جهاز',
                        'chat': {'id': '42'},
                    },
                },
            },
            format='json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret,
        )

    def test_deactivate_revokes_blocks_and_kills_session(
        self, tmp_path, settings,
    ):
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-test-123', is_trusted=True,
            mac_address='AA:BB:CC:DD:EE:FF',
        )
        cache.set(f'active_sessions:{user.id}', [
            {'session_id': 'sess-1', 'device_fingerprint': 'AND-test-123'},
        ], timeout=3600)

        client = APIClient()
        res = self._post_callback(client, device, settings)
        assert res.status_code == 200

        device.refresh_from_db()
        assert device.is_trusted is False
        assert BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-test-123'
        ).exists()
        # session killed: force_logout_user stamps the revocation time under
        # token_denylist and register_session's record was cleared
        assert cache.get('token_denylist:%s' % user.id)
        assert not cache.get('active_sessions:%s' % user.id)
        # audited — the webhook request carries no device headers, so the
        # fingerprint lives in the event details rather than the column
        assert AuditLog.objects.filter(
            event_type='DEVICE_DEACTIVATED_VIA_TELEGRAM',
            details__device_fingerprint='AND-test-123',
        ).exists()

    def test_deactivate_unknown_device_answered(self, settings):
        settings.TELEGRAM_WEBHOOK_SECRET = 's3cr3t'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        client = APIClient()
        with mock.patch(
            'apps.security.telegram_service.answer_callback_query'
        ) as answer:
            res = client.post(
                '/api/v1/security/telegram-webhook/',
                {
                    'callback_query': {
                        'id': 'x',
                        'data': f'deactivate_{uuid.uuid4()}',
                        'message': {'message_id': 1, 'chat': {'id': '42'}},
                    },
                },
                format='json',
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cr3t',
            )
        assert res.status_code == 200
        assert answer.called

    def test_wrong_secret_rejected(self, settings):
        settings.TELEGRAM_WEBHOOK_SECRET = 's3cr3t'
        client = APIClient()
        res = client.post(
            '/api/v1/security/telegram-webhook/',
            {'callback_query': None},
            format='json',
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='wrong',
        )
        assert res.status_code == 403


class TestScheduledBackupTask:
    def test_success_notifies_telegram(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        from apps.backups import tasks
        with mock.patch(
            'apps.security.telegram_service.send_backup_result_notification',
            return_value=True,
        ) as notify:
            result = tasks.run_scheduled_backup()
        assert result['status'] == 'success'
        notify.assert_called_once()
        kwargs = notify.call_args.kwargs
        assert kwargs['success'] is True
        assert kwargs['record'].delivery_status is not None

    def test_failure_notifies_telegram_and_retries(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        settings.CELERY_TASK_ALWAYS_EAGER = True
        from apps.backups import tasks
        with mock.patch(
            'apps.backups.services.create_backup',
            side_effect=RuntimeError('disk full'),
        ), mock.patch(
            'apps.security.telegram_service.send_backup_result_notification',
            return_value=True,
        ) as notify:
            with pytest.raises(Exception):
                tasks.run_scheduled_backup()
        # the failure leg reached Telegram before the retry re-raise
        assert notify.called
        assert notify.call_args.kwargs['success'] is False


class TestDashboardDeactivation:
    def test_deactivate_action_admin_only(self, tmp_path, settings):
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='PC-dash-1', is_trusted=True,
        )
        client = APIClient()

        # A stranger cannot deactivate someone else's device — the queryset
        # hides other users' devices, so the route answers 404 (or 403)
        other = UserFactory()
        client.force_authenticate(user=other)
        assert client.post(
            f'/api/v1/security/devices/{device.id}/deactivate/'
        ).status_code in (403, 404)

        admin = AdminUserFactory()
        client.force_authenticate(user=admin)
        with mock.patch(
            'apps.security.telegram_service.send_device_deactivated_notification',
            return_value=True,
        ):
            res = client.post(f'/api/v1/security/devices/{device.id}/deactivate/')
        assert res.status_code == 200

        device.refresh_from_db()
        assert device.is_trusted is False
        assert BlockedDevice.objects.enforceable().filter(
            device_fingerprint='PC-dash-1'
        ).exists()
        assert AuditLog.objects.filter(
            event_type='DEVICE_DEACTIVATED',
        ).exists()

    def test_owner_self_deactivates_without_blocklist(self, tmp_path, settings):
        """المالك يزيل جهازه: ثقة مسحوبة، بلا قائمة سوداء، بلا إشعار إنذار."""
        from apps.notifications.models import Notification

        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='PC-own-9', is_trusted=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post(f'/api/v1/security/devices/{device.id}/deactivate/')
        assert res.status_code == 200

        device.refresh_from_db()
        assert device.is_trusted is False
        assert not BlockedDevice.objects.enforceable().filter(
            device_fingerprint='PC-own-9'
        ).exists()
        assert not Notification.objects.filter(
            recipient=user, title='تم إلغاء تفعيل أحد أجهزتك',
        ).exists()

    def test_deactivated_device_fails_check_device(self, tmp_path, settings):
        """إلغاء التفعيل يمنع الجهاز من العبور مجدداً — شاشة القفل تُظهر الحجب."""
        user = UserFactory(email='revoked@securemed.app')
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-revoked-1', is_trusted=False,
        )
        BlockedDevice.objects.create(
            device_fingerprint='AND-revoked-1', reason='إلغاء تفعيل',
        )
        client = APIClient()
        res = client.post(
            '/api/v1/security/check-device/',
            {'device_fingerprint': 'AND-revoked-1'},
            format='json',
        )
        assert res.status_code == 403
        assert res.data['state'] == 'blocked'

    def test_deactivate_invalidates_blocklist_caches(self, settings):
        """السلبية المخزنة (غير محظور) تُبطل فوراً — الحظر يُفرض من الطلب التالي."""
        from django.core.cache import cache
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-cache-1', is_trusted=True,
            mac_address='11:22:33:44:55:66',
        )
        cache.set('blocked_device:AND-cache-1:11:22:33:44:55:66', False, 300)
        cache.set('waf_device_blacklist:AND-cache-1', False, 300)

        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        with mock.patch(
            'apps.security.telegram_service.send_device_deactivated_notification',
            return_value=True,
        ):
            res = client.post(f'/api/v1/security/devices/{device.id}/deactivate/')
        assert res.status_code == 200
        assert cache.get('blocked_device:AND-cache-1:11:22:33:44:55:66') is None
        assert cache.get('waf_device_blacklist:AND-cache-1') is None


class TestDeliveryStatusEndpoint:
    def test_reports_channels(self, settings):
        settings.BACKUP_SEND_TO_TELEGRAM = True
        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        settings.BACKUP_OFFSITE_ENABLED = True
        settings.BACKUP_OFFSITE_BUCKET = 'med-backups'

        client = APIClient()
        admin = AdminUserFactory()
        client.force_authenticate(user=admin)
        res = client.get('/api/v1/backups/delivery_status/')
        assert res.status_code == 200
        assert res.data['telegram']['enabled'] is True
        assert res.data['telegram']['ready'] is True
        assert res.data['cloud']['enabled'] is True
        assert res.data['cloud']['bucket'] == 'med-backups'
        assert res.data['any_enabled'] is True

        # non-admin refused
        client.force_authenticate(user=UserFactory())
        assert client.get('/api/v1/backups/delivery_status/').status_code == 403


class TestAuditTasks:
    def test_chain_verification_alerts_on_problems(self, settings):
        from django.core.cache import cache
        from apps.audit.tasks import verify_audit_chain_task
        from apps.audit.models import AuditLog

        settings.AUDIT_LOG_ASYNC = False
        AuditLog.objects.all().delete()
        log_security_event(
            user=None, event_type='SYSTEM_EVENT', request=None,
            details={'probe': 'chain-ok'},
        )
        # Forging: rewrite the row's details without recomputing its HMAC —
        # exactly what a tampering attacker with DB access would do.
        row = AuditLog.objects.first()
        row.details = {'probe': 'forged'}
        AuditLog.objects.filter(pk=row.pk).update(details=row.details)

        with mock.patch(
            'apps.security.telegram_service.send_critical_alert',
            return_value=True,
        ) as alert:
            result = verify_audit_chain_task(days=1)
        assert result['ok'] is False
        assert result['problems'] >= 1
        alert.assert_called_once()

    def test_digest_task_runs(self, settings):
        from apps.audit.tasks import send_security_digest

        settings.AUDIT_LOG_ASYNC = False
        log_security_event(
            user=None, event_type='LOGIN_FAILED', request=None,
            details={'probe': 'digest'},
        )
        with mock.patch(
            'apps.security.telegram_service.send_critical_alert',
            return_value=True,
        ) as alert:
            result = send_security_digest()
        assert result['events'] >= 1
        assert alert.called_once if False else alert.called

    def test_celery_beat_tasks_all_registered(self):
        """كل مهمة في beat schedule يجب أن تكون معرّفة فعلاً.

        import_default_modules يحاكي ما يفعله عامل celery عند الإقلاع — بدونه
        app.tasks فارغ والفحص يرفع إنذارات كاذبة عن كل مهمة.
        """
        from config.celery import app

        app.loader.import_default_modules()
        registered = set(app.tasks.keys())
        for name, entry in app.conf.beat_schedule.items():
            assert entry['task'] in registered, (
                f"beat task {name} -> {entry['task']} is not registered"
            )


class TestActiveSessionsView:
    def test_list_and_end_own_session(self, settings):
        from django.core.cache import cache
        import time as _time

        user = UserFactory()
        cache.set('active_sessions:%s' % user.id, [
            {'session_id': 'sess-a', 'device_fingerprint': 'FP-A',
             'ip_address': '10.0.0.1', 'timestamp': _time.time()},
            {'session_id': 'sess-b', 'device_fingerprint': 'FP-B',
             'ip_address': '10.0.0.2', 'timestamp': _time.time()},
        ], timeout=3600)

        client = APIClient()
        client.force_authenticate(user=user)

        # list shows both
        res = client.get('/api/v1/security/sessions/')
        assert res.status_code == 200
        assert res.data['count'] == 2
        ids = {s['session_id'] for s in res.data['sessions']}
        assert ids == {'sess-a', 'sess-b'}

        # end one of them
        res = client.delete(
            '/api/v1/security/sessions/',
            {'session_id': 'sess-b'}, format='json',
        )
        assert res.status_code == 200
        assert cache.get('session_denylist:sess-b')
        remaining = cache.get('active_sessions:%s' % user.id)
        assert {s['session_id'] for s in remaining} == {'sess-a'}

        # ending a session the user does not own → 404
        res = client.delete(
            '/api/v1/security/sessions/',
            {'session_id': 'someone-elses'}, format='json',
        )
        assert res.status_code == 404

        # audited
        from apps.audit.models import AuditLog
        assert AuditLog.objects.filter(
            event_type='SESSION_ENDED_BY_USER',
        ).exists()

    def test_end_all_sessions(self, settings):
        from django.core.cache import cache

        user = UserFactory()
        cache.set('active_sessions:%s' % user.id, [
            {'session_id': 'sess-x', 'device_fingerprint': 'FP-X',
             'ip_address': '10.0.0.1', 'timestamp': 0},
            {'session_id': 'sess-y', 'device_fingerprint': 'FP-Y',
             'ip_address': '10.0.0.2', 'timestamp': 0},
        ], timeout=3600)

        client = APIClient()
        client.force_authenticate(user=user)
        res = client.delete('/api/v1/security/sessions/', format='json')
        assert res.status_code == 200
        # account-wide revocation stamp + registry cleared — force_logout_user
        # denies every token the user holds via token_denylist, which is
        # stronger than a per-session denylist
        assert cache.get('token_denylist:%s' % user.id)
        assert cache.get('active_sessions:%s' % user.id) is None

    def test_requires_auth(self):
        client = APIClient()
        assert client.get('/api/v1/security/sessions/').status_code == 401


class TestUserNotifications:
    """المستخدم يُبلَّغ داخل التطبيق عند أحداث أجهزته."""

    def test_deactivation_notifies_owner(self, settings):
        from apps.notifications.models import Notification

        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-notify-1', is_trusted=True,
        )
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        with mock.patch(
            'apps.security.telegram_service.send_device_deactivated_notification',
            return_value=True,
        ):
            client.post(f'/api/v1/security/devices/{device.id}/deactivate/')

        notif = Notification.objects.filter(
            recipient=user, notification_type='SECURITY_ALERT',
        ).first()
        assert notif is not None
        assert 'إلغاء تفعيل' in notif.title

    def test_approval_notifies_owner(self, settings):
        from apps.notifications.models import Notification

        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-notify-2', is_trusted=False,
        )
        settings.TELEGRAM_WEBHOOK_SECRET = 's3cr3t'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'
        client = APIClient()
        with mock.patch(
            'apps.security.telegram_service.answer_callback_query'
        ), mock.patch(
            'apps.security.telegram_service.edit_message_text'
        ):
            client.post(
                '/api/v1/security/telegram-webhook/',
                {
                    'callback_query': {
                        'id': 'x',
                        'data': f'approve_{device.id}',
                        'message': {'message_id': 1, 'chat': {'id': '42'}},
                    },
                },
                format='json',
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN='s3cr3t',
            )
        assert Notification.objects.filter(
            recipient=user, notification_type='LOGIN_ALERT',
            title='تم تفعيل جهاز جديد',
        ).exists()

    def test_registration_request_notifies_user(self, settings):
        from apps.notifications.models import Notification

        user = UserFactory(email='pending@securemed.app')
        client = APIClient()
        with mock.patch(
            'apps.security.telegram_service.send_device_approval_request',
            return_value=True,
        ):
            client.post(
                '/api/v1/security/check-device/',
                {
                    'device_fingerprint': 'AND-new-req-1',
                    'email': 'pending@securemed.app',
                },
                format='json',
            )
        assert Notification.objects.filter(
            recipient=user, notification_type='LOGIN_ALERT',
            title='وصلنا طلب تفعيل جهازك',
        ).exists()


class TestCleanupBlocklists:
    def test_expired_blocks_removed_and_stale_untrusted(self, tmp_path, settings):
        from django.core.management import call_command
        from django.utils import timezone
        from datetime import timedelta
        from apps.security.models import BlockedIP

        BlockedDevice.objects.create(
            device_fingerprint='AND-expired-1',
            expires_at=timezone.now() - timedelta(days=1),
        )
        BlockedIP.objects.create(
            ip_address='203.0.113.50',
            expires_at=timezone.now() - timedelta(days=1),
        )
        stale = DeviceRegistry.objects.create(
            user=UserFactory(), device_fingerprint='AND-stale-1',
            is_trusted=True,
        )
        DeviceRegistry.objects.filter(pk=stale.pk).update(
            last_login=timezone.now() - timedelta(days=200),
        )

        call_command('cleanup_blocklists', untrust_days=180)

        assert not BlockedDevice.objects.filter(
            device_fingerprint='AND-expired-1'
        ).exists()
        assert not BlockedIP.objects.filter(ip_address='203.0.113.50').exists()
        stale.refresh_from_db()
        assert stale.is_trusted is False

    def test_dry_run_changes_nothing(self, tmp_path, settings):
        from django.core.management import call_command
        from django.utils import timezone
        from datetime import timedelta

        BlockedDevice.objects.create(
            device_fingerprint='AND-expired-2',
            expires_at=timezone.now() - timedelta(days=1),
        )
        call_command('cleanup_blocklists', dry_run=True)
        assert BlockedDevice.objects.filter(
            device_fingerprint='AND-expired-2'
        ).exists()


def log_security_event(user, event_type, request, details, severity='INFO'):
    from apps.audit.utils import log_security_event as real
    return real(user=user, event_type=event_type, request=request,
                details=details, severity=severity)
