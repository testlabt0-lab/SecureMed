"""
Tests for Phase 5 features:
- AI clinical case summary (with mocked AI microservice)
- Email service (filebased backend) + test_email endpoint
- Monthly report email endpoint (admin/auditor only)
- Scheduled reports management command
- Notification email real delivery
"""
import os
import shutil
from io import BytesIO
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.channels.models import Channel, ChannelMembership
from apps.notifications.models import Notification
from apps.patients.models import MedicalRecord
from tests.factories import UserFactory, PatientFactory, ChannelFactory

from tests.test_phase4_features import make_client, make_admin, make_channel_with_owner


AI_SUMMARY_FIXTURE = {
    'summary': 'ملخص الحالة السريرية\n**نظرة عامة**: مريض ذكر.\n- نقطة انتباه',
    'generated_at': '2026-08-31T10:00:00Z',
}


# ============================================================
# AI clinical summary
# ============================================================

@pytest.mark.django_db
class TestAISummary:

    def setup_method(self):
        self.owner, self.channel = make_channel_with_owner()
        self.patient = self.channel.patient
        MedicalRecord.objects.create(
            channel=self.channel, created_by=self.owner,
            record_type=MedicalRecord.RecordType.DIAGNOSIS,
            title='تشخيص أولي', content='ارتفاع ضغط الدم', is_critical=False,
        )

    def _url(self):
        return f'/api/v1/patients/{self.patient.id}/ai-summary/'

    @mock.patch('urllib.request.urlopen')
    def test_summary_success(self, mocked_urlopen):
        import json as _json
        resp_obj = mock.MagicMock()
        resp_obj.read.return_value = _json.dumps(AI_SUMMARY_FIXTURE).encode()
        resp_obj.__enter__.return_value = resp_obj
        mocked_urlopen.return_value = resp_obj

        resp = make_client(self.owner).post(self._url(), format='json')
        assert resp.status_code == 200
        assert 'ملخص الحالة' in resp.data['summary']
        assert resp.data['records_used'] >= 1
        assert AuditLog.objects.filter(event_type='AI_SUMMARY_GENERATED').exists()

    @mock.patch('urllib.request.urlopen', side_effect=OSError('service down'))
    def test_summary_service_down_returns_503(self, _mocked):
        resp = make_client(self.owner).post(self._url(), format='json')
        assert resp.status_code == 503
        assert AuditLog.objects.filter(event_type='AI_SUMMARY_FAILED').exists()

    def test_summary_requires_auth(self):
        assert APIClient().post(self._url(), format='json').status_code == 401

    def test_non_member_forbidden(self):
        outsider = UserFactory(role=User.Role.NURSE)
        resp = make_client(outsider).post(self._url(), format='json')
        assert resp.status_code == 403


# ============================================================
# Email service
# ============================================================

@pytest.mark.django_db
class TestEmailService:

    def test_send_securemed_email_writes_message(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        from utils.email_service import send_securemed_email
        ok = send_securemed_email(
            'doctor@securemed.app',
            'SecureMed — اختبار',
            'عنوان الرسالة',
            '<p>مرحباً <b>بالعالم</b></p>',
        )
        assert ok is True
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        assert msg.to == ['doctor@securemed.app']
        # branded Arabic RTL template present
        html = msg.alternatives[0][0]
        assert 'dir="rtl"' in html and 'SecureMed' in html

    def test_invalid_recipient_returns_false(self):
        from utils.email_service import send_securemed_email
        assert send_securemed_email('', 's', 't', '<p/>') is False

    @pytest.mark.django_db
    def test_notification_email_actually_sent(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = UserFactory(email='doctor@securemed.app')
        notif = Notification.objects.create(
            recipient=user,
            notification_type=Notification.Type.SECURITY_ALERT,
            priority=Notification.Priority.HIGH,
            title='تنبيه أمني اختبار',
            message='تم رصد محاولة دخول مشبوهة',
        )
        from utils.email_service import send_notification_email
        assert send_notification_email(user, notif) is True
        assert len(mail.outbox) == 1
        assert 'تنبيه أمني اختبار' in mail.outbox[0].subject

    def test_test_email_endpoint(self, settings):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        user = UserFactory(email='nurse@securemed.app')
        resp = make_client(user).post('/api/v1/notifications/test_email/', format='json')
        assert resp.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['nurse@securemed.app']
        assert AuditLog.objects.filter(event_type='TEST_EMAIL_SENT').exists()

    def test_test_email_requires_auth(self):
        assert APIClient().post(
            '/api/v1/notifications/test_email/', format='json'
        ).status_code == 401


# ============================================================
# Monthly report email endpoint + scheduled command
# ============================================================

@pytest.mark.django_db
class TestMonthlyReportEmail:

    @mock.patch('apps.reports.monthly.send_report_email', return_value=True)
    def test_admin_can_email_monthly_report(self, mocked_send):
        admin = make_admin()
        resp = make_client(admin).post('/api/v1/reports/monthly/email/', format='json')
        assert resp.status_code == 200
        assert resp.data['filename'].startswith('SecureMed_Monthly_')
        assert len(resp.data['sent_to']) >= 1
        assert mocked_send.called
        assert AuditLog.objects.filter(event_type='MONTHLY_REPORT_EMAILED').exists()

    @mock.patch('apps.reports.monthly.send_report_email', return_value=True)
    def test_auditor_can_email_monthly_report(self, _mocked):
        auditor = UserFactory(role=User.Role.AUDITOR)
        resp = make_client(auditor).post('/api/v1/reports/monthly/email/', format='json')
        assert resp.status_code == 200

    def test_doctor_cannot_email_monthly_report(self):
        doctor = UserFactory(role=User.Role.DOCTOR)
        resp = make_client(doctor).post('/api/v1/reports/monthly/email/', format='json')
        assert resp.status_code == 403

    def test_email_monthly_requires_auth(self):
        assert APIClient().post('/api/v1/reports/monthly/email/', format='json').status_code == 401


@pytest.mark.django_db
class TestScheduledReportsCommand:

    @mock.patch('apps.reports.monthly.send_report_email', return_value=True)
    def test_monthly_command_sends_to_admins(self, mocked_send, capsys):
        make_admin()  # recipient
        UserFactory(role=User.Role.AUDITOR)
        call_command('send_scheduled_reports', '--type', 'monthly')
        assert mocked_send.called
        assert mocked_send.call_count >= 2
        out = capsys.readouterr().out
        assert '[monthly' in out

    @mock.patch(
        'apps.reports.management.commands.send_scheduled_reports.send_securemed_email',
        return_value=True,
    )
    def test_weekly_command_sends_summary(self, mocked_send, capsys):
        make_admin()
        call_command('send_scheduled_reports', '--type', 'weekly')
        assert mocked_send.called
        out = capsys.readouterr().out
        assert '[weekly]' in out

    @mock.patch('apps.reports.monthly.send_report_email', return_value=False)
    def test_failed_send_recorded(self, mocked_send, capsys):
        make_admin()
        call_command('send_scheduled_reports', '--type', 'monthly')
        out = capsys.readouterr().out
        assert 'فشل:' in out
