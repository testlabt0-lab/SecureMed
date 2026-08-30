"""
Tests for the password reset (forgot password) flow:
- POST /api/v1/auth/password/reset/          → emails a one-time signed link
- POST /api/v1/auth/password/reset/confirm/  → sets the new password

Security properties covered:
- No user enumeration (identical response for existing/unknown emails)
- Valid link changes the password + audits the event
- Invalid / reused links are rejected
- Weak or mismatched passwords are rejected by validators
"""
import re

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from tests.factories import UserFactory

RESET_URL = '/api/v1/auth/password/reset/'
CONFIRM_URL = '/api/v1/auth/password/reset/confirm/'
LOGIN_URL = '/api/v1/auth/login/'

STRONG_PASSWORD = 'Xk9#mR2$vLp7&Qw3'


def _extract_uid_token(email_body: str):
    """Pull uid & token out of the reset link embedded in the email."""
    match = re.search(r'uid=([\w-]+)&token=([\w-]+)', email_body)
    assert match, 'reset link with uid & token not found in email body'
    return match.group(1), match.group(2)


# NOTE: Django's test environment automatically swaps EMAIL_BACKEND for the
# locmem backend, so sent emails are inspectable via `mail.outbox`.
@pytest.mark.django_db
class TestPasswordResetRequest:
    def test_existing_email_returns_generic_response_and_sends_email(self):
        user = UserFactory(email='doctor@securemed.test')
        user.set_password('OldPassword#2026a')
        user.save()

        client = APIClient()
        res = client.post(RESET_URL, {'email': 'doctor@securemed.test'}, format='json')

        assert res.status_code == 200
        assert 'reset' in res.data['detail'] or 'رابط' in res.data['detail']
        # Exactly one email was dispatched, addressed to the user
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['doctor@securemed.test']
        # The email contains a reset link with uid & token
        body = mail.outbox[0].alternatives[0][0]
        uid, token = _extract_uid_token(body)
        assert uid and token
        # Request is audited
        assert AuditLog.objects.filter(
            user=user, event_type='PASSWORD_RESET_REQUESTED'
        ).exists()

    def test_unknown_email_gets_the_same_generic_response(self):
        client = APIClient()
        res = client.post(RESET_URL, {'email': 'ghost@securemed.test'}, format='json')

        assert res.status_code == 200
        assert 'رابط' in res.data['detail']
        # No email, no audit entry for a non-existent account
        assert len(mail.outbox) == 0
        assert not AuditLog.objects.filter(
            event_type='PASSWORD_RESET_REQUESTED'
        ).exists()

    def test_inactive_user_is_ignored(self):
        user = UserFactory(email='inactive@securemed.test', is_active=False)
        client = APIClient()
        res = client.post(RESET_URL, {'email': user.email}, format='json')

        assert res.status_code == 200
        assert len(mail.outbox) == 0

    def test_missing_email_is_rejected(self):
        client = APIClient()
        res = client.post(RESET_URL, {}, format='json')
        assert res.status_code == 400


@pytest.mark.django_db
class TestPasswordResetConfirm:
    def _request_reset(self, email: str):
        UserFactory(email=email)
        client = APIClient()
        client.post(RESET_URL, {'email': email}, format='json')
        body = mail.outbox[0].alternatives[0][0]
        return _extract_uid_token(body)

    def test_full_flow_changes_password(self):
        email = 'flow@securemed.test'
        uid, token = self._request_reset(email)

        client = APIClient()
        res = client.post(CONFIRM_URL, {
            'uid': uid,
            'token': token,
            'new_password': STRONG_PASSWORD,
            'confirm_password': STRONG_PASSWORD,
        }, format='json')

        assert res.status_code == 200
        user = User.objects.get(email=email)
        assert user.check_password(STRONG_PASSWORD)
        # Completion is audited
        assert AuditLog.objects.filter(
            user=user, event_type='PASSWORD_RESET_COMPLETED'
        ).exists()

    def test_login_works_with_new_password_only(self):
        email = 'login@securemed.test'
        uid, token = self._request_reset(email)

        client = APIClient()
        client.post(CONFIRM_URL, {
            'uid': uid, 'token': token,
            'new_password': STRONG_PASSWORD,
            'confirm_password': STRONG_PASSWORD,
        }, format='json')

        # Old password no longer works
        old = APIClient().post(LOGIN_URL, {
            'email': email, 'password': 'OldPassword#2026a',
        }, format='json')
        assert old.status_code in (400, 401)

        # New password works
        new = APIClient().post(LOGIN_URL, {
            'email': email, 'password': STRONG_PASSWORD,
        }, format='json')
        assert new.status_code == 200
        assert 'tokens' in new.data

    def test_token_is_single_use(self):
        email = 'single@securemed.test'
        uid, token = self._request_reset(email)
        payload = {
            'uid': uid, 'token': token,
            'new_password': STRONG_PASSWORD,
            'confirm_password': STRONG_PASSWORD,
        }

        client = APIClient()
        first = client.post(CONFIRM_URL, payload, format='json')
        second = client.post(CONFIRM_URL, payload, format='json')

        assert first.status_code == 200
        assert second.status_code == 400

    def test_invalid_token_rejected(self):
        email = 'invalid@securemed.test'
        uid, _token = self._request_reset(email)

        client = APIClient()
        res = client.post(CONFIRM_URL, {
            'uid': uid, 'token': 'bogus-token-123',
            'new_password': STRONG_PASSWORD,
            'confirm_password': STRONG_PASSWORD,
        }, format='json')

        assert res.status_code == 400

    def test_weak_password_rejected(self):
        email = 'weak@securemed.test'
        uid, token = self._request_reset(email)

        client = APIClient()
        res = client.post(CONFIRM_URL, {
            'uid': uid, 'token': token,
            'new_password': 'short123',
            'confirm_password': 'short123',
        }, format='json')

        assert res.status_code == 400
        assert 'new_password' in res.data

    def test_mismatched_passwords_rejected(self):
        email = 'mismatch@securemed.test'
        uid, token = self._request_reset(email)

        client = APIClient()
        res = client.post(CONFIRM_URL, {
            'uid': uid, 'token': token,
            'new_password': STRONG_PASSWORD,
            'confirm_password': 'Different#Pass2026x',
        }, format='json')

        assert res.status_code == 400
        assert 'confirm_password' in res.data

    def test_malformed_uid_rejected(self):
        client = APIClient()
        res = client.post(CONFIRM_URL, {
            'uid': '!!!not-base64!!!', 'token': 'whatever-token',
            'new_password': STRONG_PASSWORD,
            'confirm_password': STRONG_PASSWORD,
        }, format='json')
        assert res.status_code == 400
