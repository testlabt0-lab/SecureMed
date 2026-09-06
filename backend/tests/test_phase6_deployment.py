"""
Tests for Phase 6 — production deployment features:
- Native Gemini AI endpoints under /api/v1/ai/ — auth, basin module gating,
  input validation, history sanitization, size limits, PHI anonymisation and
  the audit trail
- SPA catch-all serving (index.html fallback + backend prefixes excluded)
- Database resolution matrix (DATABASE_URL / DB_ENGINE=sqlite / explicit PG)
"""
import base64
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.basins.models import Basin
from tests.factories import BasinFactory, UserFactory
from tests.test_phase4_features import make_admin

AI = '/api/v1/ai/'
ASK = f'{AI}ask/'
IMAGE = f'{AI}analyze-image/'
NOTE = f'{AI}structure-note/'
TRIAGE = f'{AI}triage/'
HEALTH = f'{AI}health/'

ANSWER = 'تستخدم المنصة JWT و WAF وتشفيراً للبيانات الحساسة.'
PNG_B64 = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 32).decode()
NATIONAL_ID = '1234567890'


def _fake_model(text=ANSWER, error=None, sent=None):
    """Stand-in for ``genai.GenerativeModel``.

    The AI module calls Gemini in-process, so there is no HTTP request left to
    intercept: what a view "sends" is the argument it hands to
    ``generate_content``. `sent` collects those arguments, which is the only
    place PHI leaving the deployment would show up.
    """
    model = mock.MagicMock()

    def generate_content(payload, *args, **kwargs):
        if sent is not None:
            sent.append(payload)
        if error is not None:
            raise error
        return mock.MagicMock(text=text)

    model.generate_content.side_effect = generate_content
    return model


def _patched(**kwargs):
    """Patch the module's model factory with a fake, bypassing the API key."""
    return mock.patch('apps.ai.views.get_gemini_model',
                      return_value=_fake_model(**kwargs))


# ============================================================
# AI endpoints (native Gemini, /api/v1/ai/*)
# ============================================================

