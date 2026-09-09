"""
Tests for the «special session» rule in `SessionManager` (4-1 / القسم 7).

The rule the plan documents: fingerprint comparison is scoped to *the
caller's own session* (via ``session_id``), not to every live session of the
user. The aggregate comparison it replaced made two ordinary events look like
hijacking — a second login evicting the caller's record (the concurrent limit
is 1), and a cache flush — and ``reject_if_hijacked`` answers a mismatch with
``force_logout_user``, so a phone whose record was evicted signed the account
out *everywhere* on its next request.

No test touched ``SessionManager`` before this file; every assertion below is
an incident report written as code.
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIRequestFactory

from apps.accounts.models import User
from apps.security.session_security import SessionManager
from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def clean_cache(db):
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def rf():
    return APIRequestFactory()


@pytest.fixture
def user(db):
    return UserFactory(role=User.Role.DOCTOR)


def _request(rf, fingerprint, path='/api/v1/auth/me/'):
    request = rf.get(path, HTTP_X_DEVICE_FINGERPRINT=fingerprint)
    request.user = None  # set per-test when needed
    return request


def _register(user_id, session_id, fingerprint):
    """Drop a session record into the cache the way login does."""
    sessions = cache.get(f'active_sessions:{user_id}', [])
    sessions = [s for s in sessions if s.get('session_id') != session_id]
    sessions.append({
        'session_id': session_id,
        'device_fingerprint': fingerprint,
        'timestamp': 0,
        'ip_address': '10.0.0.9',
    })
    cache.set(f'active_sessions:{user_id}', sessions, timeout=86400)


@pytest.mark.django_db
class TestScopedSessionValidation:
    def test_matching_own_session_is_valid(self, rf, user):
        _register(user.id, 's1', 'F1')
        request = _request(rf, 'F1')

        assert SessionManager.is_session_valid(user, request, session_id='s1') is True
        assert SessionManager.reject_if_hijacked(user, request, session_id='s1') is False

    def test_mismatch_on_own_session_is_rejected_and_force_logs_out(self, rf, user):
        _register(user.id, 's1', 'F1')
        request = _request(rf, 'F2')

        assert SessionManager.is_session_valid(user, request, session_id='s1') is False
        assert SessionManager.reject_if_hijacked(user, request, session_id='s1') is True

        # The rejection force-logs out: every session is forgotten and the
        # revocation timestamp is recorded so BoundJWTAuthentication can
        # tell revoked tokens from ones minted later.
        assert cache.get(f'active_sessions:{user.id}') is None
        assert cache.get(f'token_denylist:{user.id}') is not None

    def test_evicted_session_is_not_evidence_of_theft(self, rf, user):
        """The headline false positive: register_session keeps only the
        newest session (limit = 1). A client naming its *evicted* session
        must NOT read as a hijack — the old aggregate comparison did."""
        _register(user.id, 's1', 'F1')
        _register(user.id, 's2', 'F2')  # s1 evicted: register keeps the newest

        request = _request(rf, 'F1')
        assert SessionManager.is_session_valid(user, request, session_id='s1') is True

    def test_cache_flush_is_not_evidence_of_theft(self, rf, user):
        _register(user.id, 's1', 'F1')
        cache.clear()  # Redis restart, memory cache eviction, etc.

        request = _request(rf, 'F1')
        assert SessionManager.is_session_valid(user, request, session_id='s1') is True

    def test_no_fingerprint_header_is_valid(self, rf, user):
        _register(user.id, 's1', 'F1')
        request = rf.get('/api/v1/auth/me/')  # no X-Device-Fingerprint at all

        assert SessionManager.is_session_valid(user, request, session_id='s1') is True

    def test_session_registered_without_fingerprint_is_valid(self, rf, user):
        # A client that does not send the header registered this session.
        cache.set(
            f'active_sessions:{user.id}',
            [{'session_id': 's1', 'device_fingerprint': '', 'timestamp': 0, 'ip_address': ''}],
            timeout=86400,
        )
        request = _request(rf, 'F1')

        assert SessionManager.is_session_valid(user, request, session_id='s1') is True

    def test_unauthenticated_caller_is_valid(self, rf, db):
        request = _request(rf, 'F1')

        assert SessionManager.is_session_valid(None, request) is True


@pytest.mark.django_db
class TestSessionLifecycle:
    def test_register_denies_the_previous_session(self, rf, user):
        request = _request(rf, 'F2')
        request.user = user

        SessionManager.register_session(user, request, token={'jti': 's1'})
        SessionManager.register_session(user, request, token={'jti': 's2'})

        assert SessionManager.is_session_denied('s1') is True
        assert SessionManager.is_session_denied('s2') is False
        assert SessionManager.is_session_denied('') is False

    def test_end_session_removes_only_that_session(self, user):
        _register(user.id, 's1', 'F1')
        _register(user.id, 's2', 'F2')

        SessionManager.end_session(user.id, 's1')

        assert SessionManager.is_session_denied('s1') is True
        remaining = cache.get(f'active_sessions:{user.id}', [])
        assert [s['session_id'] for s in remaining] == ['s2']

    def test_end_session_clears_the_key_when_nothing_remains(self, user):
        _register(user.id, 's1', 'F1')

        SessionManager.end_session(user.id, 's1')

        assert cache.get(f'active_sessions:{user.id}') is None
        assert SessionManager.is_session_denied('s1') is True

    def test_end_session_without_an_id_is_a_no_op(self, user):
        _register(user.id, 's1', 'F1')

        SessionManager.end_session(user.id, '')

        assert SessionManager.is_session_denied('s1') is False
        assert cache.get(f'active_sessions:{user.id}') is not None

    def test_force_logout_forgets_sessions_and_records_revocation(self, user):
        _register(user.id, 's1', 'F1')

        SessionManager.force_logout_user(user.id)

        assert cache.get(f'active_sessions:{user.id}') is None
        assert cache.get(f'token_denylist:{user.id}') is not None
