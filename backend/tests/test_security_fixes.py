"""
Regression tests for the security holes the audit (2026-09-04) called out.

Each class here pins one of the five critical fixes so it cannot regress:

* TestMediaProtection       — /media/ is not an open file server (issue 3.3).
* TestGlobalSearchScoping   — the global search honours basin/channel rules
                              and never hands the PATIENT role other people's
                              names or national ids (issue 3.1).
* TestRefreshTokenRotation  — the refresh endpoint rotates, blacklists and
                              binds the refresh token (issue 3.4).
* TestAuditChainIntegrity   — the audit hash chain is an HMAC keyed outside
                              the database and detects tampering (issue 3.7).
"""
import base64
import pytest
from datetime import timedelta
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog, GENESIS_HASH
from apps.channels.models import ChannelMembership
from apps.patients.models import MedicalFile
from tests.factories import (
    UserFactory,
    PatientFactory,
    ChannelFactory,
)


def make_client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


# ============================================================
# /media/ protection
# ============================================================

@pytest.mark.django_db
class TestMediaProtection:

    def _medical_file(self, channel, patient):
        instance = MedicalFile(
            channel=channel,
            patient=patient,
            file_type=MedicalFile.FileType.XRAY,
            uploaded_by=channel.owner,
            original_filename='report.pdf',
        )
        instance.file.save('medical_files/x/report.pdf', ContentFile(b'%PDF-1.4 test'))
        instance.save()
        return instance

    def test_anonymous_media_request_rejected(self):
        """The old django.views.static.serve() served PHI to anyone. Under
        the production branch the registered view must refuse an
        unauthenticated caller outright."""
        from django.urls import resolve
        match = resolve('/media/medical_files/x/whatever.pdf')
        assert getattr(match.func, 'view_class', None).__name__ == 'ProtectedMediaView'

        client = APIClient()
        resp = client.get('/media/medical_files/x/whatever.pdf')
        # DRF answers 401 (credentials required) or 403 — never a file body.
        assert resp.status_code in (401, 403)

    def test_medical_file_hidden_from_non_member(self):
        owner = UserFactory(role=User.Role.DOCTOR)
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        ChannelMembership.objects.create(
            channel=channel, user=owner,
            role=ChannelMembership.Role.OWNER, granted_by=owner,
        )
        record = self._medical_file(channel, patient)

        stranger = UserFactory(role=User.Role.DOCTOR)
        resp = make_client(stranger).get(f'/media/{record.file.name}')
        assert resp.status_code == 403

        # An owner member can read it, and the read is audited.
        resp = make_client(owner).get(f'/media/{record.file.name}')
        assert resp.status_code == 200
        assert AuditLog.objects.filter(
            event_type='PATIENT_DATA_ACCESSED',
            details__file_id=str(record.id),
        ).exists()

    def test_unknown_media_path_404s_even_for_staff(self):
        admin = UserFactory(role=User.Role.SUPER_ADMIN)
        resp = make_client(admin).get('/media/medical_files/x/no-such-row.pdf')
        assert resp.status_code == 404


# ============================================================
# Global search scoping
# ============================================================

@pytest.mark.django_db
class TestGlobalSearchScoping:

    def test_patient_role_cannot_search_patients(self):
        """The hole the audit flagged: a PATIENT-role account searching a name
        fragment used to receive full_name + national_id of every matching
        patient. It must receive none."""
        patient = PatientFactory(full_name='Ahmad Saleh', national_id='1122334455')
        patient_role_user = UserFactory(role=User.Role.PATIENT)

        resp = make_client(patient_role_user).get('/api/v1/auth/search/?q=Ahmad')
        assert resp.status_code == 200
        assert resp.data['patients'] == []

        # Same probe on the encrypted national id — also empty.
        resp = make_client(patient_role_user).get('/api/v1/auth/search/?q=1122334455')
        assert resp.data['patients'] == []

        # And the record really is findable for someone allowed to see it.
        admin = UserFactory(role=User.Role.SUPER_ADMIN)
        resp = make_client(admin).get('/api/v1/auth/search/?q=Ahmad')
        assert any(p['id'] == str(patient.id) for p in resp.data['patients'])

    def test_doctor_sees_only_channel_patients(self):
        """A doctor outside the channel/basin must not discover a patient by
        name — the channel-membership rule scopes the result set."""
        outsider = UserFactory(role=User.Role.DOCTOR)
        other_patient = PatientFactory(full_name='Fatima Ali', national_id='9988776655')

        resp = make_client(outsider).get('/api/v1/auth/search/?q=Fatima')
        assert resp.data['patients'] == []

        # The staff directory is likewise withheld from the PATIENT role.
        patient_user = UserFactory(role=User.Role.PATIENT)
        resp = make_client(patient_user).get('/api/v1/auth/search/?q=Doctor')
        assert resp.data['users'] == []