@pytest.mark.django_db
class TestAIEndpoints:
    """The four POST views + the health probe.

    Every request passes through RateLimitMiddleware (60/min per IP+path), so
    the cache is cleared per test to keep a long class from tripping it.
    """

    def setup_method(self):
        cache.clear()
        self.admin = make_admin()
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    # --- authentication + basin module gating ----------------------------

    def test_ask_requires_authentication(self):
        resp = APIClient().post(ASK, {'question': 'مرحبا'}, format='json')
        assert resp.status_code == 401

    def test_every_endpoint_is_gated_by_the_ai_module(self):
        # _require_module was called by /ask only, so a basin without the
        # ai_assistant module could still reach the other three views.
        basin = BasinFactory()
        basin.disable_module(Basin.MODULE_AI_ASSISTANT)
        client = APIClient()
        client.force_authenticate(user=UserFactory(basin=basin))

        assert client.post(ASK, {'question': 'س'}, format='json').status_code == 403
        assert client.post(IMAGE, {'imageBase64': PNG_B64}, format='json').status_code == 403
        assert client.post(NOTE, {'text': 'ملاحظة'}, format='json').status_code == 403
        assert client.post(TRIAGE, {'symptoms': 'حمى'}, format='json').status_code == 403

    # --- /ask -------------------------------------------------------------

    def test_ask_success_and_audit(self):
        with _patched(text=f'{ANSWER}\n---SUGGESTIONS---\n["أ", "ب", "ج"]'):
            resp = self.client.post(
                ASK, {'question': 'ما أهم الميزات الأمنية؟', 'history': []},
                format='json',
            )
        assert resp.status_code == 200
        assert 'JWT' in resp.data['answer']
        assert '---SUGGESTIONS---' not in resp.data['answer']
        assert resp.data['suggestions'] == ['أ', 'ب', 'ج']
        assert AuditLog.objects.filter(
            event_type='AI_ASSISTANT_QUERY', user=self.admin
        ).exists()

    def test_unparseable_suggestions_fall_back_to_defaults(self):
        # Malformed model output must degrade, never 500. The bare `except:`
        # this replaced also swallowed KeyboardInterrupt and SystemExit.
        with _patched(text=f'{ANSWER}\n---SUGGESTIONS---\nnot json at all'):
            resp = self.client.post(ASK, {'question': 'س'}, format='json')
        assert resp.status_code == 200
        assert len(resp.data['suggestions']) == 3

    def test_ask_failure_returns_503_and_hides_the_upstream_error(self):
        secret = 'API key AIzaSyLEAKED at https://generativelanguage.googleapis.com'
        with _patched(error=RuntimeError(secret)):
            resp = self.client.post(ASK, {'question': 'سؤال'}, format='json')
        assert resp.status_code == 503
        assert 'AIzaSyLEAKED' not in str(resp.data)
        assert 'googleapis' not in str(resp.data)
        # The real error is kept — in the audit trail, not in the response.
        log = AuditLog.objects.filter(
            event_type='AI_ASSISTANT_FAILED', user=self.admin
        ).first()
        assert log is not None
        assert 'AIzaSyLEAKED' in str(log.details)

    def test_empty_question_rejected(self):
        resp = self.client.post(ASK, {'question': '   '}, format='json')
        assert resp.status_code == 400

    def test_overlong_question_rejected(self):
        resp = self.client.post(ASK, {'question': 'ا' * 2001}, format='json')
        assert resp.status_code == 400

    def test_history_is_sanitized_and_capped(self):
        # Garbage first, so the 10 turns the view keeps are all valid dicts —
        # this isolates capping from drop behaviour.
        history = (
            ['garbage-string', 42, None]                                     # dropped
            + [{'role': 'user', 'content': f'msg-{i}'} for i in range(20)]   # capped
        )
        sent = []
        with _patched(sent=sent):
            resp = self.client.post(
                ASK, {'question': 'س', 'history': history}, format='json'
            )
        assert resp.status_code == 200
        prompt = sent[0]
        assert prompt.count('user: msg-') == 10   # capped to MAX_HISTORY_MESSAGES
        assert 'msg-19' in prompt and 'msg-10' in prompt
        assert 'msg-9' not in prompt              # older turns dropped
        assert 'garbage-string' not in prompt     # non-dict entries dropped

    def test_unknown_history_role_coerced_and_content_truncated(self):
        sent = []
        with _patched(sent=sent):
            resp = self.client.post(ASK, {
                'question': 'س',
                'history': [{'role': 'system', 'content': 'x' * 5000}],
            }, format='json')
        assert resp.status_code == 200
        prompt = sent[0]
        assert 'system:' not in prompt            # unknown role → user
        assert 'user: ' + 'x' * 2000 in prompt
        assert 'x' * 2001 not in prompt           # truncated to 2000

    def test_malformed_history_does_not_500(self):
        # A non-dict entry used to raise AttributeError inside the view.
        with _patched():
            resp = self.client.post(
                ASK, {'question': 'س', 'history': 'not-a-list'}, format='json'
            )
        assert resp.status_code == 200

    def test_oversized_context_rejected(self):
        resp = self.client.post(
            ASK, {'question': 'س', 'context': {'blob': 'x' * 500_001}}, format='json'
        )
        assert resp.status_code == 413

    def test_patient_context_is_anonymised_before_it_leaves(self):
        sent = []
        with _patched(sent=sent):
            resp = self.client.post(ASK, {
                'question': 'ما التشخيص المحتمل؟',
                'context': {'full_name': 'أحمد علي', 'national_id': NATIONAL_ID,
                            'diagnosis': 'ارتفاع ضغط الدم'},
            }, format='json')
        assert resp.status_code == 200
        prompt = sent[0]
        assert 'أحمد علي' not in prompt
        assert NATIONAL_ID not in prompt
        assert 'ارتفاع ضغط الدم' in prompt   # clinical content still reaches the model

    def test_ask_degrades_without_an_api_key(self):
        with override_settings(GEMINI_API_KEY=''):
            resp = self.client.post(ASK, {'question': 'س'}, format='json')
        assert resp.status_code == 200
        assert 'GEMINI_API_KEY' in resp.data['answer']
        assert resp.data['suggestions']

    # --- /analyze-image ---------------------------------------------------

    def test_image_is_required(self):
        resp = self.client.post(IMAGE, {}, format='json')
        assert resp.status_code == 400

    def test_declared_mime_type_is_forwarded_not_hardcoded(self):
        sent = []
        with _patched(sent=sent, text='لا توجد كسور'):
            resp = self.client.post(
                IMAGE, {'imageBase64': f'data:image/png;base64,{PNG_B64}'},
                format='json',
            )
        assert resp.status_code == 200
        assert resp.data['analysis'] == 'لا توجد كسور'
        _prompt, image_part = sent[0]
        assert image_part['mime_type'] == 'image/png'
        assert image_part['data'] == base64.b64decode(PNG_B64)
        assert AuditLog.objects.filter(
            event_type='AI_IMAGE_ANALYSIS', user=self.admin
        ).exists()

    def test_unsupported_image_type_rejected(self):
        resp = self.client.post(
            IMAGE, {'imageBase64': f'data:image/svg+xml;base64,{PNG_B64}'},
            format='json',
        )
        assert resp.status_code == 415

    def test_invalid_base64_rejected(self):
        resp = self.client.post(IMAGE, {'imageBase64': 'not-base64!!!'}, format='json')
        assert resp.status_code == 400

    def test_oversized_image_rejected_before_decoding(self):
        # The ceiling is patched rather than exercised at its real 8MB, so the
        # bound is asserted without a multi-megabyte request body: the encoded
        # length is checked first, so nothing is ever allocated.
        with mock.patch('apps.ai.views.MAX_IMAGE_BYTES', 8):
            resp = self.client.post(IMAGE, {'imageBase64': PNG_B64}, format='json')
        assert resp.status_code == 413

    def test_image_failure_returns_503_and_audits(self):
        with _patched(error=RuntimeError('quota exceeded for project 1234')):
            resp = self.client.post(IMAGE, {'imageBase64': PNG_B64}, format='json')
        assert resp.status_code == 503
        assert 'quota' not in str(resp.data)
        assert AuditLog.objects.filter(
            event_type='AI_IMAGE_ANALYSIS_FAILED', user=self.admin
        ).exists()

    # --- /structure-note --------------------------------------------------

    def test_note_text_is_required(self):
        resp = self.client.post(NOTE, {'text': '  '}, format='json')
        assert resp.status_code == 400

    def test_overlong_note_rejected(self):
        resp = self.client.post(NOTE, {'text': 'ا' * 20_001}, format='json')
        assert resp.status_code == 413

    def test_note_is_anonymised_before_it_leaves(self):
        sent = []
        with _patched(sent=sent, text='S: صداع'):
            resp = self.client.post(
                NOTE, {'text': f'المريض يشكو من صداع، هويته {NATIONAL_ID}'},
                format='json',
            )
        assert resp.status_code == 200
        assert NATIONAL_ID not in sent[0]
        assert 'صداع' in sent[0]   # the clinical signal survives masking

    def test_note_failure_returns_503_and_audits(self):
        with _patched(error=RuntimeError('model overloaded')):
            resp = self.client.post(NOTE, {'text': 'ملاحظة'}, format='json')
        assert resp.status_code == 503
        assert AuditLog.objects.filter(
            event_type='AI_STRUCTURE_NOTE_FAILED', user=self.admin
        ).exists()

    # --- /triage ----------------------------------------------------------

    def test_triage_returns_the_parsed_level(self):
        payload = '{"level": 2, "reasoning": "ألم صدري", "recommendations": ["ECG"]}'
        with _patched(text=f'```json\n{payload}\n```'):
            resp = self.client.post(TRIAGE, {'symptoms': 'ألم في الصدر'}, format='json')
        assert resp.status_code == 200
        assert resp.data['level'] == 2
        assert resp.data['recommendations'] == ['ECG']

    def test_triage_anonymises_patient_data(self):
        sent = []
        with _patched(sent=sent, text='{"level": 3}'):
            resp = self.client.post(TRIAGE, {
                'patient': {'full_name': 'سالم', 'national_id': NATIONAL_ID},
                'symptoms': f'اتصل من الرقم {NATIONAL_ID}',
                'vitals': {'bp': '120/80'},
            }, format='json')
        assert resp.status_code == 200
        assert 'سالم' not in sent[0]
        assert NATIONAL_ID not in sent[0]
        assert '120/80' in sent[0]

    def test_triage_rejects_oversized_payload(self):
        resp = self.client.post(
            TRIAGE, {'patient': {'blob': 'x' * 500_001}}, format='json'
        )
        assert resp.status_code == 413

    def test_triage_non_object_json_returns_503_and_audits(self):
        with _patched(text='["not", "an", "object"]'):
            resp = self.client.post(TRIAGE, {'symptoms': 'حمى'}, format='json')
        assert resp.status_code == 503
        assert AuditLog.objects.filter(
            event_type='AI_TRIAGE_FAILED', user=self.admin
        ).exists()

    # --- /health ----------------------------------------------------------

    def test_health_is_public_and_reports_unavailable_without_a_key(self):
        # AllowAny: a caller deciding whether to show the assistant needs this
        # before it has a token.
        with override_settings(GEMINI_API_KEY=''):
            resp = APIClient().get(HEALTH)
        assert resp.status_code == 200
        assert resp.data['status'] == 'unavailable'
        assert resp.data['configured'] is False

    def test_health_reports_available_when_configured(self):
        with override_settings(GEMINI_API_KEY='test-key'):
            resp = self.client.get(HEALTH)
        assert resp.status_code == 200
        assert resp.data['status'] == 'available'
        assert resp.data['configured'] is True

    def test_health_does_not_disclose_the_key(self):
        with override_settings(GEMINI_API_KEY='AIzaSySHOULD-NOT-APPEAR'):
            resp = APIClient().get(HEALTH)
        assert 'AIzaSy' not in str(resp.data)


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
