"""
Tests for Phase 6 — production deployment features:
- Django AI proxy (POST /ai/ask/ + GET /ai/health/) with auth, validation,
  history sanitization, size limits and audit trail
- SPA catch-all serving (index.html fallback + backend prefixes excluded)
- Database resolution matrix (DATABASE_URL / DB_ENGINE=sqlite / explicit PG)
"""
import json as _json
from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from tests.test_phase4_features import make_admin

AI_ANSWER_FIXTURE = {
    'answer': 'تستخدم المنصة JWT و WAF وتشفيراً للبيانات الحساسة.',
    'model': 'glm-mock',
}


def _mock_urlopen(payload):
    """Build a mock for urllib.request.urlopen returning payload as JSON."""
    resp_obj = mock.MagicMock()
    resp_obj.read.return_value = _json.dumps(payload).encode()
    resp_obj.__enter__.return_value = resp_obj
    return resp_obj


# ============================================================
# AI assistant proxy
# ============================================================

@pytest.mark.django_db
class TestAIAssistantProxy:

    def setup_method(self):
        self.admin = make_admin()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_ask_requires_authentication(self):
        anon = APIClient()
        resp = anon.post('/ai/ask/', {'question': 'مرحبا'}, format='json')
        assert resp.status_code == 401

    def test_ask_success_and_audit(self):
        with mock.patch('apps.ai.views.urllib.request.urlopen',
                        return_value=_mock_urlopen(AI_ANSWER_FIXTURE)):
            resp = self.client.post(
                '/ai/ask/',
                {'question': 'ما أهم الميزات الأمنية؟', 'history': []},
                format='json',
            )
        assert resp.status_code == 200
        assert 'JWT' in resp.data['answer']
        assert AuditLog.objects.filter(
            event_type='AI_ASSISTANT_QUERY', user=self.admin
        ).exists()

    def test_ask_failure_returns_503_and_audits(self):
        with mock.patch('apps.ai.views.urllib.request.urlopen',
                        side_effect=OSError('service down')):
            resp = self.client.post('/ai/ask/', {'question': 'سؤال'}, format='json')
        assert resp.status_code == 503
        assert AuditLog.objects.filter(
            event_type='AI_ASSISTANT_FAILED', user=self.admin
        ).exists()

    def test_empty_question_rejected(self):
        resp = self.client.post('/ai/ask/', {'question': '   '}, format='json')
        assert resp.status_code == 400

    def test_overlong_question_rejected(self):
        resp = self.client.post('/ai/ask/', {'question': 'ا' * 2001}, format='json')
        assert resp.status_code == 400

    def test_history_is_sanitized_and_capped(self):
        # Garbage entries first so the final 10 (which is all the view keeps)
        # are valid dicts — isolates capping from drop-behaviour.
        history = (
            ['garbage-string', 42, None]                            # dropped
            + [{'role': 'invalid_role', 'content': 'x' * 5000}]     # role → user
            + [{'role': 'user', 'content': f'msg-{i}'} for i in range(20)]  # capped
        )
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured['payload'] = _json.loads(req.data.decode('utf-8'))
            return _mock_urlopen(AI_ANSWER_FIXTURE)

        with mock.patch('apps.ai.views.urllib.request.urlopen', side_effect=fake_urlopen):
            resp = self.client.post(
                '/ai/ask/', {'question': 'س', 'history': history}, format='json'
            )
        assert resp.status_code == 200
        sent = captured['payload']['history']
        assert len(sent) == 10                                   # capped to 10
        assert all(set(h) == {'role', 'content'} for h in sent)  # dicts only
        assert all(len(h['content']) <= 2000 for h in sent)      # truncated
        assert all(h['content'].startswith('msg-') for h in sent)  # garbage gone

    def test_oversized_context_rejected(self):
        big_context = {'blob': 'x' * 500_001}
        resp = self.client.post(
            '/ai/ask/', {'question': 'س', 'context': big_context}, format='json'
        )
        assert resp.status_code == 413

    def test_health_proxy_with_mock(self):
        with mock.patch('apps.ai.views.urllib.request.urlopen',
                        return_value=_mock_urlopen({'status': 'healthy'})):
            resp = self.client.get('/ai/health/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'healthy'

    def test_health_proxy_degrades_gracefully(self):
        with mock.patch('apps.ai.views.urllib.request.urlopen',
                        side_effect=OSError('down')):
            resp = APIClient().get('/ai/health/')  # AllowAny
        assert resp.status_code == 200
        assert resp.data['status'] == 'unavailable'


# ============================================================
# SPA catch-all serving (production single-service mode)
# ============================================================

@pytest.mark.django_db
class TestSPAServing:

    FAKE_DIST = '/tmp/securemed-fake-dist'

    def _prepare(self):
        import os
        os.makedirs(self.FAKE_DIST, exist_ok=True)
        with open(f'{self.FAKE_DIST}/index.html', 'w') as f:
            f.write('<!doctype html><html lang="ar"><body>SPA-OK</body></html>')

    @override_settings(FRONTEND_DIST=FAKE_DIST)
    def test_root_serves_index_html(self):
        self._prepare()
        resp = APIClient().get('/')
        assert resp.status_code == 200
        assert b'SPA-OK' in b''.join(resp.streaming_content)

    @override_settings(FRONTEND_DIST=FAKE_DIST)
    def test_deep_client_route_serves_index_html(self):
        self._prepare()
        resp = APIClient().get('/patients/abc-123/records')
        assert resp.status_code == 200
        assert b'SPA-OK' in b''.join(resp.streaming_content)

    @override_settings(FRONTEND_DIST=FAKE_DIST)
    def test_unknown_api_path_not_swallowed_by_spa(self):
        self._prepare()
        resp = APIClient().get('/api/v1/does-not-exist/')
        assert resp.status_code == 404  # API 404 — never index.html

    def test_missing_dist_returns_404(self):
        import shutil
        shutil.rmtree(self.FAKE_DIST, ignore_errors=True)
        from django.test import Client
        with override_settings(FRONTEND_DIST=self.FAKE_DIST):
            resp = Client().get('/some/route')
        assert resp.status_code == 404


# ============================================================
# Database resolution matrix (settings import behaviour)
# ============================================================

class TestDatabaseResolution:
    """Reload settings with different env vars and assert resolution."""

    def _reload(self, monkeypatch, **env):
        import importlib
        import os
        defaults = {
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DATABASE_URL': '',
            'DB_ENGINE': '',
        }
        for k, v in {**defaults, **env}.items():
            monkeypatch.setenv(k, v)
        import django.conf
        django.conf.settings._wrapped = django.conf.empty
        import config.settings as s
        importlib.reload(s)
        return s

    def test_database_url_postgres(self, monkeypatch):
        s = self._reload(
            monkeypatch,
            DATABASE_URL='postgresql://u:p@db.example.com/securemed?sslmode=require',
        )
        db = s.DATABASES['default']
        assert db['ENGINE'] == 'django.db.backends.postgresql'
        assert db['NAME'] == 'securemed'
        assert db['OPTIONS'].get('sslmode') == 'require'
        assert db.get('ATOMIC_REQUESTS') is True

    def test_db_engine_sqlite(self, monkeypatch):
        s = self._reload(monkeypatch, DB_ENGINE='sqlite')
        db = s.DATABASES['default']
        assert db['ENGINE'] == 'django.db.backends.sqlite3'

    def test_file_url_sqlite(self, monkeypatch):
        s = self._reload(monkeypatch, DATABASE_URL='file:/tmp/smoke.db')
        db = s.DATABASES['default']
        assert db['ENGINE'] == 'django.db.backends.sqlite3'
        assert db['NAME'] == '/tmp/smoke.db'

    def test_explicit_pg_gets_sslmode(self, monkeypatch):
        s = self._reload(monkeypatch)
        db = s.DATABASES['default']
        assert db['ENGINE'] == 'django.db.backends.postgresql'
        assert db['OPTIONS']['sslmode'] == 'require'

    def test_csrf_wildcard_derivation(self, monkeypatch):
        s = self._reload(
            monkeypatch,
            ALLOWED_HOSTS='.onrender.com,localhost',
            CSRF_TRUSTED_ORIGINS='',
        )
        assert 'https://*.onrender.com' in s.CSRF_TRUSTED_ORIGINS
        assert 'https://localhost' in s.CSRF_TRUSTED_ORIGINS
