"""
Tests for the Phase-4 feature additions:

* in-channel chat REST (list / send / permission scoping)
* medication plan sync (upsert by source_id, patient scoping)
* patient portal (linked-record self-service + role gating)
* FHIR Observation export (LOINC mapping + scoping)
* AI drug-interaction check (rule-based path, no API key needed)
* PHI access velocity anomaly detection
* push token registration
"""
import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.channels.models import Channel, ChannelMembership
from apps.core import anomaly
from apps.lab.models import LabTest, LabOrder, LabResult
from apps.notifications.models import PushToken
from apps.patients.models import Patient
from apps.pharmacy.models import Medication, DrugInteraction, MedicationPlan
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    PatientFactory,
    ChannelFactory,
    ChannelMembershipFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def doctor(db):
    return UserFactory(role=User.Role.DOCTOR)


@pytest.fixture
def admin(db):
    return AdminUserFactory()


@pytest.fixture
def patient(db):
    return PatientFactory()


@pytest.fixture
def channel(db, doctor, patient):
    return ChannelFactory(owner=doctor, patient=patient)


# ---------------------------------------------------------------------------
# Channel chat
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestChannelChat:
    def test_member_can_list_and_send(self, api_client, doctor, channel):
        ChannelMembershipFactory(channel=channel, user=doctor)
        api_client.force_authenticate(doctor)

        response = api_client.post(
            reverse('channel-messages', kwargs={'pk': channel.id}),
            {'body': 'مرحباً بالفريق الطبي'},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['body'] == 'مرحباً بالفريق الطبي'
        assert response.data['sender_name'] == doctor.full_name

        listing = api_client.get(
            reverse('channel-messages', kwargs={'pk': channel.id})
        )
        assert listing.status_code == status.HTTP_200_OK
        assert len(listing.data) == 1

    def test_non_member_cannot_send(self, api_client, db, channel):
        outsider = UserFactory(role=User.Role.DOCTOR)
        api_client.force_authenticate(outsider)
        response = api_client.post(
            reverse('channel-messages', kwargs={'pk': channel.id}),
            {'body': 'أنا لست عضواً هنا'},
        )
        # 403 or 404 are both correct here: the project's contract hides
        # channels a caller cannot view (404), which subsumes the 403.
        assert response.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
        )

    def test_message_is_audited(self, api_client, doctor, channel):
        ChannelMembershipFactory(channel=channel, user=doctor)
        api_client.force_authenticate(doctor)
        api_client.post(
            reverse('channel-messages', kwargs={'pk': channel.id}),
            {'body': 'رسالة تُدقَّق'},
        )
        assert AuditLog.objects.filter(
            event_type='CHANNEL_MESSAGE_SENT'
        ).exists()


# ---------------------------------------------------------------------------
# Medication plan sync
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMedicationPlanSync:
    def _payload(self, patient):
        return {
            'patient_id': str(patient.id),
            'name': 'أموكسيسيلين 500',
            'dosage': '500 ملغ',
            'times': ['08:00', '20:00'],
            'start_date': str(date.today()),
            'instructions': 'بعد الأكل',
            'source_id': str(uuid.uuid4()),
        }

    def _grant(self, doctor, patient):
        channel = ChannelFactory(owner=doctor, patient=patient)
        ChannelMembershipFactory(channel=channel, user=doctor)
        return channel

    def test_create_then_upsert_same_source_id(self, api_client, doctor, patient):
        self._grant(doctor, patient)
        api_client.force_authenticate(doctor)
        payload = self._payload(patient)

        first = api_client.post(
            reverse('medication-plan-list'), payload, format='json'
        )
        assert first.status_code == status.HTTP_201_CREATED

        payload['dosage'] = '1 غرام'
        second = api_client.post(
            reverse('medication-plan-list'), payload, format='json'
        )
        assert second.status_code == status.HTTP_200_OK
        assert second.data['id'] == first.data['id']
        assert second.data['dosage'] == '1 غرام'
        assert MedicationPlan.objects.count() == 1

    def test_plan_name_is_encrypted_at_rest(self, api_client, doctor, patient):
        self._grant(doctor, patient)
        api_client.force_authenticate(doctor)
        payload = self._payload(patient)
        api_client.post(reverse('medication-plan-list'), payload, format='json')

        row = MedicationPlan.objects.get()
        assert row.name == payload['name']            # reads through Fernet
        assert payload['name'] not in row._name       # ciphertext in the column

    def test_list_scopes_by_patient_access(self, api_client, db, doctor, patient):
        self._grant(doctor, patient)
        api_client.force_authenticate(doctor)

        payload = self._payload(patient)
        api_client.post(reverse('medication-plan-list'), payload, format='json')

        listing = api_client.get(reverse('medication-plan-list'))
        assert listing.status_code == status.HTTP_200_OK
        assert listing.data[0]['patient_id'] == str(patient.id)


