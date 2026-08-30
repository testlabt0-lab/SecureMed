"""
Tests for the Backups (النسخ الاحتياطي) app.

Dev requirement: «تتضمن آلية للنسخ الاحتياطي»
"""
import io
import json
import os
import zipfile

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.backups.models import BackupRecord
from apps.backups.services import create_backup, restore_backup, verify_backup
from apps.patients.models import Patient
from tests.factories import AdminUserFactory, PatientFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestBackupService:
    def test_create_backup_creates_zip_and_record(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(3)
        PatientFactory.create_batch(2)

        record = create_backup()
        assert os.path.exists(record.filepath)
        assert record.filename.startswith('securemed_backup_')
        assert record.filename.endswith('.zip')
        assert record.size_bytes > 0
        assert len(record.checksum) == 64
        assert record.row_counts.get('accounts.User', 0) >= 3

        with zipfile.ZipFile(record.filepath) as zf:
            names = zf.namelist()
            assert 'db.json' in names
            assert 'manifest.json' in names
            data = json.loads(zf.read('db.json').decode('utf-8'))
            labels = {obj['model'] for obj in data}
            assert 'accounts.user' in labels
            assert 'patients.patient' in labels
            # transient tables are excluded
            assert 'sessions.session' not in labels

    def test_verify_backup_detects_tampering(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup()
        manifest = verify_backup(record.filepath)
        assert manifest['checksum_sha256'] == record.checksum

        # Tamper with the archive → verification must fail
        with zipfile.ZipFile(record.filepath) as zf:
            db_json = zf.read('db.json')
        tampered = tmp_path / 'tampered.zip'
        with zipfile.ZipFile(tampered, 'w') as zf:
            zf.writestr('db.json', db_json + b'[]')
            zf.writestr('manifest.json', '{"checksum_sha256": "%s"}' % ('0' * 64))
        with pytest.raises(ValueError):
            verify_backup(str(tampered))

    def test_retention_keeps_newest_n(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        settings.BACKUP_KEEP_COUNT = 3
        for _ in range(5):
            create_backup()
        assert BackupRecord.objects.count() == 3
        files = list(tmp_path.joinpath('backups').glob('*.zip'))
        assert len(files) == 3

    def test_restore_roundtrip(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        patient = PatientFactory(full_name='مريض النسخ')
        record = create_backup()

        # Delete everything, then restore
        User.objects.all().delete()
        Patient.objects.all().delete()
        assert User.objects.count() == 0

        result = restore_backup(record.filepath, force=True)
        assert result['restored'] is True
        assert User.objects.count() >= 2
        assert Patient.objects.filter(id=patient.id).exists()


class TestBackupCommands:
    def test_create_backup_command(self, tmp_path, settings, capsys):
        settings.BACKUP_DIR = tmp_path / 'backups'
        call_command('create_backup', '--note', 'اختبار')
        out = capsys.readouterr().out
        assert 'تم إنشاء النسخة الاحتياطية' in out
        assert BackupRecord.objects.count() == 1

    def test_restore_backup_plan_mode(self, tmp_path, settings, capsys):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup()
        # Without --force: verify only (data untouched)
        call_command('restore_backup', record.filepath)
        out = capsys.readouterr().out
        assert 'الأرشيف سليم' in out


class TestBackupAPI:
    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.client.force_authenticate(user=self.admin)

    def test_backup_endpoints_admin_only(self):
        # Anonymous → 401
        client = APIClient()
        assert client.get('/api/v1/backups/').status_code == 401
        # Regular user → 403
        client.force_authenticate(user=UserFactory())
        assert client.get('/api/v1/backups/').status_code == 403

    def test_create_and_download_backup_via_api(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        res = self.client.post(
            '/api/v1/backups/create_backup_action/',
            {'note': 'نسخة من الواجهة'}, format='json',
        )
        assert res.status_code == 201
        backup_id = res.data['id']

        # List shows it
        res = self.client.get('/api/v1/backups/')
        assert res.status_code == 200
        assert len(res.data['results']) == 1

        # Download
        res = self.client.get(f'/api/v1/backups/{backup_id}/download/')
        assert res.status_code == 200
        content = b''.join(res.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            assert 'db.json' in zf.namelist()

        # Verify endpoint
        res = self.client.get(f'/api/v1/backups/{backup_id}/verify/')
        assert res.status_code == 200
        assert res.data['valid'] is True

    def test_delete_backup(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup(created_by=self.admin)
        path = record.filepath
        res = self.client.delete(f'/api/v1/backups/{record.id}/')
        assert res.status_code == 204
        assert not os.path.exists(path)
        assert BackupRecord.objects.count() == 0
