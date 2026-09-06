"""
Tests for accounts app: authentication, biometric, user management.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from apps.accounts.models import User, BiometricProfile, BiometricChallenge
from apps.security.crypto import b64url_encode, b64url_decode, public_key_to_pem
from tests.factories import UserFactory, AdminUserFactory


def _new_credential():
    """An ES256 key pair standing in for one held in device secure hardware."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, public_key_to_pem(private_key.public_key())


def _spki_b64(private_key):
    return b64url_encode(private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))


@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model."""

    def test_create_user(self):
        user = User.objects.create_user(
            email='test@securemed.test',
            password='TestPassword123!',
            full_name='Test User',
            role=User.Role.DOCTOR,
        )
        assert user.pk is not None
        assert user.email == 'test@securemed.test'
        assert user.check_password('TestPassword123!')
        assert user.is_active is True
        assert user.is_medical_staff is True

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='super@securemed.test',
            password='SuperPassword123!',
            full_name='Super User',
        )
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.role == User.Role.SUPER_ADMIN

    def test_user_str_representation(self):
        user = UserFactory()
        assert str(user) == f'{user.full_name} ({user.get_role_display()})'

    def test_is_medical_staff_property(self):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient = UserFactory(role=User.Role.PATIENT)
        assert doctor.is_medical_staff is True
        assert patient.is_medical_staff is False

    def test_account_lock_after_failed_attempts(self):
        from django.utils import timezone
        user = UserFactory()
        user.failed_login_attempts = 5
        user.lock_account(minutes=30)
        assert user.is_locked is True

    def test_reset_failed_attempts(self):
        user = UserFactory(failed_login_attempts=3)
        user.reset_failed_attempts()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


@pytest.mark.django_db
class TestLoginAPI:
    """Tests for login endpoints."""

    def setup_method(self):
        self.client = APIClient()

    def test_login_success(self):
        user = UserFactory()
        user.set_password('TestPassword123!')
        user.save()

        response = self.client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'TestPassword123!',
        }, format='json')

        assert response.status_code == status.HTTP_200_OK, response.data
        assert 'tokens' in response.data
        assert 'access' in response.data['tokens']
        assert 'refresh' in response.data['tokens']
        assert response.data['user']['email'] == user.email

    def test_login_wrong_password(self):
        user = UserFactory()
        user.set_password('TestPassword123!')
        user.save()

        response = self.client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'WrongPassword!',
        }, format='json')

        assert response.status_code == 400

    def test_login_nonexistent_user(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'nonexistent@securemed.test',
            'password': 'AnyPassword123!',
        }, format='json')

        assert response.status_code == 400

    def test_login_missing_fields(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'test@securemed.test',
        }, format='json')

        assert response.status_code == 400


@pytest.mark.django_db
class TestUserManagementAPI:
    """Tests for user management endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.admin.set_password('AdminPass123!')
        self.admin.save()
        self.client.force_authenticate(user=self.admin)

    def test_list_users(self):
        UserFactory.create_batch(3)
        response = self.client.get('/api/v1/auth/users/')
        assert response.status_code == 200
        # Should include admin + 3 created
        assert len(response.data) >= 4

    def test_get_current_user(self):
        response = self.client.get('/api/v1/auth/users/me/')
        assert response.status_code == 200
        assert response.data['email'] == self.admin.email

    def test_create_user(self):
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'newuser@securemed.test',
            'full_name': 'New User',
            'role': 'NURSE',
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!',
        }, format='json')
        assert response.status_code == 201
        assert User.objects.filter(email='newuser@securemed.test').exists()

    def test_password_mismatch(self):
        response = self.client.post('/api/v1/auth/users/', {
            'email': 'newuser2@securemed.test',
            'full_name': 'New User 2',
            'role': 'NURSE',
            'password': 'Password123!',
            'password_confirm': 'Different123!',
        }, format='json')
        assert response.status_code == 400

    def test_deactivate_user(self):
        user = UserFactory()
        response = self.client.post(f'/api/v1/auth/users/{user.id}/deactivate/')
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False


