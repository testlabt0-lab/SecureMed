"""
Tests for MAC-address recording in LoginHistory.

Dr. Majd's requirement: «سجل التدقيق لكل حدث ويرصد الماك ادرس» — the audit
log recorded the MAC but the login history table (the table auditors actually
browse per login attempt) dropped it on the floor at all four call sites:
failed login, password login, biometric login, and the 2FA completion path.
"""
import pyotp
import pytest

from apps.security.models import LoginHistory
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


HEADERS = {
    'HTTP_X_DEVICE_FINGERPRINT': 'AND-mac-1',
    'HTTP_X_MAC_ADDRESS': 'AA:BB:CC:DD:EE:01',
    'HTTP_X_OS_INFO': 'Android 14',
    'HTTP_X_BROWSER_INFO': 'SecureMedApp',
    'HTTP_USER_AGENT': 'SecureMedApp/1.0',
}


class TestLoginHistoryMac:
    def test_failed_login_records_mac(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory(email='mac@securemed.app')

        from rest_framework.test import APIClient
        client = APIClient()
        client.post(
            '/api/v1/auth/login/',
            {'email': 'mac@securemed.app', 'password': 'wrong-password'},
            format='json',
            **HEADERS,
        )

        row = LoginHistory.objects.filter(
            device_fingerprint='AND-mac-1', is_success=False,
        ).first()
        assert row is not None
        assert row.mac_address == 'AA:BB:CC:DD:EE:01'

    def test_successful_login_records_mac(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        user = UserFactory(email='mac2@securemed.app', password='Str0ng!Pass1')

        from rest_framework.test import APIClient
        client = APIClient()
        res = client.post(
            '/api/v1/auth/login/',
            {'email': 'mac2@securemed.app', 'password': 'Str0ng!Pass1'},
            format='json',
            **HEADERS,
        )
        assert res.status_code == 200

        row = LoginHistory.objects.filter(
            device_fingerprint='AND-mac-1', is_success=True,
        ).first()
        assert row is not None
        assert row.mac_address == 'AA:BB:CC:DD:EE:01'

    def test_mfa_login_records_mac(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        settings.ADAPTIVE_MFA_ENABLED = True
        from apps.security.crypto import encrypt_field
        from django.core.cache import cache

        user = UserFactory(email='mac3@securemed.app', password='Str0ng!Pass1')
        raw_secret = pyotp.random_base32()
        user.mfa_enabled = True
        user.mfa_secret = encrypt_field(raw_secret)
        user.save(update_fields=['mfa_enabled', 'mfa_secret'])

        DeviceRegistry = __import__(
            'apps.security.models', fromlist=['DeviceRegistry']
        ).DeviceRegistry
        DeviceRegistry.objects.create(
            user=user, device_fingerprint='AND-mac-1', is_trusted=True,
        )

        cache.set('mfa_pending:mac-tok', str(user.id), timeout=300)

        from rest_framework.test import APIClient
        client = APIClient()
        res = client.post(
            '/api/v1/auth/2fa/login/',
            {'mfa_token': 'mac-tok', 'code': pyotp.TOTP(raw_secret).now()},
            format='json',
            **HEADERS,
        )
        assert res.status_code == 200

        row = LoginHistory.objects.filter(
            device_fingerprint='AND-mac-1', is_success=True,
        ).first()
        assert row is not None
        assert row.mac_address == 'AA:BB:CC:DD:EE:01'
