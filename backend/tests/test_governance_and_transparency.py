"""
Unit tests for Phase 4: Dual-Custody (Four-Eyes) Governance & Patient Access Transparency Ledger (PDPL/HIPAA).
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import django
from django.conf import settings

import pytest

if not settings.configured:
    settings.configure(
        SECRET_KEY='test-insecure-key-for-governance-tests-32bytes!',
        DEBUG=True,
        CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'apps.accounts',
            'apps.audit',
            'apps.security',
        ],
        AUTH_USER_MODEL='accounts.User',
    )
    django.setup()
else:
    from django.apps import apps
    if not apps.ready:
        django.setup()

from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.security.models import DualCustodyApproval
from tests.factories import UserFactory

from apps.security.governance import (
    create_approval_request,
    approve_request,
    reject_request,
    verify_and_consume_token,
    OperationType,
    ApprovalStatus,
    DualCustodyException,
    DualCustodySelfApprovalForbidden,
)
from apps.patients.transparency import (
    get_patient_access_ledger,
    mask_client_ip,
)


class MockAdminUser:
    def __init__(self, user_id=1, email="admin1@hospital.sa", role="SUPER_ADMIN"):
        self.id = user_id
        self.pk = user_id
        self.email = email
        self.role = role
        self.is_authenticated = True

    def get_full_name(self):
        return "د. المدير العام"


class MockSecondAdminUser:
    def __init__(self, user_id=2, email="admin2@hospital.sa", role="HOSPITAL_ADMIN"):
        self.id = user_id
        self.pk = user_id
        self.email = email
        self.role = role
        self.is_authenticated = True

    def get_full_name(self):
        return "د. نائب المدير"


class MockPatientUser:
    def __init__(self, user_id=50, email="patient@hospital.sa"):
        self.id = user_id
        self.pk = user_id
        self.email = email
        self.role = "PATIENT"
        self.is_authenticated = True


class MockPatientRecord:
    def __init__(self, patient_id="11111111-1111-1111-1111-111111111111", user=None, full_name="سالم القحطاني"):
        self.id = patient_id
        self.pk = patient_id
        self.user = user
        self.full_name = full_name
        self.basin = MagicMock()
        self.basin.name = "حوض الرياض الصحي"


@pytest.mark.django_db
class DualCustodyGovernanceTests(unittest.TestCase):
    """Test Four-Eyes segregation of duties and dual authorization."""

    def setUp(self):
        cache.clear()
        # Real DB users: the approval record now persists to DualCustodyApproval,
        # which has foreign keys to User, so mock objects cannot be assigned.
        self.admin1 = UserFactory(role=User.Role.SUPER_ADMIN)
        self.admin2 = UserFactory(role=User.Role.HOSPITAL_ADMIN)
        self.doctor = UserFactory(role=User.Role.DOCTOR)

    def tearDown(self):
        cache.clear()

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_create_approval_request(self, mock_audit, mock_tg):
        # Non-admin cannot initiate sensitive bulk operations
        with self.assertRaises(PermissionDenied):
            create_approval_request(
                requester=self.doctor,
                operation_type=OperationType.BULK_PATIENT_EXPORT,
                target_resource="Patients:All",
            )

        # Authorized admin can initiate
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.BULK_PATIENT_EXPORT,
            target_resource="Patients:All",
            justification="تصدير بيانات الأبحاث الطبية المعتمدة",
        )
        self.assertEqual(req['status'], ApprovalStatus.PENDING)
        self.assertEqual(req['requester_id'], str(self.admin1.id))
        mock_audit.assert_called_once()
        mock_tg.assert_called_once()

        # The request is persisted, not merely cached.
        self.assertTrue(
            DualCustodyApproval.objects.filter(pk=req['id']).exists(),
            'an approval for an irreversible operation must survive in the DB',
        )

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_self_approval_strictly_forbidden(self, mock_audit, mock_tg):
        """Verify that an administrator CANNOT approve their own critical operation."""
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.RECORD_PURGE,
            target_resource="Channel:Emergency-Archive",
            justification="تنظيف الأرشيف",
        )
        req_id = req['id']

        # Requester attempts to approve their own request
        with self.assertRaises(DualCustodySelfApprovalForbidden):
            approve_request(approver=self.admin1, request_id=req_id)

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_independent_approval_and_single_use_execution(self, mock_audit, mock_tg):
        """Full lifecycle: create -> approve by second admin -> execute -> prevent replay."""
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.BULK_PATIENT_EXPORT,
            target_resource="Registry:Full",
        )
        req_id = req['id']

        # Second admin approves
        approved_req = approve_request(
            approver=self.admin2,
            request_id=req_id,
            notes="تمت المراجعة والتحقق من التفويض"
        )
        self.assertEqual(approved_req['status'], ApprovalStatus.APPROVED)
        token = approved_req['execution_token']
        self.assertIsNotNone(token)
        self.assertTrue(token.startswith("4EYES_"))

        # Execute operation with the valid token
        executed = verify_and_consume_token(
            operation_type=OperationType.BULK_PATIENT_EXPORT,
            executor=self.admin1,
            execution_token=token,
        )
        self.assertEqual(executed['status'], ApprovalStatus.EXECUTED)

        # REPLAY ATTACK TEST: Attempting to use the SAME token again must fail!
        with self.assertRaises(DualCustodyException) as ctx:
            verify_and_consume_token(
                operation_type=OperationType.BULK_PATIENT_EXPORT,
                executor=self.admin1,
                execution_token=token,
            )
        self.assertIn("Replay Attack Prevented", str(ctx.exception))

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_rejection_workflow(self, mock_audit, mock_tg):
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.SYSTEM_OVERRIDE,
            target_resource="WAF:GlobalDisable",
        )
        req_id = req['id']

        rejected = reject_request(
            reviewer=self.admin2,
            request_id=req_id,
            rejection_reason="غير مبرر ومخالف لسياسة الأمان"
        )
        self.assertEqual(rejected['status'], ApprovalStatus.REJECTED)

        # Cannot approve an already rejected request
        with self.assertRaises(DualCustodyException):
            approve_request(approver=self.admin2, request_id=req_id)

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_approval_survives_a_cache_flush(self, mock_audit, mock_tg):
        """An approved irreversible operation must survive Redis being cleared.

        The approval used to live only in the cache, so flushing it (deliberately
        or during an incident) erased the record that an operation was authorised.
        The database row is now authoritative.
        """
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.RECORD_PURGE,
            target_resource="Records:2018-2020",
        )
        approved = approve_request(approver=self.admin2, request_id=req['id'])
        token = approved['execution_token']

        # Simulate a cache flush / restart.
        cache.clear()

        executed = verify_and_consume_token(
            operation_type=OperationType.RECORD_PURGE,
            executor=self.admin1,
            execution_token=token,
        )
        self.assertEqual(executed['status'], ApprovalStatus.EXECUTED)

        row = DualCustodyApproval.objects.get(pk=req['id'])
        self.assertEqual(row.status, DualCustodyApproval.Status.EXECUTED)

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_token_cannot_be_replayed_across_operation_types(self, mock_audit, mock_tg):
        """The operation type is bound into the token signature.

        A token minted for a purge must not authorise a bulk export, even if the
        cache row for the original request is gone.
        """
        req = create_approval_request(
            requester=self.admin1,
            operation_type=OperationType.RECORD_PURGE,
            target_resource="Records:Archive",
        )
        approved = approve_request(approver=self.admin2, request_id=req['id'])
        token = approved['execution_token']

        with self.assertRaises(DualCustodyException) as ctx:
            verify_and_consume_token(
                operation_type=OperationType.BULK_PATIENT_EXPORT,
                executor=self.admin1,
                execution_token=token,
            )
        self.assertIn('نوع العملية', str(ctx.exception))

        # And the token is still unconsumed for its own operation.
        cache.clear()
        executed = verify_and_consume_token(
            operation_type=OperationType.RECORD_PURGE,
            executor=self.admin1,
            execution_token=token,
        )
        self.assertEqual(executed['status'], ApprovalStatus.EXECUTED)


class PatientTransparencyLedgerTests(unittest.TestCase):
    """Test Saudi PDPL / HIPAA patient access disclosure ledger."""

    def test_ip_masking_for_privacy(self):
        self.assertEqual(mask_client_ip("192.168.1.50"), "192.168.***.***")
        self.assertEqual(mask_client_ip("10.0.0.1"), "10.0.***.***")
        self.assertEqual(mask_client_ip(""), "—")
        self.assertEqual(mask_client_ip(None), "—")

    def test_patient_can_only_view_own_access_ledger(self):
        patient1_user = MockPatientUser(user_id=101)
        patient2_user = MockPatientUser(user_id=102)

        patient1_record = MockPatientRecord(
            patient_id="patient-uuid-1",
            user=patient1_user,
            full_name="مريض أول",
        )
        patient1_user.patient_record = patient1_record

        patient2_record = MockPatientRecord(
            patient_id="patient-uuid-2",
            user=patient2_user,
            full_name="مريض ثان",
        )
        patient2_user.patient_record = patient2_record

        # Patient 1 can view their own ledger
        ledger = get_patient_access_ledger(patient1_record, patient1_user)
        self.assertIsInstance(ledger, list)

        # Patient 2 CANNOT view Patient 1's ledger
        with self.assertRaises(PermissionDenied):
            get_patient_access_ledger(patient1_record, patient2_user)


if __name__ == '__main__':
    unittest.main()