# ---------------------------------------------------------------------------
# Patient portal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPatientPortal:
    def test_linked_patient_reads_own_appointments(self, api_client, db, patient):
        account = UserFactory(role=User.Role.PATIENT)
        patient.user = account
        patient.save(update_fields=['user'])

        doctor = UserFactory(role=User.Role.DOCTOR)
        from apps.appointments.models import Appointment
        Appointment.objects.create(
            patient=patient, doctor=doctor,
            scheduled_at=__import__('django.utils.timezone', fromlist=['now']).now(),
        )

        api_client.force_authenticate(account)
        response = api_client.get(
            reverse('patient-portal-detail', kwargs={'pk': 'appointments'})
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_patient_role_without_link_is_404(self, api_client, db):
        account = UserFactory(role=User.Role.PATIENT)
        api_client.force_authenticate(account)
        response = api_client.get(reverse('patient-portal-list'))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_staff_role_is_forbidden(self, api_client, db):
        api_client.force_authenticate(UserFactory(role=User.Role.DOCTOR))
        response = api_client.get(reverse('patient-portal-list'))
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# FHIR Observation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFHIRObservation:
    def _result(self, patient, doctor, tech):
        test = LabTest.objects.create(
            name='Glucose', code='1558-6', unit='mg/dL',
            normal_range_min=70, normal_range_max=110,
        )
        order = LabOrder.objects.create(
            patient=patient, doctor=doctor, test=test,
            status=LabOrder.Status.VALIDATED,
        )
        return LabResult.objects.create(
            order=order, numeric_value=250, performed_by=tech,
        )

    def test_export_maps_loinc_and_flags_critical(self, api_client, db, admin, doctor, patient):
        tech = UserFactory(role=User.Role.LAB_TECH)
        result = self._result(patient, doctor, tech)

        api_client.force_authenticate(admin)
        response = api_client.get(
            reverse('fhir-observation-detail', kwargs={'pk': result.id})
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.data
        assert body['resourceType'] == 'Observation'
        assert body['code']['coding'][0]['code'] == '1558-6'
        assert body['valueQuantity']['value'] == 250.0
        assert any(
            f['coding'][0]['code'] in ('HH', 'LL')
            for f in body['interpretation']
        )

    def test_doctor_without_channel_cannot_export(self, api_client, db, doctor, patient):
        tech = UserFactory(role=User.Role.LAB_TECH)
        result = self._result(patient, doctor, tech)

        # A doctor with no channel for this patient cannot read the result.
        outsider = UserFactory(role=User.Role.DOCTOR)
        api_client.force_authenticate(outsider)
        response = api_client.get(
            reverse('fhir-observation-detail', kwargs={'pk': result.id})
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_attending_doctor_can_export(self, api_client, db, doctor, patient):
        ChannelFactory(owner=doctor, patient=patient)
        tech = UserFactory(role=User.Role.LAB_TECH)
        result = self._result(patient, doctor, tech)

        api_client.force_authenticate(doctor)
        response = api_client.get(
            reverse('fhir-observation-detail', kwargs={'pk': result.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['resourceType'] == 'Observation'


# ---------------------------------------------------------------------------
# AI interaction check — rule-based path (no GEMINI key in tests)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAIDrugInteractionCheck:
    def test_rule_engine_finds_registered_interaction(
        self, api_client, settings, doctor, patient
    ):
        settings.GEMINI_API_KEY = ''  # force the rule-based-only path
        ChannelFactory(owner=doctor, patient=patient)

        warfarin = Medication.objects.create(name='Warfarin')
        aspirin = Medication.objects.create(name='Aspirin')
        DrugInteraction.objects.create(
            drug_a=warfarin, drug_b=aspirin, severity='SEVERE',
            description='خطر نزف مرتفع',
        )

        api_client.force_authenticate(doctor)
        response = api_client.post(
            reverse('ai-interactions-check'),
            {
                'medications': ['Warfarin', 'Aspirin'],
                'patient_id': str(patient.id),
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['has_severe'] is True
        assert response.data['ai_review'] is None
        hits = response.data['rule_based']
        assert len(hits) == 1
        assert {hits[0]['drug_a'], hits[0]['drug_b']} == {'Warfarin', 'Aspirin'}

    def test_unknown_patient_is_403(self, api_client, settings, doctor, db):
        settings.GEMINI_API_KEY = ''
        api_client.force_authenticate(doctor)
        response = api_client.post(
            reverse('ai-interactions-check'),
            {
                'medications': ['Warfarin'],
                'patient_id': str(uuid.uuid4()),
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------------
# PHI access velocity anomaly
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPhiAnomalyDetection:
    def test_threshold_crossing_raises_audited_alert(self, db, monkeypatch):
        from django.core.cache import cache
        cache.clear()

        user = UserFactory()
        # Scale thresholds to zero so the very first read crosses them.
        monkeypatch.setattr(anomaly, '_threshold_scale', lambda: 0.0)

        assert anomaly.record_phi_access(user, resource='medical_file') is True
        assert AuditLog.objects.filter(
            event_type='SUSPICIOUS_ACTIVITY', user=user
        ).exists()

    def test_under_threshold_is_silent(self, db):
        from django.core.cache import cache
        cache.clear()

        user = UserFactory()
        assert anomaly.record_phi_access(user) is False
        assert not AuditLog.objects.filter(
            event_type='SUSPICIOUS_ACTIVITY', user=user
        ).exists()


# ---------------------------------------------------------------------------
# Push token registration
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPushTokenRegistration:
    def test_register_rebinds_token_to_current_account(self, api_client, db):
        token_value = 'fcm-token-' + uuid.uuid4().hex

        first = UserFactory(role=User.Role.DOCTOR)
        api_client.force_authenticate(first)
        response = api_client.post(
            reverse('push-token-register'), {'token': token_value}
        )
        assert response.status_code == status.HTTP_200_OK
        assert PushToken.objects.get(token=token_value).user == first

        # Same physical token re-registered under a different account
        second = UserFactory(role=User.Role.DOCTOR)
        api_client.force_authenticate(second)
        api_client.post(reverse('push-token-register'), {'token': token_value})
        row = PushToken.objects.get(token=token_value)
        assert row.user == second
        assert row.is_active is True

    def test_unregister_deactivates(self, api_client, db):
        user = UserFactory(role=User.Role.DOCTOR)
        api_client.force_authenticate(user)
        api_client.post(reverse('push-token-register'), {'token': 'tok-1'}, format='json')
        api_client.delete(
            reverse('push-token-register'), {'token': 'tok-1'}, format='json'
        )
        assert PushToken.objects.get(token='tok-1').is_active is False
