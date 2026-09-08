"""
Tests locking the patient-profile aggregate contract (ع6):

`GET patients/{id}/profile/` is the endpoint the mobile patient page is built
on. Its defining property is *attribution*: the records it returns must belong
to the patient's own channels — the global `patients/records/` list cannot
express that because `MedicalRecord` carries no patient field, which is how a
single patient page used to show every patient's records.

Covers:
* the profile returns only records of the patient's channels
* channel-scoped records of *other* patients never leak in
* caller access scoping (a non-member does not see the profile)
* the attribution itself — record channel membership, not global listing
* the stats block matches the returned payload
"""
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.channels.models import Channel, ChannelMembership
from apps.patients.models import MedicalRecord
from tests.factories import (
    UserFactory,
    PatientFactory,
    ChannelFactory,
    ChannelMembershipFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


def _make_channel(patient, owner, name):
    channel = ChannelFactory(name=name, patient=patient, owner=owner)
    ChannelMembershipFactory(channel=channel, user=owner, role=ChannelMembership.Role.OWNER)
    return channel


def _record(channel, title, created_by=None):
    return MedicalRecord.objects.create(
        channel=channel,
        record_type=MedicalRecord.RecordType.NOTES,
        title=title,
        content=f'محتوى {title}',
        created_by=created_by,
    )


@pytest.mark.django_db
class TestPatientProfileAttribution:
    def test_profile_returns_only_this_patients_records(
        self, api_client, db
    ):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient_a = PatientFactory(full_name='المريض الأول')
        patient_b = PatientFactory(full_name='المريض الثاني')

        channel_a = _make_channel(patient_a, doctor, 'قناة المريض الأول')
        channel_b = _make_channel(patient_b, doctor, 'قناة المريض الثاني')

        record_a1 = _record(channel_a, 'سجل للمريض الأول', created_by=doctor)
        record_a2 = _record(channel_a, 'سجل ثانٍ للمريض الأول', created_by=doctor)
        _record(channel_b, 'سجل للمريض الثاني', created_by=doctor)

        api_client.force_authenticate(doctor)
        response = api_client.get(
            reverse('patient-profile', kwargs={'pk': patient_a.id})
        )

        assert response.status_code == status.HTTP_200_OK
        titles = {r['title'] for r in response.data['records']}
        assert titles == {'سجل للمريض الأول', 'سجل ثانٍ للمريض الأول'}
        record_ids = {r['id'] for r in response.data['records']}
        assert str(record_a1.id) in record_ids
        assert str(record_a2.id) in record_ids

    def test_multi_channel_patient_aggregates_all_channels(
        self, api_client, db
    ):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        clinic = _make_channel(patient, doctor, 'عيادة خارجية')
        imaging = _make_channel(patient, doctor, 'قسم الأشعة')

        _record(clinic, 'ملاحظة عيادة', created_by=doctor)
        _record(imaging, 'تقرير أشعة', created_by=doctor)

        api_client.force_authenticate(doctor)
        response = api_client.get(
            reverse('patient-profile', kwargs={'pk': patient.id})
        )

        assert response.status_code == status.HTTP_200_OK
        titles = {r['title'] for r in response.data['records']}
        assert titles == {'ملاحظة عيادة', 'تقرير أشعة'}

    def test_non_member_cannot_read_profile(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        outsider = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        _make_channel(patient, owner, 'قناة مغلقة')

        api_client.force_authenticate(outsider)
        response = api_client.get(
            reverse('patient-profile', kwargs={'pk': patient.id})
        )

        assert response.status_code in (
            status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND
        )

    def test_member_sees_only_viewable_channels_records(self, api_client, db):
        owner = UserFactory(role=User.Role.DOCTOR)
        member = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()

        open_channel = _make_channel(patient, owner, 'قناة عامة')
        # A second channel of the same patient where `member` holds no
        # membership row at all — `can_view` must be False for them.
        private_channel = ChannelFactory(name='قناة بلا عضوية', patient=patient, owner=owner)

        ChannelMembershipFactory(channel=open_channel, user=member)
        _record(open_channel, 'سجل مرئي', created_by=owner)
        _record(private_channel, 'سجل غير مرئي', created_by=owner)

        api_client.force_authenticate(member)
        response = api_client.get(
            reverse('patient-profile', kwargs={'pk': patient.id})
        )

        assert response.status_code == status.HTTP_200_OK
        titles = {r['title'] for r in response.data['records']}
        assert 'سجل مرئي' in titles
        assert 'سجل غير مرئي' not in titles

    def test_stats_match_payload(self, api_client, db):
        doctor = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        channel = _make_channel(patient, doctor, 'قناة وحيدة')

        _record(channel, 'سجل واحد', created_by=doctor)

        api_client.force_authenticate(doctor)
        response = api_client.get(
            reverse('patient-profile', kwargs={'pk': patient.id})
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['stats']['total_records'] == len(response.data['records'])
        assert response.data['stats']['total_channels'] == len(response.data['channels'])
        assert response.data['patient']['id'] == str(patient.id)