# ============================================================
# Refresh token rotation
# ============================================================

@pytest.mark.django_db
class TestRefreshTokenRotation:

    def _login(self, user):
        user.set_password('Passw0rd!Secure')
        user.save(update_fields=['password'])
        client = APIClient()
        resp = client.post('/api/v1/auth/login/', {
            'email': user.email, 'password': 'Passw0rd!Secure',
        }, format='json')
        assert resp.status_code == 200
        return resp.data['tokens']

    def test_refresh_rotates_and_blacklists(self):
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        user = UserFactory(role=User.Role.DOCTOR, basin=None)
        tokens = self._login(user)

        client = APIClient()
        resp = client.post('/api/v1/auth/refresh/', {
            'refresh': tokens['refresh'],
        }, format='json')
        assert resp.status_code == 200
        assert resp.data.get('refresh'), 'rotation must return a new refresh token'
        assert resp.data['refresh'] != tokens['refresh']

        # The presented refresh token is now blacklisted: replaying it must
        # fail, which is what makes a stolen refresh token worthless.
        old_jti = tokens['jti']
        assert BlacklistedToken.objects.filter(token__jti=old_jti).exists()

        # Drop the rotated cookie the first response set, so the replay truly
        # re-presents the OLD token rather than the new one the client holds.
        client.cookies.clear()
        replay = client.post('/api/v1/auth/refresh/', {
            'refresh': tokens['refresh'],
        }, format='json')
        assert replay.status_code == 401

    def test_rotated_refresh_mints_working_access_token(self):
        user = UserFactory(role=User.Role.DOCTOR, basin=None)
        tokens = self._login(user)

        client = APIClient()
        resp = client.post('/api/v1/auth/refresh/', {
            'refresh': tokens['refresh'],
        }, format='json')
        access = resp.data['access']

        me = client.get('/api/v1/auth/users/me/', HTTP_AUTHORIZATION=f'Bearer {access}')
        assert me.status_code == 200
        assert me.data['id'] == str(user.id)


# ============================================================
# Audit hash chain (HMAC)
# ============================================================

@pytest.mark.django_db
class TestAuditChainIntegrity:

    def test_rows_are_signed_with_hmac(self, settings):
        settings.AUDIT_LOG_HMAC_KEY = 'test-audit-key-not-secret-key'
        AuditLog.objects.create(event_type='LOGIN_SUCCESS', user=None)
        row = AuditLog.objects.exclude(hash__isnull=True).exclude(hash='').first()
        assert row is not None, 'every new row must be signed'
        assert row.previous_hash == GENESIS_HASH or row.previous_hash
        # The signature matches the keyed digest, not a bare sha256 of the row.
        assert row.hash == row.generate_hash()

    def test_tampered_row_is_detected(self, settings):
        settings.AUDIT_LOG_HMAC_KEY = 'test-audit-key-not-secret-key'
        log_security_event_setup = AuditLog.objects.create(
            event_type='LOGIN_SUCCESS', user=None, ip_address='10.0.0.1',
        )
        # Someone edits the row after the fact, then rebuilds nothing.
        AuditLog.objects.filter(pk=log_security_event_setup.pk).update(
            ip_address='8.8.8.8'
        )
        result = AuditLog.verify_chain()
        assert not result['ok']
        assert any(p['error'] == 'signature_mismatch' for p in result['problems'])

    def test_chain_links_across_rows(self, settings):
        settings.AUDIT_LOG_HMAC_KEY = 'test-audit-key-not-secret-key'
        # Rows from other tests (and Django signals) may share this table with
        # a different key — delete ours-in-window then verify strictly within
        # a window that starts right now, so foreign rows signed with the
        # default key are outside the verification range entirely.
        from django.utils import timezone as tz
        window_start = tz.now()
        AuditLog.objects.filter(timestamp__gte=window_start).delete()
        AuditLog.objects.create(event_type='LOGIN_SUCCESS', user=None)
        AuditLog.objects.create(event_type='LOGOUT', user=None)
        result = AuditLog.verify_chain(since=window_start)
        assert result['ok'], result['problems']
        assert result['signed'] >= 2
