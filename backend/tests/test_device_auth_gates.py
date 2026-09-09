"""
Tests for the device-authorization holes that were closed:

* MFALoginView enforced no device gate — an untrusted device could complete
  2FA and receive tokens; a blocked device even more so.
* MFALoginView honoured trust_device=True under ENFORCE_DEVICE_AUTHORIZATION,
  letting a client mint its own activation license.
* devices/{id}/trust/ let a user trust a blacklisted device back into the
  WAF's good graces without lifting the block.
* New-device logins now notify the owner (LOGIN_ALERT).
"""
import pytest
import pyotp
from unittest import mock

from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.security.models import BlockedDevice, DeviceRegistry
from tests.factories import UserFactory, PatientFactory

pytestmark = pytest.mark.django_db


def _start_mfa(client, user, settings):
    """Drive the first leg of 2FA login and return the pending token."""
    cache.set('mfa_pending:tok-1', str(user.id), timeout=300)
    return 'tok-1'


def _make_2fa_user():
    """2FA-enabled user whose mfa_secret is stored encrypted, as production
    writes it. Returns (user, raw_secret) — the stored field decrypts only
    through decrypt_field, so the test needs the raw TOTP secret to mint codes.
    """
    from apps.security.crypto import encrypt_field
    user = UserFactory()
    raw_secret = pyotp.random_base32()
    user.mfa_enabled = True
    user.mfa_secret = encrypt_field(raw_secret)
    user.save(update_fields=['mfa_enabled', 'mfa_secret'])
    return user, raw_secret


class TestMFADeviceGate:
    def _settings_for_2fa(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        settings.ADAPTIVE_MFA_ENABLED = True

    def test_blocked_device_cannot_complete_mfa(self, settings):
        self._settings_for_2fa(settings)
        user, raw_secret = _make_2fa_user()

        BlockedDevice.objects.create(device_fingerprint='AND-evil-1')

        client = APIClient()
        res = client.post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': _start_mfa(client, user, settings),
             'code': pyotp.TOTP(raw_secret).now()},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='AND-evil-1',
        )
        assert res.status_code == 403
        assert not hasattr(res, 'data') or 'tokens' not in res.data

    def test_untrusted_device_cannot_complete_mfa(self, settings):
        self._settings_for_2fa(settings)
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user, raw_secret = _make_2fa_user()

        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-new-9', is_trusted=False,
        )

        client = APIClient()
        res = client.post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': _start_mfa(client, user, settings),
             'code': pyotp.TOTP(raw_secret).now()},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='AND-new-9',
        )
        assert res.status_code == 403
        assert 'tokens' not in res.data

    def test_trusted_device_completes_mfa(self, settings):
        self._settings_for_2fa(settings)
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user, raw_secret = _make_2fa_user()

        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-ok-1', is_trusted=True,
        )

        client = APIClient()
        res = client.post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': _start_mfa(client, user, settings),
             'code': pyotp.TOTP(raw_secret).now()},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='AND-ok-1',
        )
        assert res.status_code == 200
        assert 'tokens' in res.data

    def test_trust_device_ignored_when_enforced(self, settings):
        """trust_device=True لا يصنع ترخيصاً ذاتياً — التوثيق للإدارة فقط."""
        self._settings_for_2fa(settings)
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user, raw_secret = _make_2fa_user()

        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-self-1', is_trusted=False,
        )

        client = APIClient()
        res = client.post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': _start_mfa(client, user, settings),
             'code': pyotp.TOTP(raw_secret).now(),
             'trust_device': True},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='AND-self-1',
        )
        assert res.status_code == 403
        # and the device is still untrusted — no self-license
        device = DeviceRegistry.objects.get(device_fingerprint='AND-self-1')
        assert device.is_trusted is False


class TestTrustBlockedDevice:
    def test_cannot_trust_blacklisted_device(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-blocked-7', is_trusted=False,
        )
        BlockedDevice.objects.create(device_fingerprint='AND-blocked-7')

        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post(f'/api/v1/security/devices/{device.id}/trust/')
        assert res.status_code == 403
        device.refresh_from_db()
        assert device.is_trusted is False

    def test_trust_non_blocked_device_works_and_audits(self, settings):
        """In the lenient adaptive-auth mode self-trust still works, and is
        audited."""
        settings.AUDIT_LOG_ASYNC = False
        settings.ENFORCE_DEVICE_AUTHORIZATION = False
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-clean-3', is_trusted=False,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post(f'/api/v1/security/devices/{device.id}/trust/')
        assert res.status_code == 200
        # the audit row carries the fingerprint in details — the API test
        # request sends no X-Device-Fingerprint header
        assert AuditLog.objects.filter(
            event_type='DEVICE_TRUSTED',
            details__device_fingerprint='AND-clean-3',
        ).exists()

    def test_self_trust_refused_under_enforcement(self, settings):
        """مستخدم بجهاز موثوق لا يمنح ثقة لأجهزته الجديدة ذاتياً — التوثيق
        عبر الإدارة فقط عندما يكون التفعيل إلزامياً."""
        settings.AUDIT_LOG_ASYNC = False
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user = UserFactory()
        # their existing trusted device — the classic self-escalation start
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-own-1', is_trusted=True,
        )
        new_device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-own-2', is_trusted=False,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post(f'/api/v1/security/devices/{new_device.id}/trust/')
        assert res.status_code == 403
        new_device.refresh_from_db()
        assert new_device.is_trusted is False

    def test_admin_may_trust_any_user_device(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-admin-1', is_trusted=False,
        )
        from tests.factories import AdminUserFactory
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'/api/v1/security/devices/{device.id}/trust/')
        assert res.status_code == 200
        device.refresh_from_db()
        assert device.is_trusted is True


