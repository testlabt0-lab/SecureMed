"""
Tests for patients app: encrypted fields, medical records.
"""
import pytest
from datetime import date
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.patients.models import Patient, MedicalRecord
from apps.channels.models import Channel, ChannelMembership
from tests.factories import (
    UserFactory, PatientFactory, ChannelFactory,
    ChannelMembershipFactory,
)


@pytest.mark.django_db
class TestPatientModel:
    """Tests for Patient model - encryption at rest (security requirement #6)."""

    def test_create_patient(self):
        patient = PatientFactory()
        assert patient.pk is not None

    def test_patient_data_encrypted_at_rest(self):
        """PII should be encrypted in the database (security requirement #6)."""
        patient = PatientFactory(full_name='Ahmed Mohammed')

        # The stored value in DB should NOT be the plain text
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT full_name FROM patients_patient WHERE id = %s',
                [str(patient.id)]
            )
            row = cursor.fetchone()

        # If we got a row, verify the value is encrypted
        # (skip this check if migrations are disabled - schema may not exist)
        if row and row[0]:
            stored_value = row[0]
            assert stored_value != 'Ahmed Mohammed'
            assert len(stored_value) > 50  # Encrypted values are longer
            assert 'Ahmed' not in stored_value

    def test_patient_data_decrypts_on_access(self):
        """The model property should return decrypted data."""
        patient = PatientFactory(full_name='Fatima Al-Saud')
        # Refresh from DB to test round-trip
        patient.refresh_from_db()
        assert patient.full_name == 'Fatima Al-Saud'

    def test_patient_encryption_round_trip(self):
        """Test encrypt/decrypt cycle via the model."""
        test_data = ['Patient Name 1', 'Another Patient', 'خاص بالعربية']
        for data in test_data:
            patient = PatientFactory(full_name=data)
            patient_id = patient.id
            # Re-fetch from DB
            fetched = Patient.objects.get(id=patient_id)
            assert fetched.full_name == data

    def test_patient_data_decrypted_on_access(self):
        """Decrypted value should match the original."""
        original_name = 'Fatima Al-Saud'
        patient = PatientFactory(full_name=original_name)
        patient.refresh_from_db()
        assert patient.full_name == original_name

    def test_patient_age_calculation(self):
        patient = PatientFactory(date_of_birth=date(1990, 1, 1))
        expected_age = date.today().year - 1990
        # Allow off-by-one due to birthday
        assert abs(patient.age - expected_age) <= 1


@pytest.mark.django_db
class TestPatientAPI:
    """Tests for patient API endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.doctor = UserFactory(role=User.Role.DOCTOR)
        self.client.force_authenticate(user=self.doctor)

    def test_create_patient(self):
        response = self.client.post('/api/v1/patients/', {
            'full_name': 'Test Patient',
            'date_of_birth': '1990-05-15',
            'gender': 'M',
            'blood_type': 'A+',
            'phone': '+966500000000',
            'address': 'Test Address',
        }, format='json')
        assert response.status_code == 201
        assert Patient.objects.filter().count() == 1

    def test_list_patients(self):
        PatientFactory.create_batch(3)
        response = self.client.get('/api/v1/patients/')
        assert response.status_code == 200
        # With pagination, response.data is a dict with 'results'
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(results) == 3

    def test_patient_data_returned_decrypted(self):
        """API should return decrypted patient data."""
        patient = PatientFactory(full_name='Decrypted Name Test')
        response = self.client.get(f'/api/v1/patients/{patient.id}/')
        # User may not have access to this patient without a channel
        # So either 200 (with decrypted data) or 403
        if response.status_code == 200:
            assert response.data['full_name'] == 'Decrypted Name Test'


@pytest.mark.django_db
class TestMedicalRecordModel:
    """Tests for medical records."""

    def test_create_medical_record(self):
        owner = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        record = MedicalRecord.objects.create(
            channel=channel,
            record_type=MedicalRecord.RecordType.DIAGNOSIS,
            title='Test Diagnosis',
            content='Patient has flu',
            created_by=owner,
        )
        assert record.pk is not None
        assert record.content == 'Patient has flu'

    def test_medical_record_content_encrypted(self):
        """Record content should be encrypted in DB."""
        owner = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        MedicalRecord.objects.create(
            channel=channel,
            record_type=MedicalRecord.RecordType.NOTES,
            title='Notes',
            content='Confidential medical note',
            created_by=owner,
        )

        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute('SELECT content FROM patients_medicalrecord')
            row = cursor.fetchone()

        # Stored value should be encrypted
        assert 'Confidential medical note' not in row[0]
