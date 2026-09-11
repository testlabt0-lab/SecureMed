"""
Tests for the device licensing system (متطلب د. مجد):

* شاشة القفل لا تُرفع إلا للأجهزة المرخصة — الثقة وحدها لا تكفي.
* التحقق يتم عبر الماك ادرس أو بصمة الجهاز.
* التفعيل/إلغاء التفعيل مرتبط بتلجرام (أوامر البوت) ولوحة الإدارة.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.security.models import DeviceLicense, DeviceRegistry
from tests.factories import AdminUserFactory, UserFactory

pytestmark = pytest.mark.django_db


def _make_device(user=None, fingerprint='AND-lic-1', mac='AA:BB:CC:DD:EE:01',
                 trusted=True):
    user = user or UserFactory()
    return DeviceRegistry.objects.create(
        user=user, device_fingerprint=fingerprint, mac_address=mac,
        is_trusted=trusted,
    )


def _check(client, fingerprint, mac=''):
    return client.post(
        '/api/v1/security/check-device/',
        {'device_fingerprint': fingerprint, 'mac_address': mac},
        format='json',
        HTTP_X_DEVICE_FINGERPRINT=fingerprint,
        HTTP_X_MAC_ADDRESS=mac,
    )


class TestLicenseModel:
    def test_issue_creates_active_license_with_readable_key(self):
        from apps.security.licensing import issue_license
        device = _make_device()
        license_obj, created = issue_license(device, issued_by='system')

        assert created is True
        assert license_obj.status == DeviceLicense.Status.ACTIVE
        assert license_obj.is_valid is True
        # SMED-XXXXX-XXXXX-XXXXX-XXXXX and no ambiguous characters
        key = license_obj.license_key
        assert key.startswith('SMED-')
        groups = key.split('-')[1:]
        assert len(groups) == 4 and all(len(g) == 5 for g in groups)
        assert not set(key.replace('SMED-', '')) & set('0O1IL')

    def test_expired_license_is_not_valid_but_reads_expired(self):
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-EXPIRED-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
            expires_at=timezone.now() - timedelta(days=1),
        )
        license_obj = DeviceLicense.objects.get(device=device)
        assert license_obj.is_valid is False
        assert license_obj.effective_status == 'EXPIRED'

    def test_reactivation_of_revoked_license_rotates_key(self):
        from apps.security.licensing import issue_license, deactivate_license
        device = _make_device()
        license_obj, _ = issue_license(device)
        old_key = license_obj.license_key
        deactivate_license(device, via='test')

        license_obj, created = issue_license(device)
        assert created is False
        assert license_obj.license_key != old_key
        assert license_obj.is_valid is True


class TestCheckDeviceLicenseGate:
    def test_licensed_trusted_device_is_authorized(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-LICENSE-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
        )
        res = _check(APIClient(), device.device_fingerprint, device.mac_address)
        assert res.status_code == 200
        assert res.data['state'] == 'authorized'
        assert res.data['licensed'] is True

    def test_revoked_license_shows_lock_screen_state(self, settings):
        """جهاز موثوق لكن ترخيصه ملغى → شاشة القفل (unlicensed) بلا حظر."""
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-REVOKED-KEY1-2345-6789',
            status=DeviceLicense.Status.REVOKED,
        )
        res = _check(APIClient(), device.device_fingerprint, device.mac_address)
        assert res.status_code == 403
        assert res.data['state'] == 'unlicensed'
        assert res.data['code'] == 'DEVICE_UNLICENSED'
        assert res.data['licensed'] is False
        # denial attempt audited with the MAC that was presented
        assert AuditLog.objects.filter(
            event_type='DEVICE_UNLICENSED_ACCESS',
            details__mac_address=device.mac_address,
        ).exists()
        # and the device was NOT blacklisted — license revocation only
        from apps.security.models import BlockedDevice
        assert not BlockedDevice.objects.enforceable().filter(
            device_fingerprint=device.device_fingerprint
        ).exists()

    def test_expired_license_denies_access(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-EXPIRED-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
            expires_at=timezone.now() - timedelta(days=1),
        )
        res = _check(APIClient(), device.device_fingerprint)
        assert res.status_code == 403
        assert res.data['license_status'] == 'EXPIRED'

    def test_legacy_trusted_device_is_licensed_automatically_once(self, settings):
        """الأجهزة الموثوقة قبل هذه الميزة تُرخَّص تلقائياً عند أول تحقق."""
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()  # trusted, no license row
        res = _check(APIClient(), device.device_fingerprint)
        assert res.status_code == 200
        assert res.data['state'] == 'authorized'
        assert DeviceLicense.objects.filter(device=device).exists()

    def test_mac_address_alone_identifies_the_device(self, settings):
        """الماك ادرس يكفي لتحديد الجهاز عندما لا تطابق البصمة."""
        settings.AUDIT_LOG_ASYNC = False
        from apps.security.licensing import is_device_licensed
        device = _make_device(fingerprint='AND-mac-1', mac='AA:BB:CC:DD:EE:99')
        DeviceLicense.objects.create(
            device=device, license_key='SMED-BYMAC00-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
        )
        assert is_device_licensed(mac_address='AA:BB:CC:DD:EE:99') is True
        assert is_device_licensed(fingerprint='AND-unknown') is False


class TestTelegramLicenseCommands:
    def test_approve_issues_license(self, settings):
        from apps.security.telegram_bot import _cmd_approve
        device = _make_device(trusted=False)
        reply = _cmd_approve(str(device.id))
        device.refresh_from_db()
        assert device.is_trusted is True
        assert DeviceLicense.objects.filter(device=device).exists()
        assert 'مفتاح الترخيص' in reply

    def test_license_command_sets_expiry(self):
        from apps.security.telegram_bot import _cmd_license
        device = _make_device(trusted=False)
        reply = _cmd_license(str(device.id), days='30')
        license_obj = DeviceLicense.objects.get(device=device)
        assert license_obj.is_valid is True
        assert license_obj.expires_at is not None
        assert timezone.now() + timedelta(days=29) < license_obj.expires_at
        assert 'المفتاح' in reply

    def test_revoke_command_revokes_and_locks(self):
        from apps.security.telegram_bot import _cmd_revoke
        from apps.security.licensing import issue_license
        device = _make_device()
        issue_license(device)
        reply = _cmd_revoke(str(device.id))
        license_obj = DeviceLicense.objects.get(device=device)
        assert license_obj.status == DeviceLicense.Status.REVOKED
        assert 'أُلغي ترخيص' in reply
        # idempotent second call
        assert 'ملغى بالفعل' in _cmd_revoke(str(device.id))

    def test_revoke_audits_deactivation(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        from apps.security.telegram_bot import _cmd_revoke
        from apps.security.licensing import issue_license
        device = _make_device()
        issue_license(device)
        _cmd_revoke(str(device.id))
        assert AuditLog.objects.filter(
            event_type='DEVICE_LICENSE_DEACTIVATED',
            details__license_key=DeviceLicense.objects.get(device=device).license_key,
        ).exists()


class TestDeactivateRevokesLicense:
    def test_full_device_deactivation_revokes_license(self, settings):
        """إلغاء تفعيل الجهاز (حظر) يسحب الترخيص أيضاً — قاعدة موحدة."""
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-BLOCKED-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
        )
        from apps.security.views import _deactivate_device
        _deactivate_device(device, request=None, via='dashboard', block=True)
        license_obj = DeviceLicense.objects.get(device=device)
        assert license_obj.status == DeviceLicense.Status.REVOKED


class TestLicenseAdminAPI:
    def test_admin_can_issue_and_revoke(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        admin = AdminUserFactory()
        device = _make_device(trusted=False)

        client = APIClient()
        client.force_authenticate(user=admin)

        res = client.post('/api/v1/security/licenses/issue/',
                          {'device_id': str(device.id), 'days': 7}, format='json')
        assert res.status_code == 201
        license_obj = DeviceLicense.objects.get(device=device)
        assert license_obj.issued_by == 'dashboard'
        assert license_obj.expires_at is not None

        res = client.post(f'/api/v1/security/licenses/{license_obj.id}/deactivate/')
        assert res.status_code == 200
        license_obj.refresh_from_db()
        assert license_obj.status == DeviceLicense.Status.REVOKED

    def test_non_admin_is_refused(self):
        device = _make_device(trusted=False)
        client = APIClient()
        client.force_authenticate(user=device.user)
        res = client.post('/api/v1/security/licenses/issue/',
                          {'device_id': str(device.id)}, format='json')
        assert res.status_code == 403

    def test_issue_unknown_device_404(self):
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post('/api/v1/security/licenses/issue/',
                          {'device_id': '00000000-0000-0000-0000-000000000000'},
                          format='json')
        assert res.status_code == 404


class TestTelegramGateOnLoginDeniedForUnlicensed:
    def test_unlicensed_trusted_device_cannot_complete_login_flow(self, settings):
        """بوابة check-device هي ما يظهر شاشة القفل — 403 للجهاز غير المرخص."""
        settings.AUDIT_LOG_ASYNC = False
        device = _make_device()
        DeviceLicense.objects.create(
            device=device, license_key='SMED-SUSPENDED-KEY1-2345-6789',
            status=DeviceLicense.Status.SUSPENDED,
        )
        res = _check(APIClient(), device.device_fingerprint)
        assert res.data['state'] == 'unlicensed'
        assert User.objects.filter(pk=device.user_id).exists()


class TestLoginLicenseGate:
    """بوابة الترخيص داخل مسارات الدخول نفسها — نداء API مباشر بمسار
    الدخول لا يتفادى شاشة القفل."""

    def _login(self, client, user, fingerprint, mac):
        return client.post(
            '/api/v1/auth/login/',
            {'email': user.email, 'password': 'Test-Pass-123'},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT=fingerprint,
            HTTP_X_MAC_ADDRESS=mac,
        )

    def _user_with_password(self):
        user = UserFactory()
        user.set_password('Test-Pass-123')
        user.save(update_fields=['password'])
        return user

    def test_login_refused_for_unlicensed_trusted_device(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = self._user_with_password()
        device = _make_device(user=user, fingerprint='AND-gate-1',
                              mac='AA:BB:CC:00:00:01', trusted=True)
        DeviceLicense.objects.create(
            device=device, license_key='SMED-LOGIN00-KEY1-2345-6789',
            status=DeviceLicense.Status.REVOKED,
        )
        res = self._login(APIClient(), user, 'AND-gate-1', 'AA:BB:CC:00:00:01')
        assert res.status_code == 403
        assert res.data['code'] == 'DEVICE_UNLICENSED'
        assert 'tokens' not in res.data
        # and the denial is audited with the license status
        assert AuditLog.objects.filter(
            event_type='LOGIN_FAILED',
            details__reason='unlicensed_device',
        ).exists()

    def test_login_succeeds_for_licensed_trusted_device(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = self._user_with_password()
        device = _make_device(user=user, fingerprint='AND-gate-ok',
                              mac='AA:BB:CC:00:00:02', trusted=True)
        DeviceLicense.objects.create(
            device=device, license_key='SMED-LOGINOK-KEY1-2345-6789',
            status=DeviceLicense.Status.ACTIVE,
        )
        res = self._login(APIClient(), user, 'AND-gate-ok', 'AA:BB:CC:00:00:02')
        assert res.status_code == 200
        assert 'tokens' in res.data

    def test_login_auto_licenses_legacy_trusted_device(self, settings):
        """جهاز موثوق قديم بلا ترخيص يُرخَّص تلقائياً ويدخل — نفس قاعدة check-device."""
        settings.AUDIT_LOG_ASYNC = False
        user = self._user_with_password()
        _make_device(user=user, fingerprint='AND-gate-old',
                     mac='AA:BB:CC:00:00:03', trusted=True)
        res = self._login(APIClient(), user, 'AND-gate-old', 'AA:BB:CC:00:00:03')
        assert res.status_code == 200
        assert DeviceLicense.objects.filter(
            device__device_fingerprint='AND-gate-old',
        ).exists()

    def test_mfa_login_refused_for_unlicensed_trusted_device(self, settings):
        import pyotp
        from apps.security.crypto import encrypt_field

        settings.AUDIT_LOG_ASYNC = False
        settings.ADAPTIVE_MFA_ENABLED = True
        user = UserFactory()
        raw_secret = pyotp.random_base32()
        user.set_password('Test-Pass-123')
        user.mfa_enabled = True
        user.mfa_secret = encrypt_field(raw_secret)
        user.save(update_fields=['password', 'mfa_enabled', 'mfa_secret'])

        device = _make_device(user=user, fingerprint='AND-gate-mfa',
                              mac='AA:BB:CC:00:00:04', trusted=True)
        DeviceLicense.objects.create(
            device=device, license_key='SMED-MFAGATE-KEY1-2345-6789',
            status=DeviceLicense.Status.REVOKED,
        )

        import django.core.cache as django_cache
        django_cache.cache.set('mfa_pending:tok-gate', str(user.id), timeout=300)
        res = APIClient().post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': 'tok-gate',
             'code': pyotp.TOTP(raw_secret).now()},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='AND-gate-mfa',
        )
        assert res.status_code == 403
        assert res.data['code'] == 'DEVICE_UNLICENSED'
        assert 'tokens' not in res.data
