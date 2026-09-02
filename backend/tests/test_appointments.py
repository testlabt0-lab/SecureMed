"""
Tests for the Appointments app.
Covers: CRUD, calendar, conflict detection, status transitions, stats.
"""
import pytest
from datetime import timedelta, time
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.appointments.models import Appointment, AppointmentSlot
from apps.patients.models import Patient


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email='admin@test.com',
        password='Admin@2026!',
        full_name='Admin Test',
        role='SUPER_ADMIN',
        is_active=True,
    )


@pytest.fixture
def doctor_user(db):
    return User.objects.create_user(
        email='doctor@test.com',
        password='Doctor@2026!',
        full_name='Dr. Ahmed',
        role='DOCTOR',
        is_active=True,
    )


@pytest.fixture
def patient_obj(db, admin_user):
    patient = Patient(
        date_of_birth='1990-01-01',
        gender='M',
    )
    patient.full_name = 'محمد علي'
    patient.national_id = '1234567890'
    patient.save()
    return patient


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def doctor_client(doctor_user):
    client = APIClient()
    client.force_authenticate(user=doctor_user)
    return client


@pytest.fixture
def future_time():
    return timezone.now() + timedelta(hours=2)


# ─── CRUD Tests ──────────────────────────────────────────────────────────────

class TestAppointmentCRUD:

    def test_create_appointment(self, admin_client, doctor_user, patient_obj, future_time):
        """Create an appointment successfully."""
        res = admin_client.post('/api/v1/appointments/', {
            'patient': str(patient_obj.id),
            'doctor': str(doctor_user.id),
            'title': 'كشف أول',
            'appointment_type': 'INITIAL',
            'scheduled_at': future_time.isoformat(),
            'duration_minutes': 30,
            'priority': 'MEDIUM',
        })
        assert res.status_code == 201, res.data
        assert res.data['status'] == 'SCHEDULED'

    def test_create_appointment_in_past_fails(self, admin_client, doctor_user, patient_obj):
        """Cannot create an appointment in the past."""
        past_time = timezone.now() - timedelta(hours=1)
        res = admin_client.post('/api/v1/appointments/', {
            'patient': str(patient_obj.id),
            'doctor': str(doctor_user.id),
            'title': 'موعد قديم',
            'appointment_type': 'FOLLOW_UP',
            'scheduled_at': past_time.isoformat(),
            'duration_minutes': 30,
        })
        assert res.status_code == 400

    def test_list_appointments(self, admin_client, doctor_user, patient_obj, future_time, db):
        """List appointments as admin."""
        Appointment.objects.create(
            patient=patient_obj,
            doctor=doctor_user,
            title='Test Appt',
            appointment_type='FOLLOW_UP',
            scheduled_at=future_time,
            duration_minutes=30,
        )
        res = admin_client.get('/api/v1/appointments/')
        assert res.status_code == 200
        assert res.data['count'] >= 1

    def test_get_appointment_detail(self, admin_client, doctor_user, patient_obj, future_time, db):
        """Get appointment details."""
        appt = Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='Detail Test', appointment_type='CONSULTATION',
            scheduled_at=future_time, duration_minutes=45,
        )
        res = admin_client.get(f'/api/v1/appointments/{appt.id}/')
        assert res.status_code == 200
        assert res.data['title'] == 'Detail Test'

    def test_update_appointment(self, admin_client, doctor_user, patient_obj, future_time, db):
        """Update appointment title."""
        appt = Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='Original', appointment_type='FOLLOW_UP',
            scheduled_at=future_time, duration_minutes=30,
        )
        res = admin_client.patch(f'/api/v1/appointments/{appt.id}/', {'title': 'Updated'})
        assert res.status_code == 200
        assert res.data['title'] == 'Updated'

    def test_delete_appointment(self, admin_client, doctor_user, patient_obj, future_time, db):
        """Delete an appointment."""
        appt = Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='To Delete', appointment_type='FOLLOW_UP',
            scheduled_at=future_time, duration_minutes=30,
        )
        res = admin_client.delete(f'/api/v1/appointments/{appt.id}/')
        assert res.status_code == 204
        assert not Appointment.objects.filter(pk=appt.id).exists()


# ─── Status Transitions ───────────────────────────────────────────────────────

