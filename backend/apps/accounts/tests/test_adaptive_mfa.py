"""Adaptive MFA: what the login endpoint actually promises.

This file used to assert a contract that never shipped — HTTP 403 with a
``requires_verification`` flag, and a first device that is trusted on sight.
The shipped contract is HTTP 200 with ``requires_2fa``/``mfa_token``/``method``:
that is what ``apps.accounts.views.LoginView`` returns, what the SPA reads
(``frontend/src/pages/Login.tsx``), what the Android client deserialises
(``data/model/Models.kt``), what ``docs/DEVELOPMENT_LOG.md`` documents, and what
``tests/test_phase4_features.py`` asserts for the TOTP path. ``requires_verification``
appeared nowhere but in this file.

The other half was a policy inversion: ``DeviceRegistry.is_trusted`` defaults to
False and a device becomes trusted only by passing a challenge with
``trust_device``. Auto-trusting whatever device logged in first would have
removed the control instead of testing it.
"""
import re

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from apps.audit.models import AuditLog
from apps.security.models import DeviceRegistry

User = get_user_model()

PASSWORD = 'testpassword123!'
KNOWN_DEVICE = 'fingerprint-123'
OTHER_DEVICE = 'fingerprint-456'


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    ADAPTIVE_MFA_ENABLED=True,
    # These tests exercise the *adaptive* login behaviour: an untrusted device
    # is challenged with an emailed OTP instead of being refused. That path is
    # exactly the ENFORCE_DEVICE_AUTHORIZATION=False mode settings.py documents
    # (settings.py: "When False, the historical adaptive-MFA behaviour
    # applies"). With the default True the login view answers 403 before any
    # challenge exists, and every assertion below would KeyError on mfa_token.
    ENFORCE_DEVICE_AUTHORIZATION=False,
)
class AdaptiveMFATest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='testmfa@example.com',
            password=PASSWORD,
            full_name='Test MFA User',
            role='PATIENT',
        )
        self.login_url = reverse('login')
        self.mfa_login_url = reverse('mfa-login')
        cache.clear()
        mail.outbox = []

    def _login(self, fingerprint=KNOWN_DEVICE, ip='192.168.1.1'):
        return self.client.post(
            self.login_url,
            {'email': self.user.email, 'password': PASSWORD},
            REMOTE_ADDR=ip,
            HTTP_X_DEVICE_FINGERPRINT=fingerprint,
        )

    @staticmethod
    def _otp_from_email():
        assert mail.outbox, 'the challenge must actually reach the user'
        html = mail.outbox[-1].alternatives[0][0]
        match = re.search(r'<b>(\d{6})</b>', html)
        assert match, f'no 6-digit code in the challenge email: {html[:200]}'
        return match.group(1)

    def test_unrecognised_device_is_challenged_instead_of_logged_in(self):
        response = self._login()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get('requires_2fa'))
        self.assertEqual(body.get('method'), 'email')
        self.assertIn('mfa_token', body)
        # The point of a challenge is that no credentials are issued yet.
        self.assertNotIn('tokens', body)
        self.assertNotIn('access', body)

    def test_the_challenge_is_delivered_and_audited(self):
        self._login()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertRegex(mail.outbox[0].alternatives[0][0], r'<b>\d{6}</b>')
        self.assertTrue(
            AuditLog.objects.filter(user=self.user, event_type='LOGIN_CHALLENGE').exists()
        )

    def test_the_device_is_registered_but_not_trusted(self):
        self._login()
        device = DeviceRegistry.objects.filter(
            user=self.user, device_fingerprint=KNOWN_DEVICE
        ).first()
        self.assertIsNotNone(device, 'the device must be on file to be recognised later')
        self.assertFalse(
            device.is_trusted,
            'a device becomes trusted by passing a challenge, not by being first',
        )

    def test_completing_the_challenge_issues_tokens_and_can_trust_the_device(self):
        mfa_token = self._login().json()['mfa_token']

        response = self.client.post(
            self.mfa_login_url,
            {'mfa_token': mfa_token, 'code': self._otp_from_email(), 'trust_device': True},
            HTTP_X_DEVICE_FINGERPRINT=KNOWN_DEVICE,
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('tokens', response.json())
        device = DeviceRegistry.objects.get(
            user=self.user, device_fingerprint=KNOWN_DEVICE
        )
        self.assertTrue(device.is_trusted)

    def test_a_trusted_device_logs_straight_in(self):
        mfa_token = self._login().json()['mfa_token']
        self.client.post(
            self.mfa_login_url,
            {'mfa_token': mfa_token, 'code': self._otp_from_email(), 'trust_device': True},
            HTTP_X_DEVICE_FINGERPRINT=KNOWN_DEVICE,
        )

        response = self._login()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn('tokens', body)
        self.assertNotIn('requires_2fa', body)

    def test_a_different_device_is_challenged_again(self):
        mfa_token = self._login().json()['mfa_token']
        self.client.post(
            self.mfa_login_url,
            {'mfa_token': mfa_token, 'code': self._otp_from_email(), 'trust_device': True},
            HTTP_X_DEVICE_FINGERPRINT=KNOWN_DEVICE,
        )

        response = self._login(fingerprint=OTHER_DEVICE, ip='203.0.113.1')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('requires_2fa'))

    def test_a_wrong_code_does_not_issue_tokens(self):
        mfa_token = self._login().json()['mfa_token']
        response = self.client.post(
            self.mfa_login_url, {'mfa_token': mfa_token, 'code': '000000'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('tokens', response.json())

    @override_settings(ADAPTIVE_MFA_ENABLED=False)
    def test_the_gate_honours_its_setting(self):
        response = self._login(fingerprint='fingerprint-disabled')
        self.assertEqual(response.status_code, 200)
        self.assertIn('tokens', response.json())

    @patch('requests.get')
    def test_login_does_not_send_the_client_ip_to_a_third_party(self, mocked_get):
        """Device tracking used to reverse-geocode every login through ip-api.

        Over plaintext HTTP, on the critical path, with no opt-in — for a label
        on a device row. It is now behind GEOIP_LOOKUP_ENABLED, off by default.
        """
        self._login(ip='8.8.8.8')
        mocked_get.assert_not_called()
