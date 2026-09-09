"""
Tests for the write guards added with the mobile write operations (بند 3-1):

* MedicalRecord PATCH/DELETE — `perform_update`/`perform_destroy` must apply
  the same channel-role rule `perform_create` always applied. Before this,
  any authenticated user who could *read* a record could modify or destroy it
  (ModelViewSet default), which is what the Android client would have
  exposed the moment edit/delete shipped.
* Prescription create — `PRESCRIPTION_CREATED` audit trail (creation was the
  only lifecycle step without one) and item persistence through
  `PrescriptionCreateSerializer`.
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.channels.models import ChannelMembership
from apps.patients.models import MedicalRecord
from apps.pharmacy.models import Medication, Prescription
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


def _owned_channel(owner, patient, name='قناة العلاج'):
    channel = ChannelFactory(name=name, patient=patient, owner=owner)
    ChannelMembershipFactory(
        channel=channel, user=owner, role=ChannelMembership.Role.OWNER
    )
    return channel


def _record(channel, title='سجل أصلي', created_by=None):
    return MedicalRecord.objects.create(
        channel=channel,
        record_type=MedicalRecord.RecordType.NOTES,
        title=title,
        content='محتوى السجل الأصلي',
        created_by=created_by,
    )


@pytest.mark.django_db
class TestMedicalRecordWriteGuards:
    def test_viewer_cannot_update_or_delete(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        viewer = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        channel = _owned_channel(owner, patient)
        ChannelMembershipFactory(
            channel=channel, user=viewer, role=ChannelMembership.Role.VIEWER
        )
        record = _record(channel, created_by=owner)

        api_client.force_authenticate(viewer)
        patch = api_client.patch(
            reverse('medical-record-detail', kwargs={'pk': record.id}),
            {'title': 'عنوان معدّل'},
            format='json',
        )
        delete = api_client.delete(
            reverse('medical-record-detail', kwargs={'pk': record.id})
        )

        assert patch.status_code == status.HTTP_403_FORBIDDEN
        assert delete.status_code == status.HTTP_403_FORBIDDEN
        record.refresh_from_db()
        assert record.title == 'سجل أصلي'
        assert MedicalRecord.objects.filter(pk=record.pk).exists()

    def test_editor_can_update_and_delete_with_audit(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        editor = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        channel = _owned_channel(owner, patient)
        ChannelMembershipFactory(
            channel=channel, user=editor, role=ChannelMembership.Role.EDITOR
        )
        record = _record(channel, created_by=owner)

        api_client.force_authenticate(editor)
        patch = api_client.patch(
            reverse('medical-record-detail', kwargs={'pk': record.id}),
            {'title': 'عنوان معدّل', 'content': 'محتوى محدَّث'},
            format='json',
        )
        assert patch.status_code == status.HTTP_200_OK
        assert AuditLog.objects.filter(
            event_type='MEDICAL_RECORD_UPDATED', user=editor
        ).exists()

        delete = api_client.delete(
            reverse('medical-record-detail', kwargs={'pk': record.id})
        )
        assert delete.status_code == status.HTTP_204_NO_CONTENT
        assert not MedicalRecord.objects.filter(pk=record.pk).exists()
        assert AuditLog.objects.filter(
            event_type='MEDICAL_RECORD_DELETED', user=editor
        ).exists()

    def test_outside_channel_cannot_modify(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        stranger = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        channel = _owned_channel(owner, patient)
        record = _record(channel, created_by=owner)

        api_client.force_authenticate(stranger)
        delete = api_client.delete(
            reverse('medical-record-detail', kwargs={'pk': record.id})
        )
        assert delete.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_can_modify_any_record(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        admin = AdminUserFactory()
        patient = PatientFactory()
        channel = _owned_channel(owner, patient)
        record = _record(channel, created_by=owner)

        api_client.force_authenticate(admin)
        patch = api_client.patch(
            reverse('medical-record-detail', kwargs={'pk': record.id}),
            {'title': 'تعديل إداري'},
            format='json',
        )
        assert patch.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPrescriptionCreate:
    def _catalog_medication(self, name='أموكسيسيلين'):
        return Medication.objects.create(name=name, stock_quantity=100)

    def test_create_with_items_persists_items_and_audits(self, api_client, db):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        _owned_channel(doctor, patient)
        medication = self._catalog_medication()

        api_client.force_authenticate(doctor)
        response = api_client.post(
            reverse('prescription-list'),
            {
                'patient': str(patient.id),
                'diagnosis_code': 'J06.9',
                'notes': 'جرعة بعد الأكل',
                'items': [
                    {
                        'medication': str(medication.id),
                        'dosage': '500 ملغ',
                        'frequency': 'كل 12 ساعة',
                        'duration_days': 7,
                        'quantity': 14,
                    }
                ],
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        prescription = Prescription.objects.get(pk=response.data['id'])
        assert prescription.items.count() == 1
        item = prescription.items.first()
        assert item.dosage == '500 ملغ'
        assert item.duration_days == 7
        assert prescription.doctor == doctor
        assert AuditLog.objects.filter(
            event_type='PRESCRIPTION_CREATED', user=doctor
        ).exists()

    def test_created_prescription_lists_back_with_names(self, api_client, db):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        _owned_channel(doctor, patient)
        medication = self._catalog_medication('باراسيتامول')

        api_client.force_authenticate(doctor)
        created = api_client.post(
            reverse('prescription-list'),
            {
                'patient': str(patient.id),
                'items': [
                    {
                        'medication': str(medication.id),
                        'dosage': '1 قرص',
                        'frequency': 'ثلاث مرات يومياً',
                        'duration_days': 5,
                        'quantity': 15,
                    }
                ],
            },
            format='json',
        )
        assert created.status_code == status.HTTP_201_CREATED

        listing = api_client.get(reverse('prescription-list'))
        assert listing.status_code == status.HTTP_200_OK
        results = (
            listing.data['results']
            if isinstance(listing.data, dict) and 'results' in listing.data
            else listing.data
        )
        match = [r for r in results if r['id'] == created.data['id']]
        assert len(match) == 1
        assert match[0]['items'][0]['medication_name'] == 'باراسيتامول'