class TestAppointmentStatusTransitions:

    @pytest.fixture
    def scheduled_appt(self, db, doctor_user, patient_obj):
        return Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='Status Test', appointment_type='FOLLOW_UP',
            scheduled_at=timezone.now() + timedelta(hours=1),
            duration_minutes=30,
        )

    def test_confirm_appointment(self, admin_client, scheduled_appt):
        res = admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/confirm/')
        assert res.status_code == 200
        assert res.data['status'] == 'CONFIRMED'

    def test_start_appointment(self, admin_client, scheduled_appt):
        res = admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/start/')
        assert res.status_code == 200
        assert res.data['status'] == 'IN_PROGRESS'

    def test_complete_appointment(self, admin_client, scheduled_appt):
        admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/start/')
        res = admin_client.post(
            f'/api/v1/appointments/{scheduled_appt.id}/complete/',
            {'summary': 'اكتملت الجلسة بنجاح', 'follow_up_needed': False},
        )
        assert res.status_code == 200
        assert res.data['status'] == 'COMPLETED'

    def test_cancel_appointment(self, admin_client, scheduled_appt):
        res = admin_client.post(
            f'/api/v1/appointments/{scheduled_appt.id}/cancel/',
            {'reason': 'تعارض في المواعيد'},
        )
        assert res.status_code == 200
        assert res.data['status'] == 'CANCELLED'

    def test_cannot_cancel_completed(self, admin_client, scheduled_appt):
        admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/start/')
        admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/complete/')
        res = admin_client.post(f'/api/v1/appointments/{scheduled_appt.id}/cancel/')
        assert res.status_code == 400


# ─── Conflict Detection ───────────────────────────────────────────────────────

class TestAppointmentConflict:

    def test_double_booking_rejected(self, admin_client, doctor_user, patient_obj, db):
        """Two appointments at the same time for the same doctor should fail."""
        future = timezone.now() + timedelta(hours=3)

        # First appointment
        Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='First', appointment_type='FOLLOW_UP',
            scheduled_at=future, duration_minutes=60,
            status='SCHEDULED',
        )

        # Second at overlapping time
        res = admin_client.post('/api/v1/appointments/', {
            'patient': str(patient_obj.id),
            'doctor': str(doctor_user.id),
            'title': 'Conflicting',
            'appointment_type': 'FOLLOW_UP',
            'scheduled_at': (future + timedelta(minutes=30)).isoformat(),
            'duration_minutes': 30,
        })
        assert res.status_code == 400


# ─── Calendar View ────────────────────────────────────────────────────────────

class TestAppointmentCalendar:

    def test_calendar_returns_events(self, admin_client, doctor_user, patient_obj, db):
        future = timezone.now() + timedelta(days=1)
        Appointment.objects.create(
            patient=patient_obj, doctor=doctor_user,
            title='Calendar Event', appointment_type='INITIAL',
            scheduled_at=future, duration_minutes=30,
        )
        start = (future - timedelta(days=1)).isoformat()
        end = (future + timedelta(days=1)).isoformat()
        res = admin_client.get(f'/api/v1/appointments/calendar/?start={start}&end={end}')
        assert res.status_code == 200
        assert len(res.data) >= 1

    def test_today_endpoint(self, admin_client):
        res = admin_client.get('/api/v1/appointments/today/')
        assert res.status_code == 200
        assert 'count' in res.data

    def test_upcoming_endpoint(self, admin_client):
        res = admin_client.get('/api/v1/appointments/upcoming/')
        assert res.status_code == 200


# ─── Stats ────────────────────────────────────────────────────────────────────

class TestAppointmentStats:

    def test_stats_endpoint(self, admin_client):
        res = admin_client.get('/api/v1/appointments/stats/')
        assert res.status_code == 200
        assert 'total' in res.data
        assert 'completion_rate' in res.data
        assert 'by_status' in res.data


# ─── Availability Slots ───────────────────────────────────────────────────────

class TestAppointmentSlots:

    def test_create_slot(self, admin_client, doctor_user):
        res = admin_client.post('/api/v1/appointments/slots/', {
            'doctor': str(doctor_user.id),
            'day_of_week': 1,  # Monday
            'start_time': '09:00:00',
            'end_time': '17:00:00',
            'slot_duration_minutes': 30,
        })
        assert res.status_code == 201

    def test_list_slots(self, admin_client):
        res = admin_client.get('/api/v1/appointments/slots/')
        assert res.status_code == 200
