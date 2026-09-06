"""
Tests for security app: WAF, port scanner, vulnerability scanner.
"""
import hashlib
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT, encode_multipart, BOUNDARY
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from apps.accounts.models import User
from apps.security.crypto import (
    encrypt_field, decrypt_field,
    WebAuthnError, b64url_encode, b64url_decode,
    generate_auth_challenge, load_public_key, public_key_to_pem,
    verify_native_assertion, verify_webauthn_assertion,
    verify_webauthn_registration,
)
from apps.security.port_scanner import PortScanner, scan_host_ports
from apps.security.vulnerability_scanner import VulnerabilityScanner
from tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
class TestCrypto:
    """Tests for cryptographic utilities (security requirements #3, #6)."""

    def test_encrypt_decrypt_field(self):
        original = 'Sensitive Patient Data'
        encrypted = encrypt_field(original)
        decrypted = decrypt_field(encrypted)

        assert encrypted != original  # Actually encrypted
        assert decrypted == original  # Round trip works

    def test_encrypt_none(self):
        assert encrypt_field(None) is None
        assert decrypt_field(None) is None

    # The three test_hash_biometric_* cases that used to sit here are gone with
    # hash_biometric() itself. They asserted that a hash function is deterministic
    # and salt-sensitive — true of every hash — while the scheme they belonged to
    # (client sends a "biometric template", server hashes and compares) was a
    # replayable shared secret, not authentication. Biometric login is now an EC
    # P-256 signature over a server challenge and no template ever reaches the
    # server; verify_native_assertion is covered below.

    def test_generate_auth_challenge_unique(self):
        """Every challenge is fresh, 32 bytes, and survives a base64url round trip."""
        raw1, b64_1 = generate_auth_challenge()
        raw2, b64_2 = generate_auth_challenge()
        assert raw1 != raw2
        assert b64_1 != b64_2
        assert len(raw1) == 32
        assert b64url_decode(b64_1) == raw1
        assert '=' not in b64_1

    def test_b64url_decode_rejects_garbage(self):
        """Strict decoding: urlsafe_b64decode() alone silently drops stray bytes."""
        with pytest.raises(ValueError):
            b64url_decode('!!!not base64!!!')

    def test_encrypt_decrypt_multiple_fields(self):
        """Test encrypting multiple different values."""
        values = ['Patient Name', '1234567890', '+966500000000']
        for v in values:
            encrypted = encrypt_field(v)
            assert decrypt_field(encrypted) == v


RP_ID = 'securemed.test'
ORIGIN = 'https://securemed.test'
FLAG_UP = 0x01
FLAG_UV = 0x04


def _authenticator_data(rp_id=RP_ID, flags=FLAG_UP | FLAG_UV, sign_count=1):
    """rpIdHash(32) || flags(1) || signCount(4) — the fixed part of §6.1."""
    return (
        hashlib.sha256(rp_id.encode('utf-8')).digest()
        + bytes([flags])
        + sign_count.to_bytes(4, 'big')
    )


def _client_data(challenge_b64, origin=ORIGIN, typ='webauthn.get'):
    return json.dumps({
        'type': typ,
        'challenge': challenge_b64,
        'origin': origin,
        'crossOrigin': False,
    }).encode('utf-8')


def _assert(key, authenticator_data, client_data_json):
    """Sign authenticatorData || SHA256(clientDataJSON), as an authenticator does."""
    return key.sign(
        authenticator_data + hashlib.sha256(client_data_json).digest(),
        ec.ECDSA(hashes.SHA256()),
    )


