from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.security.models import DeviceRegistry
from unittest.mock import patch

User = get_user_model()

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class AdaptiveMFATest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testmfa@example.com',
            password='testpassword123!',
            full_name='Test MFA User',
            role='PATIENT'
        )
        self.login_url = reverse('login')
        # Clear cache to avoid rate limit or pending MFA tokens
        cache.clear()

    @patch('apps.audit.device_tracker.log_security_event')
    def test_adaptive_mfa_flow(self, mock_log_security_event):
        """
        1. Login from a normal IP. Should succeed and register device.
        2. Login from a different IP. Should require verification.
        """
        # --- Step 1: First login from IP 1 ---
        response = self.client.post(self.login_url, {
            'email': 'testmfa@example.com',
            'password': 'testpassword123!'
        }, REMOTE_ADDR='192.168.1.1', HTTP_X_DEVICE_FINGERPRINT='fingerprint-123')
        
        self.assertEqual(response.status_code, 200, f"Expected 200 OK for first login, got {response.status_code}")
        self.assertIn('tokens', response.json())
        
        # Check that the device was registered
        device = DeviceRegistry.objects.filter(user=self.user, device_fingerprint='fingerprint-123').first()
        self.assertIsNotNone(device, "Device should be registered after first login")
        self.assertTrue(device.is_trusted, "First device should be auto-trusted")

        # --- Step 2: Second login from IP 2 (New Location) ---
        response2 = self.client.post(self.login_url, {
            'email': 'testmfa@example.com',
            'password': 'testpassword123!'
        }, REMOTE_ADDR='203.0.113.1', HTTP_X_DEVICE_FINGERPRINT='fingerprint-456')
        
        self.assertEqual(response2.status_code, 403, "Expected 403 for new location login")
        data = response2.json()
        self.assertTrue(data.get('requires_verification'), "Expected requires_verification flag to be True")
        self.assertIn('mfa_token', data, "Expected an mfa_token to be returned for verification")
