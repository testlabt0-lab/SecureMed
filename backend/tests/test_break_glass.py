"""
Tests for Break-Glass Emergency Access Protocol in SecureMed.
Verifies role enforcement, audit logging, emergency profile override, and revocation.
"""
import datetime
from unittest.mock import patch
import pytest
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.security.models import BreakGlassAccess
from apps.audit.models import AuditLog
from apps.patients.models import Patient
from tests.factories import UserFactory, PatientFactory


def get_json(res):
    """Safely extract response data whether Response or JsonResponse."""
    if hasattr(res, 'data') and res.data is not None:
        return res.data
    return res.json()


@pytest.mark.django_db
class TestBreakGlassProtocol:
    """Break-Glass Emergency Protocol security test suite."""

    def setup_method(self):
        from apps.security.models import ZTNAPendingApproval
        self.client = APIClient()
        self.client.cookies['ztna_device_id'] = 'test-ztna-device'
        self.client.defaults['HTTP_X_DEVICE_FINGERPRINT'] = 'test-ztna-device'
        ZTNAPendingApproval.objects.create(
            device_fingerprint='test-ztna-device',
            ip_address='127.0.0.1',
            is_approved=True
        )
        self.doctor = UserFactory(role=User.Role.DOCTOR, department='قسم الطوارئ')
        self.nurse = UserFactory(role=User.Role.NURSE, department='العناية المركزة')
        self.patient_user = UserFactory(role=User.Role.PATIENT)
        self.receptionist = UserFactory(role=User.Role.RECEPTIONIST)
        self.admin = UserFactory(role=User.Role.SUPER_ADMIN)
        self.patient = PatientFactory()

    @patch('apps.security.break_glass_views.send_break_glass_alert')
    def test_non_clinical_user_cannot_activate_break_glass(self, mock_alert):
        """Patients and administrative non-clinical staff cannot trigger Break-Glass."""
        self.client.force_authenticate(user=self.patient_user)
        url = reverse('break-glass-activate')
        payload = {
            'patient_id': str(self.patient.id),
            'reason': 'حالة طوارئ قلبية إسعافية تستدعي فتح الملف فوراً لإنقاذ الحياة'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == status.HTTP_403_FORBIDDEN
        data = get_json(res)
        assert data['code'] == 'PERMISSION_DENIED'

        # Receptionist test
        self.client.force_authenticate(user=self.receptionist)
        res2 = self.client.post(url, payload, format='json')
        assert res2.status_code == status.HTTP_403_FORBIDDEN

    @patch('apps.security.break_glass_views.send_break_glass_alert')
    def test_reason_validation_minimum_length(self, mock_alert):
        """Clinical user must provide a substantial medical justification (at least 20 chars)."""
        self.client.force_authenticate(user=self.doctor)
        url = reverse('break-glass-activate')
        payload = {
            'patient_id': str(self.patient.id),
            'reason': 'طوارئ قصيرة'  # less than 20 chars
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        data = get_json(res)
        assert data['code'] == 'INVALID_REASON'

    @patch('apps.security.break_glass_views.send_break_glass_alert')
    def test_doctor_activates_break_glass_success_and_logs_audit(self, mock_alert):
        """Doctor can activate break-glass with audit trail and 4-hour validity."""
        self.client.force_authenticate(user=self.doctor)
        url = reverse('break-glass-activate')
        reason_text = 'توقف مفاجئ في عضلة القلب في قسم الطوارئ يستدعي معرفة فصيلة الدم والتاريخ الدوائي'
        payload = {
            'patient_id': str(self.patient.id),
            'reason': reason_text,
            'department': 'طوارئ الباطنية'
        }
        res = self.client.post(url, payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED
        data = get_json(res)
        assert data['status'] == 'success'
        bg_id = data['break_glass']['id']

        # Verify DB record
        bg = BreakGlassAccess.objects.get(id=bg_id)
        assert bg.user == self.doctor
        assert bg.patient == self.patient
        assert bg.status == BreakGlassAccess.Status.ACTIVE
        assert bg.is_currently_active is True
        assert bg.department == 'طوارئ الباطنية'

        # Verify Audit Log event with CRITICAL severity
        audit_entry = AuditLog.objects.filter(
            event_type=AuditLog.EventType.BREAK_GLASS_ACTIVATED,
            user_id=str(self.doctor.id)
        ).first()
        assert audit_entry is not None
        assert audit_entry.severity == 'CRITICAL'
        assert audit_entry.details['patient_id'] == str(self.patient.id)

    @patch('apps.security.break_glass_views.send_break_glass_alert')
    def test_doctor_access_lifecycle_before_and_after_break_glass(self, mock_alert):
        """Doctor is blocked with Break-Glass recommendation, then granted access after activation."""
        # 1. Before break-glass: Doctor cannot view patient profile
        self.client.force_authenticate(user=self.doctor)
        profile_url = reverse('patient-profile', kwargs={'pk': str(self.patient.id)})
        res_before = self.client.get(profile_url)
        assert res_before.status_code == status.HTTP_403_FORBIDDEN
        data_before = get_json(res_before)
        assert data_before.get('break_glass_available') is True

        # 2. Activate Break-Glass
        activate_url = reverse('break-glass-activate')
        activate_res = self.client.post(activate_url, {
            'patient_id': str(self.patient.id),
            'reason': 'حالة حرجة جداً تتطلب التدخل الفوري في غرفة الإنعاش'
        }, format='json')
        assert activate_res.status_code == status.HTTP_201_CREATED

        # 3. After break-glass: Doctor CAN view patient profile, and break_glass banner data is present!
        res_after = self.client.get(profile_url)
        assert res_after.status_code == status.HTTP_200_OK
        data_after = get_json(res_after)
        assert 'patient' in data_after
        assert data_after.get('break_glass') is not None
        assert data_after['break_glass']['id']

    def test_revocation_of_break_glass(self):
        """Ending the emergency session revokes access immediately."""
        now = timezone.now()
        bg = BreakGlassAccess.objects.create(
            user=self.doctor,
            patient=self.patient,
            reason='حالة إسعافية تطلبت تدخلاً سريعاً في قسم الطوارئ',
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at=now + datetime.timedelta(hours=4)
        )
        assert bg.is_currently_active is True

        # Revoke via API
        self.client.force_authenticate(user=self.doctor)
        revoke_url = reverse('break-glass-revoke')
        res = self.client.post(revoke_url, {'break_glass_id': str(bg.id)}, format='json')
        assert res.status_code == status.HTTP_200_OK

        bg.refresh_from_db()
        assert bg.status == BreakGlassAccess.Status.REVOKED
        assert bg.is_currently_active is False

        # Verify access is now denied again
        profile_url = reverse('patient-profile', kwargs={'pk': str(self.patient.id)})
        profile_res = self.client.get(profile_url)
        assert profile_res.status_code == status.HTTP_403_FORBIDDEN

    def test_expired_break_glass_is_inactive(self):
        """Expired break-glass sessions cannot be used."""
        past_time = timezone.now() - datetime.timedelta(minutes=10)
        bg = BreakGlassAccess.objects.create(
            user=self.doctor,
            patient=self.patient,
            reason='حالة إسعافية انتهت صلاحيتها الزمنية المقررة',
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at=past_time
        )
        assert bg.is_currently_active is False

        self.client.force_authenticate(user=self.doctor)
        profile_url = reverse('patient-profile', kwargs={'pk': str(self.patient.id)})
        res = self.client.get(profile_url)
        assert res.status_code == status.HTTP_403_FORBIDDEN