class TestNewDeviceLoginAlert:
    def test_new_device_login_notifies_owner(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory()

        from apps.audit.device_tracker import DeviceTracker

        class FakeRequest:
            path = '/api/v1/auth/login/'
            method = 'POST'
            META = {'HTTP_X_DEVICE_FINGERPRINT': 'AND-alert-1'}

        device, suspicious = DeviceTracker.track_device(
            user, FakeRequest(),
            {'device_fingerprint': 'AND-alert-1', 'ip_address': '10.1.1.1',
             'os_info': 'Android 14', 'mac_address': '', 'browser_info': ''},
        )
        assert suspicious is True
        notif = Notification.objects.filter(
            recipient=user, notification_type='LOGIN_ALERT',
            title='دخول من جهاز جديد',
        ).first()
        assert notif is not None
        assert '10.1.1.1' in notif.message

    def test_repeat_login_does_not_realert(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory()
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-known-1', is_trusted=True,
            location='Riyadh',
        )

        from apps.audit.device_tracker import DeviceTracker

        class FakeRequest:
            path = '/api/v1/auth/login/'
            method = 'POST'
            META = {'HTTP_X_DEVICE_FINGERPRINT': 'AND-known-1'}

        # same device, same location → not suspicious → no alert
        device, suspicious = DeviceTracker.track_device(
            user, FakeRequest(),
            {'device_fingerprint': 'AND-known-1', 'ip_address': '10.1.1.1',
             'os_info': 'Android 14', 'mac_address': '', 'browser_info': ''},
        )
        assert suspicious is False
        assert not Notification.objects.filter(
            recipient=user, title='دخول من جهاز جديد',
        ).exists()


class TestPendingDevicesDigest:
    def test_digest_lists_pending_with_buttons(self, settings):
        from apps.security.tasks import send_pending_devices_digest_task

        settings.TELEGRAM_BOT_TOKEN = '123:abc'
        settings.TELEGRAM_ADMIN_CHAT_ID = '42'

        user = UserFactory()
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-wait-1', is_trusted=False,
        )
        DeviceRegistry.objects.create(
            user=UserFactory(), device_fingerprint='AND-wait-2',
            is_trusted=False,
        )

        with mock.patch(
            'apps.security.telegram_service.requests.post',
        ) as tg:
            tg.return_value.status_code = 200
            result = send_pending_devices_digest_task()

        assert result['pending'] == 2
        assert result['sent'] is True
        payload = tg.call_args.kwargs['json']
        assert 'بانتظار الموافقة (2)' in payload['text']
        buttons = payload['reply_markup']['inline_keyboard']
        # one approve row per device, each carrying the approve callback
        assert len(buttons) == 2
        assert buttons[0][0]['callback_data'].startswith('approve_')

    def test_digest_silent_when_nothing_pending(self, settings):
        from apps.security.tasks import send_pending_devices_digest_task

        with mock.patch(
            'apps.security.telegram_service.requests.post'
        ) as tg:
            result = send_pending_devices_digest_task()
        assert result['pending'] == 0
        tg.assert_not_called()


class TestSelfDeactivation:
    """المستخدم يزيل جهازه ذاتياً: ثقة سحبت وجلسة قتلت بلا قائمة سوداء."""

    def test_owner_deactivates_own_device(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-mine-1', is_trusted=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        with mock.patch(
            'apps.security.telegram_service.send_device_deactivated_notification',
            return_value=True,
        ):
            res = client.post(
                f'/api/v1/security/devices/{device.id}/deactivate/',
            )
        assert res.status_code == 200
        device.refresh_from_db()
        assert device.is_trusted is False
        # NOT blacklisted — the owner may request activation again later
        assert not BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-mine-1'
        ).exists()
        # no alarm notification — the user did it themselves
        assert not Notification.objects.filter(
            recipient=user, title='تم إلغاء تفعيل أحد أجهزتك',
        ).exists()
        # audited with the self path
        assert AuditLog.objects.filter(
            event_type='DEVICE_DEACTIVATED',
            details__via='self',
        ).exists()

    def test_other_users_device_still_admin_only(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        owner = UserFactory()
        device = DeviceRegistry.objects.create(
            user=owner, device_fingerprint='AND-theirs-1', is_trusted=True,
        )
        stranger = UserFactory()

        client = APIClient()
        client.force_authenticate(user=stranger)
        res = client.post(
            f'/api/v1/security/devices/{device.id}/deactivate/',
        )
        # 404 from the queryset scoping (a stranger's device is invisible) —
        # the important part is "not 2xx" and the device untouched
        assert res.status_code in (403, 404)
        device.refresh_from_db()
        assert device.is_trusted is True

