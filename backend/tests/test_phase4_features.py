"""
Tests for Phase 4 features:
- Channel chat (messages API)
- Global search
- Two-factor authentication (TOTP)
- Biometric device management
- Patient full profile
- Reports (channel PDF / audit Excel / monthly PDF)
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, BiometricProfile
from apps.audit.models import AuditLog
from apps.channels.models import Channel, ChannelMembership
from tests.factories import UserFactory, PatientFactory, ChannelFactory


def make_client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def make_admin():
    return UserFactory(role=User.Role.SUPER_ADMIN)


def make_channel_with_owner():
    owner = UserFactory(role=User.Role.DOCTOR)
    patient = PatientFactory()
    channel = ChannelFactory(owner=owner, patient=patient)
    ChannelMembership.objects.create(
        channel=channel, user=owner,
        role=ChannelMembership.Role.OWNER, granted_by=owner,
    )
    return owner, channel


# ============================================================
# Channel chat
# ============================================================

@pytest.mark.django_db
class TestChannelChat:

    def setup_method(self):
        self.owner, self.channel = make_channel_with_owner()
        self.url = f'/api/v1/channels/{self.channel.id}/messages/'
        self.client = make_client(self.owner)

    def test_send_and_list_messages(self):
        resp = self.client.post(self.url, {'body': 'مرحبا فريق الطب'}, format='json')
        assert resp.status_code == 201
        assert resp.data['body'] == 'مرحبا فريق الطب'
        assert resp.data['sender_name'] == self.owner.full_name

        resp = self.client.get(self.url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_empty_message_rejected(self):
        resp = self.client.post(self.url, {'body': '   '}, format='json')
        assert resp.status_code == 400

    def test_non_member_cannot_send(self):
        outsider = UserFactory(role=User.Role.NURSE)
        resp = make_client(outsider).post(
            self.url, {'body': 'رسالة'}, format='json'
        )
        # 404 (hidden via scoped queryset) or 403 (explicit denial)
        assert resp.status_code in (403, 404)

    def test_message_audited(self):
        self.client.post(self.url, {'body': 'رسالة مدققة'}, format='json')
        assert AuditLog.objects.filter(event_type='CHANNEL_MESSAGE_SENT').exists()


# ============================================================
# Global search
# ============================================================

@pytest.mark.django_db
class TestGlobalSearch:

    def test_search_requires_min_length(self):
        resp = make_client(make_admin()).get('/api/v1/auth/search/?q=a')
        assert resp.status_code == 200
        assert resp.data['total'] == 0

    def test_search_finds_channel(self):
        admin = make_admin()
        owner, channel = make_channel_with_owner()
        q = channel.name.split(' ')[1][:6]
        resp = make_client(admin).get(f'/api/v1/auth/search/?q={q}')
        assert resp.status_code == 200
        assert resp.data['total'] >= 1
        assert any(c['id'] == str(channel.id) for c in resp.data['channels'])

    def test_search_scoped_for_non_admin(self):
        owner, channel = make_channel_with_owner()
        q = channel.name.split(' ')[1][:6]
        # owner should find it; a stranger should not
        resp = make_client(owner).get(f'/api/v1/auth/search/?q={q}')
        assert len(resp.data['channels']) >= 1
        stranger = UserFactory(role=User.Role.NURSE)
        resp2 = make_client(stranger).get(f'/api/v1/auth/search/?q={q}')
        assert len(resp2.data['channels']) == 0


# ============================================================
# Two-factor authentication
# ============================================================

def _setup_mfa(user) -> str:
    import pyotp
    from apps.security.crypto import encrypt_field
    secret = pyotp.random_base32()
    user.mfa_secret = encrypt_field(secret)
    user.save(update_fields=['mfa_secret'])
    return secret


@pytest.mark.django_db
class TestTwoFactor:

    def test_setup_returns_qr(self):
        resp = make_client(make_admin()).post('/api/v1/auth/2fa/setup/')
        assert resp.status_code == 200
        assert resp.data['qr_image'].startswith('data:image/png')
        assert resp.data['otpauth_url'].startswith('otpauth://totp/SecureMed')

    def test_enable_then_login_requires_2fa(self):
        import pyotp
        user = UserFactory(role=User.Role.DOCTOR)
        user.set_password('Passw0rd!Secure')
        user.save(update_fields=['password'])
        secret = _setup_mfa(user)
        client = make_client(user)

        code = pyotp.TOTP(secret).now()
        resp = client.post('/api/v1/auth/2fa/verify/', {'code': code}, format='json')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.mfa_enabled is True

        anon = APIClient()
        resp = anon.post('/api/v1/auth/login/', {
            'email': user.email, 'password': 'Passw0rd!Secure',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data.get('requires_2fa') is True
        assert 'mfa_token' in resp.data
        assert 'tokens' not in resp.data

    def test_mfa_login_success_and_wrong_code(self):
        import pyotp
        user = UserFactory(role=User.Role.DOCTOR)
        user.set_password('Passw0rd!Secure')
        user.save(update_fields=['password'])
        secret = _setup_mfa(user)
        client = make_client(user)
        client.post('/api/v1/auth/2fa/verify/',
                    {'code': pyotp.TOTP(secret).now()}, format='json')

        anon = APIClient()
        challenge = anon.post('/api/v1/auth/login/', {
            'email': user.email, 'password': 'Passw0rd!Secure',
        }, format='json').data

        # wrong code
        resp = anon.post('/api/v1/auth/2fa/login/', {
            'mfa_token': challenge['mfa_token'], 'code': '000000',
        }, format='json')
        assert resp.status_code == 400

        # right code
        resp = anon.post('/api/v1/auth/2fa/login/', {
            'mfa_token': challenge['mfa_token'],
            'code': pyotp.TOTP(secret).now(),
        }, format='json')
        assert resp.status_code == 200
        assert 'tokens' in resp.data

    def test_disable_mfa(self):
        import pyotp
        user = UserFactory(role=User.Role.DOCTOR)
        secret = _setup_mfa(user)
        client = make_client(user)
        client.post('/api/v1/auth/2fa/verify/',
                    {'code': pyotp.TOTP(secret).now()}, format='json')

        resp = client.post('/api/v1/auth/2fa/disable/',
                           {'code': pyotp.TOTP(secret).now()}, format='json')
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.mfa_enabled is False


# ============================================================
# Biometric device management
# ============================================================

@pytest.mark.django_db
class TestBiometricDevices:

    def test_list_and_delete_device(self):
        user = UserFactory(role=User.Role.DOCTOR)
        profile = BiometricProfile.objects.create(
            user=user, device_id='dev-1', device_name='هاتف أحمد',
            platform='ANDROID', biometric_hash='x', salt='s',
        )
        client = make_client(user)

        resp = client.get('/api/v1/auth/biometric-profiles/')
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data['results']
        assert any(d['device_id'] == 'dev-1' for d in items)

        resp = client.delete(f'/api/v1/auth/biometric-profiles/{profile.id}/remove/')
        assert resp.status_code == 200
        assert not BiometricProfile.objects.filter(id=profile.id).exists()

    def test_user_cannot_delete_others_device(self):
        user_a = UserFactory(role=User.Role.DOCTOR)
        user_b = UserFactory(role=User.Role.NURSE)
        profile = BiometricProfile.objects.create(
            user=user_b, device_id='dev-b', platform='IOS',
            biometric_hash='x', salt='s',
        )
        resp = make_client(user_a).delete(
            f'/api/v1/auth/biometric-profiles/{profile.id}/remove/'
        )
        assert resp.status_code in (403, 404)


# ============================================================
# Patient full profile
# ============================================================

@pytest.mark.django_db
class TestPatientProfile:

    def test_profile_aggregates_data(self):
        admin = make_admin()
        owner, channel = make_channel_with_owner()
        patient = channel.patient
        resp = make_client(admin).get(f'/api/v1/patients/{patient.id}/profile/')
        assert resp.status_code == 200
        assert resp.data['patient']['id'] == str(patient.id)
        assert 'records' in resp.data
        assert 'channels' in resp.data
        assert 'stats' in resp.data

    def test_profile_denied_for_stranger(self):
        owner, channel = make_channel_with_owner()
        stranger = UserFactory(role=User.Role.NURSE)
        resp = make_client(stranger).get(
            f'/api/v1/patients/{channel.patient.id}/profile/'
        )
        assert resp.status_code == 403


# ============================================================
# Reports
# ============================================================

@pytest.mark.django_db
class TestReports:

    def test_channel_pdf_report(self):
        owner, channel = make_channel_with_owner()
        resp = make_client(owner).get(
            f'/api/v1/reports/channel/{channel.id}/pdf/'
        )
        assert resp.status_code == 200
        assert resp['Content-Type'] == 'application/pdf'
        assert resp.content[:5] == b'%PDF-'

    def test_channel_pdf_denied_for_stranger(self):
        owner, channel = make_channel_with_owner()
        stranger = UserFactory(role=User.Role.NURSE)
        resp = make_client(stranger).get(
            f'/api/v1/reports/channel/{channel.id}/pdf/'
        )
        assert resp.status_code == 403

    def test_audit_excel_report(self):
        admin = make_admin()
        resp = make_client(admin).get('/api/v1/reports/audit/excel/')
        assert resp.status_code == 200
        assert 'spreadsheetml' in resp['Content-Type']
        assert resp.content[:2] == b'PK'  # xlsx zip magic

    def test_monthly_pdf_report(self):
        admin = make_admin()
        resp = make_client(admin).get('/api/v1/reports/monthly/pdf/')
        assert resp.status_code == 200
        assert resp.content[:5] == b'%PDF-'

    def test_reports_require_auth(self):
        client = APIClient()
        assert client.get('/api/v1/reports/audit/excel/').status_code == 401
        assert client.get('/api/v1/reports/monthly/pdf/').status_code == 401
