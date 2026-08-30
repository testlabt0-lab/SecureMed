"""
Integration tests for the complete secure workflow.
Tests the full flow: login -> create channel -> grant permissions -> access data.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.channels.models import Channel, ChannelMembership
from apps.patients.models import Patient
from tests.factories import UserFactory, PatientFactory, AdminUserFactory


@pytest.mark.django_db
class TestEndToEndWorkflow:
    """End-to-end tests for the complete secure workflow."""

    def setup_method(self):
        self.client = APIClient()

    def test_full_medical_workflow(self):
        """Test the complete medical workflow from login to record access."""
        # 1. Create a doctor (will be the channel owner)
        doctor = UserFactory(role=User.Role.DOCTOR, email='doctor@securemed.test')
        doctor.set_password('DoctorPass123!')
        doctor.save()

        # 2. Create a nurse (will be a member)
        nurse = UserFactory(role=User.Role.NURSE, email='nurse@securemed.test')
        nurse.set_password('NursePass123!')
        nurse.save()

        # 3. Doctor logs in
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'doctor@securemed.test',
            'password': 'DoctorPass123!',
        }, format='json')
        assert response.status_code == 200
        doctor_token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor_token}')

        # 4. Doctor creates a patient
        response = self.client.post('/api/v1/patients/', {
            'full_name': 'Patient One',
            'date_of_birth': '1985-03-20',
            'gender': 'M',
            'blood_type': 'O+',
            'phone': '+966500000001',
        }, format='json')
        assert response.status_code == 201
        patient_id = response.data['id']

        # 5. Doctor creates a channel (patient case)
        response = self.client.post('/api/v1/channels/', {
            'name': 'Case: Patient One',
            'description': 'Routine checkup',
            'channel_type': 'OUTPATIENT',
            'priority': 'MEDIUM',
            'patient': patient_id,
        }, format='json')
        assert response.status_code == 201
        channel_id = response.data['id']

        # 6. Doctor grants VIEWER permission to nurse
        response = self.client.post(f'/api/v1/channels/{channel_id}/grant_permission/', {
            'user_email': 'nurse@securemed.test',
            'role': 'VIEWER',
        }, format='json')
        assert response.status_code == 201

        # 7. Nurse logs in
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'nurse@securemed.test',
            'password': 'NursePass123!',
        }, format='json')
        assert response.status_code == 200
        nurse_token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {nurse_token}')

        # 8. Nurse can see the channel
        response = self.client.get('/api/v1/channels/')
        assert response.status_code == 200
        # With pagination, response.data is a dict with 'results'
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        channel_ids = [c['id'] for c in results]
        assert channel_id in channel_ids

        # 9. Nurse's role is VIEWER (single role - DV requirement)
        response = self.client.get(f'/api/v1/channels/{channel_id}/')
        assert response.status_code == 200
        assert response.data['current_user_role'] == 'VIEWER'

        # 10. Stranger cannot see the channel
        stranger = UserFactory(role=User.Role.DOCTOR, email='stranger@securemed.test')
        stranger.set_password('StrangerPass123!')
        stranger.save()

        response = self.client.post('/api/v1/auth/login/', {
            'email': 'stranger@securemed.test',
            'password': 'StrangerPass123!',
        }, format='json')
        stranger_token = response.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {stranger_token}')

        response = self.client.get(f'/api/v1/channels/{channel_id}/')
        assert response.status_code == 404  # Cannot see what they're not member of

    def test_security_tools_workflow(self):
        """Test the security tools are accessible to admin."""
        admin = AdminUserFactory()
        admin.set_password('AdminPass123!')
        admin.save()
        self.client.force_authenticate(user=admin)

        # Port scan
        response = self.client.post('/api/v1/security/port-scanner/', {
            'target': 'localhost',
            'ports': [80, 443, 8000],
        }, format='json')
        assert response.status_code == 200

        # Vulnerability scan
        response = self.client.post('/api/v1/security/vulnerability-scanner/', {}, format='json')
        assert response.status_code == 200

        # Security dashboard
        response = self.client.get('/api/v1/security/dashboard/')
        assert response.status_code == 200

    def test_waf_protection_workflow(self):
        """Test that WAF blocks malicious requests."""
        # Use authenticated client
        admin = AdminUserFactory()
        admin.set_password('AdminPass123!')
        admin.save()
        self.client.force_authenticate(user=admin)

        # SQL injection attempt
        response = self.client.get('/api/v1/channels/?search=%27%20OR%20%271%27%3D%271')
        assert response.status_code == 403

        # XSS attempt
        response = self.client.get('/api/v1/channels/?search=%3Cscript%3Ealert%281%29%3C%2Fscript%3E')
        assert response.status_code == 403
