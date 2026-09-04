from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.patients.models import Patient
from apps.channels.models import Channel, ChannelMembership

class PatientAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            password='password123',
            role='DOCTOR',
            full_name='Test Doctor'
        )
        self.other_doctor = User.objects.create_user(
            email='other@example.com',
            password='password123',
            role='DOCTOR',
            full_name='Other Doctor'
        )
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='password123',
            role='SUPER_ADMIN',
            full_name='Test Admin'
        )

        self.patient = Patient.objects.create(
            full_name='Test Patient',
            national_id='1234567890',
            gender='MALE'
        )

        self.channel = Channel.objects.create(
            name='Test Channel',
            owner=self.doctor,
            patient=self.patient
        )

    def test_doctor_access_own_patient(self):
        self.client.force_authenticate(user=self.doctor)
        url = reverse('patient-detail', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_doctor_denied_access(self):
        self.client.force_authenticate(user=self.other_doctor)
        url = reverse('patient-detail', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_has_full_access(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('patient-detail', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_member_doctor_has_access(self):
        ChannelMembership.objects.create(
            channel=self.channel,
            user=self.other_doctor,
            role='CONTRIBUTOR',
            granted_by=self.doctor
        )
        self.client.force_authenticate(user=self.other_doctor)
        url = reverse('patient-detail', args=[self.patient.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
