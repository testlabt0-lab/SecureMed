"""
Tests for medication plans, today's schedule, dose logging, adherence,
and the biometric public-key signature login flow.
"""
import base64
from datetime import date, timedelta

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import BiometricProfile, User
from apps.channels.models import ChannelMembership
from apps.notifications.models import Notification
from apps.patients.models import Medication, MedicationLog
def _results(resp):
    """Unwrap paginated DRF responses ({count,...,results}) to a list."""
    data = resp.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data


from tests.factories import (
    ChannelFactory,
    ChannelMembershipFactory,
    PatientFactory,
    UserFactory,
    AdminUserFactory,
)


@pytest.mark.django_db
class TestMedicationAPI:
    """CRUD + schedule + adherence for Medication plans."""

    def _setup(self, dose_times='08:00,20:00'):
        doctor = UserFactory(role=User.Role.DOCTOR)
        nurse = UserFactory(role=User.Role.NURSE)
        outsider = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory(full_name='مريض الأدوية')
        channel = ChannelFactory(owner=doctor, patient=patient)
        ChannelMembershipFactory(channel=channel, user=doctor, role=ChannelMembership.Role.OWNER)
        ChannelMembershipFactory(channel=channel, user=nurse, role=ChannelMembership.Role.EDITOR)

        client = APIClient()
        client.force_authenticate(user=doctor)
        payload = {
            'patient': str(patient.id),
            'channel': str(channel.id),
            'name': 'ميتفورمين',
            'dosage': '500 ملغ',
            'dose_times': dose_times,
            'start_date': str(date.today()),
            'instructions': 'بعد الأكل مباشرة',
        }
        return client, payload, doctor, nurse, outsider, patient, channel

    def test_create_medication(self):
        client, payload, doctor, *_ = self._setup()
        response = client.post('/api/v1/patients/medications/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        med = Medication.objects.get(id=response.data['id'])
        assert med.name == 'ميتفورمين'
        assert med.prescribed_by == doctor
        assert med.times == ['08:00', '20:00']

    def test_create_medication_notifies_channel_members(self):
        client, payload, doctor, nurse, *_ = self._setup()
        client.post('/api/v1/patients/medications/', payload, format='json')
        notification = Notification.objects.filter(recipient=nurse).first()
        assert notification is not None
        assert notification.notification_type == Notification.Type.MEDICATION_REMINDER
        assert 'ميتفورمين' in notification.message
        # The prescribing doctor is the actor: no self-notification
        assert not Notification.objects.filter(recipient=doctor).exists()

    def test_invalid_dose_times_rejected(self):
        client, payload, *_ = self._setup()
        payload['dose_times'] = '8 صباحاً'
        response = client.post('/api/v1/patients/medications/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_end_date_before_start_rejected(self):
        client, payload, *_ = self._setup()
        payload['end_date'] = str(date.today() - timedelta(days=1))
        response = client.post('/api/v1/patients/medications/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_today_schedule_pending_status(self):
        client, payload, *_ = self._setup()
        response = client.post('/api/v1/patients/medications/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        today = client.get('/api/v1/patients/medications/today/')
        assert today.status_code == status.HTTP_200_OK
        doses = today.data['doses']
        assert len(doses) == 2
        times = [d['time'] for d in doses]
        assert times == ['08:00', '20:00']
        assert all(d['status'] in ('PENDING', 'MISSED') for d in doses)
        assert doses[0]['medication_name'] == 'ميتفورمين'

    def test_log_dose_taken_updates_today(self):
        client, payload, *_ = self._setup()
        created = client.post('/api/v1/patients/medications/', payload, format='json')
        med_id = created.data['id']

        today = client.get('/api/v1/patients/medications/today/').data
        dose = today['doses'][0]

        logged = client.post('/api/v1/patients/medications/log_dose/', {
            'medication_id': med_id,
            'scheduled_for': dose['scheduled_for'],
            'status': 'TAKEN',
        }, format='json')
        assert logged.status_code == status.HTTP_201_CREATED
        assert logged.data['status'] == 'TAKEN'
        assert logged.data['taken_at'] is not None

        today_after = client.get('/api/v1/patients/medications/today/').data
        statuses = {d['time']: d['status'] for d in today_after['doses']}
        assert statuses[dose['time']] == 'TAKEN'

    def test_log_dose_invalid_status(self):
        client, payload, *_ = self._setup()
        created = client.post('/api/v1/patients/medications/', payload, format='json')
        med_id = created.data['id']
        response = client.post('/api/v1/patients/medications/log_dose/', {
            'medication_id': med_id,
            'scheduled_for': '2026-08-31T08:00:00Z',
            'status': 'MAYBE',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_log_dose_for_foreign_medication_forbidden(self):
        client, payload, doctor, nurse, outsider, *_ = self._setup()
        created = client.post('/api/v1/patients/medications/', payload, format='json')
        med_id = created.data['id']

        other_client = APIClient()
        other_client.force_authenticate(user=outsider)
        response = other_client.post('/api/v1/patients/medications/log_dose/', {
            'medication_id': med_id,
            'scheduled_for': '2026-08-31T08:00:00Z',
            'status': 'TAKEN',
        }, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_channel_member_sees_medication_outsider_does_not(self):
        client, payload, doctor, nurse, outsider, patient, *_ = self._setup()
        client.post('/api/v1/patients/medications/', payload, format='json')

        nurse_client = APIClient()
        nurse_client.force_authenticate(user=nurse)
        nurse_list = nurse_client.get('/api/v1/patients/medications/')
        assert nurse_list.status_code == status.HTTP_200_OK
        names = [m['name'] for m in _results(nurse_list)]
        assert 'ميتفورمين' in names

        outsider_client = APIClient()
        outsider_client.force_authenticate(user=outsider)
        empty = outsider_client.get('/api/v1/patients/medications/')
        names_out = [m['name'] for m in _results(empty)]
        assert 'ميتفورمين' not in names_out

    def test_adherence_percentages(self):
        client, payload, *_ = self._setup(dose_times='08:00')
        created = client.post('/api/v1/patients/medications/', payload, format='json')
        med_id = created.data['id']

        today = client.get('/api/v1/patients/medications/today/').data
        dose = today['doses'][0]
        client.post('/api/v1/patients/medications/log_dose/', {
            'medication_id': med_id,
            'scheduled_for': dose['scheduled_for'],
            'status': 'TAKEN',
        }, format='json')

        adherence = client.get('/api/v1/patients/medications/adherence/')
        assert adherence.status_code == status.HTTP_200_OK
        assert adherence.data['taken_doses'] >= 1
        assert 0 <= adherence.data['adherence_percent'] <= 100

    def test_admin_sees_all_medications(self):
        client, payload, doctor, *_ = self._setup()
        client.post('/api/v1/patients/medications/', payload, format='json')
        admin = AdminUserFactory()
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)
        response = admin_client.get('/api/v1/patients/medications/')
        names = [m['name'] for m in _results(response)]
        assert 'ميتفورمين' in names


@pytest.mark.django_db
class TestBiometricSignatureLogin:
    """End-to-end biometric enrollment + challenge + signature login."""

    @staticmethod
    def _generate_key():
        private_key = ec.generate_private_key(ec.SECP256R1())
        der_b64 = base64.b64encode(
            private_key.public_key().public_bytes(
                serialization.Encoding.DER,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        ).decode('utf-8')
        return private_key, der_b64

    def _enroll(self, client, private_key, public_pem, device_id='test-device'):
        response = client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': device_id,
            'device_name': 'Pixel Test',
            'platform': 'ANDROID',
            'public_key': public_pem,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        return response

    def _challenge(self, client, email, device_id='test-device'):
        response = client.post('/api/v1/auth/biometric/challenge/', {
            'email': email,
            'device_id': device_id,
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        return response.data['challenge_id'], response.data['challenge']

    def test_enroll_with_public_key(self):
        user = UserFactory(role=User.Role.DOCTOR)
        client = APIClient()
        client.force_authenticate(user=user)
        _, pem = self._generate_key()
        self._enroll(client, None, pem)

        profile = BiometricProfile.objects.get(user=user, device_id='test-device')
        assert profile.public_key  # stored (encrypted)
        assert pem not in profile.public_key  # encrypted at rest
        user.refresh_from_db()
        assert user.is_biometric_enabled is True

    def test_enroll_requires_key_or_template(self):
        user = UserFactory(role=User.Role.DOCTOR)
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post('/api/v1/auth/biometric/enroll/', {
            'device_id': 'd1', 'platform': 'ANDROID',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_full_signature_login_success(self):
        user = UserFactory(role=User.Role.DOCTOR, is_biometric_enabled=True)
        client = APIClient()
        client.force_authenticate(user=user)
        private_key, pem = self._generate_key()
        self._enroll(client, private_key, pem)

        anon = APIClient()
        challenge_id, challenge = self._challenge(anon, user.email)

        signature = private_key.sign(
            challenge.encode('utf-8'), ec.ECDSA(hashes.SHA256())
        )
        response = anon.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge_id,
            'signature': base64.b64encode(signature).decode('utf-8'),
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'tokens' in response.data
        assert response.data['user']['email'] == user.email

    def test_signature_login_wrong_key_rejected(self):
        user = UserFactory(role=User.Role.DOCTOR, is_biometric_enabled=True)
        client = APIClient()
        client.force_authenticate(user=user)
        _, pem = self._generate_key()
        self._enroll(client, None, pem)

        attacker_key, _ = self._generate_key()

        anon = APIClient()
        challenge_id, challenge = self._challenge(anon, user.email)
        signature = attacker_key.sign(
            challenge.encode('utf-8'), ec.ECDSA(hashes.SHA256())
        )
        response = anon.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge_id,
            'signature': base64.b64encode(signature).decode('utf-8'),
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_challenge_requires_enrolled_device(self):
        user = UserFactory(role=User.Role.DOCTOR, is_biometric_enabled=True)
        client = APIClient()
        client.force_authenticate(user=user)
        _, pem = self._generate_key()
        self._enroll(client, None, pem, device_id='device-a')

        anon = APIClient()
        response = anon.post('/api/v1/auth/biometric/challenge/', {
            'email': user.email,
            'device_id': 'device-b',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_challenge_single_use(self):
        user = UserFactory(role=User.Role.DOCTOR, is_biometric_enabled=True)
        client = APIClient()
        client.force_authenticate(user=user)
        private_key, pem = self._generate_key()
        self._enroll(client, private_key, pem)

        anon = APIClient()
        challenge_id, challenge = self._challenge(anon, user.email)
        signature = base64.b64encode(
            private_key.sign(challenge.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
        ).decode('utf-8')

        first = anon.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge_id, 'signature': signature,
        }, format='json')
        assert first.status_code == status.HTTP_200_OK

        second = anon.post('/api/v1/auth/biometric/login/', {
            'challenge_id': challenge_id, 'signature': signature,
        }, format='json')
        assert second.status_code == status.HTTP_400_BAD_REQUEST

    def test_multiple_devices_both_can_login(self):
        user = UserFactory(role=User.Role.DOCTOR, is_biometric_enabled=True)
        client = APIClient()
        client.force_authenticate(user=user)

        key_a, pem_a = self._generate_key()
        key_b, pem_b = self._generate_key()
        self._enroll(client, key_a, pem_a, device_id='device-a')
        self._enroll(client, key_b, pem_b, device_id='device-b')

        anon = APIClient()
        for device, key in (('device-a', key_a), ('device-b', key_b)):
            challenge_id, challenge = self._challenge(anon, user.email, device_id=device)
            signature = base64.b64encode(
                key.sign(challenge.encode('utf-8'), ec.ECDSA(hashes.SHA256()))
            ).decode('utf-8')
            response = anon.post('/api/v1/auth/biometric/login/', {
                'challenge_id': challenge_id, 'signature': signature,
            }, format='json')
            assert response.status_code == status.HTTP_200_OK, f'device {device} failed'
