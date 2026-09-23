import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.security.models import DeviceRegistry, ZTNAPendingApproval
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestSingleDeviceLockingAndSwitch:
    def setup_method(self):
        cache.clear()

    @patch('apps.security.telegram_service.send_device_switch_request')
    def test_login_from_second_device_blocked_and_triggers_switch_request(self, mock_switch, settings):
        """
        When a user already has an active trusted device, attempting to log in
        from a second device with valid credentials must be blocked (403),
        and send_device_switch_request must be called with old & new device details.
        """
        settings.ENFORCE_DEVICE_AUTHORIZATION = True
        user = UserFactory(email='doctor@securemed.com')
        user.set_password('CorrectPassword123!')
        user.save()

        # Old device registered and trusted
        old_device = DeviceRegistry.objects.create(
            user=user,
            device_fingerprint='OLD-DEVICE-FP-001',
            os_info='Windows 10',
            browser_info='Chrome 120',
            last_ip_address='192.168.1.50',
            is_trusted=True
        )

        client = APIClient()
        response = client.post(
            '/api/v1/auth/login/',
            {'email': 'doctor@securemed.com', 'password': 'CorrectPassword123!'},
            format='json',
            HTTP_X_DEVICE_FINGERPRINT='NEW-DEVICE-FP-002',
            HTTP_X_OS_INFO='Android 14',
            HTTP_X_BROWSER_INFO='SecureMed Mobile App',
            REMOTE_ADDR='192.168.1.99'
        )

        assert response.status_code == 403
        assert response.data.get('code') == 'DEVICE_LOCKED_TO_ANOTHER_DEVICE'
        assert 'مفعّل على جهاز آخر' in response.data.get('detail', '')

        # Verify new device was created as untrusted
        new_device = DeviceRegistry.objects.get(user=user, device_fingerprint='NEW-DEVICE-FP-002')
        assert new_device.is_trusted is False

        # Verify telegram switch request was dispatched
        mock_switch.assert_called_once()
        call_kwargs = mock_switch.call_args[1] if mock_switch.call_args[1] else {}
        call_args = mock_switch.call_args[0]
        # Check args passed (user, new_device, old_device)
        assert (call_kwargs.get('user') == user or call_args[0] == user)

    def test_switch_callback_untrusts_old_and_trusts_new_for_that_user_only(self, settings):
        """
        When Telegram admin approves switch (switch_<id>), old devices for THIS user
        are revoked/untrusted, and the new device is trusted and licensed. Other users'
        devices must remain untouched.
        """
        settings.TELEGRAM_ADMIN_CHAT_ID = '12345678'
        user1 = UserFactory(email='user1@securemed.com')
        user2 = UserFactory(email='user2@securemed.com')

        # User 1 old device
        u1_old = DeviceRegistry.objects.create(
            user=user1, device_fingerprint='U1-OLD', is_trusted=True
        )
        # User 1 new device
        u1_new = DeviceRegistry.objects.create(
            user=user1, device_fingerprint='U1-NEW', is_trusted=False
        )

        # User 2 device (must NOT be touched)
        u2_dev = DeviceRegistry.objects.create(
            user=user2, device_fingerprint='U2-DEVICE', is_trusted=True
        )

        from apps.security.telegram_bot import process_update

        update = {
            'callback_query': {
                'id': 'cb-switch-1',
                'data': f'switch_{u1_new.id}',
                'message': {
                    'message_id': 999,
                    'chat': {'id': 12345678},
                    'text': 'طلب نقل تفعيل حساب'
                }
            }
        }

        with patch('apps.security.telegram_service.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {'ok': True}
            result = process_update(update)

        assert result is True

        u1_old.refresh_from_db()
        u1_new.refresh_from_db()
        u2_dev.refresh_from_db()

        # User 1 old device untrusted, new device trusted
        assert u1_old.is_trusted is False
        assert u1_new.is_trusted is True

        # User 2 device is still trusted and untouched!
        assert u2_dev.is_trusted is True


class TestStrictZTNAIPValidation:
    def setup_method(self):
        cache.clear()

    def test_network_change_blocks_access_without_ip_update(self):
        """
        When a trusted device connects from an unapproved IP, check-device
        must return 403 (network_changed / ZTNA_BLOCKED) and NOT silently update last_ip_address.
        """
        user = UserFactory()
        device = DeviceRegistry.objects.create(
            user=user,
            device_fingerprint='TRUSTED-DEVICE-IP-TEST',
            last_ip_address='10.0.0.1',
            is_trusted=True
        )

        client = APIClient()
        response = client.post(
            '/api/v1/security/check-device/',
            {'device_fingerprint': 'TRUSTED-DEVICE-IP-TEST'},
            format='json',
            REMOTE_ADDR='10.0.0.99'  # Changed network IP!
        )

        assert response.status_code == 403
        assert response.data.get('state') == 'network_changed'
        assert response.data.get('code') == 'ZTNA_BLOCKED'

        # Verify device last_ip_address was NOT silently updated
        device.refresh_from_db()
        assert device.last_ip_address == '10.0.0.1'