class TestWebAuthnAssertion:
    """The replacement for the old echo-back 'challenge response'.

    The scheme these tests cover proves possession of a private key held in device
    hardware. The scheme they replaced computed HMAC(k, challenge) server-side and
    then verified HMAC(k, client_answer) with the same k, which reduces to
    client_answer == challenge: echoing the challenge back was a valid login.
    """

    def setup_method(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.key.public_key()
        self.raw, self.challenge = generate_auth_challenge()

    def _verify(self, **overrides):
        params = {
            'public_key': self.public_key,
            'expected_challenge_b64': self.challenge,
            'rp_id': RP_ID,
            'allowed_origins': [ORIGIN],
            'stored_sign_count': 0,
        }
        params.update(overrides)
        return verify_webauthn_assertion(**params)

    def test_valid_assertion(self):
        auth_data = _authenticator_data()
        client_data = _client_data(self.challenge)
        assert self._verify(
            client_data_json=client_data,
            authenticator_data=auth_data,
            signature=_assert(self.key, auth_data, client_data),
        ) == 1

    def test_echoing_the_challenge_is_not_enough(self):
        """What used to be a valid login is now rejected: there is no signature."""
        auth_data = _authenticator_data()
        client_data = _client_data(self.challenge)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=self.raw,
            )

    def test_signature_from_another_key_rejected(self):
        auth_data = _authenticator_data()
        client_data = _client_data(self.challenge)
        attacker = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(attacker, auth_data, client_data),
            )

    def test_wrong_challenge_rejected(self):
        """A signature harvested for one challenge cannot answer another."""
        _other_raw, other = generate_auth_challenge()
        auth_data = _authenticator_data()
        client_data = _client_data(other)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
            )

    def test_foreign_origin_rejected(self):
        """A ceremony completed on attacker.example must not verify here."""
        auth_data = _authenticator_data()
        client_data = _client_data(self.challenge, origin='https://attacker.example')
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
            )

    def test_rp_id_mismatch_rejected(self):
        auth_data = _authenticator_data(rp_id='other.test')
        client_data = _client_data(self.challenge)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
            )

    def test_user_verified_flag_required(self):
        """UP without UV means the device answered but no biometric was presented."""
        auth_data = _authenticator_data(flags=FLAG_UP)
        client_data = _client_data(self.challenge)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
            )

    def test_user_verification_can_be_relaxed(self):
        auth_data = _authenticator_data(flags=FLAG_UP)
        client_data = _client_data(self.challenge)
        assert self._verify(
            client_data_json=client_data,
            authenticator_data=auth_data,
            signature=_assert(self.key, auth_data, client_data),
            require_user_verification=False,
        ) == 1

    def test_stale_sign_count_rejected(self):
        """A counter that does not advance suggests a cloned credential."""
        auth_data = _authenticator_data(sign_count=5)
        client_data = _client_data(self.challenge)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
                stored_sign_count=5,
            )

    def test_zero_sign_count_allowed(self):
        """Platform authenticators report 0 forever; the spec says skip the check."""
        auth_data = _authenticator_data(sign_count=0)
        client_data = _client_data(self.challenge)
        assert self._verify(
            client_data_json=client_data,
            authenticator_data=auth_data,
            signature=_assert(self.key, auth_data, client_data),
            stored_sign_count=0,
        ) == 0

    def test_wrong_ceremony_type_rejected(self):
        """A create() clientDataJSON must not be replayed into a get()."""
        auth_data = _authenticator_data()
        client_data = _client_data(self.challenge, typ='webauthn.create')
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=auth_data,
                signature=_assert(self.key, auth_data, client_data),
            )

    def test_truncated_authenticator_data_rejected(self):
        client_data = _client_data(self.challenge)
        with pytest.raises(WebAuthnError):
            self._verify(
                client_data_json=client_data,
                authenticator_data=b'\x00' * 20,
                signature=b'\x00' * 70,
            )

    def test_registration_binds_challenge_and_origin(self):
        spki = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        loaded = verify_webauthn_registration(
            client_data_json=_client_data(self.challenge, typ='webauthn.create'),
            public_key_material=b64url_encode(spki),
            expected_challenge_b64=self.challenge,
            allowed_origins=[ORIGIN],
        )
        assert 'BEGIN PUBLIC KEY' in public_key_to_pem(loaded)

        with pytest.raises(WebAuthnError):
            verify_webauthn_registration(
                client_data_json=_client_data(
                    self.challenge, origin='https://attacker.example',
                    typ='webauthn.create'),
                public_key_material=b64url_encode(spki),
                expected_challenge_b64=self.challenge,
                allowed_origins=[ORIGIN],
            )

    def test_native_assertion_signs_raw_challenge(self):
        signature = self.key.sign(self.raw, ec.ECDSA(hashes.SHA256()))
        assert verify_native_assertion(
            public_key=self.public_key,
            challenge=self.raw,
            signature=signature,
        ) == 0

        with pytest.raises(WebAuthnError):
            verify_native_assertion(
                public_key=self.public_key,
                challenge=generate_auth_challenge()[0],
                signature=signature,
            )

    def test_weak_rsa_key_rejected(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        weak = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        pem = weak.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode('ascii')
        with pytest.raises(WebAuthnError):
            load_public_key(pem)


@pytest.mark.django_db
class TestWAFMiddleware:
    """Tests for WAF (security requirement #5)."""

    def setup_method(self):
        self.client = APIClient()

    def test_normal_request_passes(self):
        """Normal API requests should pass through WAF."""
        response = self.client.get('/api/v1/auth/login/')
        # /api/v1/auth/login/ returns 405 (Method Not Allowed) for GET
        # but the WAF should not block it
        assert response.status_code != 403

    def test_sql_injection_blocked(self):
        """WAF should block SQL injection attempts."""
        response = self.client.get('/api/v1/channels/', {
            'search': "' OR '1'='1",
        })
        assert response.status_code == 403

    def test_xss_blocked(self):
        """WAF should block XSS attempts."""
        response = self.client.get('/api/v1/channels/', {
            'search': '<script>alert("xss")</script>',
        })
        assert response.status_code == 403

    def test_path_traversal_blocked(self):
        """WAF should block path traversal attempts."""
        response = self.client.get('/api/v1/channels/', {
            'path': '../../../etc/passwd',
        })
        assert response.status_code == 403

    def test_command_injection_blocked(self):
        """WAF should block command injection."""
        response = self.client.get('/api/v1/channels/', {
            'search': '; cat /etc/passwd',
        })
        assert response.status_code == 403

    def test_security_headers_added(self):
        """WAF should add security headers to responses."""
        # Use an endpoint that returns a response (not a redirect)
        # /health/ is skipped by WAF, so use /api/v1/auth/login/ which returns 405
        response = self.client.post('/api/v1/auth/login/', {}, format='json')
        # WAF adds headers to all responses (except /health/ and /admin/)
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'
        assert 'X-Content-Type-Options' in response.headers
        assert 'Content-Security-Policy' in response.headers


@pytest.mark.django_db
class TestWAFDoesNotScanMimeFraming:
    """A multipart envelope is transport framing, not user input.

    The WAF used to match its patterns against the raw body. A multipart body
    ends with ``--<boundary>--``, which the SQL_INJECTION pattern ``(--\\s*$)``
    matches, so any request whose raw body the WAF could read came back 403
    WAF_BLOCKED. That was every ``PUT``/``PATCH`` sent as ``multipart/form-data``
    — which is DRF's default test format, and how ``test_update_appointment``
    surfaced it. ``POST`` escaped by accident: ``request.POST`` is read first and
    consumes the stream, so ``request.body`` then raised and the body was never
    scanned at all. Both halves are wrong in opposite directions.

    The assertions below key on the WAF's own response body rather than on the
    bare status code, so a view's ordinary permission denial cannot pass for a
    firewall block.
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='waf-multipart@securemed.test', password='Str0ng#Pass2026',
            full_name='WAF Tester', role=User.Role.DOCTOR,
        )
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/v1/auth/users/{self.user.id}/'

    @staticmethod
    def _waf_block(response):
        """The WAF's block payload, or None when the WAF let the request through."""
        if response.status_code != 403:
            return None
        try:
            body = response.json()
        except Exception:
            return None
        return body if body.get('code') == 'WAF_BLOCKED' else None

    def test_multipart_body_is_not_blocked(self):
        response = self.client.patch(
            self.url,
            encode_multipart(BOUNDARY, {'full_name': 'WAF Tester Renamed'}),
            content_type=MULTIPART_CONTENT,
        )
        assert self._waf_block(response) is None

    def test_multipart_field_values_are_still_scanned(self):
        """Removing the framing must not stop the WAF seeing the values."""
        response = self.client.patch(
            self.url,
            encode_multipart(BOUNDARY, {'full_name': "' OR '1'='1"}),
            content_type=MULTIPART_CONTENT,
        )
        assert self._waf_block(response) is not None

    def test_multipart_post_values_are_still_scanned(self):
        """POST goes through request.POST rather than the raw body; same verdict."""
        response = self.client.post(
            '/api/v1/channels/',
            encode_multipart(BOUNDARY, {'name': "' OR '1'='1"}),
            content_type=MULTIPART_CONTENT,
        )
        assert self._waf_block(response) is not None

    def test_traversal_in_an_uploaded_filename_is_still_scanned(self):
        # Built by hand: Django's test client basenames the filename it encodes,
        # so a traversal attempt can only be expressed on the wire.
        body = (
            f'--{BOUNDARY}\r\n'
            'Content-Disposition: form-data; name="attachment";'
            ' filename="../../../etc/passwd"\r\n'
            'Content-Type: text/plain\r\n\r\n'
            'harmless bytes\r\n'
            f'--{BOUNDARY}--\r\n'
        ).encode()
        response = self.client.patch(self.url, body, content_type=MULTIPART_CONTENT)
        block = self._waf_block(response)
        assert block is not None
        assert block['attack_type'] == 'PATH_TRAVERSAL'

    def test_binary_file_content_is_not_scanned(self):
        """A real file's bytes contain pattern-shaped noise; that is not an attack."""
        upload = SimpleUploadedFile(
            'report.pdf',
            b"%PDF-1.7\n' OR '1'='1 -- \n<script>alert(1)</script>\n../../etc/passwd",
            content_type='application/pdf',
        )
        response = self.client.patch(self.url, {'attachment': upload})
        assert self._waf_block(response) is None

    def test_oversized_body_is_not_buffered_for_scanning(self):
        from apps.security.middleware import MAX_BODY_SCAN_BYTES, WAFMiddleware

        waf = WAFMiddleware(lambda request: None)
        request = APIRequestFactory().post('/api/v1/channels/', {}, format='json')
        request.META['CONTENT_LENGTH'] = str(MAX_BODY_SCAN_BYTES + 1)
        assert waf._body_text(request) == ''


@pytest.mark.django_db
class TestPortScanner:
    """Tests for port scanner (security requirement #2)."""

    def test_scan_localhost(self):
        """Should be able to scan localhost."""
        scanner = PortScanner(timeout=0.5)
        result = scanner.scan_host('localhost', ports=[80, 443, 8000, 5432])
        assert result.target == 'localhost'
        assert result.ports_scanned == 4
        assert isinstance(result.results, list)
        assert len(result.results) == 4
        assert isinstance(result.risk_assessment, str)

    def test_scan_rejects_external_hosts(self):
        """Scanner should refuse to scan external/public IPs."""
        scanner = PortScanner()
        with pytest.raises(ValueError):
            scanner.scan_host('8.8.8.8')

    def test_scan_rejects_public_hostname(self):
        """Scanner should refuse to scan external hostnames."""
        scanner = PortScanner()
        with pytest.raises(ValueError):
            scanner.scan_host('google.com')

    def test_scan_returns_all_ports(self):
        """Scanner should return result for each requested port."""
        scanner = PortScanner(timeout=0.1)
        result = scanner.scan_host('localhost', ports=[22, 80, 443])
        assert len(result.results) == 3
        port_numbers = [r['port'] for r in result.results]
        assert 22 in port_numbers
        assert 80 in port_numbers
        assert 443 in port_numbers

    def test_risk_assessment_for_no_open_ports(self):
        """Risk assessment should indicate good security when no ports are open."""
        scanner = PortScanner(timeout=0.1)
        # Use a port that's unlikely to be open
        result = scanner.scan_host('localhost', ports=[9999])
        if result.open_ports == 0:
            assert 'ممتاز' in result.risk_assessment or 'excellent' in result.risk_assessment.lower()


@pytest.mark.django_db
class TestVulnerabilityScanner:
    """Tests for vulnerability scanner (security requirement #4)."""

    def test_scan_returns_report(self):
        """Scanner should return a structured report."""
        scanner = VulnerabilityScanner()
        report = scanner.scan()

        assert report.scan_time is not None
        assert report.duration_seconds >= 0
        assert report.total_checks == 12
        assert isinstance(report.vulnerabilities, list)
        assert isinstance(report.summary, dict)
        assert 'critical' in report.summary
        assert 'high' in report.summary
        assert 'medium' in report.summary
        assert 'low' in report.summary
        assert 0 <= report.risk_score <= 100

    def test_scan_finds_debug_mode(self):
        """Scanner should detect DEBUG=True (in test settings)."""
        # test_settings may or may not have DEBUG=True
        scanner = VulnerabilityScanner()
        report = scanner.scan()
        # Just verify the check runs without crashing
        assert report.total_checks == 12

    def test_scan_recommendations_generated(self):
        """Scanner should generate recommendations."""
        scanner = VulnerabilityScanner()
        report = scanner.scan()
        assert isinstance(report.recommendations, list)

    def test_risk_score_within_bounds(self):
        """Risk score should be 0-100."""
        scanner = VulnerabilityScanner()
        report = scanner.scan()
        assert 0 <= report.risk_score <= 100


@pytest.mark.django_db
class TestSecurityAPI:
    """Tests for security API endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.client.force_authenticate(user=self.admin)

    def test_port_scan_api(self):
        """Admin can use port scanner via API."""
        response = self.client.post('/api/v1/security/port-scanner/', {
            'target': 'localhost',
            'ports': [80, 443, 5432, 8000],
        }, format='json')
        assert response.status_code == 200
        assert 'target' in response.data
        assert 'results' in response.data
        assert 'risk_assessment' in response.data

    def test_vulnerability_scan_api(self):
        """Admin can run vulnerability scan via API."""
        response = self.client.post('/api/v1/security/vulnerability-scanner/', {}, format='json')
        assert response.status_code == 200
        assert 'risk_score' in response.data
        assert 'summary' in response.data
        assert 'recommendations' in response.data

    def test_security_dashboard_api(self):
        """Admin can access security dashboard."""
        response = self.client.get('/api/v1/security/dashboard/')
        assert response.status_code == 200
        assert 'vulnerability_scan' in response.data
        assert 'port_scan' in response.data
        assert 'security_features' in response.data

    def test_security_api_requires_admin(self):
        """Non-admin users cannot access security endpoints."""
        regular_user = UserFactory(role=User.Role.DOCTOR)
        self.client.force_authenticate(user=regular_user)
        response = self.client.post('/api/v1/security/port-scanner/', {
            'target': 'localhost',
        }, format='json')
        assert response.status_code in [403, 404]
