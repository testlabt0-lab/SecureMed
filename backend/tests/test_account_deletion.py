"""
Tests for the Play-mandated account-deletion path (4-3 / §2 of the Play
checklist): ``DELETE auth/account/``.

The contract: password re-verification (a stolen unlocked session must not
wipe the account), deactivation instead of a physical delete (PHI rows carry
the user id, and the audit chain depends on the actor surviving), every
session force-ended, and an audit trail.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    user = UserFactory(role=User.Role.DOCTOR)
    user.set_password('Old-Pass-123')
    user.save(update_fields=['password'])
    return user


@pytest.fixture
def authed_client(api_client, user):
    api_client.force_authenticate(user)
    return api_client


@pytest.mark.django_db
class TestDeleteAccount:
    def test_requires_password(self, authed_client, user):
        response = authed_client.delete(reverse('account-delete'), {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.is_active is True

    def test_rejects_wrong_password(self, authed_client, user):
        response = authed_client.delete(
            reverse('account-delete'), {'password': 'Wrong-Pass'}, format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.is_active is True

    def test_deactivates_instead_of_deleting(self, authed_client, user):
        response = authed_client.delete(
            reverse('account-delete'), {'password': 'Old-Pass-123'}, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_active is False
        # The row survives — PHI chains and the audit log depend on it.
        assert User.objects.filter(pk=user.pk).exists()

    def test_force_ends_all_sessions(self, authed_client, user):
        from django.core.cache import cache

        cache.set(f'active_sessions:{user.id}', [
            {'session_id': 's1', 'device_fingerprint': 'F1',
             'timestamp': 0, 'ip_address': ''}
        ], timeout=86400)

        response = authed_client.delete(
            reverse('account-delete'), {'password': 'Old-Pass-123'}, format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert cache.get(f'active_sessions:{user.id}') is None
        # Revocation timestamp recorded — BoundJWTAuthentication rejects
        # every token minted before this moment.
        assert cache.get(f'token_denylist:{user.id}') is not None

    def test_audits_the_deactivation(self, authed_client, user):
        authed_client.delete(
            reverse('account-delete'), {'password': 'Old-Pass-123'}, format='json'
        )

        assert AuditLog.objects.filter(
            user=user, event_type='USER_DEACTIVATED'
        ).exists()

    def test_deactivated_user_cannot_log_back_in(self, api_client, user):
        from rest_framework.test import APIClient as Client

        authed = Client()
        authed.force_authenticate(user)
        authed.delete(
            reverse('account-delete'), {'password': 'Old-Pass-123'}, format='json'
        )

        # The login gate rejects inactive users before the password check.
        response = api_client.post(
            reverse('login'), {'email': user.email, 'password': 'Old-Pass-123'},
            format='json',
        )
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_requires_authentication(self, api_client, user):
        response = api_client.delete(
            reverse('account-delete'), {'password': 'Old-Pass-123'}, format='json'
        )

        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN
        )
        user.refresh_from_db()
        assert user.is_active is True
