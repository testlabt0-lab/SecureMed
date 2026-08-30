"""
Tests for audit logging.
"""
import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.utils import log_security_event
from tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestAuditLog:
    """Tests for audit logging system."""

    def test_log_security_event(self):
        user = AdminUserFactory()
        log_security_event(
            user=user,
            event_type=AuditLog.EventType.LOGIN_SUCCESS,
            details={'method': 'password'},
        )
        assert AuditLog.objects.count() == 1
        log = AuditLog.objects.first()
        assert log.event_type == AuditLog.EventType.LOGIN_SUCCESS
        assert log.user == user

    def test_log_with_request_info(self):
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.post('/api/v1/auth/login/', {}, format='json')
        request.META['REMOTE_ADDR'] = '192.168.1.100'
        request.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'

        user = AdminUserFactory()
        log_security_event(
            user=user,
            event_type=AuditLog.EventType.LOGIN_SUCCESS,
            request=request,
        )

        log = AuditLog.objects.first()
        assert log.ip_address == '192.168.1.100'
        assert 'TestBrowser' in log.user_agent
        assert log.path == '/api/v1/auth/login/'
        assert log.method == 'POST'


@pytest.mark.django_db
class TestAuditLogAPI:
    """Tests for audit log API endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.client.force_authenticate(user=self.admin)

    def test_list_audit_logs(self):
        # Create some audit logs
        for _ in range(3):
            log_security_event(
                user=self.admin,
                event_type=AuditLog.EventType.LOGIN_SUCCESS,
            )

        response = self.client.get('/api/v1/audit/logs/')
        assert response.status_code == 200
        # With pagination, response.data is a dict with 'results'
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(results) == 3

    def test_filter_audit_logs_by_event_type(self):
        log_security_event(
            user=self.admin,
            event_type=AuditLog.EventType.LOGIN_SUCCESS,
        )
        log_security_event(
            user=self.admin,
            event_type=AuditLog.EventType.LOGOUT,
        )

        response = self.client.get('/api/v1/audit/logs/?event_type=LOGIN_SUCCESS')
        assert response.status_code == 200
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        assert len(results) == 1

    def test_non_admin_cannot_access(self):
        doctor = UserFactory(role=User.Role.DOCTOR)
        self.client.force_authenticate(user=doctor)
        response = self.client.get('/api/v1/audit/logs/')
        assert response.status_code in [403, 404]
