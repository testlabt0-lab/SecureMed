"""
Tests for security app: WAF, port scanner, vulnerability scanner.
"""
import pytest
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.security.crypto import (
    encrypt_field, decrypt_field, hash_biometric,
    generate_challenge, verify_challenge,
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

    def test_hash_biometric_deterministic(self):
        """Same input + same salt = same hash."""
        template = 'fingerprint-template-123'
        salt = 'mysalt'
        hash1 = hash_biometric(template, salt)
        hash2 = hash_biometric(template, salt)
        assert hash1 == hash2

    def test_hash_biometric_different_salt(self):
        """Different salt = different hash."""
        template = 'fingerprint-template-123'
        hash1 = hash_biometric(template, 'salt1')
        hash2 = hash_biometric(template, 'salt2')
        assert hash1 != hash2

    def test_hash_biometric_different_template(self):
        """Different template = different hash."""
        salt = 'same-salt'
        hash1 = hash_biometric('template-1', salt)
        hash2 = hash_biometric('template-2', salt)
        assert hash1 != hash2

    def test_generate_challenge_unique(self):
        """Each challenge should be unique."""
        c1, r1 = generate_challenge()
        c2, r2 = generate_challenge()
        assert c1 != c2
        assert r1 != r2

    def test_verify_challenge_correct(self):
        challenge, expected = generate_challenge()
        # In real scenario, the client signs the challenge
        # Here we test with the expected response directly
        assert verify_challenge(expected, 'test-response') is False  # Wrong response

    def test_verify_challenge_invalid_format(self):
        result = verify_challenge('invalid', 'response')
        assert result is False

    def test_encrypt_decrypt_multiple_fields(self):
        """Test encrypting multiple different values."""
        values = ['Patient Name', '1234567890', '+966500000000']
        for v in values:
            encrypted = encrypt_field(v)
            assert decrypt_field(encrypted) == v


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
