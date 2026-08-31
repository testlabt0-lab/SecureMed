"""
Tests for accounts app: authentication, biometric, user management.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User, BiometricProfile
from tests.factories import UserFactory, AdminUserFactory


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

        assert response.status_code == status.HTTP_200_OK
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

    def test_login_deactivated_user_rejected(self):
        """Deactivated accounts must not be able to login (production hardening)."""
        user = UserFactory()
        user.set_password('TestPassword123!')
        user.is_active = False
        user.save()

        response = self.client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'TestPassword123!',
        }, format='json')

        assert response.status_code == 400
        assert 'معطل' in str(response.data)


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
    """Tests for biometric authentication endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory(is_biometric_enabled=True)
        self.user.set_password('TestPassword123!')
        self.user.save()
        BiometricProfile.objects.create(
            user=self.user,
            device_id='test-device-001',
            device_name='Test Device',
            platform='ANDROID',
            biometric_hash='encrypted_hash',
            salt='testsalt123456',
        )

    def test_biometric_challenge_request(self):
        response = self.client.post('/api/v1/auth/biometric/challenge/', {
            'email': self.user.email,
            'device_id': 'test-device-001',
        }, format='json')
        assert response.status_code == 200
        assert 'challenge_id' in response.data
        assert 'challenge' in response.data

    def test_biometric_challenge_nonexistent_user(self):
        response = self.client.post('/api/v1/auth/biometric/challenge/', {
            'email': 'nonexistent@securemed.test',
            'device_id': 'test-device',
        }, format='json')
        assert response.status_code == 400

    def test_biometric_challenge_unregistered_device(self):
        response = self.client.post('/api/v1/auth/biometric/challenge/', {
            'email': self.user.email,
            'device_id': 'unregistered-device',
        }, format='json')
        assert response.status_code == 400

    def test_biometric_enroll_requires_auth(self):
        """Biometric enrollment requires authentication."""
        client = APIClient()  # Not authenticated
        response = client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'new-device',
            'device_name': 'New Device',
            'platform': 'ANDROID',
            'biometric_template': 'template-data',
        }, format='json')
        assert response.status_code == 401

    def test_biometric_enroll_success(self):
        """Authenticated user can enroll biometric."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'new-device-002',
            'device_name': 'New Device',
            'platform': 'ANDROID',
            'biometric_template': 'template-data-123',
        }, format='json')
        assert response.status_code == 201
