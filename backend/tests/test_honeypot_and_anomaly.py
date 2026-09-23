"""
Unit tests for Threat Intelligence: Canary/Honeypot Patients and EHR Hopping Anomaly Detection.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY='test-insecure-key-for-security-tests-32bytes!',
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
from django.http import Http404

from apps.security.honeypot import (
    register_canary_patient,
    unregister_canary_patient,
    is_canary_patient,
    handle_canary_access,
    CANARY_CACHE_KEY,
)
from apps.core.anomaly import (
    record_patient_hopping,
    _HOPPING_CACHE_PREFIX,
)
from apps.core.mixins import PatientAccessMixin


class MockUser:
    def __init__(self, user_id=999, email="suspicious.user@hospital.sa", role="DOCTOR"):
        self.id = user_id
        self.pk = user_id
        self.email = email
        self.role = role
        self.is_authenticated = True


class MockRequest:
    def __init__(self, client_ip="198.51.100.99"):
        self.META = {
            'REMOTE_ADDR': client_ip,
            'HTTP_USER_AGENT': 'Mozilla/5.0 SecurityScanner/1.0',
        }
        self.method = 'GET'
        self.path = '/api/v1/patients/test-canary-uuid/'
        self.session = MagicMock()
        self.session.session_key = 'test-session-canary'


class MockPatient:
    def __init__(self, patient_id="00000000-0000-0000-0000-000000000099", is_canary=False, full_name="VIP Decoy Patient"):
        self.id = patient_id
        self.pk = patient_id
        self.is_canary = is_canary
        self.full_name = full_name
        self.channels = MagicMock()
        self.channels.filter.return_value.exists.return_value = False


class CanaryHoneypotTests(unittest.TestCase):
    """Test Canary/Honeypot patient registration, detection, and countermeasures."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_canary_registration_and_detection(self):
        canary_id = "canary-secret-vip-1234"
        regular_id = "patient-regular-5678"

        # Initially, neither is canary
        self.assertFalse(is_canary_patient(canary_id))
        self.assertFalse(is_canary_patient(regular_id))

        # Register canary
        self.assertTrue(register_canary_patient(canary_id, note="VIP Decoy for SecOps"))
        self.assertTrue(is_canary_patient(canary_id))
        self.assertFalse(is_canary_patient(regular_id))

        # Test with MockPatient object
        patient_obj = MockPatient(patient_id=canary_id)
        self.assertTrue(is_canary_patient(patient_obj))

        # Test object with explicit is_canary=True flag
        explicit_canary = MockPatient(patient_id="explicit-canary-000", is_canary=True)
        self.assertTrue(is_canary_patient(explicit_canary))

        # Unregister canary
        self.assertTrue(unregister_canary_patient(canary_id))
        self.assertFalse(is_canary_patient(canary_id))

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_handle_canary_access_defenses(self, mock_audit, mock_tg):
        mock_tg.return_value = True
        canary_id = "honeypot-patient-omega"
        register_canary_patient(canary_id)

        user = MockUser(user_id=101, email="doctor.snooper@hospital.sa")
        req = MockRequest(client_ip="203.0.113.55")

        result = handle_canary_access(user, canary_id, request=req, action='retrieve')

        self.assertEqual(result['status'], 'triggered')
        self.assertTrue(result['blocked'])
        self.assertEqual(result['client_ip'], '203.0.113.55')

        # Verify IP was instantly blocked in WAF cache
        waf_block = cache.get('waf_blacklist:203.0.113.55')
        self.assertTrue(waf_block)

        # Verify audit event was logged with CRITICAL severity
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        self.assertEqual(call_kwargs['event_type'], 'CANARY_PATIENT_ACCESSED')
        self.assertEqual(call_kwargs['severity'], 'CRITICAL')

        # Verify Telegram alert was dispatched
        mock_tg.assert_called_once()

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_patient_access_mixin_blocks_canary_with_404(self, mock_audit, mock_tg):
        """Verify PatientAccessMixin intercepts Canary access and returns stealth 404."""
        canary_id = "decoy-vip-patient"
        register_canary_patient(canary_id)

        canary_patient = MockPatient(patient_id=canary_id)
        user = MockUser(user_id=88)

        mixin_instance = PatientAccessMixin()
        mixin_instance.request = MockRequest(client_ip="198.51.100.77")

        with self.assertRaises(Http404):
            mixin_instance.check_patient_access(user, canary_patient, action_name='view')

        # Check WAF blacklist
        self.assertTrue(cache.get('waf_blacklist:198.51.100.77'))


class EhrHoppingAnomalyTests(unittest.TestCase):
    """Test detection of anomalous rapid switching / snooping across distinct patient charts."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_normal_patient_reading_within_limits(self, mock_audit, mock_tg):
        user = MockUser(user_id=501)

        # Viewing 5 distinct patients (well below the 15-patient 5m threshold)
        for i in range(1, 6):
            triggered = record_patient_hopping(user, f"patient-case-{i}")
            self.assertFalse(triggered)

        mock_audit.assert_not_called()
        mock_tg.assert_not_called()

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_duplicate_views_of_same_patient_not_counted_as_hopping(self, mock_audit, mock_tg):
        user = MockUser(user_id=502)

        # Clinician repeatedly reviewing the SAME patient 25 times
        for _ in range(25):
            triggered = record_patient_hopping(user, "intensive-care-patient-001")
            self.assertFalse(triggered)

        # Distinct patient count should be 1
        key_5m = f'{_HOPPING_CACHE_PREFIX}:{user.id}:5m'
        distinct_patients = cache.get(key_5m)
        self.assertEqual(len(distinct_patients), 1)
        mock_audit.assert_not_called()

    @patch('apps.security.telegram_service.send_critical_alert')
    @patch('apps.audit.utils.log_security_event')
    def test_ehr_hopping_anomaly_triggers_when_threshold_exceeded(self, mock_audit, mock_tg):
        user = MockUser(user_id=503, email="insider.threat@hospital.sa")

        # Threshold for 5m is 15 distinct patients.
        # Access 15 distinct patients:
        for i in range(1, 16):
            triggered = record_patient_hopping(user, f"target-patient-{i}")
            self.assertFalse(triggered)

        # 16th distinct patient breaches the threshold (> 15)
        triggered = record_patient_hopping(user, "target-patient-16")
        self.assertTrue(triggered)

        # Verify audit logged
        mock_audit.assert_called_once()
        kwargs = mock_audit.call_args[1]
        self.assertEqual(kwargs['event_type'], 'EHR_HOPPING_ANOMALY')
        self.assertEqual(kwargs['severity'], 'WARNING')
        self.assertEqual(kwargs['details']['crossed']['count'], 16)

        # Verify SecOps telegram alert was sent
        mock_tg.assert_called_once()


if __name__ == '__main__':
    unittest.main()
