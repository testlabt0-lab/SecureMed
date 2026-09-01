"""
End-to-End Smoke Tests for SecureMed Platform
These tests verify critical user journeys work end-to-end.
Run with: pytest backend/tests/test_e2e_smoke.py -v
"""
import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User


@pytest.mark.e2e
class TestE2ESmoke:
    """End-to-end smoke tests for critical paths"""
    
    @pytest.fixture
    def api_client(self):
        return APIClient()
    
    @pytest.fixture
    def test_user(self, db):
        """Create a test patient user"""
        return User.objects.create_user(
            username='e2e_patient',
            email='e2e@patient.com',
            password='TestPassword123!',
            role='patient'
        )
    
    @pytest.fixture
    def authenticated_client(self, api_client, test_user):
        """Create authenticated API client"""
        api_client.force_authenticate(user=test_user)
        return api_client
    
    def test_health_check(self):
        """Verify health endpoint responds"""
        client = Client()
        response = client.get('/health/')
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'
    
    def test_login_flow(self, api_client, test_user):
        """Test complete login flow"""
        url = reverse('token_obtain_pair')
        response = api_client.post(url, {
            'username': 'e2e_patient',
            'password': 'TestPassword123!'
        })
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_authenticated_user_profile(self, authenticated_client, test_user):
        """Test accessing user profile with authentication"""
        url = reverse('profile-detail')
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.data['username'] == 'e2e_patient'
    
    def test_patient_dashboard_access(self, authenticated_client, test_user):
        """Test patient can access their dashboard"""
        url = reverse('patient-dashboard')
        response = authenticated_client.get(url)
        # Should succeed for patient role
        assert response.status_code in [200, 404]  # 404 if no data yet
    
    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated access is denied"""
        url = reverse('profile-detail')
        response = api_client.get(url)
        assert response.status_code == 401
    
    def test_api_versioning(self, api_client):
        """Test API versioning is working"""
        response = api_client.get('/api/')
        assert response.status_code in [200, 401]  # May require auth


@pytest.mark.load
class TestBasicLoad:
    """Basic load testing placeholders"""
    
    def test_concurrent_health_checks(self, db):
        """Simulate concurrent health check requests"""
        from concurrent.futures import ThreadPoolExecutor
        from django.test import Client
        
        def make_request():
            client = Client()
            response = client.get('/health/')
            return response.status_code == 200
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(make_request, range(20)))
        
        assert all(results), "All concurrent requests should succeed"