@pytest.mark.django_db
class TestBiometricAPI:
    """Tests for biometric authentication endpoints.

    The device signs a server-issued challenge. Enrollment stores a public key, so
    nothing that can be replayed as a credential is ever sent twice.
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_biometric_enabled=True)
        self.user.set_password('TestPassword123!')
        self.user.save()
        self.private_key, public_pem = _new_credential()
        self.profile = BiometricProfile.objects.create(
            user=self.user,
            device_id='test-device-001',
            device_name='Test Device',
            platform='ANDROID',
            public_key=public_pem,
        )

    def _request_challenge(self, email=None, device_id='test-device-001'):
        return self.client.post('/api/v1/auth/biometric/challenge/', {
            'email': email or self.user.email,
            'device_id': device_id,
        }, format='json')

    def _sign(self, challenge_b64):
        return b64url_encode(self.private_key.sign(
            b64url_decode(challenge_b64), ec.ECDSA(hashes.SHA256())))

    def test_biometric_challenge_request(self):
        response = self._request_challenge()
        assert response.status_code == 200
        assert 'challenge_id' in response.data
        assert 'challenge' in response.data
        assert BiometricChallenge.objects.filter(
            id=response.data['challenge_id'], profile=self.profile).exists()

    def test_challenge_is_bound_to_the_device(self):
        """A challenge belongs to one enrolled credential, not just to the user."""
        response = self._request_challenge()
        challenge = BiometricChallenge.objects.get(id=response.data['challenge_id'])
        assert challenge.profile_id == self.profile.id

    def test_challenge_does_not_reveal_whether_the_account_exists(self):
        """Unknown account, unknown device and locked account answer identically.

        The old endpoint returned three distinct 400s, which let anyone confirm
        that a named person had an account here — in a hospital, that a named
        person is a patient.
        """
        real = self._request_challenge()
        unknown_user = self._request_challenge(email='nobody@securemed.test')
        unknown_device = self._request_challenge(device_id='unregistered-device')

        for response in (unknown_user, unknown_device):
            assert response.status_code == real.status_code == 200
            assert set(response.data) == set(real.data)
            assert response.data['challenge'] != real.data['challenge']

        # The decoys are not backed by a row, so they can never be answered.
        for response in (unknown_user, unknown_device):
            assert not BiometricChallenge.objects.filter(
                id=response.data['challenge_id']).exists()

    def test_decoy_challenge_cannot_be_answered(self):
        response = self._request_challenge(email='nobody@securemed.test')
        login = self.client.post('/api/v1/auth/biometric/login/', {
            'challenge_id': response.data['challenge_id'],
            'signature': self._sign(response.data['challenge']),
        }, format='json')
        assert login.status_code == 400

    def test_biometric_login_success(self):
        challenge = self._request_challenge()
        response = self.client.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge.data['challenge_id'],
            'signature': self._sign(challenge.data['challenge']),
        }, format='json')
        assert response.status_code == 200
        assert 'tokens' in response.data
        assert response.data['user']['email'] == self.user.email

    def test_echoing_the_challenge_is_rejected(self):
        """The old scheme accepted exactly this: the challenge sent back verbatim."""
        challenge = self._request_challenge()
        response = self.client.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge.data['challenge_id'],
            'signature': challenge.data['challenge'],
        }, format='json')
        assert response.status_code == 400

    def test_signature_from_another_device_is_rejected(self):
        other_key, _pem = _new_credential()
        challenge = self._request_challenge()
        forged = b64url_encode(other_key.sign(
            b64url_decode(challenge.data['challenge']), ec.ECDSA(hashes.SHA256())))
        response = self.client.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge.data['challenge_id'],
            'signature': forged,
        }, format='json')
        assert response.status_code == 400

    def test_challenge_cannot_be_replayed(self):
        """One challenge, one login. The second attempt finds it already burned."""
        challenge = self._request_challenge()
        payload = {
            'challenge_id': challenge.data['challenge_id'],
            'signature': self._sign(challenge.data['challenge']),
        }
        assert self.client.post(
            '/api/v1/auth/biometric/login/', payload, format='json'
        ).status_code == 200
        assert self.client.post(
            '/api/v1/auth/biometric/login/', payload, format='json'
        ).status_code == 400

    def test_failed_attempt_burns_the_challenge(self):
        """A wrong signature cannot be retried against the same nonce."""
        challenge = self._request_challenge()
        self.client.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge.data['challenge_id'],
            'signature': b64url_encode(b'\x00' * 70),
        }, format='json')
        assert BiometricChallenge.objects.get(
            id=challenge.data['challenge_id']).used is True

    def test_biometric_enroll_requires_auth(self):
        """Biometric enrollment requires authentication."""
        client = APIClient()  # Not authenticated
        key, _pem = _new_credential()
        response = client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'new-device',
            'device_name': 'New Device',
            'platform': 'ANDROID',
            'public_key': _spki_b64(key),
        }, format='json')
        assert response.status_code == 401

    def test_biometric_enroll_success(self):
        """Authenticated user can enroll a device's public key."""
        self.client.force_authenticate(user=self.user)
        key, _pem = _new_credential()
        response = self.client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'new-device-002',
            'device_name': 'New Device',
            'platform': 'ANDROID',
            'public_key': _spki_b64(key),
        }, format='json')
        assert response.status_code == 201

        profile = BiometricProfile.objects.get(
            user=self.user, device_id='new-device-002')
        assert 'BEGIN PUBLIC KEY' in profile.public_key
        # Nothing that could authenticate on its own is stored.
        assert profile.private_key_encrypted == ''
        assert profile.biometric_hash == ''

    def test_enroll_rejects_material_that_is_not_a_key(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'bogus-device',
            'platform': 'ANDROID',
            'public_key': b64url_encode(b'this is not a public key'),
        }, format='json')
        assert response.status_code == 400

    def test_registration_options_include_a_server_challenge(self):
        """The browser no longer invents its own challenge."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/auth/biometric/enroll/')
        assert response.status_code == 200
        assert len(b64url_decode(response.data['challenge'])) == 32
        assert response.data['rp']['id']
        assert response.data['authenticatorSelection']['userVerification'] == 'required'
        assert {p['alg'] for p in response.data['pubKeyCredParams']} == {-7, -257}
