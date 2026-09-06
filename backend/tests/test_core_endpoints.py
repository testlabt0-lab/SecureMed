"""
Tests for the cross-cutting endpoints in apps.core:

  * POST /api/v1/core/sync/  — offline batch upload, currently 501
  * GET  /health/live/       — liveness
  * GET  /health/ready/      — readiness, and who is allowed to see the breakdown

Both readiness and /metrics answer to ``internal_access_allowed``, so the gate is
exercised here through the readiness body rather than duplicated per endpoint.
"""
import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.core.health import _check_ai_service
from tests.test_phase4_features import make_admin

SYNC = '/api/v1/core/sync/'
LIVE = '/health/live/'
READY = '/health/ready/'

# APIClient sends REMOTE_ADDR=127.0.0.1, which METRICS_ALLOWED_IPS trusts by
# default. Tests that need the *public* view of an internal endpoint have to leave
# that allowlist, so they scrape from an off-network address instead.
OUTSIDE = '203.0.113.7'


@pytest.mark.django_db
class TestOfflineSync:

    def setup_method(self):
        self.admin = make_admin()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_requires_authentication(self):
        assert APIClient().post(SYNC, {'operations': []}, format='json').status_code == 401

    def test_reports_not_implemented_and_never_claims_success(self):
        # The old view answered 200 {"status": "success", "synced": N} while
        # writing nothing, so a PWA trimming its queue on success lost the
        # observations for good. Anything but 501 here is that bug returning.
        resp = self.client.post(SYNC, {'operations': [
            {'type': 'vital_sign', 'data': {'bp': '120/80'}},
            {'type': 'medical_note', 'data': {'text': 'ملاحظة'}},
        ]}, format='json')
        assert resp.status_code == 501
        assert resp.data['code'] == 'OFFLINE_SYNC_NOT_IMPLEMENTED'
        assert resp.data['synced'] == 0
        assert resp.data['received'] == 2
        assert 'vital_sign' in resp.data['supported_types']

    def test_audits_counts_only_never_the_payload(self, caplog):
        secret = 'ضغط الدم 190/120'
        with caplog.at_level('INFO'):
            resp = self.client.post(SYNC, {'operations': [
                {'type': 'vital_sign', 'data': {'note': secret}},
            ]}, format='json')
        assert resp.status_code == 501
        assert secret not in caplog.text          # PHI never reaches the log

        log = AuditLog.objects.filter(event_type='OFFLINE_SYNC_REJECTED').first()
        assert log is not None
        assert log.details['operation_count'] == 1
        assert log.details['by_type'] == {'vital_sign': 1}
        assert secret not in str(log.details)

    def test_malformed_body_does_not_500(self):
        for body in ({}, {'operations': 'not-a-list'}, {'operations': [None, 7, 'x']}):
            resp = self.client.post(SYNC, body, format='json')
            assert resp.status_code == 501, body

    def test_unknown_operation_types_are_bucketed(self):
        resp = self.client.post(
            SYNC, {'operations': [{'type': 'wire_transfer'}, {'no': 'type'}]}, format='json'
        )
        assert resp.status_code == 501
        log = AuditLog.objects.filter(event_type='OFFLINE_SYNC_REJECTED').first()
        assert log.details['by_type'] == {'unknown': 2}


@pytest.mark.django_db
class TestHealthEndpoints:

    def test_liveness_is_public_and_cheap(self):
        resp = APIClient().get(LIVE)
        assert resp.status_code == 200
        assert resp.json()['status'] == 'alive'

    @override_settings(METRICS_TOKEN='', METRICS_ALLOWED_IPS=['10.0.0.0/8'])
    def test_readiness_hides_the_breakdown_from_anonymous_callers(self):
        # `checks` carries database latency, disk usage, worker counts and — via
        # str(exc) — verbatim driver errors that name the DB host, port and user.
        resp = APIClient().get(READY, REMOTE_ADDR=OUTSIDE)
        body = resp.json()
        assert 'checks' not in body
        assert body['checked'] == sorted(
            ['database', 'redis', 'ai_service', 'disk', 'celery']
        )
        assert body['status'] in ('healthy', 'degraded', 'unhealthy')

    @override_settings(METRICS_TOKEN='scrape-me', METRICS_ALLOWED_IPS=['10.0.0.0/8'])
    def test_readiness_shows_the_breakdown_to_a_token_holder(self):
        resp = APIClient().get(
            READY, REMOTE_ADDR=OUTSIDE, HTTP_AUTHORIZATION='Bearer scrape-me'
        )
        assert 'checks' in resp.json()
        assert resp.json()['checks']['database']['status'] == 'ok'

    @override_settings(METRICS_TOKEN='scrape-me', METRICS_ALLOWED_IPS=['10.0.0.0/8'])
    def test_readiness_rejects_a_wrong_token_without_leaking(self):
        resp = APIClient().get(
            READY, REMOTE_ADDR=OUTSIDE, HTTP_AUTHORIZATION='Bearer wrong'
        )
        assert 'checks' not in resp.json()

    @override_settings(GEMINI_API_KEY='')
    def test_ai_check_is_a_settings_lookup_not_an_http_call(self):
        # It used to GET {AI_SERVICE_URL}/health with a 3s timeout against a Node
        # sidecar that is no longer deployed: 'degraded' forever, plus up to three
        # seconds of latency on every readiness probe.
        result = _check_ai_service()
        assert result['status'] == 'degraded'
        assert result['configured'] is False
        assert 'GEMINI_API_KEY' in result['detail']

    @override_settings(GEMINI_API_KEY='test-key')
    def test_ai_check_ok_when_configured_and_never_echoes_the_key(self):
        result = _check_ai_service()
        assert result['status'] == 'ok'
        assert result['configured'] is True
        assert 'test-key' not in str(result)
